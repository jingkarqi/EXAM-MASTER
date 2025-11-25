# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

EXAM-MASTER 是一个基于 Flask 框架开发的在线考试系统，专为中文考试环境设计。该系统提供了完整的用户认证、题目管理、多种答题模式、历史记录和统计分析功能。

## 开发环境设置

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动应用
```bash
python app.py
```
应用将在 `http://localhost:32220` 启动（可通过 `config.py` 修改端口配置）。

### 数据库初始化
应用启动时会自动：
- 创建 SQLite 数据库 (`database.db`)
- 初始化必要的表结构
- 从 `questions.csv` 加载题目数据（如果表为空）

## 架构概览

### 蓝图架构 (Blueprint Architecture)
项目采用 Flask 蓝图模式组织代码：

- **app.py**: 主应用入口，注册所有蓝图
- **blueprints/auth.py**: 用户认证相关路由（登录、注册、登出）
- **blueprints/main.py**: 主页面和错误处理路由
- **blueprints/quiz.py**: 答题功能路由（随机题、顺序题、考试等）
- **blueprints/user.py**: 用户功能路由（历史、收藏、统计等）

### 数据库架构
- **users**: 用户信息表
- **questions**: 题目数据表（从 CSV 导入）
- **history**: 答题历史记录
- **favorites**: 用户收藏题目
- **exam_sessions**: 考试会话记录

### 模板架构
- **templates/base.html**: 主应用基础模板
- **templates/base_auth.html**: 认证页面专用模板
- 其他功能模板继承自基础模板

## 核心开发任务

### 运行测试
```bash
python test.py
```

**注意**：`test.py` 主要用于检查 CSV 文件格式，不是完整的测试框架。项目目前没有自动化测试套件。

### 测试约定
- 所有功能测试由用户完成，开发人员专注于代码实现
- 开发完成后提供完整的代码修改说明
- 用户负责验证修复效果和功能完整性

### 添加新功能
1. 在相应的蓝图文件中添加路由
2. 如需新表，修改 `database.py` 中的 `init_db()` 函数
3. 添加对应的模板文件到 `templates/` 目录
4. 更新静态资源（如需要）

### 修改题目数据
1. 更新 `questions.csv` 文件
2. 使用 SQLite 工具清空 questions 表，或删除 `database.db` 让系统重建
3. 重启应用自动重新加载数据

## 重要文件说明

### 配置相关
- **config.py**: 应用配置（密钥、Session、文件路径）
- **requirements.txt**: Python 依赖列表

### 核心模块
- **database.py**: 数据库操作和初始化
- **app.py**: 应用主入口和蓝图注册

### 数据文件
- **questions.csv**: 题目数据源文件
- **database.db**: SQLite 数据库文件（自动生成）

### 数据转换工具
- **tools/convert_txt_csv.py**: 将文本格式题目转换为 CSV 格式
- **tools/convert_gongtongt_txt_to_csv.py**: 特定格式的题目转换工具

**使用说明**：
- 将源文本文件放在 `tools/` 目录下
- 运行相应的转换脚本
- 生成的 CSV 文件可用于替换 `questions.csv`

## 开发约定

### 路由命名
- 使用蓝图名称作为路由前缀（如 `auth.login`, `quiz.random`）
- 保持 URL 路径简洁直观

### 认证保护
- 使用 `@login_required` 装饰器保护需要认证的路由
- 认证状态通过 Session 管理

### 数据库操作
- 使用参数化查询防止 SQL 注入
- 数据库连接使用后及时关闭
- 错误处理包含适当的异常捕获

### 前端模板
- 使用 Jinja2 模板继承
- 响应式设计，支持移动端
- CSS 使用 BEM 命名约定

## 常见操作

### 重置用户数据
删除 `database.db` 文件并重启应用

### 更新题目数据
替换 `questions.csv` 文件并重启应用

### 调试模式
应用默认运行在调试模式，修改 `app.py` 中的 `debug=True` 可关闭

### 生产部署
- 设置强 `SECRET_KEY` 环境变量
- 确保应用有写入权限创建数据库
- 考虑使用生产级 WSGI 服务器