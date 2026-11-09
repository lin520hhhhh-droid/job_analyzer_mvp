# 竞品岗位数据分析系统 (Job Analyzer MVP)

这是一个基于 Python 的自动化数据管道项目，主要利用 `DrissionPage` 进行网页数据抓取，并结合 `DeepSeek API` 进行智能数据分析与处理。

## ✨ 核心功能

- **自动化爬虫**：基于 DrissionPage 抓取岗位招聘数据（带字体解密反爬）。
- **AI 智能分析**：接入 DeepSeek 大模型 API，对抓取的职位数据进行深度解析提取。
- **数据可视化**：自动生成技能图表（HTML）。
- **数据持久化**：使用本地 SQLite 数据库 (`jobs.db`) 进行数据存储。

## 🛠️ 环境要求

- **Python**: 建议 3.9 及以上版本
- **浏览器**: 建议安装最新版 Google Chrome 浏览器
- **API Key**: 需要准备一个有效的 DeepSeek API Key

## 🚀 快速开始 (Quick Start)

请严格按照以下 4 步操作，即可在本地一键跑通项目。

### 1. 克隆项目并进入目录
```bash
git clone <你的GitHub仓库地址>
cd job_analyzer_mvp
2. 安装依赖
建议使用虚拟环境（如 venv 或 conda）。激活虚拟环境后，运行：

bash
pip install -r requirements.txt
3. 配置环境变量 (⚠️ 核心步骤)
为了保护密钥安全，项目使用 .env 文件管理环境变量。代码仓库中不包含真实的密钥文件。

在 job_analyzer_mvp 目录下，复制一份模板文件并重命名为 .env：

Windows (PowerShell): copy .env.example .env

Mac/Linux: cp .env.example .env

打开新建的 .env 文件，填入你自己的 DeepSeek API Key：

env
# DeepSeek 配置
# 请前往 https://platform.deepseek.com/ 申请你自己的 Key
DEEPSEEK_API_KEY=sk-你的真实API密钥填在这里
DEEPSEEK_BASE_URL=https://api.deepseek.com
4. 启动项目
环境配置好后，直接运行主程序：

bash
python main.py
（如果程序提示缺少环境变量，请检查第 3 步的 .env 文件是否配置正确。）

📁 项目目录结构
text
job_analyzer_mvp/
├── .env                # 本地环境变量（包含真实密钥，被 .gitignore 忽略）
├── .env.example        # 环境变量模板文件
├── config.py           # 全局配置与密钥加载
├── main.py             # 项目主入口
├── spider.py           # 爬虫核心逻辑（DrissionPage）
├── font_decoder.py     # 字体反爬解密模块
├── auto_pipeline.py    # 自动化流水线处理脚本
├── draw_chart.py       # 数据图表生成
├── jobs.db             # SQLite 数据库（运行时自动生成，被忽略）
└── requirements.txt    # 项目依赖列表
⚠️ 常见问题 (FAQ)
运行 spider.py 报错找不到浏览器路径？
代码中默认写死了 Windows 的 Chrome 路径（如 C:\Program Files\Google\Chrome\Application\chrome.exe）。如果你使用的是 Mac 或自定义安装路径，请打开 spider.py，找到 options.set_browser_path(...) 这一行，将其修改为你电脑上真实的浏览器路径，或直接注释掉该行让其自动寻找。

数据库 jobs.db 需要手动创建吗？
不需要。代码内部包含自动建表逻辑，首次运行时会自动在当前目录下生成 jobs.db 文件。

如何重置数据库？
直接删除 jobs.db 文件，重新运行代码即可。