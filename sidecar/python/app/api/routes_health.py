# File: python/app/api/routes_health.py
# Project: Tip Desktop Assistant
# Description: Health endpoint exposing status, version, and capability list.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter

from ..version import SIDECAR_VERSION

router = APIRouter(prefix='/health', tags=['health'])

CAPABILITIES = ('selection:text',)


@router.get('', summary='Health check')
async def health_check():
    return {'status': 'ok', 'version': SIDECAR_VERSION, 'capabilities': list(CAPABILITIES)}
