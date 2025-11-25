#!/usr/bin/env python3
"""
EXAM-MASTER - A Flask-based Online Quiz System

This is the main entry point of the application.
It initializes the Flask app, loads configuration, sets up the database,
and registers the blueprints that handle the actual route logic.

Author: ShayneChen (xinyu-c@outlook.com)
License: MIT
"""

from flask import Flask
from config import Config
from database import init_db

# 导入各个功能蓝图
from blueprints.main import bp as main_bp
from blueprints.auth import bp as auth_bp
from blueprints.quiz import bp as quiz_bp
from blueprints.user import bp as user_bp
from blueprints.load_data import bp as load_data_bp

# 初始化 Flask 应用
app = Flask(__name__)

# 加载配置 (从 config.py 中读取 Config 类)
app.config.from_object(Config)

# 初始化数据库
# 创建必要的表并加载初始 CSV 数据（如果表为空）
# 注意：在应用启动前执行一次即可
init_db()

# 注册蓝图 (Blueprints)
# 我们不设置 url_prefix，以保持与原版 URL 结构的一致性
# 例如: 原来的 /login 现在依然是 /login (虽然内部端点变成了 auth.login)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(user_bp)
app.register_blueprint(load_data_bp)

if __name__ == '__main__':
    # 启动应用
    # host="0.0.0.0" 允许外部访问
    # debug=True 开启调试模式
    app.run(host="0.0.0.0", debug=True, port=32220)