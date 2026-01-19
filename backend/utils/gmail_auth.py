# new_gmail_auth.py - 使用新的OAuth客户端
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
import os

# OAuth配置 - 从环境变量读取
import os
CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")

def setup_gmail_auth():
    """配置Gmail认证"""
    print("🔐 开始Gmail认证...")
    
    # 创建客户端配置
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8001/oauth2callback"]
        }
    }
    
    # OAuth权限范围 - 包含发送权限
    scopes = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    try:
        # 创建OAuth流程
        flow = InstalledAppFlow.from_client_config(client_config, scopes)
        
        print("🌐 即将打开浏览器进行授权...")
        print("请在浏览器中完成Google账户授权")
        
        # 使用8001端口进行认证
        creds = flow.run_local_server(
            port=8001,
            open_browser=True,
            prompt='consent'
        )
        
        print("✅ 认证成功！")
        
        # 保存访问令牌
        with open('./backend/access_token.txt', 'w') as f:
            f.write(creds.token)
        
        print("💾 访问令牌已保存到 ./backend/access_token.txt")
        
        # 测试Gmail连接
        print("📧 测试Gmail连接...")
        service = build('gmail', 'v1', credentials=creds)
        print("已启动服务")
        
        # 获取用户信息
        profile = service.users().getProfile(userId='me').execute()
        print(f"📧 邮箱: {profile['emailAddress']}")
        print(f"📊 总邮件数: {profile.get('messagesTotal', 'N/A')}")
        
        # 获取最新3封邮件
        print("\n📬 获取最新3封邮件...")
        messages = service.users().messages().list(userId='me', maxResults=3).execute()
        
        if messages.get('messages'):
            for i, msg in enumerate(messages['messages'][:3], 1):
                msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
                snippet = msg_detail.get('snippet', '无内容')[:50]
                print(f"  {i}. {snippet}...")
        
        print("\n🎉 Gmail API 配置完成！")
        print("现在可以使用Gmail功能了：")
        print("  • 读取邮件")
        print("  • 发送邮件")
        print("  • 搜索邮件")
        
        return True
        
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        print("\n💡 解决方案:")
        print("1. 确保在Google Cloud Console中添加了重定向URI: http://localhost:8001/")
        print("2. 检查客户端ID和密钥是否正确")
        print("3. 确保Gmail API已启用")
        return False

def test_gmail_functionality():
    """测试Gmail功能"""
    print("\n🧪 测试Gmail功能...")
    
    # 检查访问令牌
    if not os.path.exists('access_token.txt'):
        print("❌ 未找到访问令牌，请先运行认证")
        return
    
    with open('access_token.txt', 'r') as f:
        token = f.read().strip()
    
    if not token:
        print("❌ 访问令牌为空")
        return
    
    print(f"✅ 访问令牌: {token[:30]}...")
    print("🎯 Gmail API 已就绪!")

if __name__ == '__main__':
    print("=" * 50)
    print("📧 Gmail API 认证配置")
    print("=" * 50)
    
    print("🔧 使用的OAuth配置:")
    print(f"   客户端ID: {CLIENT_ID}")
    print(f"   重定向端口: 8001")
    
    # 运行认证
    success = setup_gmail_auth()
    
    if success:
        # 测试功能
        test_gmail_functionality()
    else:
        print("\n💥 认证失败，请检查配置")