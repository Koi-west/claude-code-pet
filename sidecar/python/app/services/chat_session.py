# File: python/app/services/chat_session.py
# Project: Tip Desktop Assistant
# Description: Chat session state manager handling context, intent metadata, and streamed assistant replies.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional
import time

from ..schemas.chat import ChatMessage
from ..schemas.common import SelectionRect
from .llm import LLMService, IntentGenerationResult, ChatPromptMetadata


@dataclass
class ChatSession:
    session_id: str
    intent: Optional[str] = None
    messages: List[ChatMessage] = field(default_factory=list)
    snapshot_image: Optional[str] = None
    selection: Optional[SelectionRect] = None
    selection_text: Optional[str] = None
    intent_candidates: List[str] = field(default_factory=list)
    intent_prompt: Optional[IntentGenerationResult] = None
    chat_prompts: List['ChatPromptRecord'] = field(default_factory=list)
    closed_at: Optional[float] = None
    active_assistant: Optional[ChatMessage] = None


@dataclass
class ChatPromptRecord:
    system_prompt: str
    user_prompt: str
    language: str
    selection_hint: str
    assistant_response: str = ''


class ChatSessionManager:
    def __init__(self, llm_service: LLMService) -> None:
        # In-memory session cache with TTL cleanup to avoid unbounded growth.
        self._llm = llm_service
        self._sessions: Dict[str, ChatSession] = {}
        self._session_ttl_seconds = 15 * 60
        self._last_cleanup = 0.0

    def _cleanup_sessions(self) -> None:
        now = time.time()
        # Skip sweeping if the last cleanup was recent to keep hot paths cheap.
        if now - self._last_cleanup < 60:
            return
        removable = []
        for session_id, session in self._sessions.items():
            # Sessions become eligible for removal only after being closed for a full TTL.
            if session.closed_at and now - session.closed_at > self._session_ttl_seconds:
                removable.append(session_id)
        for session_id in removable:
            self._sessions.pop(session_id, None)
        # Record the cleanup timestamp so future checks can be throttled.
        self._last_cleanup = now

    def ensure_session(self, session_id: str) -> ChatSession:
        self._cleanup_sessions()
        session = self._sessions.get(session_id)
        if not session:
            session = ChatSession(session_id=session_id)
            self._sessions[session_id] = session
        # Re-activating a closed session resets its expiry timer.
        session.closed_at = None
        return session

    def set_intent(self, session_id: str, intent: str) -> None:
        session = self.ensure_session(session_id)
        session.intent = intent

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        session = self.ensure_session(session_id)
        session.messages.append(message)

    def attach_context(
        self,
        session_id: str,
        image_data: Optional[str],
        text: Optional[str],
        selection: Optional[SelectionRect],
    ) -> None:
        session = self.ensure_session(session_id)
        # Persist the latest visual/text selection context for downstream LLM calls.
        session.snapshot_image = image_data
        session.selection = selection
        session.selection_text = text

    def attach_snapshot(self, session_id: str, image_data: str, selection: Optional[SelectionRect]) -> None:
        self.attach_context(session_id, image_data, None, selection)

    def record_intent_metadata(self, session_id: str, result: IntentGenerationResult) -> None:
        session = self.ensure_session(session_id)
        # Keep intent suggestions and prompts for later replay/debugging.
        session.intent_candidates = result.suggestions
        session.intent_prompt = result

    def record_chat_prompt(self, session_id: str, record: ChatPromptRecord) -> None:
        session = self.ensure_session(session_id)
        session.chat_prompts.append(record)

    async def stream_response(self, session_id: str, user_message: str) -> AsyncGenerator[str, None]:
        # Stream assistant output chunk-by-chunk while tracking prompts and active messages.
        session = self.ensure_session(session_id)
        intent = session.intent or '未指定意图'
        self.append_message(session_id, ChatMessage(role='user', content=user_message))
        chunks: List[str] = []
        prompt_record: Optional[ChatPromptRecord] = None
        assistant_message: Optional[ChatMessage] = None

        def handle_metadata(metadata: ChatPromptMetadata) -> None:
            nonlocal prompt_record
            # Capture the prompts that led to the streamed reply for diagnostics.
            prompt_record = ChatPromptRecord(
                system_prompt=metadata.system_prompt,
                user_prompt=metadata.user_prompt,
                language=metadata.language_label,
                selection_hint=metadata.selection_hint,
            )

        try:
            async for chunk in self._llm.stream_chat(
                intent=intent,
                user_message=user_message,
                image_b64=session.snapshot_image,
                selection=session.selection,
                selection_text=session.selection_text,
                on_metadata=handle_metadata,
            ):
                chunks.append(chunk)
                if assistant_message is None:
                    # First chunk: create an assistant placeholder so UI can update incrementally.
                    assistant_message = ChatMessage(role='assistant', content='')
                    session.messages.append(assistant_message)
                    session.active_assistant = assistant_message
                assistant_message.content += chunk
                yield chunk
        finally:
            # Always clear active flag even if streaming failed midway.
            session.active_assistant = None
        assistant_reply = ''.join(chunks).strip()
        if assistant_message:
            if not assistant_reply:
                session.messages.remove(assistant_message)
            else:
                assistant_message.content = assistant_reply
        elif assistant_reply:
            self.append_message(session_id, ChatMessage(role='assistant', content=assistant_reply))
        if prompt_record:
            prompt_record.assistant_response = assistant_reply
            self.record_chat_prompt(session_id, prompt_record)

    def discard_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            # Mark as closed so TTL-based cleanup can reclaim memory.
            session.closed_at = time.time()
        self._cleanup_sessions()

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)
