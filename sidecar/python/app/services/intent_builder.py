# File: python/app/services/intent_builder.py
# Project: Tip Desktop Assistant
# Description: Builds intent candidates via LLMService and seeds chat sessions with captured context.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import uuid
from typing import List

from ..schemas.intent import IntentCandidate, IntentResponse
from ..schemas.intent import IntentRequest
from .llm import LLMService
from .chat_session import ChatSessionManager


class IntentService:
    def __init__(self, llm: LLMService, chat_sessions: ChatSessionManager) -> None:
        self._llm = llm
        self._chat_sessions = chat_sessions

    async def build_intents(self, request: IntentRequest) -> IntentResponse:
        session_id = str(uuid.uuid4())
        has_context = bool((request.image or '').strip() or (request.text or '').strip())
        candidates = []
        if has_context:
            result = await self._llm.generate_intents(
                image_b64=request.image,
                text=request.text,
                language=request.language,
            )
            for idx, suggestion in enumerate(result.suggestions, 1):
                title = (suggestion or '').strip() or f'建议 {idx}'
                candidates.append(
                    IntentCandidate(
                        id=f'intent-{idx}',
                        title=title,
                    ),
                )
            self._chat_sessions.record_intent_metadata(session_id, result)

        self._chat_sessions.ensure_session(session_id)
        self._chat_sessions.attach_context(session_id, request.image, request.text, request.selection)
        return IntentResponse(session_id=session_id, candidates=candidates)
