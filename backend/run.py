#!/usr/bin/env python3
"""
启动脚本 - 从 backend 目录运行
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_backend import app
import uvicorn

if __name__ == "__main__":
    print("🚀 启动 Miko AI Backend...")
    print("🤖 使用 Main Agent 架构")
    print("📡 WebSocket 端点: ws://localhost:8000/ws/chat")
    print("🌐 HTTP 端点: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)