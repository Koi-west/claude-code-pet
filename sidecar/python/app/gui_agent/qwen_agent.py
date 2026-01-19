# File: python/app/gui_agent/qwen_agent.py
# Project: Tip Desktop Assistant
# Description: Qwen3VL agent core handling reasoning loop, skill injection, LLM chat calls, and action parsing.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

import base64
import json
import logging
import os
import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import backoff
import httpx
from openai import OpenAI
from PIL import Image

from .qwen_prompting import PromptBuilder
from .qwen_response_parser import parse_response as parse_tool_response
from .qwen_skills import SkillManager
from .qwen_vl_utils import process_image
from .skills import SkillRepository


logger = None

# API base URLs are resolved lazily so they can be overridden by environment at runtime.
# Ollama keeps a local default to simplify offline testing scenarios.
# These defaults mirror the sidecar configuration to avoid divergence between services.
MAX_RETRY_TIMES = 5
MAX_SKILL_TURNS = 3
DEFAULT_TIP_BASE_URL = os.environ.get("TIP_LLM_BASE_URL")
DEFAULT_OPENAI_BASE_URL = os.environ.get("TIP_OPENAI_BASE_URL")
DEFAULT_OLLAMA_BASE_URL = os.environ.get("TIP_OLLAMA_BASE_URL") or "http://127.0.0.1:11434"


class Qwen3VLAgent:
    """GUI agent wrapper that drives the Qwen-3VL loop with optional skill lookups."""
    def __init__(
        self,
        platform: str = "ubuntu",
        model: str = None,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        temperature: float = 0.2,
        top_k: int = 20,
        repetition_penalty: float = 1.0,
        presence_penalty: float = 1.5,
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",
        max_steps: int = 15,
        history_n: int = 4,  # kept for backward compatibility
        add_thought_prefix: bool = False,
        coordinate_type: str = "relative",
        enable_thinking: bool = False,
        thinking_budget: int = 32768,
        skills_repo: Optional[SkillRepository] = None,
    ):
        resolved_model = (
            model
            or os.environ.get("TIP_LLM_MODEL")
            or os.environ.get("MODEL_NAME")
            or "Qwen3-32B"
        )
        self.platform = platform
        self.model = resolved_model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty
        self.presence_penalty = presence_penalty
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_steps = max_steps
        self.coordinate_type = coordinate_type
        self.enable_thinking = enable_thinking
        self.thinking_budget = thinking_budget
        self.skill_manager = SkillManager(skills_repo)
        self.prompt_builder = PromptBuilder()
        self.latest_skill_outputs: List[Dict[str, str]] = []

        # Guard rails to avoid sending unsupported control types.
        assert action_space in ["pyautogui"], "Invalid action space"
        assert observation_type in ["screenshot"], "Invalid observation type"

        # Conversation state is tracked so each predict call can continue the thread.
        # Screen width/height are cached to rebuild prompts only when layout changes.
        # Actions are retained to enforce a defensive step budget for the agent.
        self.messages: List[Dict] = []
        self.conversation_started = False
        self.executed_actions: List[str] = []
        self.screen_width: Optional[int] = None
        self.screen_height: Optional[int] = None

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        Returns (response, pyautogui_code).
        """
        # Vision inputs are available as raw bytes; both original and processed sizes are tracked.
        # Coordinate scaling depends on these dimensions to keep actions accurate on screen.
        # Decode screenshot payload to collect sizing info for coordinate scaling.
        screenshot_bytes = obs["screenshot"]

        image = Image.open(BytesIO(screenshot_bytes))
        width, height = image.size
        print(f"Original screen resolution: {width}x{height}")

        processed_image = process_image(screenshot_bytes)
        processed_img = Image.open(BytesIO(base64.b64decode(processed_image)))
        processed_width, processed_height = processed_img.size
        print(
            "Processed image resolution: "
            f"{processed_width}x{processed_height}"
        )

        # Ensure system prompt reflects latest canvas size and skill catalog.
        self._ensure_system_prompt(width, height)
        if not self.conversation_started:
            initial_message = self.prompt_builder.build_user_message(
                text=instruction,
                image_base64=processed_image,
            )
            self.messages.append(initial_message)
            self.conversation_started = True
        else:
            followup_message = self.prompt_builder.build_user_message(
                text=None,
                image_base64=processed_image,
            )
            self.messages.append(followup_message)

        # Track the whole transcript so the agent can refine plans while preserving context.
        # Each turn may carry at most one image to keep payloads small for the backend.
        # Text-only turns skip attaching the user instruction after the first call.
        # Send the updated transcript to LLM and capture raw response.
        self._log_conversation_transcript("LLM conversation context")
        response_raw = self._chat_with_skills()

        response_for_parse = self._strip_skill_markers(response_raw)
        response_display = response_for_parse

        logger.info(f"Qwen3VL Output: {response_display}")

        # Parse structured action output into low-level instructions and code.
        low_level_instruction, pyautogui_code = parse_tool_response(
            response_for_parse,
            coordinate_type=self.coordinate_type,
            logger=logger,
            original_width=width,
            original_height=height,
            processed_width=processed_width,
            processed_height=processed_height,
        )

        logger.info(f"Low level instruction: {low_level_instruction}")
        logger.info(f"Pyautogui code: {pyautogui_code}")

        # 打印当前动作（彩色输出）
        print(f"\033[1;35m🎯 Current Action:\033[0m")
        action_display = (
            low_level_instruction
            if len(low_level_instruction) <= 200
            else low_level_instruction[:67] + "..."
        )
        print(f"   {action_display}")
        
        if pyautogui_code:
            code_display = (
                pyautogui_code[0]
                if len(pyautogui_code[0]) <= 200
                else pyautogui_code[0][:67] + "..."
            )
            print(f"\033[1;34m💻 Code:\033[0m {code_display}")
        print()

        self.executed_actions.append(low_level_instruction or "Skill interaction")

        # Check if max_steps is reached and force FAIL if not terminated
        current_step = len(self.executed_actions)
        if (
            current_step >= self.max_steps
            and pyautogui_code
            and 'DONE' not in pyautogui_code[0]
            and 'FAIL' not in pyautogui_code[0]
        ):
            # Hard stop prevents the agent from looping endlessly when UI is unresponsive.
            # We still emit a FAIL code so upstream can surface a clear status.
            # The low-level instruction is overwritten to clarify the reason to the user.
            logger.warning(f"Reached maximum steps {self.max_steps}. Forcing termination.")
            low_level_instruction = 'Fail the task because reaching the maximum step limit.'
            pyautogui_code = ['FAIL']

        return response_display, pyautogui_code


    def _chat_with_skills(self) -> str:
        """
        Run the LLM conversation loop, handling skill lookups inline.
        Returns the final assistant response string.
        """
        # Keep local loop state to avoid mutating global conversation mid-iteration.
        response_raw = ""
        self.latest_skill_outputs = []
        skill_turns = 0

        while True:
            # Prepare payload in OpenAI-compatible format so multiple providers work.
            # Messages are trimmed just before sending to avoid oversized bodies.
            # Sampling params are kept small because downstream tool parsing is brittle.
            payload = {
                "model": self.model,
                "messages": self._prepare_messages_for_send(),
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "temperature": self.temperature,
            }
            response_raw = self.call_llm(payload, self.model)
            self.messages.append(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": response_raw}],
                }
            )

            # Detect inline skill requests (<skill> markers) and resolve them before continuing.
            skill_refs = self.skill_manager.extract_requests(response_raw)
            if not skill_refs:
                break

            self.latest_skill_outputs = []
            for ref in skill_refs:
                # Each skill request is immediately answered inline, letting the LLM iterate.
                reply_text, found = self.skill_manager.build_skill_reply(ref)
                self.latest_skill_outputs.append(
                    {
                        "title": ref,
                        "body": reply_text,
                        "available": found,
                    }
                )
                self.messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": reply_text}],
                    }
                )

            skill_turns += 1
            if skill_turns >= MAX_SKILL_TURNS:
                # Avoid infinite loops when the model keeps asking for skills.
                logger.warning("Skill lookup loop exceeded limit, returning latest response.")
                break

        return response_raw

    def _ensure_system_prompt(self, width: int, height: int) -> None:
        # Skip rebuilding prompt when viewport unchanged to reduce token churn.
        if self.screen_width == width and self.screen_height == height and self.messages:
            return

        skill_section = self.skill_manager.build_catalog_section()
        # The system prompt bundles viewport dimensions and skill catalog.
        # This is rehydrated into the first message so downstream models stay aligned.
        system_prompt = self.prompt_builder.build_system_prompt(
            width=width,
            height=height,
            skill_section=skill_section,
        )
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = [{"type": "text", "text": system_prompt}]
        else:
            self.messages.insert(
                0,
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
            )

        self.screen_width = width
        self.screen_height = height

    @staticmethod
    def _strip_skill_markers(response: str) -> str:
        if "<skill" not in response.lower():
            return response
        return re.sub(r"<skill>.*?</skill>", "", response, flags=re.IGNORECASE | re.DOTALL).strip()

    def reset(self, _logger=None):
        global logger
        logger = (
            _logger if _logger is not None
            else logging.getLogger("desktopenv.qwen3vl_agent")
        )

        # Clear state between agent runs to avoid leaking context.
        self.messages = []
        self.conversation_started = False
        self.executed_actions = []
        self.screen_width = None
        self.screen_height = None
        self.latest_skill_outputs = []
        self.skill_manager.reset_cache()
    
    @backoff.on_exception(
        backoff.constant,
        (httpx.HTTPError, RuntimeError),
        interval=3,
        max_tries=5,
    )
    def call_llm(self, payload, model):
        # Dispatch to configured provider; defaults to Tip Cloud compatible endpoint.
        provider = (os.environ.get("TIP_LLM_PROVIDER") or "tip_cloud").lower()
        if provider == "ollama":
            return self._call_llm_ollama(payload, model)
        if provider in {"static_openai", "tip_cloud"}:
            return self._call_llm_openai(payload, model)
        return self._call_llm_openai(payload, model)

    def _call_llm_tip(self, payload, model):
        """Call the Tip API provider (OpenAI compatible chat/completions)."""
        base_url = os.environ.get("TIP_LLM_BASE_URL", DEFAULT_TIP_BASE_URL)
        url = base_url.rstrip("/") + "/chat/completions"

        headers = {"Content-Type": "application/json"}
        # Optional headers support both JSON blob and raw Authorization strings.
        extra_headers = os.environ.get("TIP_LLM_HEADERS")
        if extra_headers:
            try:
                headers.update(json.loads(extra_headers))
            except json.JSONDecodeError:
                headers["Authorization"] = extra_headers

        timeout = float(os.environ.get("TIP_LLM_TIMEOUT", 60))

        body = dict(payload)
        body["model"] = model or self.model
        body.setdefault("max_tokens", self.max_tokens)
        body.setdefault("temperature", self.temperature)
        body.setdefault("top_p", self.top_p)
        body["stream"] = False
        body["extra_body"] = {"reasoning": {"enabled": False}}

        # Use plain POST instead of SDK to minimize dependencies in the sidecar.
        logger.info(f"[TipLLM] POST {url} model={body['model']}")
        response = httpx.post(url, json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        text = self._extract_text_from_tip_response(data)
        if not text:
            raise RuntimeError("LLM response missing content")
        return text

    def _call_llm_openai(self, payload, model):
        base_url = os.environ.get("TIP_OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
        api_key = (
            os.environ.get("TIP_OPENAI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        ).strip()
        if not api_key:
            raise RuntimeError("OpenAI API Key not configured")
        extra_headers = os.environ.get("TIP_LLM_HEADERS")
        default_headers = None
        if extra_headers:
            try:
                default_headers = json.loads(extra_headers)
            except json.JSONDecodeError:
                default_headers = {"Authorization": extra_headers}
        # Build client per-call to keep configuration localized.
        client_kwargs = {
            "api_key": api_key,
            "base_url": base_url,
        }
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        body = dict(payload)
        body["model"] = model or self.model
        body.setdefault("max_tokens", self.max_tokens)
        body.setdefault("temperature", self.temperature)
        body.setdefault("top_p", self.top_p)
        body["stream"] = False

        # Client is created per-call so different runs can swap API keys on the fly.
        client = OpenAI(**client_kwargs)
        timeout = float(os.environ.get("TIP_LLM_TIMEOUT", 60))
        response = client.chat.completions.create(timeout=timeout, **body)
        data = response.model_dump()
        text = self._extract_text_from_tip_response(data)
        if not text:
            raise RuntimeError("OpenAI response missing content")
        return text

    def _call_llm_ollama(self, payload, model):
        base_url = os.environ.get("TIP_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        chat_url = base_url + "/api/chat"
        resolved_model = os.environ.get("TIP_OLLAMA_MODEL") or model or self.model
        timeout = float(os.environ.get("TIP_LLM_TIMEOUT", 60))
        options = {
            "temperature": payload.get("temperature", self.temperature),
            "num_predict": payload.get("max_tokens", self.max_tokens),
        }
        # Keep only essential fields to match Ollama chat API surface.
        # Messages are normalised so images live in a dedicated array.
        # Streaming is disabled here because the agent loop expects full text.
        messages = self._normalize_ollama_messages(payload.get("messages") or [])
        body = {
            "model": resolved_model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        # Ollama endpoint is local; prefer short timeouts to surface errors quickly.
        logger.info(f"[Ollama] POST {chat_url} model={resolved_model}")
        response = httpx.post(chat_url, json=body, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        text = self._extract_text_from_ollama_response(data)
        if not text:
            raise RuntimeError("Ollama response missing content")
        return text

    @staticmethod
    def _extract_text_from_tip_response(resp: Dict) -> str:
        # Tip/OpenAI responses can be string or list-of-parts; prefer the first text chunk.
        choices = resp.get("choices") or []
        for choice in choices:
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and "text" in part
                ]
                if parts:
                    return "".join(parts)
        return ""

    def _normalize_ollama_messages(self, messages: List[Dict]) -> List[Dict]:
        # Ollama expects plain text content with base64 images attached separately.
        # We collapse multimodal entries into newline-separated strings to stay concise.
        # Empty user text is replaced with a friendly hint so the model still has context.
        normalized: List[Dict] = []
        for message in messages:
            role = message.get("role") or "user"
            content = message.get("content")
            text_value = ""
            images: List[str] = []
            if isinstance(content, list):
                text_value, images = self._split_multimodal_content(content)
            elif isinstance(content, str):
                text_value = content
            if not text_value and role == "user":
                text_value = "请结合提供的截图理解用户意图。"
            entry: Dict[str, object] = {
                "role": role,
                "content": text_value,
            }
            if images:
                entry["images"] = images
            normalized.append(entry)
        return normalized

    def _split_multimodal_content(self, content: List[Dict]) -> Tuple[str, List[str]]:
        texts: List[str] = []
        images: List[str] = []
        for part in content:
            part_type = part.get("type")
            if part_type == "text":
                text_value = part.get("text")
                if text_value:
                    texts.append(text_value)
            elif part_type == "image_url":
                image_url = (part.get("image_url") or {}).get("url")
                if image_url:
                    images.append(self._normalize_image_payload(image_url))
        return "\n\n".join(texts).strip(), images

    @staticmethod
    def _normalize_image_payload(reference: str) -> str:
        # Ollama only needs the base64 payload; strip data URI prefix if present.
        if reference.startswith("data:"):
            _, _, payload = reference.partition(",")
            return payload or reference
        return reference

    @staticmethod
    def _extract_text_from_ollama_response(payload: Dict) -> str:
        message = payload.get("message") or {}
        text = message.get("content")
        if isinstance(text, str):
            return text.strip()
        response = payload.get("response")
        if isinstance(response, str):
            return response.strip()
        return ""

    def _log_conversation_transcript(self, prefix: str) -> None:
        if logger is None:
            return
        lines = []
        for idx, message in enumerate(self.messages, start=1):
            role = message.get("role", "?")
            # Flatten multimodal message for logging to avoid huge blobs in logs.
            fragments = []
            for part in message.get("content", []):
                part_type = part.get("type")
                if part_type == "text":
                    fragments.append(part.get("text", ""))
                elif part_type == "image_url":
                    fragments.append("[image]")
                else:
                    fragments.append(f"[{part_type}]")
            text = " ".join(fragments).strip() or "(empty)"
            lines.append(f"{idx}. [{role}] {text}")
        if lines:
            logger.debug("%s\n%s", prefix, "\n".join(lines))

    def _prepare_messages_for_send(
        self,
        *,
        max_messages: int = 12,
        max_images: int = 1,
    ) -> List[Dict]:
        """
        Trim conversation to avoid oversized payloads:
        - Always keep system prompt if present.
        - Limit total messages and inline images (keep only the latest image).
        - Older image messages have their images stripped and replaced with a short note.
        """
        if not self.messages:
            return []

        # A shallow copy lets us remove system prompt temporarily without mutating state.
        # The method is intentionally conservative: it never adds new content,
        # it only discards items that would otherwise bloat the payload.
        system_msg = None
        remaining = list(self.messages)
        if remaining and (remaining[0].get("role") == "system"):
            system_msg = remaining.pop(0)

        trimmed: List[Dict] = []
        image_budget = max_images
        for raw in reversed(remaining):
            role = raw.get("role", "user")
            parts = raw.get("content", [])
            text_parts = [p for p in parts if p.get("type") == "text"]
            image_parts = [p for p in parts if p.get("type") == "image_url"]

            content: List[Dict] = []
            if image_parts and image_budget > 0:
                image_budget -= 1
                if text_parts:
                    content.extend(text_parts)
                content.append(image_parts[0])
            else:
                if text_parts:
                    content.extend(text_parts)
                elif image_parts:
                    content.append({"type": "text", "text": "(previous screenshot omitted)"})

            trimmed.append({"role": role, "content": content})
            if len(trimmed) >= max_messages:
                break

        # Restore chronological order and reattach system prompt if present.
        # This keeps downstream models aligned with the original conversation flow.
        trimmed.reverse()
        if system_msg:
            trimmed.insert(0, system_msg)
        return trimmed
