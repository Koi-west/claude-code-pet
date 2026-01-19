# Miko Desktop Pet
去年 7 月份，我们在 Adventure X  第一次创建了 miko 。
因为在想做什么的原因，项目以很缓慢的状态在构建，今天更新了一个版本

Miko 是常驻桌面的 AI ，以 Claude Agent SDK 形式连接 Claude Code：透明窗口、永久悬浮、随时对话，并通过 Claude Code ，配合 Skills、Plugins、Sub-agents、MCP，可以被重新组合、被重新定义。


# 一些 Aha moment
虽然大部分都是 CC 本身的能力
1. 处理我的 Obsidian
因为miko  1. 在终端 2. 永久悬浮 ，所以我可以在任何地方使用他，我不用再我用 Obsidian 的时候切换，他直接访问就好了。
为了本地化，我果断把 Heptabase 


借用 Obsidian 和 notebook LM 的 Skill，我可以让他创建一个 canvas 在 Obsidian

2. GUI Agent
最近用来一个 2B 的端侧模型（腾讯开源的 GUI youtu），然后尝试把他接入到了 Claude Code，我发现了很多可能性，对于我自己的 Aha Moment：
前面提到的端侧小模型，接入了 Doubao 的 API 后，他能执行一些有趣的小任务
我觉得他的价值是大于单独下载一个的，接在 CC 里，有需要再调用
比如：加好友



我突然发现，我们在 AdventureX 计划的很多能力，可以被如此完成。这是一个我自己构建完后，一直 start 在我的桌面，自己使用，dogfooding 的东西。
# Roadmap

- milestone1（Done）：
1. 永久悬浮桌宠+对话框，连接 Claude Code
2. 连接 Claude Code，完成初步的 ChatUI 适配 Claude Code
- milestone2（Done）：
 1. Dashboard 面板管理 Skill/Plugin/MCP/API/提示词/连接端口
2. 对话记忆与管理，/start /new /history /model，真实连接状态
3. 以子工具的方式整合了腾讯开源的端侧 GUI Agent Tip，只在意图识别为需要鼠标点击的时候调用
4. 划词监听、文件/窗口索引、窗口截图、@ 搜索联动

- milestone 2：重构 miko 的设计系统/UI/UX；优化 Dashboard 任何人都能零基础配置&下载&创建 Skill、Plugin、API、MCP .... 
- milestone 3：可以下载 GitHub 开源的应用接入 Claude Code， 在 Dashboard 管理，在意图识别需要的时候调用
- milestone 4：支持和 AI 对话后创建自己的应用，后端托管在本地，在 dashboard 直接管理
- milestone 5：开放社区开放分享和使用自己的应用
- milestone 6：更主动化的 Agent 能力，监听窗口。语音交互，以及主动交互
- milestone 7：优化桌宠实现，包括动画和交互方式，音效，发布一些周边。
- milestone 8：支持用户设计自己的主视觉和桌面宠物
- milestone 9：优化 GUI 工具，优化 SOP 和工作流形式
- milestone 10：浏览器插件
- milestone 11：Agent 沙箱
- milestone 12：优化端侧模型，尽可能保证数据和隐私安全
- milestone 13：更换 miko Agent 框架为自研框架
- milestone 14：和 miko 刻意记录和维护个人数据，，以增开更多的个人 context，增援 AI 的未来。用于更好地分析和优化自己，优化后端的数据存储和知识管理（PKM） 。数据采集+安全的数据存储+安全调用，供前端应用使用，eg:健康和生物设备的数据（血糖、压力检测、血液咖啡因）、24/7 屏幕监控和分析、录制周围环境。可能会有手机端和硬件结合。
  
 