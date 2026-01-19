# File: python/app/api/routes_gui_agent.py
# Project: Tip Desktop Assistant
# Description: Endpoints for starting GUI agent runs, streaming their events, and cancelling tasks.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import structlog

from ..core.deps import (
    get_chat_manager,
    get_chat_manager_ws,
    get_gui_agent_service,
    get_gui_agent_service_ws,
)
from ..schemas.gui_agent import GuiAgentCancelRequest, GuiAgentRunRequest, GuiAgentRunResponse
from ..services.chat_session import ChatSessionManager
from ..services.gui_agent import GuiAgentService

router = APIRouter(prefix='/gui-agent', tags=['gui-agent'])
logger = structlog.get_logger(__name__)


@router.post('/run', response_model=GuiAgentRunResponse)
async def start_gui_agent_run(
    payload: GuiAgentRunRequest,
    service: GuiAgentService = Depends(get_gui_agent_service),
    chat_manager: ChatSessionManager = Depends(get_chat_manager),
) -> GuiAgentRunResponse:
    """Start a GUI agent task for a given chat session."""
    # Validate session existence before attempting to spawn a run handle.
    # This prevents leaking orphan runs that cannot be observed by the client.
    session = chat_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Invalid session_id')
    try:
        handle = await service.start_run(session_id=payload.session_id, instruction=payload.instruction)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return GuiAgentRunResponse(
        run_id=handle.run_id,
        session_id=handle.session_id,
        instruction=handle.instruction,
        task_id=handle.task_id,
    )


@router.websocket('/stream')
async def gui_agent_stream(
    websocket: WebSocket,
    service: GuiAgentService = Depends(get_gui_agent_service_ws),
    chat_manager: ChatSessionManager = Depends(get_chat_manager_ws),
):
    """Stream GUI agent logs/events to the client over WebSocket."""
    # Close early if run_id/session_id are missing or invalid to save connections.
    # Custom close codes keep the renderer informed about the reason.
    run_id = websocket.query_params.get('run_id')
    session_id = websocket.query_params.get('session_id')
    if not run_id:
        await websocket.close(code=4000)
        return
    if not service.has_run(run_id):
        await websocket.close(code=4404)
        return
    if session_id and not chat_manager.get_session(session_id):
        await websocket.close(code=4404)
        return

    await websocket.accept()
    logger.info('gui_agent stream connected', run_id=run_id, session_id=session_id)
    stream = service.stream_events(run_id)
    try:
        async for event in stream:
            await websocket.send_json({'event': 'gui_agent_log', 'payload': event})
    except WebSocketDisconnect:
        logger.info('gui_agent stream disconnected', run_id=run_id)
    finally:
        await stream.aclose()


@router.post('/cancel')
async def cancel_gui_agent_run(
    payload: GuiAgentCancelRequest,
    service: GuiAgentService = Depends(get_gui_agent_service),
):
    """Cancel an in-flight GUI agent run if it is still active."""
    success = await service.cancel_run(payload.run_id)
    if not success:
        raise HTTPException(status_code=404, detail='Run not found or already finished')
    return {'status': 'cancelled'}
