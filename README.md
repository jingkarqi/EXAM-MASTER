# EXAM-MASTER · 在线考试系统

> 基于 Flask 的多题库在线考试与 AI 助手平台，覆盖题库维护、考试流程、智能解析及运营观测的完整闭环。

## 📌 项目简介

EXAM-MASTER 是一套面向高校与培训场景的现代化在线考试系统。它提供多题型（单选、多选、判断、填空）和多题库（内置默认题库 + 自定义题库）能力，支持随机/顺序练习、定时考试、批量抽题、收藏与统计分析等完整学习流程。

项目以 Flask 为核心框架，采用蓝图拆分业务模块，结合 SQLite 数据库存储结构化信息。前端基于 Jinja2 模板与 Bootstrap 样式，AI 模块借助统一的 `ai_service.py` 接口并支持 OpenAI 兼容供应商，通过加密存储守护 API 秘钥安全。

## ✨ 功能亮点

### 学习与考试体验
- ✅ **练习模式**：随机/顺序答题、防重复算法、即时反馈与答案解析。
- ⏱ **考试模式**：定时考试、批量抽题、成绩统计、考试历史回放。
- ⭐ **答题辅助**：收藏夹、错题回顾、题型分类统计与命中率分析。

### 题库与数据治理
- 📚 **多题库**：数据库的 `question_banks` 表实现隔离，可在 UI 里创建/切换/预览/删除题库。
- 🔄 **CSV 导入**：`blueprints.load_data` 提供 CSV 上传、字段映射、格式校验与增量刷新。
- 🧾 **数据资产**：支持默认 `questions.csv`、扩展 `questions_202505共同体概论.csv` 等多份题库文件，必要时可直接替换后重建数据库。

### AI 助手
- 🧠 **题目解析**：`ai_service.py` 统一封装多厂商 API，提供题目解析、思路提示与流式输出。
- 🔐 **密钥保护**：基于 `SECRET_KEY` 的对称加密保存 API token，前端仅暴露脱敏信息。
- 🩺 **调试可观测**：所有 AI 往返被写入 `debug/ai_stream.log`，便于回放与回归测试。

### 用户与安全
- 👤 **用户体系**：注册、登录、基于 Session 的身份认证、个人中心统计。
- 🛡 **安全基线**：密码哈希、HTTPOnly Cookie、环境变量注入秘钥、敏感信息脱敏。
- 🧱 **架构规范**：蓝图路由命名统一、JSON key 统一英文、模板与静态文件按功能分层。

## 🧱 技术栈

- **后端**：Python 3.8+、Flask 2.3.3、Werkzeug、Jinja2、itsdangerous。
- **数据库**：SQLite (`database.db`)，配套 `database.py` 初始化与迁移辅助函数。
- **AI/安全**：`requests`、`cryptography` 用于外部 API 调用与密钥加密。
- **前端**：Jinja2 模板、Bootstrap 风格、`static/` 下的定制 JS/CSS。
- **工具**：`prompt/` 内置 AI 提示词、`debug/` 留存 HAR/日志用于溯源。

## 🗂 模块与目录

### 核心模块速览

| 位置 | 职责 |
| --- | --- |
| `app.py` | 应用入口，加载 `Config`、初始化数据库并注册全部蓝图。 |
| `config.py` | 环境配置（`SECRET_KEY`、Session、数据库/CSV 默认路径）。 |
| `database.py` | SQLite 连接、表结构（users、questions、history、favorites、exam_sessions、question_banks、ai_providers）及 CSV 数据灌入。 |
| `ai_service.py` | AI 供应商统一适配、密钥加密、流式响应封装、错误处理。 |
| `blueprints/main.py` | 首页、静态页面、文件下载等通用路由。 |
| `blueprints/auth.py` | 注册、登录、Session 管理。 |
| `blueprints/quiz.py` | 练习/考试流程、判分、历史与收藏。 |
| `blueprints/user.py` | 个人中心、统计与偏好设置。 |
| `blueprints/load_data.py` | CSV 上传、字段映射、预览与导入。 |
| `blueprints/question_bank.py` | 多题库 CRUD、切换、预览。 |
| `blueprints/ai.py` | AI 提供商配置、连通性测试、前端管理页。 |
| `templates/` | 页面模板（`base.html`、`exam.html` 等）。 |
| `static/` | 样式与脚本（如 `load_data.js`、`style.css`）。 |
| `prompt/analysis.md` & `prompt/hint.md` | AI 解析/提示提示词。 |
| `prompt/csv-generator.md` | 生成符合系统格式的 CSV 提示词范本。 |
| `questions.csv` / `questions_202505共同体概论.csv` | 默认及扩展题库数据源。 |

### 目录结构

```text
EXAM-MASTER/
├── app.py
├── ai_service.py
├── database.py
├── config.py
├── requirements.txt
├── AGENTS.md
├── LICENSE
├── database.db
├── questions.csv
├── questions_202505共同体概论.csv
├── blueprints/
│   ├── main.py
│   ├── auth.py
│   ├── quiz.py
│   ├── user.py
│   ├── load_data.py
│   ├── question_bank.py
│   └── ai.py
├── templates/
├── static/
│   └── js/load_data.js
├── prompt/
│   ├── analysis.md
│   ├── hint.md
│   └── csv-generator.md
└── ...
```

## 🚀 快速开始

1. **创建虚拟环境并安装依赖**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **配置环境变量**
   ```powershell
   $env:SECRET_KEY = "请替换为生产级随机秘钥"
   $env:FLASK_APP = "app"
   ```
3. **初始化数据库（第一次或清库后需要）**
   ```powershell
   python -c "from database import init_db; init_db()"
   ```
   首次启动 `app.py` 也会自动调用 `init_db()`，确保 CSV 数据被导入。
4. **启动应用**
   ```powershell
   python app.py
   # 或
   flask run --debug --port 32220
   ```
5. **访问与体验**  
   打开浏览器访问 `http://localhost:32220`，使用题库或新建题库体验完整流程。

## ⚙️ 环境与配置

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | `change_this_in_production` | 用于 Session 与 AI 密钥加密，务必通过环境变量覆盖。 |
| `DATABASE_FILE` | `database.db` | SQLite 文件，若结构更新请删除后执行 `init_db()` 重建。 |
| `CSV_FILE` | `questions.csv` | 默认题库来源，可替换为测试/新题库。 |
| `FLASK_APP` | `app` | 使 `flask run` 能定位入口。 |
| `PORT` | `32220` | 通过 `app.py` 或 `flask run --port` 指定。 |

- 修改 CSV 后 **删除 `database.db`** 再重建，以确保新数据生效。
- 题库/AI 配置均写入 SQLite，可通过蓝图页面管理，无需手工更新表结构。
- 生产部署请搭配反向代理、TLS、持久化卷与安全密钥管理器。

## 🧪 测试与质量保证

- **单元测试**：按约定将用例放在 `tests/test_<feature>.py`，运行 `python -m unittest discover -s tests -p "test_*.py"`。
- **手动 QA（参考 TEST_INSTRUCTIONS 流程）**：
  1. 将 `test_questions.csv` 覆盖为 `questions.csv`（或通过题库管理导入测试题）。
  2. 删除 `database.db`，重新运行 `python -c "from database import init_db; init_db()"`。
  3. 启动应用，重点验证判断题与填空题的判分、AI 提示生成、题库切换与收藏功能。
  4. 记录日志并关注 `debug/ai_stream.log` 中是否有异常栈或超时。
- **AI 回归**：遇到提示词更新时，复现典型题目，核对 `prompt/analysis.md`、`prompt/hint.md` 的变更是否引入回归。
- **调试建议**：善用浏览器控制台、Flask 调试模式，以及 `debug/*.har` 逐包排查前后端联调问题。

## 📚 题库与数据工作流

- 默认 `questions.csv` 随仓库提供，`questions_202505共同体概论.csv` 可作为扩展题库示例。
- `blueprints.question_bank` 管理 `question_banks` 表：支持创建、启用、删除题库，且数据完全隔离。
- `blueprints.load_data` 提供 CSV 上传/解析、字段映射、预览与入库，确保导入前可核对。
- **更新题库的推荐步骤**：
  1. 备份现有 `database.db` 与 CSV；
  2. 使用题库管理界面导入 CSV 或直接替换 `questions.csv`；
  3. 删除旧的 `database.db` 并执行 `init_db()`；
  4. 在 UI 中切换到目标题库，使用预览功能确认字段、题型与答案无误。
- 进行批量改题后，请同步更新 `prompt/csv-generator.md` 或维护相应的脚本，保持 AI 提示词与题型结构一致。

## 🤖 AI 集成指南

1. **在前端配置供应商**：登录 -> “我的” -> “AI 功能管理”，新增 OpenAI 兼容接口，填写名称、Base URL、模型参数。
2. **安全写入密钥**：前端提交后由 `ai_service.py` 使用 `SECRET_KEY` 加密存储，仅在调用时解密。
3. **提示词管理**：`prompt/analysis.md` 定义解析模板、`prompt/hint.md` 定义思路提示、`prompt/csv-generator.md` 辅助生成题库内容；调试更新需同步 QA。
4. **流式输出**：AI 回答实时写入 SSE 流并镜像到 `debug/ai_stream.log`，排障时可回放同一题目的生成轨迹。
5. **上线前检查**：确认网络连通性、防火墙策略、请求超时与错误重试策略是否符合部署环境要求。

## 🛠 开发提示

- 遵循 PEP 8、4 空格缩进、函数/路由使用 `snake_case`，类（如 `Config`）使用 `UpperCamelCase`。
- 每个蓝图都暴露 `bp` 对象，并以功能名作为路由前缀（如 `quiz_start`），保持命名一致性。
- 模板命名采用 `lowercase_with_underscores.html`，与相应蓝图的目录结构保持对称；静态资源同步分门别类。
- JSON key 使用英文，题目文本可中英混合；涉及业务逻辑的代码块必要时添加简洁注释。
- 阅读 `AGENTS.md` 获取更多约定（提交信息格式、测试流程、敏感信息处理等）。
- AI 调试日志 (`debug/ai_stream.log`) 较大，提交前请清理或 .gitignore 中排除。

## 🩺 常见问题

| 场景 | 处理方式 |
| --- | --- |
| 题库更新后界面无变化 | 删除 `database.db` 并执行 `init_db()`，确认新 CSV/题库指向正确。 |
| CSV 导入失败 | 确认文件为 UTF-8、包含题干/题型/答案等必需列，必要时参考 `prompt/csv-generator.md`。 |
| AI 请求异常或无响应 | 检查 `AI 功能管理` 中的 Base URL/模型/密钥是否有效，同时查看 `debug/ai_stream.log`。 |
| 登录状态频繁失效 | 设置强随机 `SECRET_KEY` 并清理旧 Session Cookie；在生产启用 HTTPS。 |
| 启动端口占用 | 修改 `flask run --port <new_port>` 或在 `app.py` 中调整 `port` 参数。 |

## 🤝 贡献指南

1. Fork 或创建功能分支前，先阅读了解编码、测试、Commit/PR 规范。
2. 命名 Commit 时遵循类似 `feat(quiz): 支持批量抽题` 的 Conventional Commits 语法。
3. 为新增功能补充自动化测试（`tests/test_<feature>.py`）和/或更新手动验证步骤。
4. 涉及题库或 AI 提示词的变更，请在 PR 中说明数据来源、更新脚本与对应的 QA 结果。
5. PR 描述中附上运行 `python -m unittest`、手动流程、数据库重建等验证步骤，UI/AI 变更请附截图或日志片段。

## 📄 许可证

本项目采用 [MIT License](LICENSE)。在商用或二次开发前请保留原版权声明，并妥善处理题库/用户数据的隐私与授权。
