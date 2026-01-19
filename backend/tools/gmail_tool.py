#!/usr/bin/env python3
"""
Gmail 工具
处理Gmail邮件读取和发送操作
"""

import json
import requests
import base64
from email.mime.text import MIMEText
from pathlib import Path
from openai import OpenAI

# 初始化 MiniMax AI 客户端
import os
client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url="https://api.minimaxi.com/v1"
)

class GmailTool:
    def __init__(self):
        self.token_file = Path("access_token.txt")
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        
        # 验证必要的环境变量
        if not self.sender_email:
            print("⚠️  警告: 未设置GMAIL_SENDER_EMAIL环境变量")
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        try:
            print(f"🔍 查找访问令牌文件: {self.token_file.absolute()}")
            if self.token_file.exists():
                token = self.token_file.read_text().strip()
                print(f"✅ 成功读取访问令牌 (长度: {len(token)})")
                return token
            else:
                print(f"❌ 访问令牌文件不存在: {self.token_file.absolute()}")
                print(f"💡 请创建 access_token.txt 文件并填入Gmail API访问令牌")
                print(f"📝 参考 access_token.txt.example 文件获取令牌的步骤")
                return None
        except Exception as e:
            print(f"❌ 读取访问令牌失败: {e}")
            return None
    
    def _get_headers(self) -> dict:
        """获取请求头"""
        token = self._get_access_token()
        if not token:
            error_msg = f"未找到访问令牌，请先进行Gmail认证\n"
            error_msg += f"请确保 {self.token_file.absolute()} 文件存在并包含有效的访问令牌"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        print(f"🔑 请求头已生成，令牌前缀: {token[:20]}...")
        return headers
    
    def _get_unread_emails_simple(self, headers: dict, count: int) -> list:
        """简单获取未读邮件"""
        try:
            params = {
                'maxResults': count,
                'q': 'is:unread'
            }
            
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages',
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                return []
            
            messages = response.json().get('messages', [])
            if not messages:
                return []
            
            email_details = []
            for i, message in enumerate(messages[:count], 1):
                try:
                    detail_response = requests.get(
                        f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message["id"]}',
                        headers=headers,
                        timeout=10
                    )
                    
                    if detail_response.status_code == 200:
                        msg_data = detail_response.json()
                        
                        # 确认是否真的未读
                        labels = msg_data.get('labelIds', [])
                        if 'UNREAD' not in labels:
                            continue
                        
                        headers_data = msg_data.get('payload', {}).get('headers', [])
                        subject = next((h['value'] for h in headers_data if h['name'] == 'Subject'), '无主题')
                        sender = next((h['value'] for h in headers_data if h['name'] == 'From'), '未知发件人')
                        date = next((h['value'] for h in headers_data if h['name'] == 'Date'), '未知时间')
                        body = self._extract_email_body(msg_data.get('payload', {}))
                        
                        email_details.append({
                            'index': len(email_details) + 1,
                            'subject': subject,
                            'sender': sender,
                            'date': date,
                            'body': body[:200] + '...' if len(body) > 200 else body,
                            'is_unread': True
                        })
                        
                except Exception as e:
                    print(f"❌ 获取邮件详情失败: {e}")
                    continue
            
            return email_details
            
        except Exception as e:
            print(f"❌ 获取未读邮件失败: {e}")
            return []
    
    def _format_email_results(self, email_details: list, title: str) -> str:
        """格式化邮件结果"""
        if not email_details:
            return f"📭 {title}: 没有找到邮件"
        
        result = f"📧 {title} ({len(email_details)} 封):\n\n"
        
        for email in email_details:
            unread_mark = "🆕 " if email.get('is_unread', False) else ""
            result += f"【{unread_mark}邮件 {email['index']}】\n"
            result += f"📝 主题: {email['subject']}\n"
            result += f"👤 发件人: {email['sender']}\n"
            result += f"📅 时间: {email['date']}\n"
            result += f"📄 内容: {email['body']}\n"
            result += "-" * 50 + "\n"
        
        return result
    
    def read_latest_emails(self, count: int = 5, prioritize_unread: bool = True) -> str:
        """读取最新的邮件，可选择优先显示未读邮件"""
        try:
            print(f"📧 开始读取最新 {count} 封邮件...")
            headers = self._get_headers()
            print(f"🔑 请求头已准备完成")
            
            if prioritize_unread:
                # 先尝试获取未读邮件
                print("🔍 优先查找未读邮件...")
                unread_result = self._get_unread_emails_simple(headers, count)
                if unread_result and len(unread_result) > 0:
                    print(f"✅ 找到 {len(unread_result)} 封未读邮件")
                    return self._format_email_results(unread_result, "收件箱未读邮件")
                else:
                    print("ℹ️ 没有未读邮件，获取最新邮件...")
            
            # 获取收件箱邮件列表，使用查询参数 in:inbox
            list_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={count}&q=in:inbox"
            print(f"🌐 请求URL: {list_url}")
            
            response = requests.get(list_url, headers=headers, timeout=10)
            print(f"📡 API响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = f"❌ 获取邮件列表失败:\n"
                error_detail += f"状态码: {response.status_code}\n"
                error_detail += f"响应内容: {response.text}\n"
                error_detail += f"请求URL: {list_url}\n"
                print(error_detail)
                return error_detail
            
            messages = response.json().get('messages', [])
            if not messages:
                return "📭 没有找到邮件"
            
            # 获取每封邮件的详细信息
            email_details = []
            for i, message in enumerate(messages[:count], 1):
                msg_id = message['id']
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                
                if detail_response.status_code == 200:
                    msg_data = detail_response.json()
                    
                    # 提取邮件信息
                    headers_data = msg_data.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers_data if h['name'] == 'Subject'), '无主题')
                    sender = next((h['value'] for h in headers_data if h['name'] == 'From'), '未知发件人')
                    date = next((h['value'] for h in headers_data if h['name'] == 'Date'), '未知时间')
                    
                    # 提取邮件正文（简化处理）
                    body = self._extract_email_body(msg_data.get('payload', {}))
                    
                    # 检查是否为未读邮件
                    labels = msg_data.get('labelIds', [])
                    is_unread = 'UNREAD' in labels
                    
                    email_details.append({
                        'index': i,
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body[:200] + '...' if len(body) > 200 else body,  # 限制长度
                        'is_unread': is_unread
                    })
            
            return self._format_email_results(email_details, "收件箱最新邮件")
            
        except Exception as e:
            error_detail = f"❌ 读取邮件异常:\n"
            error_detail += f"错误类型: {type(e).__name__}\n"
            error_detail += f"错误信息: {str(e)}\n"
            error_detail += f"令牌文件路径: {self.token_file.absolute()}\n"
    
    def read_unread_emails(self, max_display: int = 3) -> str:
        """读取未读邮件，显示总数但最多只展示指定数量的详细内容"""
        try:
            print(f"📧 开始读取未读邮件，最多显示 {max_display} 封详细内容...")
            headers = self._get_headers()
            print(f"🔑 请求头已准备完成")
            
            # 先获取更多未读邮件来统计总数（最多50封用于统计）
            list_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=50&q=in:inbox is:unread"
            print(f"🌐 请求URL: {list_url}")
            
            response = requests.get(list_url, headers=headers, timeout=10)
            print(f"📡 API响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = f"❌ 获取未读邮件列表失败:\n"
                error_detail += f"状态码: {response.status_code}\n"
                error_detail += f"响应内容: {response.text}\n"
                error_detail += f"请求URL: {list_url}\n"
                print(error_detail)
                return error_detail
            
            messages = response.json().get('messages', [])
            if not messages:
                return "📭 没有找到未读邮件"
            
            total_unread = len(messages)
            display_count = min(max_display, total_unread)
            
            print(f"📊 找到 {total_unread} 封未读邮件，将显示前 {display_count} 封")
            
            # 获取前几封邮件的详细信息
            email_details = []
            for i, message in enumerate(messages[:display_count], 1):
                msg_id = message['id']
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                
                if detail_response.status_code == 200:
                    msg_data = detail_response.json()
                    
                    # 提取邮件信息
                    headers_data = msg_data.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers_data if h['name'] == 'Subject'), '无主题')
                    sender = next((h['value'] for h in headers_data if h['name'] == 'From'), '未知发件人')
                    date = next((h['value'] for h in headers_data if h['name'] == 'Date'), '未知时间')
                    
                    # 提取邮件正文（简化处理）
                    body = self._extract_email_body(msg_data.get('payload', {}))
                    
                    email_details.append({
                        'index': i,
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body[:200] + '...' if len(body) > 200 else body  # 限制长度
                    })
            
            # 格式化输出
            if total_unread <= max_display:
                result = f"� 收件箱共 有 {total_unread} 封未读邮件:\n\n"
            else:
                result = f"📧 收件箱共有 {total_unread} 封未读邮件，显示最新 {display_count} 封:\n\n"
            
            for email in email_details:
                result += f"【未读邮件 {email['index']}】\n"
                result += f"📝 主题: {email['subject']}\n"
                result += f"👤 发件人: {email['sender']}\n"
                result += f"📅 时间: {email['date']}\n"
                result += f"📄 内容: {email['body']}\n"
                result += "-" * 50 + "\n"
            
            # 如果还有更多未读邮件，添加提示
            if total_unread > max_display:
                result += f"\n💡 还有 {total_unread - display_count} 封未读邮件未显示"
            
            return result
            
        except Exception as e:
            error_detail = f"❌ 读取未读邮件异常:\n"
            error_detail += f"错误类型: {type(e).__name__}\n"
            error_detail += f"错误信息: {str(e)}\n"
            error_detail += f"令牌文件路径: {self.token_file.absolute()}\n"
            print(error_detail)
            return error_detail

    def _extract_email_body(self, payload: dict) -> str:
        """提取邮件正文"""
        try:
            # 处理简单的文本邮件
            if payload.get('body', {}).get('data'):
                body_data = payload['body']['data']
                decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8', errors='ignore')
                return decoded.strip()
            
            # 处理多部分邮件
            if payload.get('parts'):
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                        body_data = part['body']['data']
                        decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8', errors='ignore')
                        return decoded.strip()
            
            return "无法解析邮件内容"
            
        except Exception as e:
            return f"解析邮件内容失败: {str(e)}"
    
    def send_email(self, to_email: str, subject: str, body: str) -> str:
        """发送邮件"""
        try:
            headers = self._get_headers()
            
            # 创建邮件
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to_email
            message['from'] = self.sender_email
            message['subject'] = subject
            
            # 编码邮件
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # 发送请求
            data = {'raw': raw_message}
            response = requests.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return f"✅ 邮件发送成功！\n📧 收件人: {to_email}\n📝 主题: {subject}"
            else:
                error_msg = f"❌ 发送失败: {response.status_code} - {response.text}"
                if response.status_code == 403:
                    error_msg += "\n💡 可能需要发送邮件权限，请重新认证"
                return error_msg
                
        except Exception as e:
            return f"❌ 发送邮件失败: {str(e)}"
    
    def compose_email_with_ai(self, recipient: str, purpose: str) -> str:
        """使用AI起草邮件"""
        try:
            prompt = f"""请为以下邮件需求起草一封专业且友好的邮件：

收件人: {recipient}
邮件目的: {purpose}

要求：
1. 生成合适的邮件主题
2. 写一封简洁、专业、友好的邮件正文
3. 使用中文
4. 包含适当的问候和结尾

请返回JSON格式：
{{
  "subject": "邮件主题",
  "body": "邮件正文"
}}"""

            response = client.chat.completions.create(
                model="MiniMax-M1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048
            )
            
            result = response.choices[0].message.content.strip()
            
            # 解析JSON
            email_data = json.loads(result)
            subject = email_data.get('subject', '无主题')
            body = email_data.get('body', '无内容')
            
            # 发送邮件
            return self.send_email(recipient, subject, body)
            
        except Exception as e:
            return f"❌ AI起草邮件失败: {str(e)}"

def handle_gmail_operation(arguments: dict) -> str:
    """处理Gmail操作请求"""
    print(f"📧 Gmail操作请求: {arguments}")
    gmail_tool = GmailTool()
    action = arguments.get("action", "")
    
    if action == "read":
        count = arguments.get("count", 5)
        print(f"📖 执行读取邮件操作，数量: {count}")
        return gmail_tool.read_latest_emails(count)
    
    elif action == "read_unread":
        max_display = arguments.get("count", 3)
        print(f"📖 执行读取未读邮件操作，最多显示: {max_display}")
        return gmail_tool.read_unread_emails(max_display)
    
    elif action == "send":
        to_email = arguments.get("to_email", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        
        if not to_email:
            return "❌ 请提供收件人邮箱地址"
        
        return gmail_tool.send_email(to_email, subject, body)
    
    elif action == "compose":
        recipient = arguments.get("recipient", "")
        purpose = arguments.get("purpose", "")
        
        if not recipient or not purpose:
            return "❌ 请提供收件人和邮件目的"
        
        return gmail_tool.compose_email_with_ai(recipient, purpose)
    
    else:
        return f"❌ 不支持的操作: {action}。支持的操作: read, read_unread, send, compose"