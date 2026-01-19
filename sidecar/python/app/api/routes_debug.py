# File: python/app/api/routes_debug.py
# Project: Tip Desktop Assistant
# Description: Endpoint to create debug reports with optional GUI agent artifacts.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.debug import DebugReportRequest, DebugReportResponse
from ..services.debug_report import DebugReportService
from ..core.deps import get_debug_reporter

router = APIRouter(prefix='/debug', tags=['debug'])


@router.post('/report', response_model=DebugReportResponse)
async def create_debug_report(
    payload: DebugReportRequest,
    reporter: DebugReportService = Depends(get_debug_reporter),
) -> DebugReportResponse:
    try:
        return await reporter.create_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
