# File: python/app/api/routes_settings.py
# Project: Tip Desktop Assistant
# Description: Settings endpoints for reading/updating settings and managing LLM profiles.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.settings import (
    LLMProfile,
    LLMProfileCreate,
    LLMProfileUpdate,
    SettingsResponse,
    SettingsUpdate,
)
from ..services.settings_manager import SettingsManager
from ..core.deps import get_settings_manager

router = APIRouter(prefix='/settings', tags=['settings'])


@router.get('', response_model=SettingsResponse)
def read_settings(manager: SettingsManager = Depends(get_settings_manager)) -> SettingsResponse:
    """Return the current merged settings payload."""
    return manager.get_settings()


@router.put('', response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdate,
    manager: SettingsManager = Depends(get_settings_manager),
) -> SettingsResponse:
    """Persist partial settings update and return latest snapshot."""
    # model_dump(exclude_unset=True) keeps defaults untouched when users send patches.
    data = payload.model_dump(exclude_unset=True)
    return manager.save_settings(data)


@router.get('/llm-profiles', response_model=list[LLMProfile])
def list_llm_profiles(manager: SettingsManager = Depends(get_settings_manager)) -> list[LLMProfile]:
    """List all stored LLM profiles."""
    # Profiles include both cloud and local models; we simply expose the stored list.
    return manager.list_llm_profiles()


@router.post('/llm-profiles', response_model=LLMProfile)
def create_llm_profile(
    payload: LLMProfileCreate,
    manager: SettingsManager = Depends(get_settings_manager),
) -> LLMProfile:
    """Create a new LLM profile and return the persisted item."""
    # Manager will raise ValueError on duplicates; translate to HTTP 400 here.
    try:
        data = payload.model_dump(exclude_unset=True)
        return manager.add_llm_profile(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put('/llm-profiles/{profile_id}', response_model=LLMProfile)
def update_llm_profile(
    profile_id: str,
    payload: LLMProfileUpdate,
    manager: SettingsManager = Depends(get_settings_manager),
) -> LLMProfile:
    """Update fields of an existing LLM profile by id."""
    try:
        data = payload.model_dump(exclude_unset=True)
        return manager.update_llm_profile(profile_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Profile not found') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete('/llm-profiles/{profile_id}')
def delete_llm_profile(
    profile_id: str,
    manager: SettingsManager = Depends(get_settings_manager),
) -> dict[str, str]:
    """Delete the target LLM profile."""
    try:
        manager.delete_llm_profile(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Profile not found') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'deleted'}


@router.put('/llm-active/{profile_id}', response_model=LLMProfile)
def set_active_llm(
    profile_id: str,
    manager: SettingsManager = Depends(get_settings_manager),
) -> LLMProfile:
    """Switch active LLM profile for downstream requests."""
    # The active profile is cached in SettingsManager; raise if id is unknown.
    try:
        return manager.set_active_llm(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Profile not found') from exc
