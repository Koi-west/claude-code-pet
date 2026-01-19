# File: python/app/services/youtu_agent_service.py
# Project: Tip Desktop Assistant
# Description: Lifecycle manager for Youtu-Agent using Hydra configs and Tip settings to run or stream sessions.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

import os
from pathlib import Path

import structlog

from ..core.config import CONFIG_DIR
from ..core.settings import LLMProfile, Settings
from .settings_manager import SettingsManager
from .youtu_adapter import build_youtu_model

logger = structlog.get_logger(__name__)

os.environ.setdefault("UTU_LLM_TYPE", "chat.completions")
os.environ.setdefault("UTU_LLM_MODEL", "tip-placeholder")

try:  # pragma: no cover - optional dependency
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf
    from agents import StreamEvent
    from utu.agents import SimpleAgent
    from utu.agents.common import TaskRecorder
    from utu.config import ConfigLoader
    from utu.config.agent_config import AgentConfig
except ImportError:  # pragma: no cover - handled at runtime
    StreamEvent = Any  # type: ignore
    TaskRecorder = Any  # type: ignore
    SimpleAgent = None  # type: ignore
    ConfigLoader = None  # type: ignore
    AgentConfig = None  # type: ignore
    compose = None  # type: ignore
    initialize_config_dir = None  # type: ignore
    OmegaConf = None  # type: ignore

__all__ = ["YoutuAgentService"]

@dataclass
class _SessionState:
    # Each session keeps a built agent, its config signature, and a lock to serialize calls.
    agent: SimpleAgent
    signature: str
    lock: asyncio.Lock


class YoutuAgentService:
    """Manage a singleton SimpleAgent that reuses our Tip settings."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        *,
        agent_config_name: str = "agents/examples/file_manager",
        config_dir: Optional[Path] = None,
        tip_auth=None,
    ) -> None:
        # Settings manager is long-lived; we reuse it to detect config changes.
        self._settings_manager = settings_manager
        self._agent_config_name = agent_config_name
        self._default_agent_config_name = agent_config_name
        self._config_cache: Optional[Any] = None
        self._config_cache_name: Optional[str] = None
        self._build_lock = asyncio.Lock()
        self._sessions: dict[str, _SessionState] = {}
        self._config_dir = config_dir or self._detect_config_dir()
        self._tip_auth = tip_auth

    async def run(self, prompt: str, *, save_history: bool = True, session_id: Optional[str] = None) -> tuple[str, str]:
        """Run the agent once and return (output, session_id)."""
        # When no session_id is provided we create a fresh one-off agent session.
        session = session_id or self._generate_session_id()
        agent, lock = await self._ensure_agent(session)
        logger.info(
            "youtu_agent.run.start",
            session=session,
            save_history=save_history,
            prompt_len=len(prompt),
        )
        async with lock:
            recorder: TaskRecorder = await agent.run(prompt, save=save_history, log_to_db=False)
            output = recorder.final_output or ""
            logger.info("youtu_agent.run.done", session=session, output_len=len(output))
            return output, session

    async def stream(
        self, prompt: str, *, save_history: bool = True, session_id: Optional[str] = None
    ) -> tuple[str, AsyncGenerator[Any, None]]:
        """Stream events for a given prompt; emits a final output dict at the end."""
        # Stream variant yields incremental events and a final output marker.
        session = session_id or self._generate_session_id()
        agent, lock = await self._ensure_agent(session)

        async def _gen():
            async with lock:
                logger.info(
                    "youtu_agent.stream.start",
                    session=session,
                    save_history=save_history,
                    prompt_len=len(prompt),
                )
                # run_streamed returns a recorder that yields partial events without blocking.
                recorder: TaskRecorder = agent.run_streamed(prompt, save=save_history, log_to_db=False)
                async for event in recorder.stream_events():
                    yield event
                yield {"event": "final_output", "output": recorder.final_output or ""}
                logger.info(
                    "youtu_agent.stream.done",
                    session=session,
                    output_len=len(recorder.final_output or ""),
                )

        return session, _gen()

    async def close(self) -> None:
        # Clean up all tracked sessions; useful for app shutdown or reload.
        async with self._build_lock:
            await asyncio.gather(*(state.agent.cleanup() for state in self._sessions.values() if state.agent))
            self._sessions.clear()
            self._config_cache = None
            logger.info("youtu_agent.sessions.cleared")

    async def reload(self) -> str:
        """Force rebuilding all agents with current settings."""
        logger.info(
            "youtu_agent.reload_start",
            config_dir=str(self._config_dir) if self._config_dir else None,
            default_config=self._default_agent_config_name,
        )
        await self.close()
        # Force default session id so caches repopulate before user interacts again.
        agent = await self._ensure_agent(self._generate_session_id(force_default=True))
        logger.info(
            "youtu_agent.reload_success",
            active_config=self._config_cache_name or self._default_agent_config_name,
            provider=self.current_provider(),
            agent_built=bool(agent),
        )
        # Return the active config name so UI callers can display it.
        return self._config_cache_name or self._default_agent_config_name

    async def reset_session(self, session_id: str) -> None:
        # Allow user to drop a single session while keeping the rest intact.
        state = self._sessions.pop(session_id, None)
        if state and state.agent:
            await state.agent.cleanup()
        logger.info("youtu_agent.session.reset", session=session_id, existed=bool(state))

    async def _ensure_agent(self, session_id: str) -> tuple[SimpleAgent, asyncio.Lock]:
        if SimpleAgent is None or ConfigLoader is None:
            raise RuntimeError(
                "Youtu-Agent 依赖未安装。请在当前虚拟环境中安装 `youtu-agent` 或 "
                "`openai-agents` 相关依赖后再启用该功能。"
            )

        # Load current settings and guard against feature flag disablement.
        settings = self._settings_manager.get_settings()
        profile = settings.get_active_llm_profile()
        features = getattr(settings, "features", None)
        enabled = bool(getattr(features, "youtuAgentEnabled", False)) if features else False
        if not enabled:
            raise RuntimeError("Youtu-Agent 功能已禁用，请在设置中开启。")
        # Prefer user-selected agent config, otherwise fall back to default shipped sample.
        config_name = (
            getattr(features, "youtuAgentConfig", None) or self._default_agent_config_name
        ).strip() or self._default_agent_config_name
        # Signature ties a session to LLM config; rebuild when user switches provider/model.
        signature = self._signature(profile, settings)
        existing = self._sessions.get(session_id)
        if existing and existing.signature == signature:
            logger.info("youtu_agent.session.reuse", session=session_id, config=config_name)
            return existing.agent, existing.lock

        async with self._build_lock:
            existing = self._sessions.get(session_id)
            if existing and existing.signature == signature:
                return existing.agent, existing.lock

            # Tear down stale agent before building a new one to avoid leaking resources.
            if existing and existing.agent:
                await existing.agent.cleanup()
                self._sessions.pop(session_id, None)

            if not self._config_cache or self._config_cache_name != config_name:
                # Cache Hydra-loaded configs to avoid re-reading disk on every prompt.
                logger.info(
                    "youtu_agent.load_config",
                    config_name=config_name,
                    config_dir=str(self._config_dir) if self._config_dir else None,
                )
                config = self._load_agent_config(config_name)
                self._sanitize_toolkits(config)
                self._config_cache = config
                self._config_cache_name = config_name
            else:
                config = self._config_cache
            # Build model with current settings so features like device token headers are respected.
            model, model_settings = build_youtu_model(settings, profile, tip_auth=self._tip_auth)
            # SimpleAgent build may download tools/config; keep it behind the session lock.
            agent = SimpleAgent(config=config, model=model, model_settings=model_settings)
            await agent.build()

            lock = asyncio.Lock()
            self._sessions[session_id] = _SessionState(agent=agent, signature=signature, lock=lock)
            logger.info(
                "youtu_agent.ready",
                config=config_name,
                provider=profile.provider,
                session=session_id,
            )
            return agent, lock

    def _signature(self, profile: LLMProfile, settings: Settings) -> str:
        # Serialize key LLM settings; any change forces rebuild of agent/model caches.
        # This keeps per-session caching deterministic and easy to debug.
        payload = {
            "provider": profile.provider,
            "baseUrl": profile.baseUrl,
            "model": profile.model,
            "apiModel": profile.apiModel,
            "temperature": profile.temperature,
            "maxTokens": profile.maxTokens,
            "headers": profile.headers.to_dict(),
            "stream": profile.stream,
            "youtuAgentEnabled": getattr(settings.features, "youtuAgentEnabled", False),
            "youtuAgentConfig": getattr(settings.features, "youtuAgentConfig", None),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _generate_session_id(self, *, force_default: bool = False) -> str:
        # Default session id is stable so UI reloads can reuse agent caches if desired.
        if force_default:
            return "__default__"
        return uuid.uuid4().hex

    def current_provider(self) -> str:
        try:
            return (self._settings_manager.get_settings().get_active_llm_profile().provider or "tip_cloud")
        except Exception:  # pragma: no cover
            return "unknown"
        # Default to unknown when settings cannot be read; callers treat it as informational only.

    def _detect_config_dir(self) -> Optional[Path]:
        # Config resolution order:
        # 1) Explicit env override
        # 2) Bundled configs shipped with the app
        # 3) Nearest checked-out youtu-agent configs in parent directories
        # Try env override first so developers can point to custom configs.
        candidates_checked = []
        env_config = os.getenv("YOUTU_CONFIG_DIR")
        if env_config:
            path = Path(env_config).expanduser()
            if path.exists():
                resolved = path.resolve()
                logger.info("youtu_agent.config_dir.env", path=str(resolved))
                return resolved

        bundled_dir = CONFIG_DIR / "youtu-agent" / "configs"
        if bundled_dir.exists():
            resolved = bundled_dir.resolve()
            logger.info("youtu_agent.config_dir.bundled", path=str(resolved))
            return resolved

        # Walk up directories to locate youtu-agent configs in developer checkouts.
        candidates = []
        path = Path(__file__).resolve()
        for _ in range(10):
            candidates.append(path.parent / "config" / "configs")
            candidates.append(path.parent / "configs")
            candidates.append(path.parent / "youtu-agent" / "configs")
            path = path.parent
        candidates.append(Path.cwd() / "youtu-agent" / "configs")

        for candidate in candidates:
            candidates_checked.append(str(candidate))
            if candidate.exists():
                resolved = candidate.resolve()
                logger.info(
                    "youtu_agent.config_dir.discovered",
                    path=str(resolved),
                    searched=candidates_checked,
                )
                return resolved
        # If nothing was found we warn but still allow callers to handle the failure later.
        logger.warning("youtu_agent.config_dir.missing", searched=candidates_checked)
        return None

    def _load_agent_config(self, config_name: Optional[str] = None):
        target_name = config_name or self._agent_config_name
        if self._config_dir and compose and initialize_config_dir and AgentConfig:
            config_root = self._config_dir
            normalized_name = target_name
            if not normalized_name.startswith("agents/"):
                normalized_name = f"agents/{normalized_name}"
            logger.info(
                "youtu_agent.hydra.compose",
                config_root=str(config_root),
                config_name=normalized_name,
            )
            try:
                # initialize_config_dir must wrap compose; errors propagate for visibility.
                with initialize_config_dir(
                    config_dir=str(config_root),
                    version_base=ConfigLoader.version_base,
                ):  # type: ignore[arg-type]
                    cfg = compose(config_name=normalized_name)
                    OmegaConf.resolve(cfg)
                data = OmegaConf.to_container(cfg, resolve=True)
                return AgentConfig(**data)
            except Exception as exc:
                logger.warning(
                    "youtu_agent.hydra.compose_failed",
                    error=str(exc),
                    config_root=str(config_root),
                    config_name=normalized_name,
                    exc_info=True,
                )
                raise
        if ConfigLoader is None:
            raise RuntimeError("缺少 Youtu-Agent 配置，无法加载默认 Agent。")
        try:
            # Fallback to static loader when Hydra path is unavailable.
            return ConfigLoader.load_agent_config(target_name)
        except Exception as exc:
            logger.warning("youtu_agent.config_loader_failed", error=str(exc), config_name=target_name, exc_info=True)
            raise

    def _sanitize_toolkits(self, config: Any) -> None:
        """Normalize toolkit workspaces to writable directories."""
        try:
            toolkits = getattr(config, "toolkits", None) or {}
        except Exception:
            return
        if not isinstance(toolkits, dict):
            return
        # Iterate over toolkits to make sure they can write to a safe workspace.
        for name, toolkit in toolkits.items():
            try:
                cfg = getattr(toolkit, "config", None) or {}
                workspace_root = cfg.get("workspace_root")
                if not workspace_root:
                    continue
                # Expand to absolute path so downstream tools can write logs/artifacts reliably.
                expanded = Path(str(workspace_root)).expanduser()
                if not expanded.is_absolute():
                    expanded = (Path.home() / ".tip" / "youtu-agent" / "workspace").resolve()
                expanded.mkdir(parents=True, exist_ok=True)
                cfg["workspace_root"] = str(expanded)
                toolkit.config = cfg
                logger.info(
                    "youtu_agent.toolkit_workspace_ready",
                    toolkit=name,
                    workspace=str(expanded),
                )
            except Exception as exc:
                logger.warning(
                    "youtu_agent.toolkit_workspace_failed",
                    toolkit=name,
                    error=str(exc),
                    config_dir=str(self._config_dir) if self._config_dir else None,
                    exc_info=True,
                )
