# File: python/app/schemas/chat.py
# Project: Tip Desktop Assistant
# Description: Chat message and request models used by chat websocket flows.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant', 'system']
    content: str


class ChatRequest(BaseModel):
    session_id: str
    intent: Optional[str] = None
    message: str
