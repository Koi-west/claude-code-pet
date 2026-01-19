# File: python/app/gui_agent/local_env.py
# Project: Tip Desktop Assistant
# Description: Local macOS GUI automation environment built on pyautogui with screenshot and recording helpers.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

import logging
import time
import pyautogui
import threading
from typing import Dict, Any, Tuple, Optional
from io import BytesIO
from PIL import Image
import numpy as np

logger = logging.getLogger("desktopenv.local_macos")


class LocalMacOSEnv:
    """
    本地MacOS环境类，用于在本地MacOS上执行GUI自动化任务。
    实现与RemoteDesktopEnvClient_sync相同的接口，以便复用现有的执行逻辑。
    """
    
    def __init__(
        self,
        action_space: str = "pyautogui",
        screen_width: int = None,
        screen_height: int = None,
        platform: str = "macos",
        downsample_factor: int = 2,  # 下采样倍数
    ):
        """
        初始化本地MacOS环境
        
        Args:
            action_space: 动作空间类型，目前只支持"pyautogui"
            screen_width: 屏幕宽度（如果为None，会自动获取）
            screen_height: 屏幕高度（如果为None，会自动获取）
            platform: 平台类型，默认为"macos"
            downsample_factor: 截图下采样倍数，默认为2（即长宽各缩小2倍）
        """
        self.action_space = action_space
        self.platform = platform
        self.downsample_factor = downsample_factor
        
        # 获取屏幕尺寸
        if screen_width is None or screen_height is None:
            screen_size = pyautogui.size()
            self.screen_width = screen_size.width
            self.screen_height = screen_size.height
        else:
            self.screen_width = screen_width
            self.screen_height = screen_height
        
        logger.info(f"LocalMacOSEnv initialized with screen size: {self.screen_width}x{self.screen_height}")
        logger.info(f"Screenshot downsample factor: {self.downsample_factor}x")
        
        # 设置pyautogui的安全设置
        pyautogui.FAILSAFE = True  # 鼠标移到屏幕角落可以中止
        pyautogui.PAUSE = 0.5  # 每个pyautogui调用之间的暂停时间
        
        # 用于兼容性的属性
        self.env_id = "local_macos"
        self.env_url = None
        self.env_port = None
        
        # 任务配置
        self.current_task_config = None
        
        # 录屏相关
        self._recording = False
        self._recording_thread: Optional[threading.Thread] = None
        self._video_frames = []
        self._video_writer = None
        self._fps = 10  # 录屏帧率
    
    def _capture_screenshot(self) -> bytes:
        """
        捕获屏幕截图并进行下采样处理
        
        Returns:
            下采样后的截图字节数据（PNG格式）
        """
        # 捕获原始截图
        screenshot = pyautogui.screenshot()
        
        # 如果需要下采样
        if self.downsample_factor > 1:
            original_width, original_height = screenshot.size
            new_width = original_width // self.downsample_factor
            new_height = original_height // self.downsample_factor
            
            # 使用高质量的LANCZOS算法进行下采样
            screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
            
            logger.debug(f"Screenshot downsampled from {original_width}x{original_height} to {new_width}x{new_height}")
        
        # 将PIL Image转换为字节
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        screenshot_bytes = buffer.getvalue()
        
        return screenshot_bytes
    
    def reset(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        重置环境状态
        
        Args:
            task_config: 任务配置字典
            
        Returns:
            包含初始观察的字典，格式为 {"screenshot": bytes, "accessibility_tree": None}
        """
        logger.info("Resetting LocalMacOSEnv...")
        self.current_task_config = task_config
        
        # 等待一小段时间，确保环境稳定
        time.sleep(1)
        
        # 获取初始截图（使用封装的方法）
        screenshot_bytes = self._capture_screenshot()
        
        obs = {
            "screenshot": screenshot_bytes,
            "accessibility_tree": None,  # MacOS暂不支持accessibility tree
        }
        
        logger.info("LocalMacOSEnv reset complete")
        return obs
    
    def step(self, action: str, pause: float = 0.5) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        执行一个动作
        
        Args:
            action: pyautogui代码字符串
            pause: 执行后的暂停时间（秒）
            
        Returns:
            (observation, reward, done, info) 元组
        """
        logger.info(f"Executing action: {action}")
        
        done = False
        reward = 0.0
        info = {}
        
        try:
            # 检查是否是特殊动作
            if action == "DONE":
                logger.info("Task marked as DONE")
                done = True
                reward = 1.0
                info["termination"] = "success"
            elif action == "FAIL":
                logger.info("Task marked as FAIL")
                done = True
                reward = 0.0
                info["termination"] = "failure"
            elif action == "WAIT":
                logger.info("Waiting...")
                time.sleep(2)
            else:
                # 特殊处理：macOS 截图到剪贴板（Command+Control+Shift+3）
                # 检测是否是截图快捷键组合
                is_screenshot_to_clipboard = (
                    "keyDown('command')" in action and
                    "keyDown('control')" in action and
                    "keyDown('shift')" in action and
                    ("keyDown('3')" in action or "press('3')" in action)
                )
                
                if is_screenshot_to_clipboard:
                    logger.info("Detected screenshot to clipboard command, using native screencapture")
                    import subprocess
                    try:
                        # 使用 macOS 原生命令截图到剪贴板
                        # -c 参数表示复制到剪贴板
                        subprocess.run(['screencapture', '-c'], check=True)
                        logger.info("Screenshot captured to clipboard using screencapture")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"screencapture command failed: {e}")
                        # 如果失败，回退到 pyautogui 方式
                        safe_globals = {
                            "pyautogui": pyautogui,
                            "time": time,
                        }
                        exec(action, safe_globals)
                else:
                    # 执行pyautogui代码
                    # 为了安全，使用受限的命名空间
                    safe_globals = {
                        "pyautogui": pyautogui,
                        "time": time,
                    }
                    exec(action, safe_globals)
                    logger.info("Action executed successfully")
            
            # 等待指定时间
            time.sleep(pause)
            
            # 获取新的截图（使用封装的方法）
            screenshot_bytes = self._capture_screenshot()
            
            obs = {
                "screenshot": screenshot_bytes,
                "accessibility_tree": None,
            }
            
            return obs, reward, done, info
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 即使出错也要返回当前截图
            try:
                screenshot_bytes = self._capture_screenshot()
                obs = {
                    "screenshot": screenshot_bytes,
                    "accessibility_tree": None,
                }
            except:
                obs = {
                    "screenshot": b"",
                    "accessibility_tree": None,
                }
            
            info["error"] = str(e)
            return obs, 0.0, False, info
    
    def evaluate(self) -> float:
        """
        评估任务完成情况
        
        对于demo，我们简单返回1.0（成功）
        在实际应用中，这里可以实现更复杂的评估逻辑
        
        Returns:
            评估分数（0.0-1.0）
        """
        logger.info("Evaluating task...")
        # Demo模式下，简单返回1.0
        # 实际应用中可以根据任务配置进行更复杂的评估
        return 1.0
    
    def close(self):
        """
        关闭环境，清理资源
        """
        logger.info("Closing LocalMacOSEnv...")
        
        # 停止录屏（如果正在录制）
        if self._recording:
            logger.info("Stopping recording before closing...")
            self._recording = False
            if self._recording_thread:
                self._recording_thread.join(timeout=5)
        
        self.current_task_config = None
        self._video_frames = []
        logger.info("LocalMacOSEnv closed")
    
    def _recording_worker(self):
        """
        录屏工作线程，持续捕获屏幕帧
        """
        logger.info("Recording worker thread started")
        frame_interval = 1.0 / self._fps
        
        while self._recording:
            try:
                start_time = time.time()
                
                # 捕获屏幕（不下采样，保持原始分辨率）
                screenshot = pyautogui.screenshot()
                
                # 转换为numpy数组（OpenCV格式：BGR）
                frame = np.array(screenshot)
                # 去掉Alpha通道（如果有的话）
                if frame.shape[2] == 4:  # RGBA
                    frame = frame[:, :, :3]  # 去掉Alpha通道，保留RGB
                frame = frame[:, :, ::-1]  # RGB -> BGR
                
                self._video_frames.append(frame)
                
                # 控制帧率
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error capturing frame: {e}")
                break
        
        logger.info(f"Recording worker thread stopped, captured {len(self._video_frames)} frames")
    
    @property
    def controller(self):
        """
        控制器属性（兼容性）
        提供录屏功能
        """
        class RecordingController:
            def __init__(self, env):
                self.env = env
            
            def start_recording(self):
                """开始录屏"""
                if self.env._recording:
                    logger.warning("Recording is already in progress")
                    return
                
                logger.info("Starting screen recording...")
                self.env._recording = True
                self.env._video_frames = []
                
                # 启动录屏线程
                self.env._recording_thread = threading.Thread(
                    target=self.env._recording_worker,
                    daemon=True
                )
                self.env._recording_thread.start()
                logger.info("Screen recording started")
            
            def end_recording(self, filename: str):
                """结束录屏并保存视频"""
                if not self.env._recording:
                    logger.warning("No recording in progress")
                    return
                
                logger.info("Stopping screen recording...")
                self.env._recording = False
                
                # 等待录屏线程结束
                if self.env._recording_thread:
                    self.env._recording_thread.join(timeout=5)
                
                # 保存视频
                if len(self.env._video_frames) == 0:
                    logger.warning("No frames captured, cannot save video")
                    return
                
                try:
                    import cv2
                    import os
                    
                    # 获取视频尺寸（使用第一帧的尺寸）
                    height, width = self.env._video_frames[0].shape[:2]
                    
                    logger.info(
                        (
                            f"Saving video to {filename} ({width}x{height}, "
                            f"{len(self.env._video_frames)} frames, {self.env._fps} fps)"
                        )
                    )
                    
                    # 尝试多种编码器，按兼容性排序
                    codecs_to_try = [
                        ('avc1', 'H.264 (avc1)'),
                        ('H264', 'H.264 (H264)'),
                        ('X264', 'X264'),
                        ('XVID', 'Xvid'),
                        ('mp4v', 'MPEG-4'),
                    ]
                    
                    out = None
                    used_codec = None
                    
                    for codec, codec_name in codecs_to_try:
                        try:
                            logger.info(f"Trying codec: {codec_name}...")
                            fourcc = cv2.VideoWriter_fourcc(*codec)
                            test_out = cv2.VideoWriter(filename, fourcc, self.env._fps, (width, height))
                            
                            if test_out.isOpened():
                                # 尝试写入第一帧验证
                                test_out.write(self.env._video_frames[0])
                                out = test_out
                                used_codec = codec_name
                                logger.info(f"Using codec: {codec_name}")
                                break
                            else:
                                test_out.release()
                        except Exception as e:
                            logger.debug(f"Codec {codec_name} not available: {e}")
                            continue
                    
                    if out is None:
                        logger.warning("All MP4 codecs failed, trying AVI with MJPG...")
                        # 尝试使用AVI容器 + MJPG编码（最兼容）
                        base, ext = os.path.splitext(filename)
                        filename = f"{base}.avi"
                        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                        out = cv2.VideoWriter(filename, fourcc, self.env._fps, (width, height))
                        used_codec = "Motion JPEG (AVI)"
                        
                        if not out.isOpened():
                            logger.error("All video codecs failed")
                            return
                    
                    # 写入所有帧（跳过第一帧如果已经写入）
                    start_idx = 1 if used_codec and 'H.264' in used_codec or 'Xvid' in used_codec else 0
                    logger.info(f"Writing {len(self.env._video_frames)} frames...")
                    for i, frame in enumerate(self.env._video_frames[start_idx:], start=start_idx):
                        out.write(frame)
                        if (i + 1) % 50 == 0:
                            logger.info(f"Progress: {i + 1}/{len(self.env._video_frames)} frames")
                    
                    out.release()
                    
                    # 验证视频文件
                    if os.path.exists(filename):
                        file_size = os.path.getsize(filename)
                        logger.info(f"Video file created: {file_size / 1024 / 1024:.2f} MB")
                        
                        # 尝试读取验证
                        cap = cv2.VideoCapture(filename)
                        if cap.isOpened():
                            video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            logger.info(f"Video verification: {video_frames} frames readable")
                            cap.release()
                            logger.info(f"✅ Video saved successfully to {filename} using {used_codec}")
                        else:
                            logger.warning(f"⚠️ Video file created but cannot be opened for verification")
                            cap.release()
                    else:
                        logger.error("Video file was not created")
                    
                except ImportError:
                    logger.error("opencv-python is not installed. Please install it: pip install opencv-python")
                except Exception as e:
                    logger.error(f"Error saving video: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                finally:
                    # 清理
                    self.env._video_frames = []
        
        if not hasattr(self, '_controller'):
            self._controller = RecordingController(self)
        return self._controller
    
    def _get_obs(self) -> Dict[str, Any]:
        """
        获取当前观察（兼容性方法）
        
        Returns:
            当前观察字典
        """
        # 使用封装的截图方法
        screenshot_bytes = self._capture_screenshot()
        
        return {
            "screenshot": screenshot_bytes,
            "accessibility_tree": None,
        }
