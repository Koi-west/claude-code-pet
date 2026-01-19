# File: python/app/schemas/gui_agent.py
# Project: Tip Desktop Assistant
# Description: Pydantic models for starting or cancelling GUI agent runs and their responses.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pydantic import BaseModel


class GuiAgentRunRequest(BaseModel):
    session_id: str
    instruction: str


class GuiAgentRunResponse(BaseModel):
    run_id: str
    session_id: str
    instruction: str
    task_id: str | None = None


class GuiAgentCancelRequest(BaseModel):
    run_id: str
