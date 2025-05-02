#!/usr/bin/env python
"""
初始化数据库脚本
"""
import os
import logging
from flask import Flask
from app.models import db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_db():
    """
    初始化数据库，创建所有表
    """
    # 创建Flask应用
    app = Flask(__name__, instance_relative_config=True)
    
    # 确保data目录存在
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 加载配置
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(data_dir, 'app.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DATA_DIR=data_dir
    )
    
    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # 初始化数据库
    db.init_app(app)
    
    # 在应用上下文中创建所有表
    with app.app_context():
        db.create_all()
        logger.info('数据库表创建成功！')

if __name__ == '__main__':
    init_db() 