# File: python/app/api/routes_selection.py
# Project: Tip Desktop Assistant
# Description: Endpoint to capture selected text through the TextSelectionService.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends

from ..core.deps import get_text_selection_service
from ..schemas.selection import SelectionTextResponse
from ..services.text_selection import TextSelectionService

router = APIRouter(prefix='/selection', tags=['selection'])


@router.post('/text', response_model=SelectionTextResponse)
async def capture_selection_text(
    service: TextSelectionService = Depends(get_text_selection_service),
) -> SelectionTextResponse:
    text = await service.capture_selected_text()
    return SelectionTextResponse(text=text)
