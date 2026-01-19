# File: python/app/core/settings.py
# Project: Tip Desktop Assistant
# Description: Settings models and helpers including default Tip Cloud profile and active profile resolution.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, RootModel, ConfigDict

from .config import DEFAULT_SETTINGS_FILE


class LLMHeaders(RootModel[Dict[str, str]]):
    """Wrapper around per-provider HTTP headers to keep type info consistent."""
    root: Dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """Return a shallow copy so callers cannot mutate internal state."""
        return dict(self.root)


class LLMProfile(BaseModel):
    """Configuration for a single LLM/VLM provider profile."""
    id: str
    name: str
    provider: Literal['tip_cloud', 'ollama', 'static_openai']
    # Base URL where the completion endpoint is exposed; set per provider.
    baseUrl: str = Field(default='', alias='baseUrl')
    model: str = 'Qwen3-32B'
    apiModel: Optional[str] = Field(default=None, alias='apiModel')
    apiKey: Optional[str] = Field(default=None, alias='apiKey')
    # Arbitrary HTTP headers to pass through to the backend.
    headers: LLMHeaders = Field(default_factory=LLMHeaders)
    stream: bool = True
    temperature: float = 0.2
    maxTokens: int = Field(default=2048, alias='maxTokens')
    timeoutMs: int = Field(default=60000, alias='timeoutMs')
    ollamaBaseUrl: str = Field(default='http://127.0.0.1:11434', alias='ollamaBaseUrl')
    ollamaModel: Optional[str] = Field(default='qwen2.5vl:3b', alias='ollamaModel')
    openaiModel: Optional[str] = Field(default=None, alias='openaiModel')
    openaiBaseUrl: Optional[str] = Field(default=None, alias='openaiBaseUrl')
    isLocked: bool = Field(default=False, alias='isLocked')

    model_config = ConfigDict(populate_by_name=True)


class ShortcutSettings(BaseModel):
    """Keyboard and gesture shortcuts shared by renderer and main process."""
    holdToSense: list[str]
    cancelThresholdPx: int = 6


class PathSettings(BaseModel):
    """Filesystem layout calculated at startup."""
    cacheDir: str
    settingsFile: str
    logsDir: str


class FeatureSettings(BaseModel):
    """Feature toggles used to gate experimental or heavy modules."""
    visionEnabled: bool = True
    guiAgentEnabled: bool = True
    youtuAgentEnabled: bool = True
    youtuAgentConfig: str = Field(default='agents/simple/base')
    startupGuideEnabled: bool = True


class Settings(BaseModel):
    """Top-level settings container persisted on disk."""
    settingsVersion: str = ""
    language: str = "system"
    llmProfiles: list[LLMProfile] = Field(default_factory=list, alias='llmProfiles')
    llmActiveId: str = Field(default='tip_cloud', alias='llmActiveId')
    vlmActiveId: str = Field(default='', alias='vlmActiveId')
    shortcuts: ShortcutSettings
    paths: PathSettings
    features: FeatureSettings = Field(default_factory=FeatureSettings)

    model_config = ConfigDict(populate_by_name=True)

    def get_active_llm_profile(self) -> LLMProfile:
        """Return the active profile or fall back to Tip Cloud when missing."""
        for profile in self.llmProfiles:
            if profile.id == self.llmActiveId:
                return profile
        # Ensure we always have a usable profile even if settings are stale.
        for profile in self.llmProfiles:
            if profile.provider == 'tip_cloud':
                return profile
        return default_tip_cloud_profile()

    def get_active_vlm_profile(self) -> LLMProfile | None:
        """Return the active VLM profile if configured and available."""
        target_id = (self.vlmActiveId or '').strip()
        if not target_id:
            return None
        for profile in self.llmProfiles:
            if profile.id == target_id:
                return profile
        return None

    @classmethod
    def from_file(cls, path: Path) -> "Settings":
        """Load settings from JSON text file with UTF-8 encoding."""
        data = path.read_text(encoding='utf-8')
        return cls.model_validate_json(data)


TIP_CLOUD_PROFILE_ID = "tip_cloud"


def default_tip_cloud_profile() -> LLMProfile:
    """Hard-coded safe defaults for cloud access; used as a final fallback."""
    return LLMProfile(
        id=TIP_CLOUD_PROFILE_ID,
        name="Tip Cloud",
        provider="tip_cloud",
        baseUrl="https://tipapi.wandeer.world/v1",
        model="LLM",
        apiModel="LLM",
        apiKey="",
        headers=LLMHeaders(root={"Content-Type": "application/json"}),
        stream=True,
        temperature=0.2,
        maxTokens=2048,
        timeoutMs=60000,
        ollamaBaseUrl="http://127.0.0.1:11434",
        ollamaModel="qwen2.5vl:3b",
        openaiModel="",
        openaiBaseUrl="",
        isLocked=True,
    )


DEFAULT_SETTINGS = Settings.from_file(DEFAULT_SETTINGS_FILE)
