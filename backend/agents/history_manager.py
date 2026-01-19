#!/usr/bin/env python3
"""
History Manager - 历史管理
负责多轮对话管理和会话状态
"""

from datetime import datetime

class HistoryManager:
    def __init__(self):
        self.sessions = {}  # 内存存储
        self.max_history = 10  # 最多保存10轮对话
    
    def add_interaction(self, user_id: str, user_input: str, ai_response: str, tool_calls: list = None):
        """添加一次交互到历史记录，包含工具调用信息"""
        if user_id not in self.sessions:
            self.sessions[user_id] = []
        
        interaction = {
            "user": user_input,
            "ai": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加工具调用信息
        if tool_calls:
            interaction["tool_calls"] = []
            for tool_call in tool_calls:
                interaction["tool_calls"].append({
                    "function": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                })
        
        self.sessions[user_id].append(interaction)
        
        # 保持最近的对话
        if len(self.sessions[user_id]) > self.max_history:
            self.sessions[user_id] = self.sessions[user_id][-self.max_history:]
        
        print(f"📝 历史记录已更新: {user_id} ({len(self.sessions[user_id])} 条记录)")
    
    def get_recent_history(self, user_id: str, limit: int = 3) -> list:
        """获取最近的对话历史，格式化为消息列表，包含工具调用信息"""
        history = self.sessions.get(user_id, [])
        recent = history[-limit:] if len(history) > limit else history
        
        # 格式化为消息列表
        messages = []
        for item in recent:
            # 添加用户消息
            messages.append({"role": "user", "content": item["user"]})
            
            # 添加助手回复，如果有工具调用则包含工具调用信息
            assistant_content = item["ai"]
            if item.get("tool_calls"):
                tool_info = []
                for tool_call in item["tool_calls"]:
                    tool_info.append(f"调用了{tool_call['function']}工具")
                assistant_content = f"{assistant_content} (使用了工具: {', '.join(tool_info)})"
            
            messages.append({"role": "assistant", "content": assistant_content})
        
        return messages
    
    def get_session_summary(self, user_id: str) -> str:
        """获取会话摘要"""
        history = self.sessions.get(user_id, [])
        if not history:
            return "无历史记录"
        
        return f"共 {len(history)} 轮对话，最近一次: {history[-1]['timestamp']}"
    
    def clear_session(self, user_id: str):
        """清除会话历史"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            print(f"🗑️ 已清除 {user_id} 的历史记录")