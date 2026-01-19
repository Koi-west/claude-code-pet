# File: python/app/version.py
# Project: Tip Desktop Assistant
# Description: Resolves the sidecar version from environment overrides or pyproject metadata.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - tomllib is stdlib on supported versions
    tomllib = None  # type: ignore[assignment]


@lru_cache(maxsize=1)
def _read_pyproject_version() -> str | None:
    if tomllib is None:  # pragma: no cover - safeguard for unexpected environments
        return None
    pyproject_path = Path(__file__).resolve().parents[1] / 'pyproject.toml'
    if not pyproject_path.exists():
        return None
    try:
        with pyproject_path.open('rb') as fp:
            data = tomllib.load(fp)
    except Exception:  # pragma: no cover - best effort parsing
        return None
    tool = data.get('tool')
    if not isinstance(tool, dict):
        return None
    poetry = tool.get('poetry')
    if not isinstance(poetry, dict):
        return None
    version = poetry.get('version')
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def _resolve_version() -> str:
    env_version = os.environ.get('TIP_SIDECAR_BUILD_VERSION') or os.environ.get('TIP_SIDECAR_VERSION')
    if env_version:
        return env_version
    parsed = _read_pyproject_version()
    if parsed:
        return parsed
    return '0.0.0'


SIDECAR_VERSION = _resolve_version()
