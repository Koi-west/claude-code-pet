# File: python/app/services/tip_cloud_auth.py
# Project: Tip Desktop Assistant
# Description: Device-token helper that computes device IDs and fetches Tip Cloud auth headers with caching.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Optional

import httpx
import requests
import structlog

from ..core.config import CACHE_DIR

logger = structlog.get_logger(__name__)

TIP_CLOUD_GATEWAY = os.environ.get("TIP_CLOUD_BASE_URL", "https://tipapi.wandeer.world/v1").rstrip("/")


def _sha256(text: str) -> str:
    # Keep hashing helper small so we can reuse it in multiple call sites.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_io_platform_uuid() -> Optional[str]:
    # macOS-specific; other platforms fall back to hostname/MAC hashing below.
    try:
        output = subprocess.check_output(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True, timeout=2.0
        )
    except Exception:
        return None
    for line in output.splitlines():
        if "IOPlatformUUID" not in line:
            continue
        parts = line.split("=")
        if len(parts) < 2:
            continue
        value = parts[1].strip().strip('"')
        if value:
            return value
    return None


class TipCloudAuth:
    """Manage device_id and device_token for Tip Cloud gateway."""

    def __init__(self, *, cache_dir: Path = CACHE_DIR, base_url: str = TIP_CLOUD_GATEWAY) -> None:
        # Device tokens are persisted locally to avoid hammering the gateway for each request.
        self._cache_file = Path(cache_dir) / "device_token.json"
        self._base_url = base_url.rstrip("/")
        self._lock = asyncio.Lock()
        self._device_id: Optional[str] = None
        self._token: Optional[str] = None
        self._load_cache()

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def device_id(self) -> str:
        if self._device_id:
            return self._device_id
        self._device_id = self._compute_device_id()
        return self._device_id

    def _compute_device_id(self) -> str:
        # Priority: explicit env override -> stable macOS hardware UUID -> fallback to hostname/MAC hash.
        env_override = os.environ.get("TIP_DEVICE_ID", "").strip()
        if env_override:
            return env_override
        mac_uuid = _read_io_platform_uuid()
        if mac_uuid:
            return _sha256(mac_uuid)
        hostname = platform.node() or "tip-host"
        mac = uuid.getnode()
        seed = f"{hostname}-{mac}"
        return _sha256(seed)

    def _load_cache(self) -> None:
        try:
            # Cache format is intentionally minimal; missing/invalid files are tolerated silently.
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            token = str(data.get("device_token") or "").strip()
            device = str(data.get("device_id") or "").strip()
            if token and device:
                self._token = token
                self._device_id = device
        except Exception:
            return

    def _save_cache(self, token: str, device_id: str) -> None:
        try:
            # Use user cache dir for desktop apps; permissions tightened to user-only.
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps({"device_token": token, "device_id": device_id}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.chmod(self._cache_file, 0o600)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("tip_cloud.token_cache_save_failed", error=str(exc), path=str(self._cache_file))

    async def auth_headers_async(self, *, force_refresh: bool = False) -> Dict[str, str]:
        # Exposed to async callers (e.g. httpx clients) to attach Bearer + device id headers.
        token = await self._ensure_token_async(force_refresh=force_refresh)
        return {
            "Authorization": f"Bearer {token}",
            "X-Tip-Device-Id": self.device_id,
        }

    def auth_headers(self, *, force_refresh: bool = False) -> Dict[str, str]:
        # Synchronous variant mirrors the async API for convenience in CLI flows.
        token = self._ensure_token_sync(force_refresh=force_refresh)
        return {
            "Authorization": f"Bearer {token}",
            "X-Tip-Device-Id": self.device_id,
        }

    async def _ensure_token_async(self, *, force_refresh: bool = False) -> str:
        if self._token and not force_refresh:
            return self._token
        async with self._lock:
            # Re-check inside the lock to avoid duplicate refreshes under contention.
            if self._token and not force_refresh:
                return self._token
            token = await self._fetch_token_async()
            self._token = token
            self._save_cache(token, self.device_id)
            return token

    def _ensure_token_sync(self, *, force_refresh: bool = False) -> str:
        if self._token and not force_refresh:
            return self._token
        # Synchronous refresh is used by callers outside asyncio.
        token = self._fetch_token_sync()
        self._token = token
        self._save_cache(token, self.device_id)
        return token

    async def _fetch_token_async(self) -> str:
        url = f"{self._base_url}/device-token"
        payload = {
            "device_id": self.device_id,
            "app_version": os.environ.get("TIP_APP_VERSION", "dev"),
            "platform": f"{platform.system()}-{platform.machine()}",
        }
        # httpx client is short-lived; token is cached to avoid keeping sessions alive.
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            token = (data.get("device_token") or "").strip()
            if not token:
                raise RuntimeError("device_token missing in response")
            return token

    def _fetch_token_sync(self) -> str:
        url = f"{self._base_url}/device-token"
        payload = {
            "device_id": self.device_id,
            "app_version": os.environ.get("TIP_APP_VERSION", "dev"),
            "platform": f"{platform.system()}-{platform.machine()}",
        }
        # Requests keeps things synchronous for desktop contexts where event loop isn't available.
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = (data.get("device_token") or "").strip()
        if not token:
            raise RuntimeError("device_token missing in response")
        return token
