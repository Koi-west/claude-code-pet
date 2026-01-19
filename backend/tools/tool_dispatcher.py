#!/usr/bin/env python3
"""
工具调度器
负责分发和协调各种工具的调用
"""

import json
from tools.app_control import handle_app_control
from tools.file_management import handle_file_management
from tools.python_executor import handle_python_execution
from tools.gmail_tool import handle_gmail_operation

def handle_dynamic_tools(tool_calls):
    """处理动态工具调用 - 统一调度器"""
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        if function_name == "control_application":
            result = handle_app_control(arguments)
            results.append(result)
        elif function_name == "manage_files":
            result = handle_file_management(arguments)
            results.append(result)
        elif function_name == "execute_python":
            result = handle_python_execution(arguments)
            results.append(result)
        elif function_name == "gmail_operation":
            result = handle_gmail_operation(arguments)
            results.append(result)
        # 后续可以添加其他 tool 处理
        # elif function_name == "setup_workflow":
        #     result = handle_work_mode(arguments)
        else:
            results.append(f"❌ 未知的工具: {function_name}")
    
    return " | ".join(results)