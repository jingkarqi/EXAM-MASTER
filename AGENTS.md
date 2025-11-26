# EXAM-MASTER 项目开发手册

## 一、项目概述

EXAM-MASTER 是一个基于 Flask 的在线考试系统，提供多种题型支持和灵活的答题模式，旨在为用户提供完整的在线学习与考试体验。

### 技术栈
- **后端框架**: Flask 2.3.3
- **数据库**: SQLite（使用 sqlite3.Row 返回字典格式数据）
- **前端**: HTML5, CSS3, JavaScript, Bootstrap
- **模板引擎**: Jinja2
- **认证机制**: Session-based（会话时长 7 天）

### 核心功能

**1. 题型支持**
- 单选题、多选题、判断题、填空题
- 选项使用 JSON 可序列化字典存储

**2. 答题模式**
- 随机答题：抽取未答过的题目
- 顺序答题：按题号顺序答题
- 考试模式：限时考试环境
- 定时模式：自定义时长练习

**3. 用户功能**
- 用户注册/登录、答题历史记录、题目收藏、统计分析、多题库支持

---

## 二、项目架构与目录结构

```
EXAM-MASTER/
├── app.py                      # 主应用入口，初始化 Flask、Config、SQLite 和注册蓝图
├── config.py                   # 配置文件（默认端口 32220，调试模式开发环境启用）
├── database.py                 # 数据库操作和模型，集中定义模式常量（如 SYSTEM_QUESTION_BANK_ID）
├── requirements.txt            # Python 依赖
├── questions.csv               # 题目资源文件（仓库根目录，支持变体）
├── database.db                 # SQLite 数据库文件（自动生成）
├── blueprints/                 # Flask 蓝图模块（模块名与用途一致）
│   ├── main.py                 # 主页路由
│   ├── auth.py                 # 用户认证
│   ├── quiz.py                 # 答题逻辑
│   ├── user.py                 # 用户管理
│   ├── load_data.py            # 数据导入
│   └── question_bank.py        # 题库管理
├── templates/                  # Jinja2 页面，按功能分组
│   └── quiz/*.html             # 模板名与路由端点对齐
├── static/                     # 静态资源
│   ├── css/                    # 样式文件（文件名用连字符，如 quiz-summary.css）
│   ├── js/
│   └── media/
└── tools/                      # 数据转换工具与测试数据
    ├── convert_txt_csv.py              # 文本转 CSV 格式
    ├── convert_gongtongt_txt_to_csv.py # 共同体题库格式转换
    ├── test_questions.csv              # 含判断题和填空题的测试数据
    ├── test_import.csv
    └── TEST_INSTRUCTIONS.md            # 手工回归测试步骤
```

---

## 三、开发规范

### 编码风格
- **Python**: 严格遵循 PEP 8（4 空格缩进，函数/变量用 snake_case，类名用 CapWords）
- **注释**: 使用中文注释和文档字符串
- **命名**: 蓝图用途一致的模块名（如 `question_bank.py`）；模板名与路由端点对齐

### 命名规范
| 类型 | 规范 | 示例 |
| :--- | :--- | :--- |
| 函数/变量 | snake_case | `init_db()` |
| 类 | CapWords | `UserAuth` |
| 蓝图模块 | 用途命名 | `question_bank.py` |
| CSS 文件 | 连字符命名 | `quiz-summary.css` |
| 模板文件 | 与路由对齐 | `templates/quiz/detail.html` |

### 数据库操作规范
- 所有数据库操作必须通过 `database.py` 模块
- 支持数据库迁移和版本升级
- 使用集中定义的模式常量便于复用

---

## 四、构建、运行与数据管理

### 环境要求
- Python 3.7+
- pip

### 标准启动流程
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用（开发环境）
C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe app.py

# 3. 访问地址
http://localhost:32220
```

### 数据重置与 CSV 重载
当修改题目数据或数据库模式后，执行以下操作：
1. **删除** `database.db` 文件
2. **重启** 应用，触发 `init_db()` 从当前 CSV 重新初始化
3. **确认日志**出现 `Successfully loaded questions...` 提示

**测试环境数据准备**：
- 备份原始 `questions.csv`
- 将 `test_questions.csv` 复制为 `questions.csv`
- 删除 `database.db` 后重启，获得干净测试数据

---

## 五、数据库结构

### 核心数据表
- `questions`: 题目存储
- `users`: 用户信息
- `history`: 答题历史
- `favorites`: 收藏题目
- `exam_sessions`: 考试会话
- `question_banks`: 题库管理

### 题目 CSV 格式
支持字段：题号、题干、答案、难度、题型、类别、选项（A, B, C, D, E）

---

## 六、测试规范

### 测试类型
1. **手工回归测试**：参考 `tools/TEST_INSTRUCTIONS.md`
2. **冒烟测试**：每次修改模式或蓝图后，必测登录、测验模式与统计流程


**破坏性实验前**：无需备份 `database.db`，该数据不重要

---

## 七、配置与安全

### 环境变量
| 变量 | 用途 | 开发环境 | 生产环境 |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Flask 应用密钥 | 默认值 | **必须设置强随机值** |
| `DATABASE` | 数据库路径 | 默认 `database.db` | 建议自定义 |

### 生产环境部署清单
1. **设置强随机** `SECRET_KEY`（通过 `config.py` 导出覆盖）
2. **禁用**调试模式
3. 配置 WSGI 服务器（如 Gunicorn）
4. 设置数据库备份策略
5. **禁止提交** `.env` 文件或真实考题内容
6. 私有 CSV 存放于仓库外，通过 `tools/` 脚本或 load-data 蓝图导入

### 安全机制
- 密码哈希存储
- Session 安全配置
- 输入验证和过滤
- SQL 注入防护

---

## 八、Git 工作流规范

### Commit 消息格式
采用 **Conventional Commit** 风格：
```
feat(题库管理): 添加题目批量导入功能
fix(auth): 修复登录验证逻辑
refactor: 优化 quiz 模块代码结构
```

**规范**：
- 作用域可双语（如 `题库管理` 或 `question_bank`），但必须描述所涉区域
- 保持描述简洁、聚焦

### 合并请求要求
- **保持聚焦**：一个 MR 只解决一个问题
- **说明内容**：用户影响、模式变更、数据迁移步骤
- **提供证据**：测试命令、截图
- **关联 Issue**：关联相关检查项
- **特殊标注**：若需重载 CSV 或重置数据库，**必须明确标注**

---

## 九、工具与脚本

| 工具脚本 | 用途 |
| :--- | :--- |
| `tools/convert_txt_csv.py` | 通用 TXT 转 CSV 格式 |
| `tools/convert_gongtongt_txt_to_csv.py` | 共同体题库专用转换 |
| `test_questions.csv` | 含判断题和填空题的测试数据集 |
| `test_import.csv` | 导入功能测试数据 |

---

## 十、故障排除

### 高频问题
**问题**：数据库报错或数据异常  
**解决**：删除 `database.db` 文件，重启应用

---