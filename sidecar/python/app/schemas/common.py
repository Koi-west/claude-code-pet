# File: python/app/schemas/common.py
# Project: Tip Desktop Assistant
# Description: Shared shapes such as SelectionRect with alias handling for display identifiers.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SelectionRect(BaseModel):
    x: float
    y: float
    width: float
    height: float
    display_id: Optional[int] = Field(default=None, alias='displayId')
