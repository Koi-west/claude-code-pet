#!/usr/bin/env python3
"""
Python 脚本执行工具
动态生成和执行 Python 代码来完成各种任务
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path
from openai import OpenAI

# 初始化 AI 客户端
import os
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

def execute_python_code(code: str) -> str:
    """安全执行 Python 代码"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # 执行 Python 代码 (尝试 python3，如果失败则尝试 python)
        try:
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超时
                cwd=os.path.dirname(temp_file)
            )
        except FileNotFoundError:
            # 如果 python3 不存在，尝试 python
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超时
                cwd=os.path.dirname(temp_file)
            )
        
        # 清理临时文件
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return f"✅ 执行成功:\n{result.stdout.strip()}"
        else:
            return f"❌ 执行失败:\n{result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return "❌ 执行超时 (30秒)"
    except Exception as e:
        return f"❌ 执行错误: {str(e)}"

def generate_python_script(task: str) -> str:
    """使用 AI 生成 Python 脚本"""
    script_prompt = f"""请为以下任务生成 Python 代码：

任务：{task}

要求：
1. 只返回可执行的 Python 代码，不要解释
2. 代码要完整且能直接运行，尽量简单
3. 如果需要网络请求，使用 requests 库
4. 如果需要处理数据，使用标准库或常见库
5. 最后要 print 输出结果

天气查询示例（默认杭州）：
```python
import requests
def get_weather(city="杭州"):
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.weatherapi.com/v1/forecast.json"
    params = {{'key': api_key, 'q': city, 'days': 1, 'lang': 'zh'}}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if response.status_code == 200:
            current = data['current']['condition']['text']
            today = data['forecast']['forecastday'][0]['day']
            max_temp = today['maxtemp_c']
            min_temp = today['mintemp_c']
            print(f"🌤️ {{city}}: {{current}}, {{min_temp}}°C ~ {{max_temp}}°C")
        else:
            print(f"❌ 错误: {{data.get('error', {{}}).get('message', '未知错误')}}")
    except Exception as e:
        print(f"❌ {{city}} 获取失败: {{e}}")
get_weather("杭州")
```

常见任务类型：
- 获取天气：使用上面的weatherapi.com示例，地点是杭州
- 获取时间：使用 datetime 库
- 文件操作：使用 os, pathlib 库
- 网络请求：使用 requests 库
- 数据处理：使用 json, csv 等库
- 统计数据查询：使用可靠的API或数据源

重要注意事项：
- 不要使用需要特殊权限的操作（如psutil.net_connections()在macOS上需要权限）
- 不要执行危险的系统命令
- 天气查询直接使用上面的示例代码
- 对于人口、经济等统计数据，要使用权威数据源，如果API数据不准确要说明
- 如果无法获取准确数据，应该说明数据来源的限制
- 避免生成可能不准确的硬编码数据
- 系统状态查询避免使用需要权限的功能，改用基础的CPU、内存、磁盘信息

请生成完整的 Python 代码："""

    print(f"🤖 正在生成Python脚本 for: {task}")
    
    response = client.chat.completions.create(
        model="kimi-k2-0711-preview",
        messages=[{"role": "user", "content": script_prompt}],
        temperature=0.0
    )
    
    script = response.choices[0].message.content.strip()
    # 清理可能的markdown标记
    script = script.replace("```python", "").replace("```", "").strip()
    
    print(f"📝 生成的脚本:\n{script}\n")
    return script

def handle_python_execution(arguments: dict) -> str:
    """处理 Python 脚本执行请求"""
    task = arguments.get("task", "")
    code = arguments.get("code", "")
    
    if code:
        # 直接执行提供的代码
        print(f"🐍 直接执行Python代码")
        result = execute_python_code(code)
    else:
        # 生成并执行代码
        print(f"🤖 为任务生成Python脚本: {task}")
        generated_code = generate_python_script(task)
        print(f"🔧 开始执行生成的代码...")
        result = execute_python_code(generated_code)
        print(f"📊 执行结果: {result}")
    
    return f"⚡ Python执行结果: {result}"

# 预定义的一些常用脚本模板
SCRIPT_TEMPLATES = {
    "weather": """
import requests

def get_weather(city="杭州"):
    \"\"\"获取天气、最高温、最低温\"\"\"
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.weatherapi.com/v1/forecast.json"
    params = {
        'key': api_key,
        'q': city,
        'days': 1,
        'lang': 'zh'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            # 当前天气
            current = data['current']['condition']['text']
            # 今日最高最低温
            today = data['forecast']['forecastday'][0]['day']
            max_temp = today['maxtemp_c']
            min_temp = today['mintemp_c']
            
            print(f"🌤️ {city}: {current}, {min_temp}°C ~ {max_temp}°C")
            return {
                'city': city,
                'weather': current,
                'min_temp': min_temp,
                'max_temp': max_temp
            }
        else:
            print(f"❌ 错误: {data.get('error', {}).get('message', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"❌ {city} 获取失败: {e}")
        return None

if __name__ == "__main__":
    result = get_weather("杭州")
""",
    
    "time": """
from datetime import datetime
import locale

def get_current_time():
    try:
        now = datetime.now()
        
        print(f"📅 当前日期: {now.strftime('%Y年%m月%d日')}")
        print(f"🕐 当前时间: {now.strftime('%H:%M:%S')}")
        print(f"📆 星期: {now.strftime('%A')}")
        
    except Exception as e:
        print(f"获取时间失败: {e}")

if __name__ == "__main__":
    get_current_time()
""",
    
    "system_info": """
import platform
import psutil
import os

def get_system_info():
    try:
        print(f"💻 系统: {platform.system()} {platform.release()}")
        print(f"🖥️ 处理器: {platform.processor()}")
        print(f"🧠 CPU使用率: {psutil.cpu_percent()}%")
        print(f"💾 内存使用率: {psutil.virtual_memory().percent}%")
        print(f"💿 磁盘使用率: {psutil.disk_usage('/').percent}%")
        
    except Exception as e:
        print(f"获取系统信息失败: {e}")

if __name__ == "__main__":
    get_system_info()
"""
}