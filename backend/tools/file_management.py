#!/usr/bin/env python3
"""
文件管理工具
处理文件整理、清理等操作
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# 初始化 AI 客户端
import os
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

def execute_shell_command(command: str) -> str:
    """执行shell命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return f"✅ 命令执行成功:\n{result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"❌ 命令执行失败:\n{e.stderr.strip()}"

def scan_directory(path: str) -> str:
    """扫描目录并返回文件列表信息"""
    try:
        target_path = Path(path).expanduser()
        if not target_path.exists():
            return f"❌ 路径不存在: {path}"
        
        files_info = []
        total_size = 0
        
        for item in target_path.iterdir():
            if item.is_file():
                size = item.stat().st_size
                total_size += size
                modified = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                
                files_info.append({
                    "name": item.name,
                    "size": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "extension": item.suffix.lower(),
                    "modified": modified,
                    "is_hidden": item.name.startswith('.')
                })
            elif item.is_dir():
                files_info.append({
                    "name": item.name,
                    "type": "folder",
                    "is_hidden": item.name.startswith('.')
                })
        
        summary = {
            "path": str(target_path),
            "total_files": len([f for f in files_info if f.get("type") != "folder"]),
            "total_folders": len([f for f in files_info if f.get("type") == "folder"]),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "files": files_info
        }
        
        return json.dumps(summary, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"❌ 扫描失败: {str(e)}"

def handle_file_management(arguments: dict) -> str:
    """处理文件管理请求"""
    action = arguments.get("action", "organize")
    path = arguments.get("path", "~/Desktop")
    
    if action == "organize":
        return organize_files_with_ai(path)
    elif action == "scan":
        return scan_directory(path)
    elif action == "clean":
        return clean_files(path)
    else:
        return f"❌ 不支持的操作: {action}"

def organize_files_with_ai(path: str) -> str:
    """智能文件整理 - 内部多轮AI调用自动完成整理"""
    try:
        print(f"🚀 开始智能整理文件: {path}")
        
        # 系统消息
        system_message = """你是一个智能文件管理助手。你可以：
1. 扫描目录查看文件信息
2. 使用shell命令进行文件操作（移动、删除、创建文件夹等）

当用户要求整理文件时，你应该：
1. 先扫描目录了解文件情况
2. 根据文件类型、大小、名称等信息制定整理策略
3. 使用适当的shell命令执行整理操作
4. 如果需要多步操作，请逐步执行

常用的文件分类：
- 图片：jpg, png, gif, jpeg, tiff等 -> 图片文件夹
- 文档：pdf, doc, docx, txt, rtf, pages, md等 -> 文档文件夹
- 表格：xls, xlsx, csv, numbers等 -> 表格文件夹
- 演示：ppt, pptx, key等 -> 演示文件夹
- 代码：py, js, html, css, swift, sql等 -> 代码文件夹
- 音视频：mp3, mp4, wav, mov, avi, mkv, m4a等 -> 音视频文件夹
- 压缩包：zip, rar, 7z, tar, gz等 -> 压缩文件夹
- 配置：json, env, gitignore等 -> 配置文件夹
- 安装包：dmg, pkg等 -> 安装包文件夹
- 临时文件：tmp, cache, bak, log等 -> 临时文件夹

重要提示：
- 执行每个操作前要确保目标文件夹存在
- 处理文件名包含空格或特殊字符时要正确转义
- 如果发现重复文件，创建"重复文件"文件夹进行管理
- 总是告诉用户你在做什么，并在完成后给出总结

请根据具体情况智能决定如何操作，并主动执行多步整理流程。"""

        # 工具定义
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "scan_directory", 
                    "description": "扫描指定目录，获取文件和文件夹的详细信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "要扫描的目录路径"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "execute_shell_command",
                    "description": "执行shell命令进行文件操作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的shell命令"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]
        
        # 消息历史
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"请帮我整理 {path} 目录的文件"}
        ]
        
        results = []
        max_rounds = 10  # 最大轮次
        
        for round_num in range(max_rounds):
            print(f"🔄 第 {round_num + 1} 轮AI调用")
            
            # AI调用
            response = client.chat.completions.create(
                model="kimi-k2-0711-preview",
                messages=messages,
                tools=tools,
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            # 添加AI回复到消息历史
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls
            })
            
            if message.content:
                print(f"🤖 AI: {message.content}")
                results.append(message.content)
            
            # 处理工具调用
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    if function_name == "scan_directory":
                        tool_result = scan_directory(arguments["path"])
                        print(f"📁 扫描结果: {arguments['path']}")
                    elif function_name == "execute_shell_command":
                        command = arguments["command"]
                        print(f"🔧 执行命令: {command}")
                        tool_result = execute_shell_command(command)
                        print(f"📋 命令结果: {tool_result}")
                    
                    # 添加工具结果到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # 继续下一轮，让AI分析工具结果并决定下一步
                continue
            else:
                # AI没有调用工具，检查是否完成
                if message.content and any(keyword in message.content.lower() for keyword in ["完成", "整理结束", "已完成", "整理完毕"]):
                    print("🎉 文件整理完成！")
                    break
                else:
                    # 提示AI继续
                    messages.append({
                        "role": "user",
                        "content": "请继续执行文件整理操作。如果需要扫描、创建文件夹或移动文件，请直接使用相应的工具命令执行。"
                    })
        
        # 汇总结果
        final_result = "✅ 智能文件整理完成！\n\n"
        final_result += "📋 整理过程:\n"
        for i, result in enumerate(results, 1):
            final_result += f"{i}. {result}\n"
        
        final_result += f"\n🔄 总共进行了 {round_num + 1} 轮AI调用"
        
        return final_result
        
    except Exception as e:
        return f"❌ 智能文件整理失败: {str(e)}"

def clean_files(path: str) -> str:
    """清理文件"""
    try:
        expanded_path = Path(path).expanduser()
        if not expanded_path.exists():
            return f"❌ 路径不存在: {path}"
        
        # 清理临时文件和缓存
        temp_extensions = [".tmp", ".cache", ".log", ".bak", ".DS_Store"]
        cleaned_count = 0
        
        for file_path in expanded_path.rglob("*"):
            if file_path.is_file():
                if file_path.suffix.lower() in temp_extensions or file_path.name.startswith('.'):
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except:
                        continue
        
        return f"✅ 清理完成！删除了 {cleaned_count} 个临时文件"
        
    except Exception as e:
        return f"❌ 文件清理失败: {str(e)}"