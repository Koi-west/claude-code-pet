# File: python/app/schemas/settings.py
# Project: Tip Desktop Assistant
# Description: Pydantic schemas for settings CRUD and LLM profile creation or updates.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from ..core.settings import LLMHeaders, LLMProfile, ShortcutSettings, PathSettings, Settings, FeatureSettings


class SettingsResponse(Settings):
    """Public-facing settings payload returned by the API layer."""
    pass


class SettingsUpdate(BaseModel):
    """Partial update payload used to patch existing settings."""
    settingsVersion: Optional[str] = None
    language: Optional[str] = None
    llmProfiles: Optional[list[LLMProfile]] = None
    llmActiveId: Optional[str] = None
    vlmActiveId: Optional[str] = None
    shortcuts: Optional[ShortcutSettings] = None
    paths: Optional[PathSettings] = None
    features: Optional[FeatureSettings] = None


class LLMProfileCreate(BaseModel):
    """Allowed fields when creating a new custom LLM/VLM profile."""
    id: Optional[str] = None
    name: str
    provider: Literal['ollama', 'static_openai']
    baseUrl: Optional[str] = ''
    model: Optional[str] = None
    apiModel: Optional[str] = None
    apiKey: Optional[str] = None
    headers: Optional[LLMHeaders] = None
    stream: Optional[bool] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    timeoutMs: Optional[int] = None
    ollamaBaseUrl: Optional[str] = None
    ollamaModel: Optional[str] = None
    openaiModel: Optional[str] = None
    openaiBaseUrl: Optional[str] = None


class LLMProfileUpdate(BaseModel):
    """Patch payload for mutating an existing profile while leaving unspecified values intact."""
    name: Optional[str] = None
    provider: Optional[Literal['ollama', 'static_openai']] = None
    baseUrl: Optional[str] = None
    model: Optional[str] = None
    apiModel: Optional[str] = None
    apiKey: Optional[str] = None
    headers: Optional[LLMHeaders] = None
    stream: Optional[bool] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    timeoutMs: Optional[int] = None
    ollamaBaseUrl: Optional[str] = None
    ollamaModel: Optional[str] = None
    openaiModel: Optional[str] = None
    openaiBaseUrl: Optional[str] = None
