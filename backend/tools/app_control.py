#!/usr/bin/env python3
"""
应用控制工具
处理应用程序启动、控制等操作
"""

import json
import subprocess
from openai import OpenAI

# 初始化 AI 客户端
import os
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

def execute_applescript(script: str) -> str:
    """执行AppleScript并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True
        )
        return f"✅ 执行成功: {result.stdout.strip() or '操作完成'}"
    except subprocess.CalledProcessError as e:
        return f"❌ 执行失败: {e.stderr.strip()}"

def handle_app_control(arguments: dict) -> str:
    """处理应用控制请求"""
    task = arguments["task_description"]
    target_app = arguments.get("target_app", "")
    
    # 生成 AppleScript
    script_prompt = f"""请为以下任务生成AppleScript代码：

任务：{task}
目标应用：{target_app}

要求：
1. 只返回AppleScript代码，不要解释
2. 代码要能直接执行，避免使用delay命令（会阻塞）
3. 如果是音乐相关，使用Music应用
4. 如果是提醒事项/待办，使用Reminders应用
5. 如果是打开应用，使用tell application语法
6. 如果是时间查询，使用current date获取当前时间

示例:
播放音乐: 
tell application "Music"
    activate
    play
end tell

设置提醒事项:
tell application "Reminders"
    make new reminder with properties {{name:"蓝调活动", due date:(current date) + (11 * hours - (time of (current date)))}}
end tell

查询时间:
set currentTime to current date
set timeString to (time string of currentTime)
set dateString to (date string of currentTime)
return "现在是 " & dateString & " " & timeString

查询星期几:
set currentDate to current date
set dayOfWeek to weekday of currentDate as string
return "今天是 " & dayOfWeek

"""

    print(f"🤖 正在生成AppleScript for: {task}")
    
    script_response = client.chat.completions.create(
        model="kimi-k2-0711-preview",
        messages=[{"role": "user", "content": script_prompt}],
        temperature=0.0
    )
    
    script = script_response.choices[0].message.content.strip()
    # 清理可能的markdown标记
    script = script.replace("```applescript", "").replace("```", "").strip()
    
    print(f"📝 生成的脚本:\n{script}\n")
    
    result = execute_applescript(script)
    return f"⚡ {task}: {result}"