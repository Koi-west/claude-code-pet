# File: python/app/services/gui_agent.py
# Project: Tip Desktop Assistant
# Description: Async manager for GUI Agent runs, invoking run_prompt with patched env vars and streaming events.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import threading
import structlog

from ..core.settings import LLMProfile, Settings
from ..gui_agent import build_default_args, run_prompt
from ..gui_agent.skills import SkillRepository
from .llm import tip_cloud_api_key, tip_cloud_base_url, tip_cloud_model
from .settings_manager import SettingsManager

logger = structlog.get_logger(__name__)


@dataclass
# 跟踪 GUI Agent 单次运行的状态、队列与产物目录。
class GuiAgentRun:
    run_id: str
    session_id: str
    instruction: str
    queue: asyncio.Queue[Dict[str, Any]]
    status: str = "pending"
    history: List[Dict[str, Any]] = field(default_factory=list)
    task: Optional[asyncio.Task[Any]] = None
    task_id: Optional[str] = None
    result_dir: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


@dataclass
# 对外暴露的运行句柄，供 IPC 返回。
class GuiAgentRunHandle:
    run_id: str
    session_id: str
    instruction: str
    task_id: Optional[str] = None


class GuiAgentService:
    def __init__(
        self,
        settings_manager: SettingsManager,
        *,
        history_limit: int = 200,
        retention_seconds: int = 300,
        skill_repo: Optional[SkillRepository] = None,
        tip_auth=None,
    ) -> None:
        # 管理单例 GUI Agent 运行状态与缓存，避免并发占用系统资源。
        self._settings_manager = settings_manager
        self._skill_repo = skill_repo
        self._runs: Dict[str, GuiAgentRun] = {}
        self._history_limit = history_limit
        self._retention_seconds = retention_seconds
        self._lock = asyncio.Lock()
        self._tip_auth = tip_auth

    async def start_run(self, *, session_id: str, instruction: str) -> GuiAgentRunHandle:
        # 入口：创建唯一运行实例，避免多个 GUI 任务抢占输入焦点。
        normalized = (instruction or "").strip()
        if not normalized:
            raise ValueError("Instruction is required")

        async with self._lock:
            active = self._active_run()
            if active is not None and active.status in {"pending", "running"}:
                raise RuntimeError("Another GUI agent task is already running")

            run_id = uuid.uuid4().hex
            queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
            run = GuiAgentRun(
                run_id=run_id,
                session_id=session_id,
                instruction=normalized,
                queue=queue,
            )
            self._runs[run_id] = run

            loop = asyncio.get_running_loop()
            run.status = "running"
            # 在事件循环中异步启动执行线程，结果通过队列回传。
            run.task = loop.create_task(self._execute_run(run))

        return GuiAgentRunHandle(
            run_id=run_id,
            session_id=session_id,
            instruction=normalized,
        )

    async def stream_events(self, run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(run_id)

        # 先补发历史事件，避免前端丢消息。
        for event in run.history:
            yield event

        while True:
            event = await run.queue.get()
            if event.get("__internal__") == "close":
                break
            # 队列事件按产生顺序流式返回给调用方。
            yield event

    def _active_run(self) -> Optional[GuiAgentRun]:
        # 默认仅允许单并发；若未来需要并发可调整此逻辑。
        for run in self._runs.values():
            if run.status in {"pending", "running"}:
                return run
        return None

    def has_run(self, run_id: str) -> bool:
        # 仅检查是否存在，不验证状态。
        return run_id in self._runs

    def get_run(self, run_id: str) -> Optional[GuiAgentRun]:
        # 返回内部缓存引用，调用方不应修改其字段。
        return self._runs.get(run_id)

    async def cancel_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if not run:
            return False
        if run.status in {"completed", "error", "cancelled"}:
            return False
        # 通过事件与标志通知执行线程退出。
        run.status = "cancelled"
        run.cancel_event.set()
        try:
            run.queue.put_nowait(
                {
                    "type": "status",
                    "message": "用户已请求中断",
                    "status": "cancelled",
                    "run_id": run_id,
                }
            )
        except asyncio.QueueFull:
            pass
        return True

    async def _execute_run(self, run: GuiAgentRun) -> None:
        settings = self._settings_manager.get_settings()
        profile = settings.get_active_vlm_profile()
        if profile is None:
            # 缺少视觉模型时直接返回错误事件。
            run.queue.put_nowait(
                {
                    "type": "error",
                    "message": "未设置视觉模型，请在设置中选择 VLM 后再试。",
                    "run_id": run.run_id,
                }
            )
            self._finalize_run(run.run_id)
            return
        # 结果目录按会话隔离，便于收集日志与截图。
        result_root = self._resolve_result_root(settings)
        loop = asyncio.get_running_loop()

        def log_callback(event: Dict[str, Any]) -> None:
            # 将 GUI Agent 线程内的事件转发回 asyncio 事件循环。
            loop.call_soon_threadsafe(self._handle_event, run.run_id, event)

        def worker() -> Dict[str, Any]:
            return self._invoke_agent(run.instruction, profile, result_root, log_callback, run.cancel_event)

        try:
            result = await loop.run_in_executor(None, worker)
            run.task_id = result.get("task_id")
            run.result_dir = result.get("result_dir")
        except Exception as exc:  # pragma: no cover - GUI automation side-effects
            # GUI 自动化易受环境影响，失败时仅记录警告。
            logger.warning("gui_agent.run_failed", error=str(exc))
        finally:
            self._finalize_run(run.run_id)

    def _invoke_agent(
        self,
        instruction: str,
        profile: LLMProfile,
        result_root: Path,
        log_callback,
        cancel_event: threading.Event,
    ) -> Dict[str, Any]:
        # 为 run_prompt 注入模型/鉴权环境变量，保证调用正确落在配置的后端。
        env_patch = self._build_env_patch(profile)
        args = build_default_args(
            result_dir=str(result_root),
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.maxTokens,
        )

        previous: Dict[str, Optional[str]] = {}
        for key, value in env_patch.items():
            previous[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # run_prompt 在线程中执行；取消由 cancel_event 传递。
            return run_prompt(
                instruction,
                args=args,
                result_root=str(result_root),
                log_callback=log_callback,
                cancel_event=cancel_event,
                skills_repo=self._skill_repo,
            )
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _build_env_patch(self, profile: LLMProfile) -> Dict[str, str]:
        # 按 provider 填充通用的 TIP_* 环境变量，兼容 OpenAI/Ollama。
        provider = (profile.provider or "tip_cloud").strip()
        headers = profile.headers.to_dict()
        payload: Dict[str, str] = {
            "TIP_LLM_PROVIDER": provider,
            "TIP_LLM_MODEL": profile.model,
            "TIP_LLM_TIMEOUT": str(profile.timeoutMs / 1000),
        }
        if provider == "tip_cloud":
            payload["TIP_LLM_MODEL"] = profile.model or tip_cloud_model()
            payload["TIP_LLM_BASE_URL"] = tip_cloud_base_url()
            payload["TIP_OPENAI_BASE_URL"] = tip_cloud_base_url()
            token_headers: Dict[str, str] = {}
            if self._tip_auth:
                try:
                    token_headers = self._tip_auth.auth_headers()
                except Exception as exc:  # pragma: no cover - best effort
                    # 令牌获取失败不应中断流程；回退到本地 key。
                    logger.warning("gui_agent.tip_token_failed", error=str(exc))
            token = token_headers.get("Authorization", "") or tip_cloud_api_key()
            if token.lower().startswith("bearer "):
                token = token.split(" ", 1)[1].strip()
            payload["TIP_OPENAI_API_KEY"] = token
            merged_headers = dict(headers)
            merged_headers.update({k: v for k, v in token_headers.items() if k})
            headers = merged_headers
        if profile.baseUrl:
            payload["TIP_LLM_BASE_URL"] = profile.baseUrl.rstrip("/")
        if headers:
            payload["TIP_LLM_HEADERS"] = json.dumps(headers)
        if profile.apiKey:
            payload["TIP_OPENAI_API_KEY"] = profile.apiKey
        if profile.openaiBaseUrl:
            payload["TIP_OPENAI_BASE_URL"] = profile.openaiBaseUrl.rstrip("/")
        if profile.ollamaBaseUrl:
            payload["TIP_OLLAMA_BASE_URL"] = profile.ollamaBaseUrl.rstrip("/")
        if profile.ollamaModel:
            payload["TIP_OLLAMA_MODEL"] = profile.ollamaModel
        return payload

    def _resolve_result_root(self, settings: Settings) -> Path:
        # 缓存目录按用户配置展开，避免污染代码仓库。
        base = Path(settings.paths.cacheDir).expanduser()
        target = (base / "gui-agent").resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _handle_event(self, run_id: str, event: Dict[str, Any]) -> None:
        run = self._runs.get(run_id)
        if not run:
            return
        enriched = dict(event)
        enriched.setdefault("run_id", run_id)
        if "task_id" not in enriched and run.task_id:
            enriched["task_id"] = run.task_id
        # 维护有限历史，便于新订阅者快速回放。
        run.history.append(enriched)
        if len(run.history) > self._history_limit:
            run.history.pop(0)
        if enriched.get("type") == "error":
            run.status = "error"
        elif enriched.get("type") == "complete":
            run.status = enriched.get("status", "completed")
        if not run.task_id:
            run.task_id = enriched.get("task_id")
        if not run.result_dir:
            run.result_dir = enriched.get("result_dir")
        run.queue.put_nowait(enriched)

    def _finalize_run(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if not run:
            return
        if run.status not in {"completed", "error", "cancelled"}:
            run.status = "completed"
        run.completed_at = time.time()
        # 通知事件流结束，并在一段时间后清理内存。
        run.queue.put_nowait({"__internal__": "close"})
        loop = asyncio.get_running_loop()
        # 延迟删除，允许调用方在短时间内读取历史。
        loop.call_later(self._retention_seconds, self._runs.pop, run_id, None)
