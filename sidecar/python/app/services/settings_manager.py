# File: python/app/services/settings_manager.py
# Project: Tip Desktop Assistant
# Description: Thread-safe settings loader/writer that merges defaults, 
# enforces tip_cloud profile, and manages LLM profile CRUD.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any, Dict, Type, TypeVar
import uuid

import structlog
from pydantic import BaseModel, ValidationError

from ..core.config import DEFAULT_SETTINGS_FILE, USER_SETTINGS_FILE, _get_env_bool
from ..core.settings import (
    Settings,
    DEFAULT_SETTINGS,
    ShortcutSettings,
    PathSettings,
    FeatureSettings,
    LLMProfile,
    TIP_CLOUD_PROFILE_ID,
    default_tip_cloud_profile,
)

TModel = TypeVar('TModel', bound=BaseModel)

logger = structlog.get_logger(__name__)


class SettingsManager:
    def __init__(
        self,
        default_path: Path | None = None,
        user_path: Path | None = None,
        force_override: bool | None = None,
        migrate_if_old: bool | None = None,
    ) -> None:
        self._default_path = default_path or DEFAULT_SETTINGS_FILE
        self._user_path = user_path or USER_SETTINGS_FILE
        # 环境变量 TIP_SETTINGS_OVERWRITE=1 时，强制使用默认配置覆盖用户文件
        self._force_override = (
            force_override
            if force_override is not None
            else _get_env_bool('TIP_SETTINGS_OVERWRITE', False)
        )
        # TIP_SETTINGS_MIGRATE_IF_OLD 默认开启：当用户配置版本缺失或落后时，使用默认配置覆盖
        self._migrate_if_old = (
            migrate_if_old
            if migrate_if_old is not None
            else _get_env_bool('TIP_SETTINGS_MIGRATE_IF_OLD', True)
        )
        # RLock 确保跨线程 API 安全（FastAPI 请求/后台任务共用）
        self._lock = RLock()
        self._settings = self._load_settings()

    def _load_settings(self) -> Settings:
        # 优先读取用户文件，只有版本过旧或校验失败时回落到默认并覆盖写回
        if not self._force_override and self._user_path.exists():
            try:
                settings = Settings.from_file(self._user_path)
                if not self._should_override_for_version(settings):
                    return self._ensure_tip_cloud(settings)
                logger.info(
                    "settings.load.override_old_version",
                    user_version=getattr(settings, "settingsVersion", None),
                    default_version=getattr(DEFAULT_SETTINGS, "settingsVersion", None),
                )
            except ValidationError as exc:
                logger.warning(
                    "settings.load.user_failed",
                    error=str(exc),
                    path=str(self._user_path),
                )
        if self._force_override:
            logger.info("settings.load.force_override", path=str(self._user_path))
        # 覆盖写回用户配置，保证文件始终存在且含 tip_cloud 配置
        settings = self._ensure_tip_cloud(Settings.from_file(self._default_path))
        self._write_settings_file(settings)
        # 返回的 settings 始终是最新写盘后的拷贝
        return settings

    def _parse_version(self, value: str | None) -> tuple[int, ...] | None:
        if not value:
            return None
        parts: list[int] = []
        for part in value.strip().split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                return None
        if not parts:
            return None
        return tuple(parts)

    def _should_override_for_version(self, user_settings: Settings) -> bool:
        # 仅当开启迁移且用户版本落后或缺失时才触发覆盖
        if not self._migrate_if_old:
            return False
        default_version = self._parse_version(getattr(DEFAULT_SETTINGS, 'settingsVersion', ''))
        if default_version is None:
            return False
        user_version = self._parse_version(getattr(user_settings, 'settingsVersion', ''))
        return user_version is None or user_version < default_version

    def get_settings(self) -> Settings:
        # 返回副本以避免调用方修改内部状态
        with self._lock:
            return self._settings.model_copy(deep=True)

    def save_settings(self, payload: Dict[str, Any]) -> Settings:
        with self._lock:
            # 标准化局部更新，避免调用方传入非模型对象导致的类型漂移
            normalized = self._normalize_payload(payload)
            updated = self._settings.model_copy(update=normalized)
            updated = self._ensure_tip_cloud(updated)
            self._settings = updated
            self._write_settings_file(updated)
            return updated

    def reset_to_default(self) -> Settings:
        # 强制回滚到默认配置并写盘
        with self._lock:
            self._settings = self._ensure_tip_cloud(Settings.from_file(self._default_path))
            self._write_settings_file(self._settings)
            return self._settings

    def list_llm_profiles(self) -> list[LLMProfile]:
        # 返回深拷贝以防调用方持有引用修改内部列表
        with self._lock:
            return [profile.model_copy(deep=True) for profile in self._settings.llmProfiles]

    def add_llm_profile(self, payload: Dict[str, Any]) -> LLMProfile:
        provider = (payload.get('provider') or '').strip()
        if provider == 'tip_cloud':
            raise ValueError('不可新增 tip_cloud 配置')
        with self._lock:
            # 允许调用方指定 id，否则自动生成；避免与现有配置冲突
            profile_id = (payload.get('id') or uuid.uuid4().hex).strip() or uuid.uuid4().hex
            if any(profile.id == profile_id for profile in self._settings.llmProfiles):
                raise ValueError('配置 ID 已存在')
            data = dict(payload)
            data['id'] = profile_id
            data['isLocked'] = False
            if not data.get('name'):
                data['name'] = profile_id
            profile = LLMProfile.model_validate(data)
            # 追加新配置后重新注入 tip_cloud 以确保锁定状态
            profiles = list(self._settings.llmProfiles) + [profile]
            self._settings = self._ensure_tip_cloud(self._settings.model_copy(update={'llmProfiles': profiles}))
            self._write_settings_file(self._settings)
            return profile.model_copy(deep=True)

    def update_llm_profile(self, profile_id: str, patch: Dict[str, Any]) -> LLMProfile:
        with self._lock:
            profiles = list(self._settings.llmProfiles)
            for idx, profile in enumerate(profiles):
                if profile.id != profile_id:
                    continue
                if profile.isLocked or profile.provider == 'tip_cloud':
                    raise ValueError('tip_cloud 配置不可修改')
                payload = dict(patch)
                if payload.get('provider') == 'tip_cloud':
                    raise ValueError('tip_cloud 配置不可用于用户自定义')
                updated = profile.model_copy(update=payload)
                profiles[idx] = updated
                self._settings = self._ensure_tip_cloud(self._settings.model_copy(update={'llmProfiles': profiles}))
                self._write_settings_file(self._settings)
                return updated.model_copy(deep=True)
        raise KeyError(profile_id)

    def delete_llm_profile(self, profile_id: str) -> None:
        with self._lock:
            profiles = list(self._settings.llmProfiles)
            target = None
            for profile in profiles:
                if profile.id == profile_id:
                    target = profile
                    break
            if target is None:
                raise KeyError(profile_id)
            if target.isLocked or target.provider == 'tip_cloud':
                raise ValueError('tip_cloud 配置不可删除')
            profiles = [profile for profile in profiles if profile.id != profile_id]
            active_id = self._settings.llmActiveId
            if active_id == profile_id:
                active_id = TIP_CLOUD_PROFILE_ID
            # 删除后重置活跃配置，避免指向不存在的 ID
            self._settings = self._ensure_tip_cloud(
                self._settings.model_copy(update={'llmProfiles': profiles, 'llmActiveId': active_id})
            )
            self._write_settings_file(self._settings)

    def set_active_llm(self, profile_id: str) -> LLMProfile:
        with self._lock:
            for profile in self._settings.llmProfiles:
                if profile.id == profile_id:
                    # 更新活跃配置同时重新注入 tip_cloud 以保证特性标记一致
                    self._settings = self._settings.model_copy(update={'llmActiveId': profile_id})
                    self._settings = self._ensure_tip_cloud(self._settings)
                    self._write_settings_file(self._settings)
                    return profile.model_copy(deep=True)
        raise KeyError(profile_id)

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        # 将部分子结构合并到当前模型，避免覆盖缺省字段
        if 'llmProfiles' in normalized and isinstance(normalized['llmProfiles'], list):
            normalized['llmProfiles'] = [LLMProfile.model_validate(item) for item in normalized['llmProfiles']]
        if 'shortcuts' in normalized and isinstance(normalized['shortcuts'], dict):
            normalized['shortcuts'] = self._merge_model(
                self._settings.shortcuts,
                normalized['shortcuts'],
                ShortcutSettings,
            )
        if 'paths' in normalized and isinstance(normalized['paths'], dict):
            normalized['paths'] = self._merge_model(self._settings.paths, normalized['paths'], PathSettings)
        if 'features' in normalized and isinstance(normalized['features'], dict):
            normalized['features'] = self._merge_model(self._settings.features, normalized['features'], FeatureSettings)
        return normalized

    def _merge_model(self, current: BaseModel | None, patch: Dict[str, Any], model_type: Type[TModel]) -> TModel:
        # 使用当前值为基准，再叠加 patch，保持未提供字段不变
        base = current.model_dump(mode='python') if current else {}
        base.update(patch)
        return model_type.model_validate(base)

    def _ensure_tip_cloud(self, settings: Settings) -> Settings:
        # tip_cloud 配置必须存在且被锁定，防止用户覆盖
        profiles: list[LLMProfile] = []
        for item in settings.llmProfiles or []:
            if isinstance(item, LLMProfile):
                profiles.append(item)
            else:
                try:
                    profiles.append(LLMProfile.model_validate(item))
                except Exception:
                    logger.warning("settings.llm_profile.invalid", item=str(item))
        # 如果已有 tip_cloud，矫正其字段并保持锁定；否则补上一份默认配置
        tip_profile_index = None
        for idx, profile in enumerate(profiles):
            if profile.id == TIP_CLOUD_PROFILE_ID or profile.provider == 'tip_cloud':
                tip_profile_index = idx
                corrected = profile.model_copy(
                    update={
                        'id': TIP_CLOUD_PROFILE_ID,
                        'provider': 'tip_cloud',
                        'isLocked': True,
                        'baseUrl': profile.baseUrl or default_tip_cloud_profile().baseUrl,
                        'model': 'VLM',
                        'apiModel': 'VLM',
                        'openaiBaseUrl': '',
                        'openaiModel': '',
                    }
                )
                profiles[idx] = corrected
                break
        if tip_profile_index is None:
            profiles.append(default_tip_cloud_profile())
        active_id = settings.llmActiveId or TIP_CLOUD_PROFILE_ID
        if not any(profile.id == active_id for profile in profiles):
            active_id = TIP_CLOUD_PROFILE_ID
        vlm_id = getattr(settings, 'vlmActiveId', '').strip()
        if vlm_id and not any(profile.id == vlm_id for profile in profiles):
            vlm_id = ''
        # 确保 llmActiveId/vlmActiveId 总是指向有效配置
        with_tip = settings.model_copy(
            update={'llmProfiles': profiles, 'llmActiveId': active_id, 'vlmActiveId': vlm_id}
        )
        return self._ensure_feature_flags(with_tip)

    def _ensure_feature_flags(self, settings: Settings) -> Settings:
        features = getattr(settings, 'features', None)
        if not isinstance(features, FeatureSettings):
            features = FeatureSettings()
        vlm_id = (getattr(settings, 'vlmActiveId', '') or '').strip()
        has_vlm = bool(vlm_id and any(profile.id == vlm_id for profile in getattr(settings, 'llmProfiles', [])))
        if not has_vlm:
            patched = features.model_copy(update={'visionEnabled': False, 'guiAgentEnabled': False})
            return settings.model_copy(update={'features': patched})
        # 如果存在合法的 VLM 配置，则保持 features 原样
        return settings.model_copy(update={'features': features})

    def _write_settings_file(self, settings: Settings) -> None:
        try:
            self._user_path.parent.mkdir(parents=True, exist_ok=True)
            self._user_path.write_text(settings.model_dump_json(indent=2), encoding='utf-8')
        except Exception as exc:  # pragma: no cover - best effort
            # 写入失败仅记录日志，不抛异常以避免中断主流程
            logger.warning("settings.write_failed", error=str(exc), path=str(self._user_path))
