# File: python/app/gui_agent/runner.py
# Project: Tip Desktop Assistant
# Description: Command-line runner that prepares agent and environment, executes one GUI prompt, and saves results.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

"""
Minimal entry point for running a single GUI automation prompt.
This module removes the interactive demo UI and exposes a small function
that takes a user instruction, prepares the environment/agent, and runs it.
"""

import argparse
import datetime
import json
import os
from threading import Event
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional

from . import run_loop
from .local_env import LocalMacOSEnv
from .qwen_agent import Qwen3VLAgent
from .skills import SkillRepository


def build_default_args(**overrides: Any) -> SimpleNamespace:
    """Create a lightweight args namespace with sane defaults for the agent."""
    default_model = (
        os.environ.get("TIP_LLM_MODEL")
        or os.environ.get("MODEL_NAME")
        or "ms-ltl6mf2l"
    )
    # Defaults mirror the GUI agent runtime but trim history for faster single-shot runs.
    # Values can be overridden by env or explicit kwargs to align with experiments.
    args = SimpleNamespace(
        model=default_model,
        temperature=0.2,
        top_p=0.95,
        top_k=20,
        max_tokens=2048,
        repetition_penalty=1.0,
        presence_penalty=0.0,
        max_steps=20,
        history_n=2,
        coord="relative",
        action_space="pyautogui",
        observation_type="screenshot",
        sleep_after_execution=0.5,
        result_dir="results_core",
    )

    # Allow callers to override any field without constructing argparse.Namespace manually.
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def _create_task_config(instruction: str, task_id: str) -> Dict[str, Any]:
    """Generate the minimal task config used by lib_run_single."""
    # Only the evaluator and metadata are required for the downstream runner.
    # The evaluator is set to infeasible to avoid scoring when not needed.
    return {
        "id": task_id,
        "snapshot": "prompt",
        "instruction": instruction,
        "source": "core_runner",
        "config": [],
        "related_apps": [],
        "evaluator": {
            "func": "infeasible",
            "result": 1.0,
            "expected": {},
        },
    }


def run_prompt(
    instruction: str,
    *,
    args: Optional[SimpleNamespace] = None,
    result_root: Optional[str] = None,
    log_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_event: Optional[Event] = None,
    skills_repo: Optional[SkillRepository] = None,
) -> Dict[str, Any]:
    """
    Execute a single instruction and return metadata about the run.

    Returns:
        dict(task_id=str, result_dir=str, score=float|None)
    """
    if not instruction or not instruction.strip():
        raise ValueError("Instruction不能为空")

    args = args or build_default_args()
    base_result_dir = result_root or getattr(args, "result_dir", "results_core")

    # Generate a unique run directory; timestamp helps avoid collisions.
    task_id = f"prompt_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task_config = _create_task_config(instruction, task_id)

    def _emit_event(payload: Dict[str, Any]) -> None:
        if log_callback is None:
            return
        # Attach consistent metadata so consumers (CLI/GUI) can render logs uniformly.
        enriched = {
            "task_id": task_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        enriched.update(payload)
        log_callback(enriched)

    # results_core/<action>/<obs>/<model>/<task_id>
    result_dir = os.path.join(
        base_result_dir,
        args.action_space,
        args.observation_type,
        args.model,
        task_id,
    )
    os.makedirs(result_dir, exist_ok=True)

    # Persist inputs for reproducibility and later inspection.
    with open(os.path.join(result_dir, "task_config.json"), "w", encoding="utf-8") as f:
        json.dump(task_config, f, ensure_ascii=False, indent=2)

    with open(os.path.join(result_dir, "args.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)

    env = LocalMacOSEnv(action_space=args.action_space, platform="macos")
    # Agent mirrors runtime defaults but can be injected with custom skill repo for tests.
    agent = Qwen3VLAgent(
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        top_k=args.top_k,
        repetition_penalty=args.repetition_penalty,
        presence_penalty=args.presence_penalty,
        max_steps=args.max_steps,
        action_space=args.action_space,
        coordinate_type=args.coord,
        history_n=args.history_n,
        platform="macos",
        observation_type=args.observation_type,
        skills_repo=skills_repo,
    )

    # cancel_event allows callers (e.g., GUI) to abort mid-run; run_single_example honors it.
    # Score list is mutated by run_single_example; keep it local to avoid shared state.
    scores = []
    _emit_event(
        {
            "type": "start",
            "instruction": instruction,
            "result_dir": result_dir,
        }
    )
    try:
        run_loop.run_single_example(
            agent=agent,
            env=env,
            example=task_config,
            max_steps=args.max_steps,
            instruction=instruction,
            args=args,
            example_result_dir=result_dir,
            scores=scores,
            log_callback=_emit_event,
            cancel_event=cancel_event,
        )
    except Exception as exc:
        # Emit an error event before bubbling up so callers can log/clean up.
        _emit_event(
            {
                "type": "error",
                "message": str(exc),
                "result_dir": result_dir,
            }
        )
        raise
    finally:
        # Always close environment to release OS hooks and temp files.
        env.close()

    return {
        "task_id": task_id,
        "result_dir": result_dir,
        "score": scores[0] if scores else None,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run a single GUI prompt without the interactive shell.")
    parser.add_argument("prompt", help="用户指令，用于驱动Agent")
    parser.add_argument(
        "--result-root",
        default=None,
        help="结果输出根目录，默认使用 build_default_args() 中的 result_dir",
    )
    cli_args = parser.parse_args()

    # Entry point for CLI usage; wraps run_prompt and prints a concise summary.
    run_info = run_prompt(cli_args.prompt, result_root=cli_args.result_root)
    score_display = run_info["score"]
    print(f"任务 {run_info['task_id']} 已完成，结果目录: {run_info['result_dir']} (score={score_display})")


if __name__ == "__main__":
    _main()
