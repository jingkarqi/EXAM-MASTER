# Repository Guidelines

## Project Structure & Module Organization
Source code lives at the repo root: `app.py` bootstraps the Flask app and registers blueprints from `blueprints/`. Auth, quiz flow, user history, and landing pages live in `blueprints/auth.py`, `quiz.py`, `user.py`, and `main.py` respectively. Shared HTML resides in `templates/` (`base.html`, `base_auth.html`, plus feature templates), while static assets stay under `static/` for CSS and JS. Data helpers and CSV converters sit in `tools/`, and SQLite artifacts (`database.db`, `questions.csv`) live beside the app for easy reset.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` - install Flask, SQL helpers, and CSV utilities.
- `C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe app.py` - start the dev server (defaults to http://localhost:32220; adjust in `config.py`).
- `C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe test.py` - sanity-check CSV format before importing.
Delete `database.db` to trigger a clean migration/import on the next startup.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indents and explicit imports. Keep blueprint modules focused per domain and expose routes via `@blueprint.route` with snake_case function names that mirror their endpoint (`quiz_random`, `user_history`). Reuse template inheritance, keep Jinja blocks minimal, and stick to BEM selectors in `static/` styles (`.quiz-card__header`). Prefer parameterized SQL in `database.py` and close connections via context managers.

## Testing Guidelines
`C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe test.py` validates CSV structure; extend it when adding columns. For functional checks, run `C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe app.py` and walk through auth -> quiz -> history flows with sample accounts. When touching loaders in `blueprints/load_data.py` or schema changes in `database.py`, add temporary assertions in `tools/` scripts and remove once verified.

## Commit & Pull Request Guidelines
Match the existing history (`fix: ...`, `refactor: ...`, short imperative subjects plus optional Chinese descriptions). Squash noisy WIP commits before raising a PR. Each PR should describe scope, impacted blueprints/templates, test evidence (`C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe test.py`, manual flows), and note if a data reset is required. Attach screenshots for UI-facing tweaks and reference related issues or TODOs.

## Security & Configuration Tips
Store secrets (for example `SECRET_KEY`) via environment variables before deploying. Never commit real exam data; run converters in `tools/` to sanitize inputs. Validate user input at the form and SQL layer, and ensure authenticated routes retain `@login_required`.

# EXAM-MASTER - 在线考试系统

## 项目概述

EXAM-MASTER 是一个基于 Flask 框架开发的在线考试系统，专为中文考试环境设计。该系统提供了完整的用户认证、题目管理、多种答题模式、历史记录和统计分析功能。

### 技术栈
- **后端框架**: Flask 2.3.3
- **数据库**: SQLite3
- **前端**: HTML/CSS/JavaScript + Jinja2 模板引擎
- **认证**: Flask-Session + Werkzeug 安全哈希

### 主要功能
- 用户注册/登录/登出
- 随机答题、顺序答题、定时考试、模拟考试等多种模式
- 题目搜索、分类浏览、筛选功能
- 答题历史记录、错题集、收藏功能
- 个人统计分析（正确率、难度分布、类别统计等）

## 项目结构

```
EXAM-MASTER/
├── app.py                 # 主应用入口
├── config.py              # 应用配置
├── database.py            # 数据库操作模块
├── requirements.txt       # Python 依赖
├── blueprints/            # 蓝图模块
│   ├── auth.py           # 认证相关路由
│   ├── main.py           # 主页面路由
│   ├── quiz.py           # 答题功能路由
│   ├── user.py           # 用户功能路由
│   └── load_data.py      # 数据导入功能
├── templates/            # HTML 模板
├── static/               # 静态资源 (CSS/JS)
└── tools/                # 数据转换工具
```

## 构建和运行

### 环境准备
```bash
# 安装依赖
pip install -r requirements.txt
```

### 启动应用
```bash
# 运行主应用
C:\Users\jing\AppData\Local\Programs\Python\Python313\python.exe app.py
```

应用将在 `http://localhost:32220` 启动（可通过 `config.py` 修改端口配置）。

### 数据库初始化
应用启动时会自动：
1. 创建 SQLite 数据库 (`database.db`)
2. 初始化必要的表结构
3. 从 `questions.csv` 加载题目数据（如果表为空）

## 开发约定

### 数据库设计
- **users**: 用户信息表
- **questions**: 题目数据表（从 CSV 导入）
- **history**: 答题历史记录
- **favorites**: 用户收藏题目
- **exam_sessions**: 考试会话记录
- **question_banks**: 题库管理表

### 题目数据格式
题目数据存储在 `questions.csv` 文件中，格式如下：
- 题号、题干、A选项、B选项、C选项、D选项、E选项、答案、难度、题型
- 支持单选题、多选题、判断题、填空题
- 答案字段存储正确选项字母（如 "A" 或 "ABC"）

### 路由结构
应用使用 Flask 蓝图组织路由：
- `/auth/*`: 认证相关路由（登录、注册、登出）
- `/quiz/*`: 答题功能路由（随机题、浏览、搜索、考试等）
- `/user/*`: 用户功能路由（历史、收藏、统计等）
- `/load_data/*`: 数据导入功能路由
- `/`: 主页面和错误处理

### 认证机制
- 使用 Flask Session 管理用户登录状态
- 密码使用 Werkzeug 的安全哈希函数
- 登录装饰器 `@login_required` 保护需要认证的路由

### 安全考虑
- 所有用户输入都经过适当验证
- 密码哈希存储，不存储明文密码
- Session 配置了安全的 HttpOnly Cookie
- 防止 SQL 注入（使用参数化查询）

## 主要功能模块

### 1. 认证模块 (auth.py)
- 用户注册：用户名唯一性检查、密码强度验证
- 用户登录：凭据验证、Session 管理
- 用户登出：Session 清理

### 2. 答题模块 (quiz.py)
- **随机模式**: 从未答题目中随机选择
- **顺序模式**: 按题号顺序答题，记录进度
- **定时模式**: 限时答题，自动提交
- **模拟考试**: 无时间限制的正式考试模式
- **搜索功能**: 按题干内容搜索题目
- **浏览功能**: 分页浏览所有题目，支持筛选
- **筛选功能**: 按类别和难度筛选题目

### 3. 用户功能模块 (user.py)
- **历史记录**: 查看所有答题历史
- **错题集**: 查看和管理错题
- **收藏功能**: 收藏题目并添加标签
- **统计分析**: 
  - 总体正确率
  - 按难度/类别的正确率分布
  - 最常错题排行
  - 最近考试记录

### 4. 主页面模块 (main.py)
- 首页显示和导航
- APK 文件下载（Android 客户端）

### 5. 数据导入模块 (load_data.py)
- **文件上传**: 支持 CSV 和 TXT 格式
- **数据验证**: 题目格式、答案有效性检查
- **批量导入**: 预览和确认导入功能

## 开发和扩展

### 添加新功能
1. 在相应的蓝图文件中添加路由
2. 如需新表，修改 `database.py` 中的 `init_db()` 函数
3. 添加对应的模板文件到 `templates/` 目录
4. 更新静态资源（如需要）

### 修改题目数据
1. 更新 `questions.csv` 文件
2. 使用 SQLite 工具清空 questions 表，或删除 `database.db` 让系统重建
3. 重启应用自动重新加载数据

### 自定义配置
在 `config.py` 中修改：
- 数据库文件路径
- CSV 文件路径
- Session 配置
- 安全密钥

## 部署注意事项

1. **生产环境**：务必设置强 `SECRET_KEY` 环境变量
2. **数据库**：确保应用有写入权限创建 `database.db`
3. **静态文件**：确保 `static/` 目录可被 Web 服务器访问
4. **日志**：考虑添加生产环境日志配置

## 前端界面分析

### 模板系统架构
项目使用 Jinja2 模板引擎，采用继承式设计：

#### 基础模板
- **base.html**: 主应用基础模板，包含导航栏、页脚和全局JavaScript
- **base_auth.html**: 认证页面专用模板，简化布局，居中显示

#### 核心功能模板
- **index.html**: 首页，展示所有功能入口和Android应用推广
- **question.html**: 题目展示和答题界面，支持单选/多选题
- **browse.html**: 题目浏览页面，支持分页和筛选
- **search.html**: 题目搜索页面
- **filter.html**: 高级筛选页面
- **exam.html**: 模拟考试界面
- **timed_mode.html**: 定时答题模式
- **history.html**: 答题历史记录
- **wrong.html**: 错题集页面
- **favorites.html**: 收藏题目管理
- **statistics.html**: 个人统计分析
- **login.html/register.html**: 用户认证页面
- **import.html/import_preview.html**: 数据导入功能页面
- **error.html**: 错误页面

### 前端技术特点

#### 响应式设计
- 移动优先设计理念，支持手机、平板和桌面设备
- 使用CSS Grid和Flexbox实现灵活布局
- 移动端专属导航菜单，支持滑动手势操作
- 表格在移动端转换为卡片式布局

#### 用户体验优化
- 渐进式Web应用(PWA)特性
- 智能Flash消息系统，自动消失提示
- 题目进度条显示学习进度
- 答题结果即时反馈，正确/错误状态视觉区分
- 收藏功能一键操作

#### 交互设计
- 丰富的过渡动画和微交互
- 题目选项悬停效果和选中状态
- 移动端滑动手势支持（左滑开菜单，右滑关菜单）
- 表格横向滚动提示和指示器
- 按钮点击反馈效果

#### 视觉设计
- 现代化扁平设计风格
- 统一的色彩系统和设计语言
- Font Awesome图标库提供丰富图标
- Google Fonts字体支持中英文优化显示
- 卡片式布局，信息层次清晰

#### 性能优化
- CSS变量实现主题统一管理
- 延迟加载和按需加载JavaScript
- 图片和资源优化
- 最小化重排和重绘

### 特色功能界面

#### 首页功能展示
- Hero区域突出核心功能按钮
- Android应用推广区域，动画效果吸引注意
- 功能卡片网格布局，清晰展示各项功能
- 高级学习模式选择器，可视化配置选项

#### 题目答题界面
- 顶部进度条显示学习进度
- 题目标签系统（类型、难度、类别）
- 选项交互设计，支持单选/多选切换
- 答题结果即时反馈，正确答案高亮显示
- 收藏按钮集成在题目页面

#### 统计分析页面
- 多维度数据可视化
- 表格响应式设计，移动端友好
- 数据卡片式展示，信息层次清晰

### CSS架构
- 使用CSS变量实现主题管理
- BEM命名约定提高代码可维护性
- 组件化样式设计，便于复用
- 移动优先的响应式媒体查询
- 平滑过渡动画提升用户体验
