# File: python/app/gui_agent/run_loop.py
# Project: Tip Desktop Assistant
# Description: Execution loop for local GUI tasks: logging, screenshots, 
# recording, and action replay with cancellation support.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

"""
本地MacOS Demo任务执行模块
精简版 - 只包含本地MacOS环境所需的核心功能
"""
import datetime
import time
import json
import logging
import os
from typing import Callable, Dict, Optional
from threading import Event

logger = logging.getLogger("desktopenv.experiment")


def run_single_example(
    agent,
    env,
    example,
    max_steps,
    instruction,
    args,
    example_result_dir,
    scores,
    *,
    log_callback: Optional[Callable[[Dict], None]] = None,
    cancel_event: Optional[Event] = None,
):
    """
    执行单个任务示例
    
    Args:
        agent: Agent实例
        env: 本地MacOS环境实例
        example: 任务配置字典
        max_steps: 最大执行步数
        instruction: 任务指令
        args: 参数对象
        example_result_dir: 结果保存目录
        scores: 得分列表（用于记录结果）
    """
    runtime_logger = setup_logger(example, example_result_dir)
    log_dispatcher = _build_log_dispatcher(log_callback)
    
    # 重置Agent
    try:
        agent.reset(runtime_logger)
    except Exception as e:
        agent.reset()

    # 重置环境
    logger.info("---------------------------reset env---------------------------")
    t0 = time.time()
    log_dispatcher(
        {
            "type": "status",
            "message": "Initializing environment…",
        }
    )

    obs = env.reset(task_config=example)
    t1 = time.time()
    logger.info(f"reset time: {t1 - t0:.2f}s") 

    # 保存初始状态截图
    action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    screenshot_data = _normalize_screenshot(obs['screenshot'])
    obs['screenshot'] = screenshot_data

    reset_filename = f"step_reset_{action_timestamp}.png"
    reset_filepath = os.path.join(example_result_dir, reset_filename)
    with open(reset_filepath, "wb") as _f:
        _f.write(obs['screenshot'])

    log_dispatcher(
        {
            "type": "screenshot",
            "step": 0,
            "message": "Initial screenshot captured",
            "assets": [
                {
                    "type": "screenshot",
                    "path": reset_filepath,
                    "relative_path": reset_filename,
                }
            ],
        }
    )

    # 记录初始状态到轨迹文件
    with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
        traj_json = {
            "step_num": 0,
            "instruction": instruction,
            "action_timestamp": action_timestamp,
            "action": "reset",
            "reward": 0,
            "done": False,
            "info": {},
            "screenshot_file": f"step_reset_{action_timestamp}.png"
        }
        f.write(json.dumps(traj_json, ensure_ascii=False))
        f.write("\n")

    # 开始录屏（如果环境支持）
    if hasattr(env, 'controller') and env.controller is not None:
        env.controller.start_recording()
        log_dispatcher(
            {
                "type": "status",
                "message": "Screen recording started",
            }
        )
    
    # 执行任务循环
    done = False
    step_idx = 0
    
    while not done and step_idx < max_steps:
        if cancel_event and cancel_event.is_set():
            log_dispatcher(
                {
                    "type": "status",
                    "message": "Execution cancelled by user",
                }
            )
            break
        logger.info("---------------------------agent predict---------------------------")
        t0 = time.time()
        response, actions = agent.predict(instruction, obs)
        skill_outputs = getattr(agent, "latest_skill_outputs", [])
        if skill_outputs:
            for skill_item in skill_outputs:
                log_dispatcher(
                    {
                        "type": "skill",
                        "step": step_idx + 1,
                        "message": f'Skill "{skill_item["title"]}" provided',
                        "details": {
                            "body": skill_item["body"],
                            "available": skill_item.get("available", False),
                        },
                    }
                )
        t1 = time.time()
        logger.info(f"agent predict time: {t1 - t0:.2f}s") 
        
        # 检查response是否包含HTML错误页面（如503错误）
        if (
            response
            and isinstance(response, str)
            and ("<html>" in response.lower() or "503 service" in response.lower())
        ):
            logger.error(
                f"Agent predict returned HTML error page at step {step_idx}: {response[:200]}"
            )
            raise RuntimeError(
                "LLM service returned error page (likely 503 or similar): "
                f"{response[:100]}"
            )
        
        # 检查是否获取到有效的actions
        if not actions or len(actions) == 0:
            if skill_outputs:
                action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
                skill_info = [
                    {
                        "title": item["title"],
                        "body": item["body"],
                        "available": item.get("available", False),
                    }
                    for item in skill_outputs
                ]
                with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "step_num": step_idx + 1,
                                "action_timestamp": action_timestamp,
                                "action": "skill",
                                "response": response,
                                "reward": 0,
                                "done": False,
                                "info": {"skills": skill_info},
                                "screenshot_file": None,
                            },
                            ensure_ascii=False,
                        )
                    )
                    f.write("\n")
                if hasattr(agent, "latest_skill_outputs"):
                    agent.latest_skill_outputs = []
                step_idx += 1
                continue
            logger.warning(f"Agent predict returned empty actions at step {step_idx}")
            if step_idx == 0:
                raise RuntimeError("Agent predict failed at first step - LLM service may be unavailable")
            break
        if hasattr(agent, "latest_skill_outputs"):
            agent.latest_skill_outputs = []
            
        # 执行每个动作
        for action in actions:
            if cancel_event and cancel_event.is_set():
                log_dispatcher(
                    {
                        "type": "status",
                        "message": "Execution cancelled by user",
                    }
                )
                done = True
                break
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)

            log_dispatcher(
                {
                    "type": "step",
                    "step": step_idx + 1,
                    "message": action,
                    "details": {
                        "response": response,
                    },
                }
            )
            
            # 执行动作
            obs, reward, done, info = env.step(action, args.sleep_after_execution)

            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            
            # 保存截图
            screenshot_data = _normalize_screenshot(obs['screenshot'])
            obs['screenshot'] = screenshot_data
            
            screenshot_filename = f"step_{step_idx + 1}_{action_timestamp}.png"
            screenshot_path = os.path.join(example_result_dir, screenshot_filename)
            with open(screenshot_path, "wb") as _f:
                _f.write(obs['screenshot'])

            log_dispatcher(
                {
                    "type": "screenshot",
                    "step": step_idx + 1,
                    "message": "Screenshot captured",
                    "assets": [
                        {
                            "type": "screenshot",
                            "path": screenshot_path,
                            "relative_path": screenshot_filename,
                        }
                    ],
                    "details": {
                        "reward": reward,
                        "done": done,
                        "info": info,
                    },
                }
            )
            
            # 记录轨迹
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "response": response,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }, ensure_ascii=False))
                f.write("\n")
            
            if done:
                logger.info("The episode is done.")
                log_dispatcher(
                    {
                        "type": "status",
                        "step": step_idx + 1,
                        "message": info.get("termination", "Task completed"),
                        "details": {
                            "reward": reward,
                            "info": info,
                        },
                    }
                )
                break
        
        step_idx += 1
    
    # 评估结果
    if cancel_event and cancel_event.is_set():
        log_dispatcher(
            {
                "type": "complete",
                "status": "cancelled",
                "message": "GUI agent run cancelled",
                "result_dir": example_result_dir,
            }
        )
        scores.append(None)
    elif 'enhanced_task_id' in example:
        # Enhanced task: 跳过自动评估，等待RM评分
        result = "PENDING_FOR_RM"
        logger.info("Enhanced task detected (enhanced_task_id: %s), skipping evaluation. Result: %s", 
                   example['enhanced_task_id'], result)
        scores.append(None)  # 不计入统计
        with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
            f.write(f"{result}\n")
        log_dispatcher(
            {
                "type": "complete",
                "status": "pending",
                "message": "Waiting for RM evaluation",
                "details": {
                    "enhanced_task_id": example['enhanced_task_id'],
                },
                "result_dir": example_result_dir,
            }
        )
    else:
        # 普通evaluation task: 正常评估
        result = env.evaluate()
        logger.info("Result: %.2f", result)
        scores.append(result)
        with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
            f.write(f"{result}\n")
        log_dispatcher(
            {
                "type": "complete",
                "status": "success" if result >= 1 else "partial",
                "score": result,
                "message": "GUI agent run completed",
                "result_dir": example_result_dir,
            }
        )
    
    # 结束录屏（如果环境支持）
    if hasattr(env, 'controller') and env.controller is not None:
        recording_path = os.path.join(example_result_dir, "recording.mp4")
        env.controller.end_recording(recording_path)
        if os.path.exists(recording_path):
            log_dispatcher(
                {
                    "type": "status",
                    "message": "Recording saved",
                    "assets": [
                        {
                            "type": "video",
                            "path": recording_path,
                            "relative_path": "recording.mp4",
                        }
                    ],
                }
            )


def setup_logger(example, example_result_dir):
    """
    为单个任务设置日志记录器
    
    Args:
        example: 任务配置字典
        example_result_dir: 结果保存目录
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    runtime_logger = logging.getLogger(f"desktopenv.example.{example['id']}")
    runtime_logger.setLevel(logging.DEBUG)
    runtime_logger.addHandler(logging.FileHandler(
        os.path.join(example_result_dir, "runtime.log"),
        encoding="utf-8"
    ))
    return runtime_logger


def _build_log_dispatcher(callback: Optional[Callable[[Dict], None]]):
    def _dispatcher(payload: Dict) -> None:
        if callback is None:
            return
        callback(payload)

    return _dispatcher


def _normalize_screenshot(screenshot):
    """
    标准化截图数据为字节对象
    
    Args:
        screenshot: 截图数据（可能是base64字符串、字节对象或其他格式）
    
    Returns:
        bytes: 标准化后的字节对象
    """
    if isinstance(screenshot, str):
        # 如果是base64字符串，解码为字节
        import base64
        return base64.b64decode(screenshot)
    elif isinstance(screenshot, bytes):
        return screenshot
    else:
        # 尝试直接转换为字节
        return bytes(screenshot)

# 本地MacOS Demo只需要上面的核心函数
# 其他函数（run_single_example_human、run_single_example_agi等）已被移除
# 如需其他功能，请参考原始OSWorld项目
