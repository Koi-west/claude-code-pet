# File: python/app/api/routes_llm.py
# Project: Tip Desktop Assistant
# Description: FastAPI routes for LLM utilities such as Ollama health checks and VLM probes.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends, HTTPException

from ..core.deps import get_llm_service
from ..services.llm import LLMService, LLMProviderUnavailableError
from ..schemas.llm import LLMImageProbeRequest, LLMImageProbeResponse

router = APIRouter(prefix='/llm', tags=['llm'])


@router.get('/ollama/status')
async def check_ollama_status(llm_service: LLMService = Depends(get_llm_service)) -> dict[str, str]:
    try:
        await llm_service.ensure_ollama_available()
    except LLMProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {'status': 'ok'}


@router.post('/vision-probe', response_model=LLMImageProbeResponse)
async def probe_image_capability(
    payload: LLMImageProbeRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> LLMImageProbeResponse:
    try:
        result = await llm_service.probe_image_capability(payload.profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Profile not found') from exc
    except LLMProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return LLMImageProbeResponse(
        supports_image=result.supports_image,
        provider=result.provider,
        model=result.model,
        profile_id=result.profile_id,
        error_message=result.error_message,
        response_preview=result.response_preview,
    )
