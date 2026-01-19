# File: python/app/schemas/debug.py
# Project: Tip Desktop Assistant
# Description: Debug report schemas covering captures, attachments, and GUI agent references.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional

from .common import SelectionRect


class Viewport(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DebugSelectionPreview(BaseModel):
    data_url: str
    rect: SelectionRect
    display_id: Optional[int] = None

class DebugTextSelection(BaseModel):
    text: str
    truncated: Optional[str] = None


class DebugCaptureDisplay(BaseModel):
    id: int
    width: int
    height: int
    scale: float
    bounds: SelectionRect
    data_url: str


class DebugCapturePayload(BaseModel):
    id: str
    generated_at: int
    viewport: Optional[Viewport] = None
    displays: List[DebugCaptureDisplay]


class DebugLogAttachment(BaseModel):
    name: str
    path: str
    truncated: bool
    total_bytes: int
    retained_bytes: int
    content: str
    encoding: Optional[str] = None
    mime_type: Optional[str] = None


class DebugGuiAgentRef(BaseModel):
    run_id: str
    instruction: Optional[str] = None


class DebugReportRequest(BaseModel):
    session_id: str
    issue: str
    capture_id: Optional[str] = None
    selected_intent: Optional[str] = None
    draft_intent: Optional[str] = None
    capture: Optional[DebugCapturePayload] = None
    selection_preview: Optional[DebugSelectionPreview] = None
    viewport: Optional[Viewport] = None
    text_selection: Optional[DebugTextSelection] = None
    logs: Optional[List[DebugLogAttachment]] = None
    label: Optional[str] = None
    gui_agent: Optional[DebugGuiAgentRef] = None


class DebugReportResponse(BaseModel):
    path: str
    report_id: str
    created_at: str
