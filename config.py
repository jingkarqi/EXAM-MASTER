import os
from datetime import timedelta

class Config:
    """
    Flask Application Configuration
    """
    # 密钥配置：优先从环境变量获取，否则使用默认值
    # 在生产环境中，务必通过环境变量设置强密码
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_this_in_production')
    
    # Session 配置
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 数据库和文件路径配置 (可选，虽然目前 database.py 使用了硬编码，但在 Config 中定义是好习惯)
    DATABASE_FILE = 'database.db'
    CSV_FILE = 'questions.csv'