#!/usr/bin/env python3
import pdfplumber
import re
import json

def extract_text_from_pdf(pdf_path):
    """从PDF中提取所有文本"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- 第{i+1}页 ---\n"
                text += page_text
    return text

def analyze_pdf_content(text):
    """分析PDF内容并提取关键信息"""

    # 提取标题和作者
    title_match = re.search(r'“数字控制”下的劳动秩序\s*———外卖骑手的劳动控制研究\s*(\S+)', text)
    author = title_match.group(1) if title_match else "陈龙"

    # 提取摘要部分
    abstract_pattern = r'提要:([^。]+。)'
    abstract_match = re.search(abstract_pattern, text)
    abstract = abstract_match.group(1) if abstract_match else ""

    # 提取关键词
    keywords_pattern = r'关键词:([^\n]+)'
    keywords_match = re.search(keywords_pattern, text)
    keywords = keywords_match.group(1).strip() if keywords_match else "外卖骑手 劳动过程 控制权 数字控制"

    # 提取主要章节内容
    sections = {}

    # 组织技术控制部分
    org_control_pattern = r'(组织技术控制|控制权重新分配)[^。]*。'
    org_matches = re.findall(org_control_pattern, text)

    # 科学技术控制/数字控制部分
    tech_control_pattern = r'(数字控制|科学技术控制)[^。]*。'
    tech_matches = re.findall(tech_control_pattern, text)

    # 骑手自主性部分
    autonomy_pattern = r'(骑手自主性|骑手反抗|自主性空间)[^。]*。'
    autonomy_matches = re.findall(autonomy_pattern, text)

    # 结论部分
    conclusion_pattern = r'(结论|反思|资本控制)[^。]*。'
    conclusion_matches = re.findall(conclusion_pattern, text[-2000:])  # 只搜索最后2000字符

    return {
        "title": "数字控制下的劳动秩序——外卖骑手的劳动控制研究",
        "author": author,
        "abstract": abstract,
        "keywords": keywords,
        "org_control": org_matches[:5],  # 取前5条
        "tech_control": tech_matches[:5],
        "autonomy": autonomy_matches[:5],
        "conclusion": conclusion_matches[:5]
    }

def generate_canvas_content(analysis):
    """生成Komorebi canvas格式的内容"""

    canvas_data = {
        "nodes": [
            {
                "id": "1",
                "type": "text",
                "x": 0,
                "y": -200,
                "width": 450,
                "height": 220,
                "text": f"# 数字控制下的劳动秩序\n## 外卖骑手的劳动控制研究\n\n### 研究核心\n- **作者**：{analysis['author']}\n- **研究视角**：劳动过程理论\n- **研究对象**：外卖骑手\n- **研究方法**：参与式观察（6个月骑手体验）\n\n### 研究背景\n互联网平台经济中，外卖骑手看似自由，实则面临新的劳动控制方式。本文从组织技术和科学技术两个维度分析数字控制下的劳动秩序。"
            },
            {
                "id": "2",
                "type": "text",
                "x": -250,
                "y": 100,
                "width": 500,
                "height": 300,
                "text": "## 组织技术控制：控制权重新分配\n\n### 核心观点\n1. **平台系统负责指导骑手工作**（派单、路线规划、时间计算）\n2. **消费者负责评估骑手工作**（评分、评价、投诉）\n3. **平台系统负责最终奖惩**（蜂值、等级、奖金）\n\n### 结果\n- 劳资冲突对象转移（平台系统和消费者成为\"替罪羊\"）\n- 雇佣关系认定难度增加\n- 平台公司淡化雇主责任\n\n### 理论意义\n平台公司看似放弃直接控制，实则通过重新分配控制权实现间接控制。"
            },
            {
                "id": "3",
                "type": "text",
                "x": 350,
                "y": 100,
                "width": 500,
                "height": 320,
                "text": "## 科学技术控制：数字控制\n\n### 核心特征\n1. **数据收集**：通过GPS、Wi-Fi、蓝牙等技术收集骑手、商家、消费者数据\n2. **数据分析**：运用算法、模型分析数据，计算送达时间、规划路线\n3. **数据应用**：将分析结果用于管理，实现精准控制\n\n### 数字控制 vs 数值控制\n- **控制对象**：从机器到骑手\n- **数据含义**：从无意义数值到具有分析价值的数据\n- **数据来源**：从单一程序到多源数据\n- **控制过程**：从公开到隐秘\n\n### 控制效果\n数字控制削弱骑手反抗意愿，蚕食自主性空间。"
            },
            {
                "id": "4",
                "type": "text",
                "x": -50,
                "y": 500,
                "width": 500,
                "height": 280,
                "text": "## 骑手自主性与数字控制的较量\n\n### 骑手的自主性表现\n- **发现系统\"漏洞\"**：如\"挂单\"策略，同时接多单提高收入\n- **利用\"报备\"机制**：通过报备延长配送时间\n- **路线优化**：根据经验选择更优路线\n\n### 数字控制的回应\n- **数据监控**：收集骑手行为数据，检测异常模式\n- **系统升级**：不断升级算法，修补\"漏洞\"\n- **精准预测**：通过历史数据预测骑手行为\n\n### 最终结果\n骑手自主性空间被持续蚕食，反抗意愿和能力被削弱。"
            },
            {
                "id": "5",
                "type": "text",
                "x": -50,
                "y": 850,
                "width": 500,
                "height": 280,
                "text": "## 结论与反思\n\n### 资本控制的转变趋势\n1. **从\"硬控制\"到\"软控制\"**：从专制控制转向霸权控制\n2. **从\"显控制\"到\"隐控制\"**：从实体控制转向虚拟控制\n\n### 理论贡献\n- 揭示了互联网平台经济中劳动控制的新形态\n- 拓展了劳动过程理论在数字时代的适用性\n- 提出了\"数字控制\"概念，区别于传统\"数值控制\"\n\n### 现实反思\n- **技术中立神话破灭**：技术背后是资本操纵\n- **数据权利问题**：需警惕平台公司的数据侵犯\n- **自由幻象**：骑手的\"自由\"是被数字控制塑造的\n- **劳动关系认定**：平台经济下雇佣关系更加模糊"
            }
        ],
        "edges": [
            {
                "id": "1-2",
                "fromNode": "1",
                "fromSide": "bottom",
                "toNode": "2",
                "toSide": "top"
            },
            {
                "id": "1-3",
                "fromNode": "1",
                "fromSide": "bottom",
                "toNode": "3",
                "toSide": "top"
            },
            {
                "id": "2-4",
                "fromNode": "2",
                "fromSide": "bottom",
                "toNode": "4",
                "toSide": "top"
            },
            {
                "id": "3-4",
                "fromNode": "3",
                "fromSide": "bottom",
                "toNode": "4",
                "toSide": "top"
            },
            {
                "id": "4-5",
                "fromNode": "4",
                "fromSide": "bottom",
                "toNode": "5",
                "toSide": "top"
            }
        ]
    }

    return canvas_data

def main():
    pdf_path = "/Users/apple/Downloads/“数字控制”下的劳动秩序——外卖骑手的劳动控制研究_陈龙.pdf"

    print("正在读取PDF...")
    text = extract_text_from_pdf(pdf_path)

    print("正在分析内容...")
    analysis = analyze_pdf_content(text)

    print("正在生成canvas内容...")
    canvas_data = generate_canvas_content(analysis)

    # 保存到文件
    output_path = "/Users/apple/Documents/komorebi/komorebi/canvas/测试专用.canvas"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(canvas_data, f, ensure_ascii=False, indent=2)

    print(f"Canvas文件已保存到: {output_path}")

    # 同时生成文本总结
    summary_path = "/tmp/pdf_summary_detailed.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"论文标题: {analysis['title']}\n")
        f.write(f"作者: {analysis['author']}\n")
        f.write(f"关键词: {analysis['keywords']}\n\n")
        f.write(f"摘要: {analysis['abstract']}\n\n")
        f.write("=" * 50 + "\n\n")
        f.write("详细内容分析:\n")
        f.write("\n".join(analysis['org_control']) + "\n")
        f.write("\n".join(analysis['tech_control']) + "\n")
        f.write("\n".join(analysis['autonomy']) + "\n")
        f.write("\n".join(analysis['conclusion']) + "\n")

    print(f"详细总结已保存到: {summary_path}")

if __name__ == "__main__":
    main()
