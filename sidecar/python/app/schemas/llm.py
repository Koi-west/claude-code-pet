# File: python/app/schemas/llm.py
# Project: Tip Desktop Assistant
# Description: Schemas for probing LLM image capability by profile identifier.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LLMImageProbeResponse(BaseModel):
    supports_image: bool
    provider: str
    model: str
    profile_id: Optional[str] = None
    error_message: Optional[str] = None
    response_preview: Optional[str] = None


class LLMImageProbeRequest(BaseModel):
    profile_id: Optional[str] = None
