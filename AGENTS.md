# Repository Guidelines
## Project Structure & Module Organization
EXAM-MASTER is a Flask monolith rooted at `app.py`, which wires configs, SQLite init, and registers each feature blueprint. Feature logic sits in `blueprints/` (e.g., `quiz.py` for delivery flow, `user.py` for profiles, `ai.py` for AI-driven authoring). HTML templates live in `templates/`, static CSS/JS/assets in `static/`, prompt payloads and AI docs in `prompt/`, and CSV fixtures/tests in the repo root (`questions.csv`, `test_questions.csv`, `TEST_INSTRUCTIONS.md`). Keep helper scripts and experimental notebooks within `dev-doc/` or `debug/` to avoid polluting runtime modules.
## Build, Test, and Development Commands
- `python -m venv .venv && .venv\Scripts\activate` - recommended local isolation.
- `pip install -r requirements.txt` - installs Flask, requests, cryptography, and related tooling.
- `python app.py` (or `flask --app app run --debug --port 32220`) - boots the web server and seeds `database.db` from CSV when needed.
- `sqlite3 database.db ".tables"` - quick schema sanity check after migrations or CSV imports.
## Coding Style & Naming Conventions
Adopt Black-like formatting: 4-space indents, double quotes for user-facing strings, and snake_case for modules, functions, and variables. Blueprints expose a module-level `bp` object; keep route names `<feature>_<action>` to avoid collisions. Keep Jinja blocks and template filenames lowercase with hyphens (`templates/ai-manage.html`). Frontend assets mirror template names inside `static/css` or `static/js`.
## Testing Guidelines
Automated coverage is minimal today, so start each feature branch by adding pytest cases under `tests/` (mirror blueprint names, e.g., `tests/test_quiz.py`). Name tests `test_<condition>_<expected>()` and structure fixtures around temporary SQLite files. For manual regression, follow `TEST_INSTRUCTIONS.md` to swap in `test_questions.csv`, rebuild `database.db`, and walk judgment/fill-in modes. Hold contributors to >80% statement coverage before merging.
## Commit & Pull Request Guidelines
Match the existing conventional-commit pattern (`type(scope): summary`), using English scope tags when possible (e.g., `feat(quiz)`, `fix(auth)`, `docs(i18n)`). Commits should be scoped to a single concern and reference related CSV/template changes explicitly in the body. PRs must include: purpose paragraph, testing evidence (commands run, screenshots for UI shifts), database migration notes, and linked issue IDs. Keep branches rebased on `main` and avoid force-push after reviews.
## Security & Configuration Tips
Never commit real secrets; override `Config.SECRET_KEY`, database paths, and API tokens via environment variables or `.env` ignored by Git. When working with `database.db`, use throwaway copies for debugging and scrub any learner data before attaching logs to issues. Review blueprint endpoints for authentication decorators and ensure new routes default to login protection.

---
# EXAM-MASTER 项目文档

## 项目概述

EXAM-MASTER 是一个基于 Flask 的在线考试系统，提供完整的题目管理、答题练习和 AI 辅助功能。该系统支持多种题型（单选题、多选题、判断题、填空题），具备用户认证、题库管理、考试模式、统计分析等功能。

## 技术栈

- **后端框架**: Flask 2.3.3
- **数据库**: SQLite3
- **前端**: HTML5, CSS3, JavaScript
- **AI 集成**: 支持外部 AI 服务（OpenAI API 兼容）
- **加密**: cryptography 43.0.1

## 项目结构

```
EXAM-MASTER/
├── app.py                 # 主应用入口
├── config.py              # 配置文件
├── database.py            # 数据库操作模块
├── ai_service.py          # AI 服务集成模块
├── requirements.txt       # Python 依赖
├── blueprints/            # Flask 蓝图模块
│   ├── main.py           # 主页路由
│   ├── auth.py           # 用户认证
│   ├── quiz.py           # 答题功能
│   ├── user.py           # 用户管理
│   ├── load_data.py      # 数据导入
│   ├── question_bank.py  # 题库管理
│   └── ai.py             # AI 功能
├── templates/            # HTML 模板
├── static/              # 静态资源
├── prompt/              # AI 提示词
├── tools/               # 数据转换工具
└── debug/               # 调试日志
```

## 核心功能

### 1. 用户系统
- 用户注册/登录
- 会话管理
- 个人资料管理

### 2. 题库管理
- 多题库支持（系统默认 + 自定义题库）
- CSV 格式题目导入
- 题目分类和难度设置

### 3. 答题模式
- **随机答题**: 随机抽取未答过的题目
- **顺序答题**: 按题号顺序练习
- **考试模式**: 模拟正式考试
- **定时模式**: 限时答题挑战

### 4. AI 辅助功能
- 答案解析生成
- 答题提示提供
- 支持多种 AI 服务提供商
- API 密钥加密存储

### 5. 数据分析
- 答题历史记录
- 正确率统计
- 错题收藏
- 学习进度跟踪

## 数据库设计

### 主要表结构
- **questions**: 题目数据（支持多题库）
- **users**: 用户信息
- **history**: 答题历史
- **favorites**: 收藏题目
- **exam_sessions**: 考试会话
- **question_banks**: 题库信息
- **ai_providers**: AI 服务配置

### 支持的题型
- 单选题
- 多选题
- 判断题
- 填空题

## 安装和运行

### 环境要求
- Python 3.7+
- pip 包管理器

### 安装步骤
```bash
# 1. 克隆项目
git clone https://github.com/jingkarqi/EXAM-MASTER.git
cd EXAM-MASTER

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python app.py
```

### 访问地址
- 本地访问: http://localhost:32220
- 外部访问: http://[你的IP]:32220

## 配置说明

### 环境变量
- `SECRET_KEY`: Flask 应用密钥（生产环境必须设置）

### 数据文件
- `questions.csv`: 默认题库文件
- `database.db`: SQLite 数据库文件（自动生成）

## 开发规范

### 代码结构
- 使用 Flask 蓝图组织路由
- 数据库操作集中在 `database.py`
- AI 服务功能独立封装在 `ai_service.py`

### 安全实践
- 密码使用 Werkzeug 安全哈希
- API 密钥使用 Fernet 加密存储
- 会话 cookie 设置 HttpOnly

### 测试
- 测试文件: `test.py`
- 测试题目: `test_questions.csv`
- 测试说明: `TEST_INSTRUCTIONS.md`

## 工具和脚本

### 数据转换工具 (`tools/`)
- `convert_txt_csv.py`: TXT 转 CSV 格式
- `convert_gongtongt_txt_to_csv.py`: 共同体题目格式转换

### AI 提示词 (`prompt/`)
- `analysis.md`: 答案解析提示词
- `hint.md`: 答题提示提示词

## API 接口

### 主要路由
- `/`: 主页
- `/login`, `/register`: 用户认证
- `/quiz`: 答题功能
- `/question_banks`: 题库管理
- `/ai`: AI 相关功能
- `/statistics`: 统计分析

### 数据接口
- RESTful API 设计
- JSON 数据格式
- 支持流式响应（AI 服务）

## 部署注意事项

1. **生产环境配置**
   - 设置强密钥 `SECRET_KEY`
   - 关闭调试模式 `debug=False`
   - 配置 HTTPS

2. **数据库备份**
   - 定期备份 `database.db`
   - 保留原始 CSV 题库文件

3. **AI 服务配置**
   - 配置有效的 AI 服务提供商
   - 确保网络连接稳定
   - 监控 API 使用量

## 故障排查

### 调试日志
- AI 交互日志: `debug/ai_stream.log`
- 数据库错误信息
- Flask 应用日志

### 常见问题
1. 数据库初始化失败 → 检查 CSV 文件格式
2. AI 服务无响应 → 验证 API 配置和网络
3. 题目显示异常 → 检查数据库编码

## 扩展开发

### 添加新题型
1. 修改 `database.py` 中的 `validate_answer_by_type` 函数
2. 更新前端答题界面
3. 调整 AI 提示词

### 集成新的 AI 服务
1. 在 `ai_service.py` 中添加适配器
2. 更新数据库 `ai_providers` 表结构
3. 配置相应的 API 参数

## 许可证

MIT License - 详见项目根目录

## 作者

jingkarqi (soraet2005@outlook.com)S