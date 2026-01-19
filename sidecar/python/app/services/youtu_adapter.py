# File: python/app/services/youtu_adapter.py
# Project: Tip Desktop Assistant
# Description: Adapts Settings/LLMProfile into Youtu-Agent model bindings via OpenAI-compatible clients.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import os
import structlog
from typing import Optional, Tuple

try:  # pragma: no cover - optional dependency
    os.environ.setdefault("UTU_LLM_MODEL", "tip-placeholder")
    os.environ.setdefault("UTU_LLM_TYPE", "chat.completions")
    # Defer import so desktop app can start even when youtu-agent extras are absent.
    from agents import Model, ModelSettings, OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from utu.utils import SimplifiedAsyncOpenAI
    from utu.utils.agents_utils import SimplifiedOpenAIChatCompletionsModel
except ImportError:  # pragma: no cover
    Model = ModelSettings = OpenAIChatCompletionsModel = AsyncOpenAI = None  # type: ignore
    SimplifiedAsyncOpenAI = SimplifiedOpenAIChatCompletionsModel = None  # type: ignore

from ..core.settings import LLMProfile, Settings
from .llm import (
    LLMProviderUnavailableError,
    tip_cloud_api_key,
    tip_cloud_base_url,
    tip_cloud_model,
)
from .tip_cloud_auth import TipCloudAuth


def build_youtu_model(
    settings: Settings,
    profile: Optional[LLMProfile] = None,
    tip_auth: Optional[TipCloudAuth] = None,
) -> Tuple[Model, ModelSettings]:
    """
    Adapt our existing Settings into a Youtu-Agent compatible (Model, ModelSettings) pair.

    The mapping keeps provider-specific preferences:
    - provider==tip_cloud    -> use built-in Tip Cloud (OpenAI compatible) defaults
    - provider==static_openai-> use openaiBaseUrl/openaiModel supplied by user
    - provider==ollama       -> use ollamaBaseUrl/ollamaModel
    All of them are exposed to Youtu-Agent through the OpenAI-compatible client.
    """
    # Profile defaults to the active desktop profile; callers may override for tests.
    profile = profile or settings.get_active_llm_profile()
    if Model is None or ModelSettings is None or OpenAIChatCompletionsModel is None or AsyncOpenAI is None:
        raise RuntimeError('请先安装 `openai-agents` 依赖后再启用 Youtu-Agent 功能。')
    provider = (profile.provider or "tip_cloud").lower()
    headers = profile.headers.to_dict()
    timeout_seconds = (profile.timeoutMs or 60000) / 1000
    # Keep a minimal preview string in logs to avoid leaking real endpoints.
    # Logging kept minimal to avoid leaking secrets; only provider/model/base_url.
    base_url_preview = profile.baseUrl or profile.openaiBaseUrl or ""
    try:
        logger = structlog.get_logger(__name__)
        # Keep operational telemetry minimal to avoid exposing secrets in logs.
        logger.info(
            "youtu_adapter.build_model",
            provider=provider,
            base_url=base_url_preview,
            model=profile.model,
            api_model=profile.apiModel,
            openai_model=profile.openaiModel,
            ollama_model=profile.ollamaModel,
        )
    except Exception:  # pragma: no cover - logging best effort
        pass

    if provider == "static_openai":
        base_url = (profile.openaiBaseUrl or profile.baseUrl or "").rstrip("/")
        model_name = profile.openaiModel or profile.apiModel or profile.model
        api_key = _resolve_api_key(profile)
        # OpenAI-compatible client; headers come from profile to respect user-provided values.
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            default_headers=headers or None,
        )
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    elif provider == "tip_cloud":
        base_url = tip_cloud_base_url()
        model_name = tip_cloud_model()
        token_headers: dict[str, str] = {}
        if tip_auth:
            try:
                # Prefer fetching a device token so that Tip Cloud works without user-provided API keys.
                token_headers = tip_auth.auth_headers()
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("youtu_adapter.tip_token_failed", error=str(exc))
        api_key = (token_headers.get("Authorization") or tip_cloud_api_key()).strip()
        if api_key.lower().startswith("bearer "):
            api_key = api_key.split(" ", 1)[1].strip()
        if not api_key:
            raise LLMProviderUnavailableError("Tip Cloud 设备 token 获取失败，请重试。")
        merged_headers = dict(headers)
        merged_headers.update({k: v for k, v in token_headers.items() if k.lower() != "authorization"})
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            default_headers=merged_headers or None,
        )
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    else:
        # Fall back to user-specified provider (e.g., ollama or self-hosted OpenAI).
        base_url = _resolve_base_url(profile, provider)
        model_name = _resolve_model_name(profile, provider)
        api_key = _resolve_api_key_for_provider(profile, provider)
        model = _build_tip_api_model(
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            headers=headers,
            timeout=timeout_seconds,
            provider=provider,
        )

    # Extra OpenAI body options keep stream mode consistent with desktop settings.
    extra_body = {"stream": profile.stream}
    model_settings = ModelSettings(
        temperature=profile.temperature,
        max_tokens=profile.maxTokens,
        top_p=None,
        presence_penalty=None,
        frequency_penalty=None,
        parallel_tool_calls=True,
        extra_body=extra_body,
        extra_headers=headers or None,
    )
    return model, model_settings


def _resolve_api_key(profile: LLMProfile) -> str:
    candidates = [
        (profile.apiKey or "").strip(),
        (profile.headers.to_dict().get("Authorization") or "").strip(),
    ]
    # Environment override keeps CLI users unblocked without editing settings.json.
    for env_key in ("TIP_OPENAI_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(env_key, "").strip()
        if val:
            candidates.append(val)
    for candidate in candidates:
        if not candidate:
            continue
        if candidate.lower().startswith("bearer "):
            candidate = candidate.split(" ", 1)[1].strip()
        if candidate:
            return candidate
    raise LLMProviderUnavailableError("未配置 OpenAI API Key，请在设置中填写。")


def _resolve_base_url(profile: LLMProfile, provider: str) -> str:
    # Ollama usually runs locally; others reuse baseUrl/openaiBaseUrl from settings.
    if provider == "ollama":
        return (profile.ollamaBaseUrl or profile.baseUrl).rstrip("/")
    return (profile.baseUrl or profile.openaiBaseUrl).rstrip("/")


def _resolve_model_name(profile: LLMProfile, provider: str) -> str:
    if provider == "ollama":
        return profile.ollamaModel or profile.apiModel or profile.model
    # For hosted providers, apiModel falls back to general model field.
    return profile.apiModel or profile.model


def _resolve_api_key_for_provider(profile: LLMProfile, provider: str) -> str:
    # Youtu-Agent requires an API key even for placeholder providers; keep defaults non-empty.
    if provider == "ollama":
        return profile.apiKey or "ollama-placeholder"
    return profile.apiKey or "tip-placeholder"


def _build_tip_api_model(
    *,
    base_url: str,
    model_name: str,
    api_key: str,
    headers: dict[str, str],
    timeout: float,
    provider: str,
) -> Model:
    if not base_url:
        raise LLMProviderUnavailableError("未配置 LLM base_url，无法初始化 Youtu Agent。")
    if SimplifiedAsyncOpenAI is None or SimplifiedOpenAIChatCompletionsModel is None:
        raise RuntimeError("缺少 youtu-agent 依赖，无法构建自家 API 模型。")

    if provider == "ollama":
        # Ollama exposes an OpenAI-compatible /v1 endpoint; reuse the same client wrapper.
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_url.rstrip('/')}/v1",
            timeout=timeout,
            default_headers=headers or None,
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    client = SimplifiedAsyncOpenAI(
        type=os.environ.get("UTU_LLM_TYPE", "chat.completions"),
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        model=model_name,
    )
    if headers:
        try:
            # The simplified client exposes underlying headers; update best-effort.
            client._client.headers.update(headers)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            pass
    # Simplified client is wrapped to match OpenAIChatCompletionsModel interface.
    return SimplifiedOpenAIChatCompletionsModel(model=model_name, openai_client=client)
