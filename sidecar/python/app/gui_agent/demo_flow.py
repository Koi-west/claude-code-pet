# File: python/app/gui_agent/demo_flow.py
# Project: Tip Desktop Assistant
# Description: Offline demo showcasing the Qwen agent prompt flow with scripted responses and mock screenshots.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

"""
Simple offline demo that shows how the refactored Qwen agent constructs prompts
and reacts to scripted LLM responses. Run with:

    python -m python.app.gui_agent.demo_flow
"""

from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

from .qwen_agent import Qwen3VLAgent
from .skills import SkillRepository


def _make_obs(width: int, height: int, color: Tuple[int, int, int]) -> Dict:
    img = Image.new("RGB", (width, height), color=color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return {"screenshot": buffer.getvalue(), "accessibility_tree": None}


class MockQwenAgent(Qwen3VLAgent):
    """
    A Qwen agent that bypasses network requests and uses scripted responses.
    """

    def __init__(self, scripted_responses: List[str], **kwargs):
        super().__init__(**kwargs)
        self._scripted_responses = scripted_responses
        self._response_idx = 0

    def _call_llm_tip(self, payload, model):  # type: ignore[override]
        print("\n====== Mock LLM Call #{} ======".format(self._response_idx + 1))
        for idx, msg in enumerate(payload["messages"]):
            role = msg["role"]
            print(f"[{idx}] role={role}")
            for part in msg.get("content", []):
                if part.get("type") == "image_url":
                    print("    (image payload omitted)")
                else:
                    text = part.get("text", "")
                    print("    " + text)
        print("================================\n")

        if self._response_idx >= len(self._scripted_responses):
            response = self._scripted_responses[-1]
        else:
            response = self._scripted_responses[self._response_idx]
        self._response_idx += 1
        print(f"Mock response #{self._response_idx}: {response}\n")
        return response


def run_demo() -> None:
    repo_path = Path(__file__).parent / "skills"
    skills_repo = SkillRepository(repo_path)

    scripted_responses = [
        (
            "Thought: I need the Chrome search steps to find the terminal tab.\n"
            "Action: Requesting Chrome search skill.\n"
            "<skill>chrome-search</skill>"
        ),
        (
            "Thought: I'll open the VSCode terminal using the class icon I just learned about.\n"
            "Action: Double-clicking the VSCode icon.\n"
            "<tool_call>\n"
            '{"name": "computer_use", "arguments": {"action": "double_click", "coordinate": [400, 520]}}\n'
            "</tool_call>"
        ),
        (
            "Thought: The terminal looks open; I will stop.\n"
            "Action: Terminate task.\n"
            "<tool_call>\n"
            '{"name": "computer_use", "arguments": {"action": "terminate", "status": "success"}}\n'
            "</tool_call>"
        ),
    ]

    agent = MockQwenAgent(scripted_responses=scripted_responses, skills_repo=skills_repo)
    agent.reset()

    instruction = "在 VSCode 里打开一个新的终端"

    obs1 = _make_obs(1280, 800, (240, 240, 240))
    resp1, actions1 = agent.predict(instruction, obs1)
    print("Step 1 response:", resp1)
    print("Step 1 actions:", actions1)

    obs2 = _make_obs(1280, 800, (210, 210, 210))
    resp2, actions2 = agent.predict(instruction, obs2)
    print("Step 2 response:", resp2)
    print("Step 2 actions:", actions2)

    obs3 = _make_obs(1280, 800, (200, 200, 180))
    resp3, actions3 = agent.predict(instruction, obs3)
    print("Step 3 response:", resp3)
    print("Step 3 actions:", actions3)


if __name__ == "__main__":
    run_demo()
