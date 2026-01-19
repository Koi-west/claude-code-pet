# File: python/app/api/routes_chat.py
# Project: Tip Desktop Assistant
# Description: Websocket endpoint for streaming chat responses within a session.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
import structlog

from ..core.deps import get_chat_manager_ws
from ..services.chat_session import ChatSessionManager

router = APIRouter(tags=['chat'])
logger = structlog.get_logger(__name__)


@router.websocket('/chat')
async def chat_socket(websocket: WebSocket, chat_manager: ChatSessionManager = Depends(get_chat_manager_ws)):
    session_id = websocket.query_params.get('session_id')
    if not session_id:
        await websocket.close(code=4000)
        return

    await websocket.accept()
    chat_manager.ensure_session(session_id)
    logger.info('chat websocket connected', session_id=session_id)
    try:
        while True:
            payload = await websocket.receive_json()
            intent = payload.get('intent')
            message = payload.get('message', '')
            if intent:
                chat_manager.set_intent(session_id, intent)
            if not message:
                continue
            async for chunk in chat_manager.stream_response(session_id, message):
                await websocket.send_json({'event': 'chunk', 'content': chunk})
            await websocket.send_json({'event': 'done'})
    except WebSocketDisconnect:
        logger.info('chat websocket disconnected', session_id=session_id)
        chat_manager.discard_session(session_id)
