# File: python/app/core/config.py
# Project: Tip Desktop Assistant
# Description: Environment and path configuration for base dirs, settings files, and cache directories.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import os
import sys
from pathlib import Path


def _get_env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _resolve_base_dir() -> Path:
    frozen_root = getattr(sys, '_MEIPASS', None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[3]


BASE_DIR = _resolve_base_dir()
CONFIG_DIR = BASE_DIR / 'config'
DEFAULT_SETTINGS_FILE = CONFIG_DIR / 'settings.default.json'


def _resolve_path(key: str, fallback: Path) -> Path:
    value = os.environ.get(key)
    if value:
        return Path(value).expanduser().resolve()
    return fallback

USER_SETTINGS_FILE = _resolve_path(
    'TIP_SETTINGS_FILE',
    Path.home() / 'Library' / 'Application Support' / 'Tip' / 'settings.json',
)
LOG_DIR = _resolve_path('TIP_LOG_DIR', Path.home() / '.tip' / 'logs')
CACHE_DIR = _resolve_path('TIP_CACHE_DIR', Path.home() / 'Library' / 'Caches' / 'Tip')
DEBUG_REPORT_DIR = _resolve_path('TIP_DEBUG_DIR', CACHE_DIR / 'debug-reports')
