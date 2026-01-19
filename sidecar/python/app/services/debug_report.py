# File: python/app/services/debug_report.py
# Project: Tip Desktop Assistant
# Description: Collects session artifacts and GUI agent outputs into local debug report bundles.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import base64
import pickle
import platform
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from ..core.config import DEBUG_REPORT_DIR
from ..schemas.debug import (
    DebugGuiAgentRef,
    DebugLogAttachment,
    DebugReportRequest,
    DebugReportResponse,
)
from ..services.chat_session import ChatSessionManager
from ..services.gui_agent import GuiAgentRun, GuiAgentService
from ..services.settings_manager import SettingsManager
import structlog

logger = structlog.get_logger(__name__)


def _normalize_label(value: str | None) -> str | None:
    # Sanitize user-entered labels so file names remain predictable and safe.
    if not value:
        return None
    filtered = ''.join(ch for ch in value.lower() if ch.isalnum() or ch in ('-', '_'))
    return filtered or None


class DebugReportService:
    def __init__(
        self,
        settings_manager: SettingsManager,
        chat_manager: ChatSessionManager,
        gui_agent_service: GuiAgentService | None = None,
    ) -> None:
        # Keep shared service handles for capturing runtime state and optional uploads.
        self._settings_manager = settings_manager
        self._chat_manager = chat_manager
        self._gui_agent = gui_agent_service
        # Ensure the local report directory exists before persisting artifacts.
        DEBUG_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    async def create_report(self, payload: DebugReportRequest) -> DebugReportResponse:
        # A debug报告必须绑定到聊天会话，便于重现上下文与意图。
        session = self._chat_manager.get_session(payload.session_id)
        if not session:
            raise ValueError('会话不存在或已过期')
        report_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        # 捕获当前设置，保证排查时能对照用户的运行环境。
        settings = self._settings_manager.get_settings()
        label = _normalize_label(payload.label)
        report = {
            'report_id': report_id,
            'created_at': created_at,
            'issue': payload.issue,
            'label': label,
            'session': {
                'session_id': session.session_id,
                'intent': session.intent,
                'intent_candidates': session.intent_candidates,
                'selected_intent': payload.selected_intent or session.intent,
                'draft_intent': payload.draft_intent,
                'messages': [message.model_dump() for message in session.messages],
                'snapshot_image': session.snapshot_image,
                'selection': session.selection.model_dump(by_alias=True) if session.selection else None,
                'selection_text': session.selection_text,
                'intent_prompt': asdict(session.intent_prompt) if session.intent_prompt else None,
                'chat_prompts': [asdict(record) for record in session.chat_prompts],
            },
            'capture': payload.capture.model_dump(by_alias=True) if payload.capture else None,
            'selection_preview': (
                payload.selection_preview.model_dump(by_alias=True)
                if payload.selection_preview
                else None
            ),
            'viewport': payload.viewport.model_dump(by_alias=True) if payload.viewport else None,
            'text_selection': payload.text_selection.model_dump(by_alias=True) if payload.text_selection else None,
            'logs': [log.model_dump(by_alias=True) for log in payload.logs] if payload.logs else None,
            'settings': settings.model_dump(),
            'environment': {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
            },
        }
        # 当 GUI Agent 参与执行时，附带它的产物与执行日志。
        gui_agent_bundle = self._build_gui_agent_bundle(payload.gui_agent)
        if gui_agent_bundle:
            report['gui_agent'] = gui_agent_bundle
        suffix = f'-{label}' if label else ''
        file_path = DEBUG_REPORT_DIR / f'debug-report-{report_id}{suffix}.pkl'
        # 使用 pickle 保留嵌套结构，后续调试读取更方便。
        with file_path.open('wb') as handle:
            pickle.dump(report, handle)
        return DebugReportResponse(
            path=str(file_path),
            report_id=report_id,
            created_at=created_at,
        )

    def _build_gui_agent_bundle(self, ref: Optional[DebugGuiAgentRef]) -> dict | None:
        # 汇总 GUI Agent 的运行结果、截图与日志，供问题复现使用。
        if not ref:
            return None
        if not self._gui_agent:
            logger.warning('debug_report.gui_agent_unavailable', run_id=ref.run_id)
            return {'run_id': ref.run_id, 'error': 'service_unavailable'}
        run = self._gui_agent.get_run(ref.run_id)
        if not run:
            logger.warning('debug_report.gui_agent_missing', run_id=ref.run_id)
            return {'run_id': ref.run_id, 'error': 'not_found'}

        result_dir = self._resolve_result_dir(run)
        attachments: List[DebugLogAttachment] = []
        screenshot_total = 0
        notes: List[str] = []

        if result_dir and result_dir.exists():
            # 截图优先加入，让报告先呈现视觉线索。
            screenshot_attachments, screenshot_total = self._collect_screenshots(result_dir)
            attachments.extend(screenshot_attachments)
            # 追加常见的运行日志与配置，便于重放 Agent 执行。
            attachments.extend(
                self._collect_named_files(
                    result_dir,
                    ('runtime.log', 'traj.jsonl', 'args.json', 'task_config.json', 'result.txt'),
                )
            )
        else:
            # 结果目录缺失时记录提示，避免默默丢失信息。
            notes.append('结果目录不可用，无法读取截图/日志')

        # 仅保留最近的历史片段，避免报告体积过大。
        bundle = {
            'run_id': run.run_id,
            'session_id': run.session_id,
            'instruction': ref.instruction or run.instruction,
            'task_id': run.task_id,
            'status': run.status,
            'result_dir': str(result_dir) if result_dir else None,
            'created_at': run.created_at,
            'completed_at': run.completed_at,
            'attachments': [item.model_dump(by_alias=True) for item in attachments] if attachments else None,
            'screenshot_total': screenshot_total,
            'history_tail': run.history[-50:] if run.history else None,
            'notes': notes or None,
        }
        return bundle

    def _resolve_result_dir(self, run: GuiAgentRun) -> Path | None:
        # 优先使用显式路径，其次从事件轨迹中恢复潜在的产物目录。
        if run.result_dir:
            return Path(run.result_dir)
        for event in run.history:
            candidate = event.get('result_dir') or event.get('resultDir')
            if candidate:
                return Path(candidate)
            assets = event.get('assets') or []
            for asset in assets:
                path_value = asset.get('path')
                if path_value:
                    try:
                        return Path(path_value).resolve().parent
                    except Exception:  # noqa: BLE001
                        continue
        return None

    def _collect_screenshots(self, result_dir: Path) -> tuple[List[DebugLogAttachment], int]:
        # 收集截图并按文件名排序，保持动作时间线一致。
        image_paths = sorted(
            [
                path
                for path in result_dir.iterdir()
                if path.is_file() and path.suffix.lower() in {'.png', '.jpg', '.jpeg'}
            ],
            key=lambda p: p.name,
        )
        total = len(image_paths)
        if total == 0:
            return [], 0
        selected = image_paths
        attachments = [
            self._read_file_attachment(
                path,
                encoding='base64',
                mime_type='image/png' if path.suffix.lower() == '.png' else 'image/jpeg',
            )
            for path in selected
        ]
        return attachments, total

    def _collect_named_files(self, result_dir: Path, names: Iterable[str]) -> List[DebugLogAttachment]:
        # 只采集关键文本/日志文件，避免一次性打包整个目录。
        attachments: List[DebugLogAttachment] = []
        for name in names:
            path = result_dir / name
            if not path.exists() or not path.is_file():
                continue
            encoding = 'utf-8'
            mime_type = 'text/plain'
            if path.suffix.lower() == '.json':
                mime_type = 'application/json'
            attachments.append(self._read_file_attachment(path, encoding=encoding, mime_type=mime_type))
        return attachments

    def _read_file_attachment(
        self,
        path: Path,
        *,
        encoding: str,
        mime_type: str | None = None,
        max_bytes: int = 600 * 1024,
    ) -> DebugLogAttachment:
        # 截断过大的文件，仅保留尾部内容以便快速定位报错。
        data = path.read_bytes()
        truncated = False
        if len(data) > max_bytes:
            truncated = True
            data = data[-max_bytes:]
        if encoding == 'base64':
            content = base64.b64encode(data).decode('ascii')
        else:
            content = data.decode('utf-8', errors='replace')
        return DebugLogAttachment(
            name=path.name,
            path=str(path),
            truncated=truncated,
            total_bytes=path.stat().st_size,
            retained_bytes=len(data),
            content=content,
            encoding=encoding,
            mime_type=mime_type,
        )
