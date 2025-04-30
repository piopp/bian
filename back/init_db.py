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
        SQLALCHEMY_BINDS={
            'fee_statistics': 'sqlite:///' + os.path.join(data_dir, 'fee_statistics.db')
        },
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
    
    # 创建数据库表
    with app.app_context():
        logger.info("开始初始化数据库...")
        
        try:
            # 创建所有表
            db.create_all()
            logger.info("已创建所有数据库表")
            
            # 初始化基本设置（如果需要）
            from app.models import Setting
            
            # 检查是否存在基本设置
            if Setting.query.count() == 0:
                # 初始化一些基本设置
                settings = [
                    Setting(key="app_name", value="币安子账户管理系统", description="应用名称"),
                    Setting(key="app_version", value="1.0.0", description="应用版本")
                ]
                db.session.add_all(settings)
                db.session.commit()
                logger.info("已初始化基本设置")
            
            return True
        except Exception as e:
            logger.error(f"创建表出错: {str(e)}")
            return False

if __name__ == '__main__':
    success = init_db()
    if success:
        print("数据库初始化成功!")
    else:
        print("数据库初始化失败，请检查日志") 