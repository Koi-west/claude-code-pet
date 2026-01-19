# File: python/app/schemas/youtu_agent.py
# Project: Tip Desktop Assistant
# Description: Pydantic payloads for Youtu-Agent run, stream, and reload APIs.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class YoutuAgentRunRequest(BaseModel):
    prompt: str = Field(..., description='用户输入的意图或指令')
    save_history: bool = Field(default=True, description='是否保留内部对话历史')
    session_id: Optional[str] = Field(default=None, description='可选，会话标识用于多轮对话')


class YoutuAgentRunResponse(BaseModel):
    output: str
    session_id: Optional[str] = None
    provider: Optional[str] = None


class YoutuAgentReloadResponse(BaseModel):
    status: str = Field(default="reloaded")
    config: Optional[str] = None
    provider: Optional[str] = None
