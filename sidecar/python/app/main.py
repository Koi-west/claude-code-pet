# File: python/app/main.py
# Project: Tip Desktop Assistant
# Description: FastAPI application wiring lifespan setup, middleware, and all sidecar routers.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_chat,
    routes_debug,
    routes_gui_agent,
    routes_health,
    routes_intent,
    routes_llm,
    routes_selection,
    routes_skills,
    routes_youtu_agent,
    routes_settings,
)
from .core.config import CONFIG_DIR
from .core.logging import setup_logging
from .services.settings_manager import SettingsManager
from .services.llm import LLMService
from .services.chat_session import ChatSessionManager
from .services.intent_builder import IntentService
from .services.debug_report import DebugReportService
from .services.text_selection import TextSelectionService
from .services.gui_agent import GuiAgentService
from .services.youtu_agent_service import YoutuAgentService
from .gui_agent.skills import SkillRepository
from .services.tip_cloud_auth import TipCloudAuth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化日志与各服务，生命周期结束时 FastAPI 会自动释放资源。
    setup_logging()
    settings_manager = SettingsManager()
    tip_auth = TipCloudAuth()
    # 核心服务：LLM、会话、意图、调试、选择等。
    llm_service = LLMService(settings_manager, tip_auth=tip_auth)
    chat_manager = ChatSessionManager(llm_service)
    intent_service = IntentService(llm_service, chat_manager)
    text_selection = TextSelectionService()
    skills_path = Path(__file__).resolve().parent / "gui_agent" / "skills"
    skill_repo = SkillRepository(skills_path)
    gui_agent = GuiAgentService(settings_manager, skill_repo=skill_repo, tip_auth=tip_auth)
    debug_reporter = DebugReportService(
        settings_manager,
        chat_manager,
        gui_agent_service=gui_agent,
    )
    # Youtu Agent 配置可从打包目录读取，缺失时为空。
    bundled_youtu_dir = CONFIG_DIR / "youtu-agent" / "configs"
    youtu_agent_service = YoutuAgentService(
        settings_manager,
        config_dir=bundled_youtu_dir if bundled_youtu_dir.exists() else None,
        tip_auth=tip_auth,
    )

    # 将服务实例挂载到 app.state，供路由层访问。
    app.state.settings_manager = settings_manager
    app.state.llm_service = llm_service
    app.state.tip_auth = tip_auth
    app.state.chat_manager = chat_manager
    app.state.intent_service = intent_service
    app.state.debug_reporter = debug_reporter
    app.state.text_selection_service = text_selection
    app.state.gui_agent_service = gui_agent
    app.state.skill_repository = skill_repo
    app.state.youtu_agent_service = youtu_agent_service
    yield


# FastAPI 应用：通过 lifespan 管理资源。
app = FastAPI(title='Tip Sidecar', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)
# CORS 允许来自 Electron 渲染进程的请求。

# 逐步注册各路由：健康检查、意图、设置、聊天、调试等。
# 方便查找对应模块时可按文件名搜索 routes_xxx。
app.include_router(routes_health.router)
app.include_router(routes_intent.router)
app.include_router(routes_settings.router)
app.include_router(routes_chat.router)
app.include_router(routes_debug.router)
app.include_router(routes_selection.router)
app.include_router(routes_gui_agent.router)
app.include_router(routes_skills.router)
app.include_router(routes_llm.router)
app.include_router(routes_youtu_agent.router)


@app.get('/')
async def root():
    # 简单探针，便于进程存活检查。
    return {'service': 'tip-sidecar'}
