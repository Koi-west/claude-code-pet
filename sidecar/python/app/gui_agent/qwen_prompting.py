# File: python/app/gui_agent/qwen_prompting.py
# Project: Tip Desktop Assistant
# Description: Builds system and user prompts for the Qwen agent including tool and skill sections.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from typing import Dict, List, Optional

from .prompts import load_prompt

SYSTEM_PROMPT_TEMPLATE = load_prompt("system_prompt")
TOOL_DESCRIPTION_PROMPT = load_prompt("tool_description_prompt")


class PromptBuilder:
    """Compose prompts and helper messages for the Qwen agent."""

    def build_system_prompt(
        self,
        *,
        width: int,
        height: int,
        skill_section: str,
    ) -> str:
        return (
            SYSTEM_PROMPT_TEMPLATE.replace("{width}", str(width))
            .replace("{height}", str(height))
            .replace("{{tools_def}}", TOOL_DESCRIPTION_PROMPT)
            .replace("{{skill_section}}", skill_section)
        )

    @staticmethod
    def build_user_message(
        *,
        text: Optional[str],
        image_base64: Optional[str],
    ) -> Dict:
        content: List[Dict] = []
        if text:
            content.append({"type": "text", "text": text})
        if image_base64:
            img_url = f"data:image/png;base64,{image_base64}"
            content.append({"type": "image_url", "image_url": {"url": img_url}})
        return {
            "role": "user",
            "content": content,
        }
