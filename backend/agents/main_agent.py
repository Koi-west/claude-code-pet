#!/usr/bin/env python3
"""
Main Agent - 主控 Agent
负责意图识别、Tool调用和结果整合
"""

import asyncio
from openai import OpenAI
from agents.memory_agent import MemoryAgent
from agents.history_manager import HistoryManager
from tools.tool_dispatcher import handle_dynamic_tools
from tools.file_management import handle_file_management

class MainAgent:
    def __init__(self):
        import os
        self.ai_client = OpenAI(
            api_key=os.getenv("KIMI_API_KEY"),
            base_url="https://api.moonshot.cn/v1"
        )
        self.memory_agent = MemoryAgent()
        self.history_manager = HistoryManager()
    
    async def process_message(self, user_input: str, user_id: str = "default"):
        # 1. 获取上下文和历史 (包含完整交互信息)
        context = self.memory_agent.get_user_context(user_id)
        history = self.history_manager.get_recent_history(user_id)
        
        # 2. 构建消息 (包含记忆上下文和对话历史)
        messages = self._build_messages_with_context(user_input, context, history)
        
        # 3. AI 调用
        response = self.ai_client.chat.completions.create(
            model="kimi-k2-0711-preview",
            messages=messages,
            tools=self._get_tools(),
            temperature=0.3
        )
        
        # 4. Tool 执行
        message = response.choices[0].message
        print(f"🤖 AI响应: {message.content}")
        print(f"🔧 工具调用: {len(message.tool_calls) if message.tool_calls else 0} 个")
        
        if message.tool_calls:
            for i, tool_call in enumerate(message.tool_calls):
                print(f"   工具{i+1}: {tool_call.function.name} - {tool_call.function.arguments}")
            tool_results = handle_dynamic_tools(message.tool_calls)
            final_response = await self._generate_final_response(user_input, tool_results)
        else:
            final_response = message.content
        
        # 5. 更新记忆和历史 (包含完整交互信息)
        import asyncio
        asyncio.create_task(self.memory_agent.process_interaction(user_id, user_input, final_response))
        self.history_manager.add_interaction(user_id, user_input, final_response, message.tool_calls)
        
        return final_response
    
    def _build_messages(self, user_input: str):
        """构建消息列表"""
        return [
            {
                "role": "system",
                "content": """你是Miko，一个可爱的桌面助手，可以帮用户控制Mac电脑。你的回复要简洁友好，像个贴心的伙伴。

工具选择指南：
1. **文件管理工具 (manage_files)** - 当用户要求：
   - 整理文件/文件夹 (如："整理桌面"、"整理测试文件夹"、"分类文件")
   - 扫描目录 (如："看看桌面有什么文件")
   - 清理文件 (如："清理临时文件")
   
2. **应用控制工具 (control_application)** - 当用户要求：
   - 打开/关闭应用程序 (如："打开Chrome"、"关闭音乐")
   - 控制系统功能 (如："播放音乐"、"设置闹钟")
   - 系统操作 (如："调节音量"、"截屏")

重要：如果用户说"整理"、"分类"、"清理"文件相关的操作，必须使用 manage_files 工具，不要用 control_application 生成 AppleScript。

根据用户需求选择正确的工具。"""
            },
            {
                "role": "user", 
                "content": user_input
            }
        ]
    
    def _get_tools(self):
        """获取可用的工具列表"""
        return [
            {
                "type": "function", 
                "function": {
                    "name": "control_application",
                    "description": "控制Mac应用程序和系统操作：启动应用、音乐播放控制（播放/暂停/切歌）、设置闹钟、系统设置、时间查询等。音乐控制会通过AppleScript操作Music应用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "需要执行的任务描述，如'打开Chrome'、'播放音乐'、'暂停音乐'、'下一首歌'、'设置10分钟闹钟'、'现在几点了'等"
                            },
                            "target_app": {
                                "type": "string", 
                                "description": "目标应用程序名称，如'Chrome'、'Music'、'Calculator'等"
                            }
                        },
                        "required": ["task_description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_files",
                    "description": "文件管理操作：整理桌面文件、扫描目录、清理临时文件等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "操作类型：organize(整理文件)、scan(扫描目录)、clean(清理文件)",
                                "enum": ["organize", "scan", "clean"]
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径，如'~/Desktop'、'~/Documents'等",
                                "default": "~/Desktop"
                            }
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_python",
                    "description": "执行Python脚本来完成各种任务：获取天气、系统信息、数据处理、网络请求等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "要完成的任务描述，如'获取今天的天气'、'查看系统信息'、'数据处理'等"
                            },
                            "code": {
                                "type": "string",
                                "description": "可选：直接提供要执行的Python代码。如果不提供，将根据task自动生成"
                            }
                        },
                        "required": ["task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_operation",
                    "description": "Gmail邮件操作：读取最新邮件、读取未读邮件、发送邮件、AI起草邮件等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "操作类型：read(读取最新邮件)、read_unread(读取未读邮件)、send(发送邮件)、compose(AI起草并发送邮件)",
                                "enum": ["read", "read_unread", "send", "compose"]
                            },
                            "count": {
                                "type": "integer",
                                "description": "读取邮件数量，默认3封",
                                "default": 3
                            },
                            "to_email": {
                                "type": "string",
                                "description": "收件人邮箱地址"
                            },
                            "subject": {
                                "type": "string",
                                "description": "邮件主题"
                            },
                            "body": {
                                "type": "string",
                                "description": "邮件正文"
                            },
                            "recipient": {
                                "type": "string",
                                "description": "收件人邮箱（用于AI起草）"
                            },
                            "purpose": {
                                "type": "string",
                                "description": "邮件目的（用于AI起草）"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]
    
    async def _generate_final_response(self, user_input: str, tool_result: str):
        """基于工具执行结果生成友好回复"""
        final_response = self.ai_client.chat.completions.create(
            model="kimi-k2-0711-preview",
            messages=[
                {
                    "role": "system",
                    "content": "你是Miko，根据工具执行结果，用简洁友好的语言告诉用户操作结果。如果是统计数据查询，要提醒用户数据来源和可能的准确性限制。"
                },
                {
                    "role": "user",
                    "content": f"用户请求：{user_input}\n执行结果：{tool_result}\n请简洁地告诉用户结果。"
                }
            ],
            temperature=0.0
        )
        
        return final_response.choices[0].message.content

    def _build_messages_with_context(self, user_input: str, context: str, history: list):
        """构建包含上下文和历史的消息列表"""
        messages = [
            {
                "role": "system",
                "content": f"""你是Miko，一个可爱的桌面助手，可以帮用户控制Mac电脑。你的回复要简洁友好，像个贴心的伙伴。

{context if context.strip() else ""}

工具选择指南：
1. **文件管理工具 (manage_files)** - 当用户要求：
   - 整理文件/文件夹 (如："整理桌面"、"整理测试文件夹"、"分类文件")
   - 扫描目录 (如："看看桌面有什么文件")
   - 清理文件 (如："清理临时文件")
   
2. **应用控制工具 (control_application)** - 当用户要求：
   - 打开/关闭应用程序 (如："打开Chrome"、"关闭音乐")
   - 音乐播放控制 (如："播放音乐"、"暂停音乐"、"下一首"、"上一首") - 必须使用AppleScript控制Music应用
   - 系统功能 (如："设置闹钟"、"调节音量"、"截屏")
   - 时间查询 (如："现在几点了"、"今天几号"、"星期几")

3. **Python执行工具 (execute_python)** - 当用户要求：
   - 获取天气信息 (如："今天天气怎么样"、"杭州天气")
   - 数据处理 (如："计算"、"分析数据")
   - 网络请求 (如："查询信息"、"获取数据")
   - 系统信息 (如："查看系统状态"、"内存使用情况")
   - 统计数据查询 (如："北京人口"、"GDP数据") - 注意数据准确性

4. **Gmail工具 (gmail_operation)** - 当用户要求：
   - 读取邮件 (如："查看最新邮件"、"读取邮件")
   - 发送邮件 (如："发送邮件给xxx"、"给xxx发邮件")
   - AI起草邮件 (如："给xxx写一封关于xxx的邮件")

重要：
- 文件操作用 manage_files，不要用 control_application
- 音乐控制（播放、暂停、切歌）必须用 control_application 调用AppleScript控制Music应用，每次都要调用工具，不能直接回复
- 时间查询用 control_application (AppleScript)
- 天气查询用 execute_python
- 应用控制用 control_application
- 统计数据查询用 execute_python，但要提醒用户数据可能不够准确
- 邮件操作用 gmail_operation

注意：每次用户请求音乐控制时，都必须调用相应的工具，不要基于历史对话假设操作已完成。
根据用户需求选择正确的工具。"""
            }
        ]
        
        # 添加历史对话
        # messages.extend(history)
        
        # 添加当前用户输入
        messages.append({
            "role": "user", 
            "content": user_input
        })
        
        return messages