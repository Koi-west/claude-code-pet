#!/usr/bin/env python3
"""
Miko AI Backend - 重构版
使用 Main Agent 架构，专注于应用控制功能
"""

import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import urllib.parse
from agents.main_agent import MainAgent

app = FastAPI(title="Miko AI Backend")

# 初始化 Main Agent
main_agent = MainAgent()

# Pydantic模型
class TokenRequest(BaseModel):
    token: str

@app.get("/")
async def root():
    return {
        "message": "Miko AI Backend is running!", 
        "time": datetime.now(),
        "features": ["应用程序控制", "Main Agent 架构", "智能对话", "Gmail集成"]
    }

# @app.get("/gmail/auth")
# async def gmail_auth():
#     """Gmail OAuth认证页面"""
#     # 导入Gmail配置
#     try:
#         from gmail_config import GMAIL_CLIENT_ID, REDIRECT_URI, SCOPES
#     except ImportError:
#         return HTMLResponse("""
#         <html><body>
#         <h2>❌ Gmail配置未完成</h2>
#         <p>请先配置gmail_config.py文件中的OAuth客户端ID</p>
#         <p><a href="/">返回首页</a></p>
#         </body></html>
#         """)
    
#     if GMAIL_CLIENT_ID == "YOUR_GMAIL_CLIENT_ID_HERE":
#         return HTMLResponse("""
#         <html><body>
#         <h2>❌ Gmail配置未完成</h2>
#         <p>请在gmail_config.py中设置正确的GMAIL_CLIENT_ID</p>
#         <p><a href="/">返回首页</a></p>
#         </body></html>
#         """)
    
#     # 生成OAuth授权URL
#     auth_params = {
#         'client_id': GMAIL_CLIENT_ID,
#         'redirect_uri': f"http://localhost:8000/gmail/callback",
#         'scope': ' '.join(SCOPES),
#         'response_type': 'code',
#         'access_type': 'offline',
#         'prompt': 'consent'
#     }
    
#     auth_url = 'https://accounts.google.com/o/oauth2/auth?' + urllib.parse.urlencode(auth_params)
    
#     return HTMLResponse(f"""
#     <html>
#     <head>
#         <title>Gmail认证 - Miko</title>
#         <style>
#             body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
#             .container {{ max-width: 600px; margin: 0 auto; }}
#             .btn {{ background: #4285f4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; }}
#             .btn:hover {{ background: #3367d6; }}
#             .step {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <h1>🔐 Gmail认证设置</h1>
#             <p>为了让Miko访问您的Gmail，需要完成Google账户授权。</p>
            
#             <div class="step">
#                 <h3>📋 认证步骤：</h3>
#                 <ol>
#                     <li>点击下方"开始授权"按钮</li>
#                     <li>选择您的Google账户</li>
#                     <li>允许Miko访问Gmail（读取和发送权限）</li>
#                     <li>完成后会自动返回，即可使用Gmail功能</li>
#                 </ol>
#             </div>
            
#             <div style="text-align: center; margin: 30px 0;">
#                 <a href="{auth_url}" class="btn">🚀 开始Gmail授权</a>
#             </div>
            
#             <div class="step">
#                 <h3>⚠️ 注意事项：</h3>
#                 <ul>
#                     <li>授权是安全的，使用Google官方OAuth流程</li>
#                     <li>Miko只会访问您明确授权的Gmail功能</li>
#                     <li>您可以随时在Google账户设置中撤销授权</li>
#                 </ul>
#             </div>
            
#             <p><a href="/">← 返回Miko主页</a></p>
#         </div>
#     </body>
#     </html>
#     """)

# @app.get("/gmail/callback")
# async def gmail_callback(request: Request):
#     """Gmail OAuth回调处理"""
#     code = request.query_params.get('code')
#     error = request.query_params.get('error')
    
#     if error:
#         return HTMLResponse(f"""
#         <html><body>
#         <h2>❌ 授权失败</h2>
#         <p>错误: {error}</p>
#         <p><a href="/gmail/auth">重新授权</a> | <a href="/">返回首页</a></p>
#         </body></html>
#         """)
    
#     if not code:
#         return HTMLResponse("""
#         <html><body>
#         <h2>❌ 授权码缺失</h2>
#         <p><a href="/gmail/auth">重新授权</a> | <a href="/">返回首页</a></p>
#         </body></html>
#         """)
    
#     # 使用授权码换取访问令牌
#     try:
#         from gmail_config import GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET
        
#         token_data = {
#             'client_id': GMAIL_CLIENT_ID,
#             'client_secret': GMAIL_CLIENT_SECRET,
#             'code': code,
#             'grant_type': 'authorization_code',
#             'redirect_uri': 'http://localhost:8000/gmail/callback'
#         }
        
#         import requests
#         response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        
#         if response.status_code == 200:
#             token_info = response.json()
#             access_token = token_info.get('access_token')
            
#             # 保存访问令牌
#             with open('access_token.txt', 'w') as f:
#                 f.write(access_token)
            
#             return HTMLResponse("""
#             <html>
#             <head>
#                 <title>Gmail认证成功 - Miko</title>
#                 <style>
#                     body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; text-align: center; }
#                     .success { color: #28a745; font-size: 24px; margin: 20px 0; }
#                     .btn { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }
#                 </style>
#             </head>
#             <body>
#                 <div class="success">✅ Gmail认证成功！</div>
#                 <p>Miko现在可以访问您的Gmail了</p>
#                 <p>您可以关闭此页面，回到Miko继续使用</p>
#                 <a href="/" class="btn">返回Miko</a>
                
#                 <script>
#                     // 3秒后自动关闭窗口
#                     setTimeout(() => {
#                         window.close();
#                     }, 3000);
#                 </script>
#             </body>
#             </html>
#             """)
#         else:
#             return HTMLResponse(f"""
#             <html><body>
#             <h2>❌ 获取访问令牌失败</h2>
#             <p>错误: {response.text}</p>
#             <p><a href="/gmail/auth">重新授权</a></p>
#             </body></html>
#             """)
            
#     except Exception as e:
#         return HTMLResponse(f"""
#         <html><body>
#         <h2>❌ 处理授权失败</h2>
#         <p>错误: {str(e)}</p>
#         <p><a href="/gmail/auth">重新授权</a></p>
#         </body></html>
#         """)

# @app.get("/gmail/status")
# async def gmail_status():
#     """检查Gmail认证状态"""
#     try:
#         with open('access_token.txt', 'r') as f:
#             token = f.read().strip()
        
#         if token:
#             return {"status": "authenticated", "message": "Gmail已认证", "token_length": len(token)}
#         else:
#             return {"status": "not_authenticated", "message": "需要Gmail认证"}
#     except FileNotFoundError:
#         return {"status": "not_authenticated", "message": "需要Gmail认证"}

# @app.post("/gmail/set-token")
# async def set_gmail_token(token_request: TokenRequest):
#     """设置Gmail访问令牌"""
#     try:
#         token = token_request.token.strip()
        
#         if not token:
#             return JSONResponse(
#                 status_code=400,
#                 content={"success": False, "message": "访问令牌不能为空"}
#             )
        
#         # 保存访问令牌
#         with open('access_token.txt', 'w') as f:
#             f.write(token)
        
#         return {
#             "success": True, 
#             "message": "Gmail访问令牌设置成功",
#             "token_length": len(token),
#             "token_prefix": token[:20] + "..." if len(token) > 20 else token
#         }
        
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={"success": False, "message": f"设置访问令牌失败: {str(e)}"}
#         )

# @app.delete("/gmail/token")
# async def delete_gmail_token():
#     """删除Gmail访问令牌"""
#     try:
#         import os
#         if os.path.exists('access_token.txt'):
#             os.remove('access_token.txt')
#             return {"success": True, "message": "Gmail访问令牌已删除"}
#         else:
#             return {"success": True, "message": "访问令牌文件不存在"}
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={"success": False, "message": f"删除访问令牌失败: {str(e)}"}
#       )

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"✅ WebSocket 连接成功: {websocket.client}")
    
    # 不发送自动欢迎消息，让前端控制初始显示
    
    try:
        while True:
            # 接收前端消息
            data = await websocket.receive_text()
            print(f"📨 收到消息: {data}")
            
            try:
                message_data = json.loads(data)
                
                if message_data.get("type") == "greeting":
                    # 处理个性化打招呼请求
                    greeting = main_agent.memory_agent.get_personalized_greeting("default")
                    response = {
                        "type": "reply",
                        "content": greeting
                    }
                    await websocket.send_text(json.dumps(response))
                    
                elif message_data.get("type") == "message":
                    user_input = message_data.get("content", "")
                    
                    if user_input.strip():
                        # 发送处理中状态
                        processing_msg = {
                            "type": "reply",
                            "content": "思考中... 🤔"
                        }
                        await websocket.send_text(json.dumps(processing_msg))
                        
                        # 使用 Main Agent 处理用户消息
                        ai_reply = await main_agent.process_message(user_input)
                        
                        # 发送AI回复
                        response = {
                            "type": "reply",
                            "content": ai_reply
                        }
                        await websocket.send_text(json.dumps(response))
                    
            except json.JSONDecodeError:
                error_response = {
                    "type": "reply",
                    "content": "抱歉，我没理解你的消息格式 😅"
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        print("❌ WebSocket 连接断开")
    except Exception as e:
        print(f"💥 WebSocket 错误: {e}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 Miko AI Backend...")
    print("🤖 使用 Main Agent 架构")
    print("📡 WebSocket 端点: ws://localhost:8000/ws/chat")
    print("🌐 HTTP 端点: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)