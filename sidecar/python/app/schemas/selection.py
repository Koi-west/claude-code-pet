# File: python/app/schemas/selection.py
# Project: Tip Desktop Assistant
# Description: Response schema for selected text capture endpoints.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pydantic import BaseModel


class SelectionTextResponse(BaseModel):
    text: str | None = None
