# Repository Guidelines

## Project Structure & Module Organization
EXAM-MASTER runs as a Flask app from `app.py`, which loads `Config` and registers the feature blueprints (`main`, `auth`, `quiz`, `user`, `load_data`, `question_bank`, `ai`). Domain helpers sit beside them, while persistence lives in `database.py` and the CSV banks (`questions.csv`, `ds题库.csv`, fixtures noted in `TEST_INSTRUCTIONS.md`) that hydrate `database.db`. Front-end templates and assets live under `templates/` and `static/`, AI prompt files sit in `prompt/`, debug traces land in `debug/ai_stream.log`, and CSV conversion scripts stay in `tools/`.

## Build, Test, and Development Commands
- `python -m venv .venv && .\.venv\Scripts\activate`: create or enter the repo-local virtualenv.
- `pip install -r requirements.txt`: install Flask, requests, cryptography, and other runtime dependencies.
- `python app.py` or `set FLASK_APP=app && flask run --debug --port 32220`: start the server; the first run invokes `database.init_db()`.
- After editing CSV data, delete `database.db` then relaunch (or run `python -c "from database import init_db; init_db()"` inside `flask shell`) to reload the schema.

## Coding Style & Naming Conventions
Use PEP 8, 4-space indentation, and `snake_case` for functions and routes; keep classes like `Config` in UpperCamelCase. Each blueprint file exposes a `bp` instance and prefixes route handlers with the feature (`quiz_start`, `quiz_submit`). Save templates as lowercase_with_underscores inside feature folders, mirror that layout in `static/`, and keep JSON keys in English while allowing bilingual question text.

## Testing Guidelines
Place automated suites in `tests/`, naming files `test_<feature>.py`, and run everything via `python -m unittest discover -s tests -p "test_*.py"`. Follow `TEST_INSTRUCTIONS.md` for manual QA: replace `questions.csv` with `test_questions.csv`, remove `database.db`, and restart to validate judgment and fill-in flows. Record AI-hint regressions by replaying representative items and watching `debug/ai_stream.log` for errors.

## Commit & Pull Request Guidelines
Commits follow a Conventional Commits flavor such as `feat(import): 添加CSV生成提示词功能`, so keep the `type(scope): summary` skeleton, use imperative verbs, and mention the module touched. Pull requests should summarize the change, link its issue or task, document data migrations (CSV swaps, SQL scripts), attach screenshots for UI or AI updates, and list the tests you ran (`python -m unittest`, manual quiz paths, CSV reload steps).

## Security & Configuration Tips
Export `SECRET_KEY` before running so `ai_service.py` can encrypt downstream API tokens; never store raw provider keys in Git. Treat `database.db` as disposable dev data, purge `debug/ai_stream.log` before sharing, scrub new CSV banks for sensitive content, and keep environment-specific overrides in real environment variables instead of hard-coding them.
---
# EXAM-MASTER - 在线考试系统

## 项目概述

EXAM-MASTER 是一个基于 Flask 的现代化在线考试系统，支持多种题型、AI 辅助功能和多题库管理。系统采用模块化架构，提供完整的用户管理、题库管理和考试功能。

## 技术栈

- **后端**: Python 3.8+ + Flask 2.3.3
- **数据库**: SQLite
- **前端**: HTML5 + CSS3 + JavaScript (Bootstrap 样式)
- **AI 集成**: 支持多种 AI 提供商（OpenAI 兼容接口）
- **加密**: Cryptography (API 密钥加密存储)

## 核心功能

### 1. 用户管理系统
- 用户注册/登录
- 基于 Session 的认证
- 用户权限管理
- 个人信息管理

### 2. 题库管理
- **多题库支持**: 系统默认题库 + 用户自定义题库
- **题型支持**:
  - 单选题 (A/B/C/D/E)
  - 多选题 (A/B/C/D/E)
  - 判断题 (正确/错误)
  - 填空题 (支持多空格)
- **题库导入**: CSV 格式题库导入
- **题库预览**: 支持题库内容预览
- **题库管理**: 创建、删除、切换题库

### 3. 答题功能
- **随机答题**: 避免重复答题
- **顺序答题**: 按题号顺序答题
- **答题历史**: 完整记录答题历史
- **收藏功能**: 标记重要题目
- **统计分析**: 答题准确率、分类统计

### 4. 考试模式
- **定时考试**: 设置考试时间限制
- **批量答题**: 随机抽取指定数量题目
- **成绩统计**: 自动计算分数和排名
- **考试历史**: 完整的考试记录

### 5. AI 助手功能
- **题目解析**: AI 生成详细的题目解析
- **思路提示**: 提供循序渐进的解题思路
- **流式响应**: 实时 AI 回答流
- **多提供商支持**: 支持 OpenAI、Claude 等多种 AI 服务
- **API 管理**: 安全的 API 密钥加密存储

## 项目架构

### 目录结构
```
EXAM-MASTER/
├── app.py                    # 应用入口文件
├── config.py                 # 配置文件
├── database.py              # 数据库操作模块
├── ai_service.py            # AI 服务集成
├── requirements.txt         # Python 依赖
├── blueprints/              # Flask 蓝图模块
│   ├── auth.py             # 用户认证
│   ├── main.py             # 主要路由
│   ├── quiz.py             # 答题功能
│   ├── user.py             # 用户管理
│   ├── question_bank.py    # 题库管理
│   ├── load_data.py        # 数据导入
│   └── ai.py               # AI 功能
├── templates/              # HTML 模板
│   ├── base.html           # 基础模板
│   ├── index.html          # 首页
│   ├── exam.html           # 考试页面
│   ├── ai-manage.html      # AI 管理
│   └── ...                 # 其他模板
├── static/                 # 静态资源
│   ├── style.css           # 样式文件
│   ├── js/                 # JavaScript 文件
│   └── load_data.js        # 数据加载脚本
├── prompt/                 # AI 提示词
│   ├── analysis.md         # 题目解析提示词
│   └── hint.md             # 题目提示提示词
├── tools/                  # 工具脚本
└── debug/                  # 调试日志
```

### 核心模块

#### 数据库设计 (database.py)
- **users**: 用户信息表
- **questions**: 题目表（支持多题库）
- **history**: 答题历史表
- **favorites**: 收藏表
- **exam_sessions**: 考试会话表
- **question_banks**: 题库表
- **ai_providers**: AI 提供商配置表

#### AI 服务 (ai_service.py)
- **API 密钥加密**: 基于 SECRET_KEY 的安全加密
- **多提供商支持**: 统一的接口适配不同 AI 服务
- **流式响应**: 支持流式 AI 回答
- **连接验证**: 自动验证 API 连接状态
- **调试日志**: 完整的 AI 交互日志记录

#### 蓝图模块 (blueprints/)
- **auth.py**: 用户注册、登录、认证
- **main.py**: 主页、错误处理、文件下载
- **quiz.py**: 答题逻辑、历史记录、收藏
- **user.py**: 用户信息、个人设置
- **question_bank.py**: 题库管理、导入导出
- **load_data.py**: CSV 数据导入处理
- **ai.py**: AI 功能管理、API 调用

## 快速开始

### 环境要求
- Python 3.8+
- 必要的 Python 包（见 requirements.txt）

### 安装步骤
1. 克隆项目到本地
2. 安装依赖: `pip install -r requirements.txt`
3. 启动应用: `python app.py`
4. 访问: http://localhost:32220

### 默认配置
- **端口**: 32220
- **调试模式**: 开启
- **数据库**: SQLite (database.db)
- **初始题库**: questions.csv

## 核心特性详解

### 1. 多题库架构
- 系统内置默认题库（题库 ID: 0）
- 用户可创建自定义题库
- 题库间完全隔离，数据安全
- 支持题库切换和预览

### 2. 智能答题系统
- **去重算法**: 自动避免重复答题
- **题型适配**: 智能识别题型并提供相应界面
- **答案验证**: 支持精确匹配和容错匹配
- **实时反馈**: 即时显示答题结果

### 3. AI 集成架构
- **统一接口**: 适配任何 OpenAI 兼容的 API
- **密钥安全**: AES 加密存储用户 API 密钥
- **流式输出**: 实时显示 AI 生成内容
- **容错机制**: 自动重试和错误处理
- **调试支持**: 完整的请求响应日志

### 4. 数据安全
- **密码哈希**: 使用 Flask 安全密码哈希
- **会话管理**: 安全的 Session 配置
- **SQL 注入防护**: 参数化查询
- **数据加密**: 敏感信息加密存储

## 使用指南

### 管理员功能
1. **题库管理**: 创建、删除、导入题库
2. **用户管理**: 查看用户统计和管理
3. **系统设置**: 配置系统参数

### 普通用户功能
1. **答题练习**: 随机/顺序答题模式
2. **考试模式**: 定时考试和批量答题
3. **AI 助手**: 题目解析和思路提示
4. **个人中心**: 查看统计和历史记录

### AI 功能配置
1. 访问"我的 > AI功能管理"
2. 添加 AI 服务提供商配置
3. 输入 API 密钥（支持加密存储）
4. 激活配置并验证连接
5. 在答题中使用 AI 助手

## 开发和扩展

### 添加新题型
1. 在 `database.py` 中更新题型识别逻辑
2. 在模板中添加相应界面
3. 更新答题验证逻辑

### 集成新 AI 服务
1. 在 `ai_service.py` 中添加新的适配器
2. 更新配置界面
3. 测试连接和响应

### 自定义主题
1. 修改 `static/style.css`
2. 更新 Bootstrap 变量
3. 调整模板文件

## 故障排除

### 常见问题
1. **数据库错误**: 删除 database.db 重新初始化
2. **AI 连接失败**: 检查 API 密钥和网络连接
3. **题库导入失败**: 检查 CSV 文件格式
4. **权限错误**: 确认用户登录状态

### 调试模式
- 开启 Flask 调试模式查看详细错误信息
- 检查 `debug/ai_stream.log` 中的 AI 交互日志
- 查看浏览器控制台的前端错误

## 许可证

MIT License - 详见项目根目录 LICENSE 文件

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 更新日志

### v2.0.0
- 新增 AI 助手功能
- 支持多题库管理
- 优化用户界面
- 添加流式 AI 响应
- 增强安全机制

### v1.0.0
- 基础考试系统
- 用户认证
- 题库管理
- 答题功能