# File: python/app/gui_agent/qwen_response_parser.py
# Project: Tip Desktop Assistant
# Description: Parses LLM responses into low-level instructions and pyautogui code, handling tool_call blocks.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple


def parse_response(
    response: str,
    *,
    coordinate_type: str,
    logger: logging.Logger,
    original_width: Optional[int] = None,
    original_height: Optional[int] = None,
    processed_width: Optional[int] = None,
    processed_height: Optional[int] = None,
) -> Tuple[str, List[str]]:
    """
    Parse LLM response and convert it to low level instruction + pyautogui code.
    """
    # The parser is intentionally permissive to handle partially streamed outputs.
    low_level_instruction = ""
    pyautogui_code: List[str] = []

    # Return early when there is nothing to parse; keeps downstream callers simple.
    if response is None or not response.strip():
        return low_level_instruction, pyautogui_code

    # Basic text extraction so a plain "Action:" block is still handled without tool calls.
    action_match = re.search(r"Action:\s*(.*)", response, re.IGNORECASE)
    if action_match:
        action_text = action_match.group(1).strip()
        for marker in ("<tool_call", "<skill"):
            if marker in action_text:
                action_text = action_text.split(marker, 1)[0].strip()
        if action_text:
            low_level_instruction = action_text

    def adjust_coordinates(x: float, y: float) -> Tuple[int, int]:
        # Convert model-relative coordinates into actual screen coordinates.
        # When original dimensions are missing, fallback to integers as-is.
        # Relative mode assumes a 0-1000 grid similar to the model's prompt template.
        if not (original_width and original_height):
            return int(x), int(y)
        if coordinate_type == "absolute":
            if processed_width and processed_height:
                x_scale = original_width / processed_width
                y_scale = original_height / processed_height
                return int(x * x_scale), int(y * y_scale)
            return int(x), int(y)
        if coordinate_type == "relative":
            base = 1000.0
        else:
            base = 999.0
        x_scale = original_width / base
        y_scale = original_height / base
        return int(x * x_scale), int(y * y_scale)

    def _coerce_json(text: str) -> Optional[dict]:
        # Be tolerant to trailing braces or whitespace in model outputs.
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            opening = stripped.count("{")
            closing = stripped.count("}")
            # Some streamed outputs duplicate closing braces; trim them gradually.
            while closing > opening and stripped.endswith("}"):
                stripped = stripped[:-1].rstrip()
                closing = stripped.count("}")
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return None

    def process_tool_call(json_str: str) -> None:
        try:
            tool_call = _coerce_json(json_str)
            if not isinstance(tool_call, dict):
                return
            args = None
            if tool_call.get("name") == "computer_use" and "arguments" in tool_call:
                args = tool_call["arguments"]
            elif "action" in tool_call:
                args = tool_call

            if not isinstance(args, dict):
                return

            # Normalise action names; some models output uppercase or synonyms.
            raw_action = args.get("action")
            action = ""
            if isinstance(raw_action, str):
                action = raw_action.strip().lower()
            elif raw_action is not None:
                action = str(raw_action).strip().lower()

            alias_map = {
                "click": "left_click",
            }
            action = alias_map.get(action, action)

            # Map supported actions to pyautogui snippets with coordinate adjustment.
            if action == "left_click":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    pyautogui_code.append(f"pyautogui.click({adj_x}, {adj_y})")
                else:
                    pyautogui_code.append("pyautogui.click()")

            elif action == "right_click":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    pyautogui_code.append(
                        f"pyautogui.rightClick({adj_x}, {adj_y})"
                    )
                else:
                    pyautogui_code.append("pyautogui.rightClick()")

            elif action == "middle_click":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    pyautogui_code.append(
                        f"pyautogui.middleClick({adj_x}, {adj_y})"
                    )
                else:
                    pyautogui_code.append("pyautogui.middleClick()")

            elif action == "double_click":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    pyautogui_code.append(
                        f"pyautogui.doubleClick({adj_x}, {adj_y})"
                    )
                else:
                    pyautogui_code.append("pyautogui.doubleClick()")

            elif action == "type":
                raw_text = args.get("text", "")
                safe_text = json.dumps(str(raw_text), ensure_ascii=False)
                # Use clipboard to avoid typing latency and preserve unicode.
                pyautogui_code.append(
                    "import pyperclip; "
                    f"text_to_type = {safe_text}; "
                    "pyperclip.copy(text_to_type); "
                    "pyautogui.hotkey('command', 'v')"
                )

            elif action == "key":
                keys = args.get("keys", [])
                if isinstance(keys, list):
                    cleaned_keys = []
                    for key in keys:
                        # Normalise key arrays that arrive as embedded strings.
                        if isinstance(key, str):
                            if key.startswith("keys=["):
                                key = key[6:]
                            if key.endswith("]"):
                                key = key[:-1]
                            if key.startswith("['") or key.startswith('["'):
                                key = key[2:] if len(key) > 2 else key
                            if key.endswith("']") or key.endswith('"]'):
                                key = key[:-2] if len(key) > 2 else key
                            key = key.strip()
                            if key.lower() in {"ctrl", "control"}:
                                key = "command"
                            cleaned_keys.append(key)
                        else:
                            cleaned_keys.append(key)
                    keys = cleaned_keys

                keys_str = ", ".join([f"'{key}'" for key in keys])
                if len(keys) > 1:
                    pyautogui_code.append(f"pyautogui.hotkey({keys_str})")
                else:
                    pyautogui_code.append(f"pyautogui.press({keys_str})")

            elif action == "scroll":
                pixels = args.get("pixels", 0)
                pyautogui_code.append(f"pyautogui.scroll({pixels})")

            elif action == "wait":
                # WAIT acts as a no-op placeholder for the executor loop.
                pyautogui_code.append("WAIT")

            elif action == "terminate":
                # DONE is used by the executor to stop issuing further instructions.
                pyautogui_code.append("DONE")

            elif action == "mouse_move":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    pyautogui_code.append(f"pyautogui.moveTo({adj_x}, {adj_y})")
                else:
                    pyautogui_code.append("pyautogui.moveTo(0, 0)")

            elif action == "left_click_drag":
                if "coordinate" in args:
                    x, y = args["coordinate"]
                    adj_x, adj_y = adjust_coordinates(x, y)
                    duration = args.get("duration", 0.5)
                    pyautogui_code.append(
                        f"pyautogui.dragTo({adj_x}, {adj_y}, duration={duration})"
                    )
                else:
                    pyautogui_code.append("pyautogui.dragTo(0, 0)")
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to parse tool call: %s", exc)

    normalized_response = (
        response.replace("<tool_call>", "\n<tool_call>\n")
        .replace("</tool_call>", "\n</tool_call>\n")
    )
    # Normalise line breaks so streaming output is easier to scan.
    lines = normalized_response.split("\n")
    inside_tool_call = False
    current_tool_call: List[str] = []

    # Walk line-by-line so partial tool_call blocks are captured reliably.
    # We only collect JSON-looking lines inside <tool_call> boundaries.
    # Each completed block is parsed immediately, reducing memory footprint.
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith(("action:")):
            if not low_level_instruction:
                remainder = line.split("Action:", 1)[1].strip()
                for marker in ("<tool_call", "<skill"):
                    if marker in remainder:
                        remainder = remainder.split(marker, 1)[0].strip()
                if remainder:
                    low_level_instruction = remainder
            continue

        if line.startswith("<tool_call>"):
            inside_tool_call = True
            continue
        if line.startswith("</tool_call>"):
            if current_tool_call:
                process_tool_call("\n".join(current_tool_call))
                current_tool_call = []
            inside_tool_call = False
            continue

        if inside_tool_call:
            current_tool_call.append(line)
            continue

        if line.startswith("{") and line.endswith("}"):
            # Handle compact JSON blobs emitted without <tool_call> wrapper.
            # We only care about entries containing name + arguments to match the schema.
            try:
                json_obj = json.loads(line)
                if "name" in json_obj and "arguments" in json_obj:
                    process_tool_call(line)
            except json.JSONDecodeError:
                pass

    if current_tool_call:
        process_tool_call("\n".join(current_tool_call))

    if not low_level_instruction and len(pyautogui_code) > 0:
        first_cmd = pyautogui_code[0]
        if "." in first_cmd:
            action_type = first_cmd.split(".", 1)[1].split("(", 1)[0]
        else:
            action_type = first_cmd
        # Provide a human-readable fallback when the model only returned tool calls.
        # This keeps the UI responsive even if Action: was omitted.
        low_level_instruction = f"Performing {action_type} action"

    return low_level_instruction, pyautogui_code
