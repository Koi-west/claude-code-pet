# File: python/app/core/deps.py
# Project: Tip Desktop Assistant
# Description: FastAPI dependency providers exposing shared services from application state.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import Depends, Request, WebSocket

from ..services.chat_session import ChatSessionManager
from ..services.intent_builder import IntentService
from ..services.llm import LLMService
from ..services.settings_manager import SettingsManager
from ..services.debug_report import DebugReportService
from ..services.text_selection import TextSelectionService
from ..services.gui_agent import GuiAgentService
from ..services.youtu_agent_service import YoutuAgentService
from ..gui_agent.skills import SkillRepository


def get_settings_manager(request: Request) -> SettingsManager:
    return request.app.state.settings_manager


def get_llm_service(request: Request) -> LLMService:
    return request.app.state.llm_service


def get_intent_service(request: Request) -> IntentService:
    return request.app.state.intent_service


def get_chat_manager(request: Request) -> ChatSessionManager:
    return request.app.state.chat_manager


def get_chat_manager_ws(websocket: WebSocket) -> ChatSessionManager:
    return websocket.app.state.chat_manager


def get_debug_reporter(request: Request) -> DebugReportService:
    return request.app.state.debug_reporter


def get_text_selection_service(request: Request) -> TextSelectionService:
    return request.app.state.text_selection_service


def get_gui_agent_service(request: Request) -> GuiAgentService:
    return request.app.state.gui_agent_service


def get_gui_agent_service_ws(websocket: WebSocket) -> GuiAgentService:
    return websocket.app.state.gui_agent_service


def get_skill_repository(request: Request) -> SkillRepository:
    return request.app.state.skill_repository


def get_youtu_agent_service(request: Request) -> YoutuAgentService:
    return request.app.state.youtu_agent_service


def get_youtu_agent_service_ws(websocket: WebSocket) -> YoutuAgentService:
    return websocket.app.state.youtu_agent_service
