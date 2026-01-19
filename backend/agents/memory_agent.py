#!/usr/bin/env python3
"""
Memory Agent - 记忆 Agent
负责信息提取、持久化存储和上下文管理
"""

import json
import os
from pathlib import Path
from openai import OpenAI

class MemoryAgent:
    def __init__(self):
        import os
        self.ai_client = OpenAI(
            api_key=os.getenv("KIMI_API_KEY"),
            base_url="https://api.moonshot.cn/v1"
        )
        self.storage_file = Path("backend/data/user_memory.json")
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """确保存储文件存在"""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            self.storage_file.write_text("{}")
    
    async def process_interaction(self, user_id: str, user_input: str, ai_response: str):
        """异步处理交互，提取有用信息"""
        try:
            # 简单的信息提取
            if self._should_extract_info(user_input):
                info = await self._extract_info(user_input, ai_response)
                if info:
                    self._save_user_info(user_id, info)
                    print(f"🧠 已提取并保存用户信息: {user_id}")
        except Exception as e:
            print(f"❌ Memory processing error: {e}")
    
    def get_user_context(self, user_id: str) -> str:
        """获取用户上下文信息"""
        user_data = self._load_user_data(user_id)
        if not user_data:
            return ""
        
        # 构建基本信息部分
        basic_info = []
        if user_data.get('name'):
            basic_info.append(f"姓名: {user_data['name']}")
        if user_data.get('age'):
            basic_info.append(f"年龄: {user_data['age']}")
        if user_data.get('occupation'):
            basic_info.append(f"职业: {user_data['occupation']}")
        if user_data.get('birthday'):
            basic_info.append(f"生日: {user_data['birthday']}")
        
        context_parts = []
        
        if basic_info:
            context_parts.append(f"用户基本信息：\n- {chr(10).join(['- ' + info for info in basic_info])}")
        
        # 偏好信息
        preference_info = []
        if user_data.get('favorite_apps'):
            preference_info.append(f"常用应用: {', '.join(user_data['favorite_apps'])}")
        if user_data.get('work_habits'):
            preference_info.append(f"工作习惯: {user_data['work_habits']}")
        if user_data.get('preferences'):
            preference_info.append(f"个人设置: {user_data['preferences']}")
        if user_data.get('recent_activities'):
            preference_info.append(f"最近活动: {user_data['recent_activities']}")
        
        if preference_info:
            context_parts.append(f"用户偏好信息：\n- {chr(10).join(['- ' + info for info in preference_info])}")
        
        return '\n\n'.join(context_parts)
    
    def _should_extract_info(self, user_input: str) -> bool:
        """判断是否需要提取信息"""
        keywords = ["喜欢", "常用", "习惯", "偏好", "设置", "记住", "经常", "总是", "平时", 
                   "我叫", "我是", "我的名字", "年龄", "岁", "生日", "职业", "工作", "学生"]
        return any(keyword in user_input for keyword in keywords)
    
    async def _extract_info(self, user_input: str, ai_response: str):
        """使用 AI 提取有用信息"""
        try:
            prompt = f"""从以下对话中提取有用的用户信息，返回JSON格式：

用户: {user_input}
AI: {ai_response}

请提取以下类型的信息（如果有的话）：
- name: 用户姓名
- age: 用户年龄（数字）
- occupation: 用户职业
- birthday: 用户生日
- favorite_apps: 用户喜欢或常用的应用程序列表
- work_habits: 用户的工作习惯描述
- preferences: 用户的个人偏好设置
- recent_activities: 最近的活动或任务

如果没有有用信息，返回 null。
只返回JSON，不要其他解释。

示例格式：
{{
  "name": "小明",
  "age": 25,
  "occupation": "程序员",
  "birthday": "3月15日",
  "favorite_apps": ["Chrome", "Music"],
  "work_habits": "喜欢在晚上工作",
  "preferences": {{"music_genre": "蓝调"}},
  "recent_activities": ["设置提醒"]
}}"""

            response = self.ai_client.chat.completions.create(
                model="kimi-k2-0711-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # 尝试解析JSON
            if result.lower() == "null":
                return None
            
            return json.loads(result)
            
        except Exception as e:
            print(f"❌ 信息提取失败: {e}")
            return None
    
    def _load_user_data(self, user_id: str) -> dict:
        """加载用户数据"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                return all_data.get(user_id, {})
        except Exception as e:
            print(f"❌ 加载用户数据失败: {e}")
            return {}
    
    def _save_user_info(self, user_id: str, new_info: dict):
        """保存用户信息"""
        try:
            # 加载现有数据
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            # 获取用户现有数据
            user_data = all_data.get(user_id, {})
            
            # 合并新信息
            for key, value in new_info.items():
                if key in ['favorite_apps', 'recent_activities'] and isinstance(value, list):
                    # 对于列表类型，合并并去重
                    existing = user_data.get(key, [])
                    user_data[key] = list(set(existing + value))
                elif key == 'preferences' and isinstance(value, dict):
                    # 对于字典类型，合并
                    existing = user_data.get(key, {})
                    existing.update(value)
                    user_data[key] = existing
                elif key in ['name', 'age', 'occupation', 'birthday']:
                    # 基本信息直接覆盖（但只在有值时）
                    if value:
                        user_data[key] = value
                else:
                    # 其他类型直接覆盖
                    user_data[key] = value
            
            # 保存回文件
            all_data[user_id] = user_data
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ 保存用户信息失败: {e}")
    
    def get_all_users(self) -> list:
        """获取所有用户ID"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                return list(all_data.keys())
        except:
            return []
    
    def get_personalized_greeting(self, user_id: str) -> str:
        """获取个性化打招呼信息"""
        user_data = self._load_user_data(user_id)
        
        if not user_data:
            return "嗨！我是 Miko 🐾\n你的专属桌面智能伙伴\n\n我能帮你：\n• 控制应用 - '打开Chrome'\n• 整理文件 - '整理桌面'\n• 查看邮件 - '读取最新邮件'\n• 获取信息 - '今天天气怎么样'\n\n一句话就能搞定，试试看吧！"
        
        # 构建个性化问候
        greeting_parts = []
        
        # 基础问候
        if user_data.get('name'):
            greeting_parts.append(f"Hi, {user_data['name']}！我是 Miko🐾")
        else:
            greeting_parts.append("Hi！我是 Miko 🐾 你的桌面伙伴")
        
        # 添加个性化信息
        personal_info = []
        # if user_data.get('age'):
        #     personal_info.append(f"记得你{user_data['age']}岁")
        # if user_data.get('occupation'):
        #     personal_info.append(f"是{user_data['occupation']}")
        
        # if personal_info:
        #     greeting_parts.append(f"我{', '.join(personal_info)}！")
        
        # 功能介绍
        greeting_parts.append("作为你的桌面伙伴，我可以随时帮忙！")
        
        # 个性化建议
        suggestions = []
        if user_data.get('favorite_apps'):
            # 基于常用应用给出建议
            apps = user_data['favorite_apps'][:2]  # 取前两个
            for app in apps:
                suggestions.append(f"• 打开{app}")
        
        # 智能默认建议
        if len(suggestions) < 4:
            default_suggestions = [
                "• 提醒我明天下午四点开会", 
                "• 给Alexa发邮件", 
                "• 用Chrome搜索AdventureX",  
                "• 帮我整理桌面",
                "• 进入工作模式"
            ]
            for suggestion in default_suggestions:
                if len(suggestions) < 6:
                    suggestions.append(suggestion)
        
        if suggestions:
            greeting_parts.append(f"\n试试说：\n{chr(10).join(suggestions)}")
        
        return '\n'.join(greeting_parts)