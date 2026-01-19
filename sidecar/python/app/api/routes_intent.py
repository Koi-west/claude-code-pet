# File: python/app/api/routes_intent.py
# Project: Tip Desktop Assistant
# Description: Endpoint to generate intent suggestions from captured context.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.intent import IntentRequest, IntentResponse
from ..services.intent_builder import IntentService
from ..services.llm import LLMProviderUnavailableError
from ..core.deps import get_intent_service

router = APIRouter(prefix='/intents', tags=['intents'])


@router.post('', response_model=IntentResponse)
async def create_intents(
    payload: IntentRequest,
    intent_service: IntentService = Depends(get_intent_service),
) -> IntentResponse:
    try:
        return await intent_service.build_intents(payload)
    except LLMProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
