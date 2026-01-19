# File: python/app/api/routes_youtu_agent.py
# Project: Tip Desktop Assistant
# Description: HTTP and websocket handlers to run, stream, reload, and reset Youtu-Agent sessions.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Dict, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import structlog

from ..core.deps import get_youtu_agent_service, get_youtu_agent_service_ws
from ..schemas.youtu_agent import YoutuAgentReloadResponse, YoutuAgentRunRequest, YoutuAgentRunResponse
from ..services.youtu_agent_service import YoutuAgentService

try:  # pragma: no cover - optional dependency
    from agents.stream_events import AgentUpdatedStreamEvent, RawResponsesStreamEvent, RunItemStreamEvent
except ImportError:  # pragma: no cover
    RawResponsesStreamEvent = RunItemStreamEvent = AgentUpdatedStreamEvent = None  # type: ignore

# API surface mirrors the FastAPI router used by the Electron shell.
# When the optional agents package is absent we degrade gracefully by treating
# stream events as opaque payloads instead of structured dataclasses.
router = APIRouter(prefix='/youtu-agent', tags=['youtu-agent'])
logger = structlog.get_logger(__name__)


def _prompt_preview(text: str, limit: int = 120) -> str:
    """Trim prompt for logging so structured logs stay compact."""
    stripped = (text or "").strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit] + f"...(+{len(stripped) - limit})"


@router.post('/run', response_model=YoutuAgentRunResponse)
async def run_youtu_agent(
    payload: YoutuAgentRunRequest,
    service: YoutuAgentService = Depends(get_youtu_agent_service),
) -> YoutuAgentRunResponse:
    """Run Youtu-Agent once via HTTP and return final output."""
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail='Prompt is required')
    logger.info(
        'youtu_agent.run.request',
        session=payload.session_id,
        save_history=payload.save_history,
        prompt_preview=_prompt_preview(payload.prompt),
    )
    try:
        output, session_id = await service.run(
            payload.prompt.strip(),
            save_history=payload.save_history,
            session_id=payload.session_id,
        )
    except RuntimeError as exc:
        logger.warning('youtu_agent.run_blocked', error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected runtime failure
        logger.warning('youtu_agent.run_failed', error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail='Youtu Agent 执行失败') from exc
    logger.info('youtu_agent.run.success', session=session_id, output_len=len(output))
    return YoutuAgentRunResponse(output=output, provider=service.current_provider(), session_id=session_id)


@router.websocket('/stream')
async def youtu_agent_stream(
    websocket: WebSocket,
    service: YoutuAgentService = Depends(get_youtu_agent_service_ws),
):
    """Bi-directional stream: accepts prompts, emits events/output chunks."""
    await websocket.accept()
    session_id: str | None = None
    stream: AsyncGenerator[Any, None] | None = None
    try:
        while True:
            # WebSocket payloads are small command objects: {action, prompt, session_id?}.
            # The server replies with session state first, then streams chunks until done.
            # Each iteration may start a new run or perform a reset; no sticky state is assumed.
            try:
                payload = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info('youtu_agent stream disconnected')
                return
            except Exception:
                # Close with explicit error to help the renderer distinguish protocol issues.
                await websocket.send_json({'event': 'error', 'message': 'Invalid payload'})
                await websocket.close(code=4400)
                return

            action = (payload.get('type') or payload.get('action') or 'run').lower()
            # Reset clears cached session state; run triggers a new streaming response.
            if action == 'reset':
                target = payload.get('session_id') or session_id
                if target:
                    # Reset clears caches/history for the target session so new prompts are fresh.
                    await service.reset_session(target)
                    await websocket.send_json({'event': 'reset', 'session_id': target})
                else:
                    await websocket.send_json({'event': 'error', 'message': 'No session to reset'})
                continue

            prompt = (payload.get('prompt') or '').strip()
            save_history = bool(payload.get('save_history', True))
            requested_session = payload.get('session_id') or session_id
            if not prompt:
                # Keep connection alive but signal error so clients can retry.
                await websocket.send_json({'event': 'error', 'message': 'Prompt is required'})
                continue

            logger.info(
                'youtu_agent.stream.request',
                action=action,
                session=requested_session,
                save_history=save_history,
                prompt_preview=_prompt_preview(prompt),
            )
            try:
                session_id, stream = await service.stream(
                    prompt,
                    save_history=save_history,
                    session_id=requested_session,
                )
                # Inform client of the canonical session ID before streaming content.
                await websocket.send_json({'event': 'session', 'session_id': session_id})
            except RuntimeError as exc:
                logger.warning('youtu_agent.stream_blocked', error=str(exc), exc_info=True)
                await websocket.send_json({'event': 'error', 'message': str(exc)})
                continue

            logger.info('youtu_agent stream connected', session=session_id)
            try:
                async for event in stream:
                    # Raw response events are mostly for debugging; log them compactly.
                    if _is_raw_response_event(event):
                        try:
                            logger.info(
                                'youtu_agent.raw_response',
                                session=session_id,
                                raw=_json_safe(getattr(event, 'data', event)),
                            )
                        except Exception:
                            logger.warning('youtu_agent.raw_response_log_failed', session=session_id)
                    if isinstance(event, dict) and event.get('event') == 'final_output':
                        logger.info(
                            'youtu_agent.stream.final',
                            session=session_id,
                            output_len=len(event.get('output') or ''),
                        )
                        await websocket.send_json(
                            {
                                'event': 'done',
                                'output': event.get('output') or '',
                                'provider': service.current_provider(),
                                'session_id': session_id,
                            }
                        )
                        continue
                    # Non-final events are forwarded as incremental chunks for UI streaming.
                    payload = _serialize_stream_event(event)
                    await websocket.send_json({'event': 'chunk', 'payload': payload, 'session_id': session_id})
            except WebSocketDisconnect:
                # Client dropped the socket mid-run; just stop without raising.
                logger.info('youtu_agent stream disconnected during run')
                return
            except RuntimeError as exc:
                logger.warning('youtu_agent.stream_failed', error=str(exc), exc_info=True)
                await websocket.send_json({'event': 'error', 'message': str(exc), 'session_id': session_id})
            except Exception as exc:  # pragma: no cover - unexpected runtime failure
                logger.warning('youtu_agent.stream_crashed', error=str(exc), exc_info=True)
                await websocket.close(code=1011)
                return
            finally:
                if stream:
                    # Ensure generator is closed to release resources (e.g., async clients).
                    await stream.aclose()
                    stream = None
    finally:
        if stream:
            await stream.aclose()


@router.post('/reload', response_model=YoutuAgentReloadResponse)
async def reload_youtu_agent(
    service: YoutuAgentService = Depends(get_youtu_agent_service),
) -> YoutuAgentReloadResponse:
    """Reload agent config/models; used after on-disk updates."""
    try:
        config_name = await service.reload()
    except RuntimeError as exc:
        logger.warning('youtu_agent.reload_blocked', error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected runtime failure
        logger.warning('youtu_agent.reload_failed', error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail='Youtu Agent 重建失败') from exc
    # Return the loaded config name so the UI can display which agent is active.
    return YoutuAgentReloadResponse(config=config_name, provider=service.current_provider())


def _serialize_stream_event(event: Any) -> Dict[str, Any]:
    """Convert Youtu-Agent stream events into JSON-serializable payloads."""
    # Event classes may not be available (optional dependency); we guard each branch.
    # Unknown events fall back to repr-safe JSON conversion so clients can still render logs.
    if RawResponsesStreamEvent and isinstance(event, RawResponsesStreamEvent):
        data = _json_safe(event.data)
    elif RunItemStreamEvent and isinstance(event, RunItemStreamEvent):
        data = {"item": _json_safe(_simplify_run_item(event.item))}
    elif AgentUpdatedStreamEvent and isinstance(event, AgentUpdatedStreamEvent):
        data = {"new_agent": _json_safe(_simplify_agent(event.new_agent))}
    else:
        data = _json_safe(event)
    return {"type": event.__class__.__name__, "data": data}


def _simplify_run_item(item: Any) -> Dict[str, Any]:
    # Flatten frequently used fields so the frontend does not need the full model.
    payload: Dict[str, Any] = {
        "type": getattr(item, "type", item.__class__.__name__),
    }
    # Optional agent meta when present (e.g., nested agent orchestration).
    agent = getattr(item, "agent", None)
    agent_name = getattr(agent, "name", None)
    if agent_name:
        payload["agent"] = agent_name
    output = getattr(item, "output", None)
    if output:
        payload["output"] = output
    raw_item = getattr(item, "raw_item", None)
    if raw_item:
        payload["raw_item"] = _simplify_raw_tool_item(raw_item)
    return payload


def _simplify_raw_tool_item(raw_item: Any) -> Dict[str, Any]:
    # Convert raw tool outputs into a minimal JSON-friendly shape.
    payload: Dict[str, Any] = {}
    name = getattr(raw_item, "name", None)
    if name:
        payload["name"] = name
    arguments = getattr(raw_item, "arguments", None)
    if arguments:
        payload["arguments"] = arguments
    output = getattr(raw_item, "output", None)
    if output:
        payload["output"] = output
    item_type = getattr(raw_item, "type", None)
    if item_type:
        payload["type"] = item_type
    return payload


def _simplify_agent(agent: Any) -> Dict[str, Any]:
    # AgentUpdated events only need identity information.
    return {
        "name": getattr(agent, "name", None),
        "id": getattr(agent, "id", None),
    }


def _is_raw_response_event(event: Any) -> bool:
    """Check whether the stream event contains the raw LLM response."""
    if RawResponsesStreamEvent and isinstance(event, RawResponsesStreamEvent):
        return True
    return event.__class__.__name__ == "RawResponsesStreamEvent"


def _json_safe(value: Any) -> Any:
    """Best-effort conversion to JSON-serializable structures."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except TypeError:
            try:
                return _json_safe(json.loads(value.model_dump_json()))
            except Exception:
                return repr(value)
    if is_dataclass(value):
        try:
            return _json_safe(asdict(value))
        except Exception:
            return repr(value)
    if hasattr(value, "__dict__"):
        # Drop private attributes to avoid leaking internals (e.g., clients, locks).
        return _json_safe({k: v for k, v in value.__dict__.items() if not k.startswith("_")})
    # Fallback to repr for objects with no obvious serialisation hooks.
    return repr(value)
