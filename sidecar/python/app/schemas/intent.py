# File: python/app/schemas/intent.py
# Project: Tip Desktop Assistant
# Description: Intent generation request and response contracts including selection context.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .common import SelectionRect


class IntentRequest(BaseModel):
    image: Optional[str] = None
    text: Optional[str] = None
    language: Optional[str] = None
    selection: Optional[SelectionRect] = None


class IntentCandidate(BaseModel):
    id: str
    title: str


class IntentResponse(BaseModel):
    session_id: str
    candidates: List[IntentCandidate]
