import os
import logging
from flask import Flask
from flask_cors import CORS
from app.models import db
from loguru import logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app(config_class=None):
    """创建Flask应用实例"""
    # 创建Flask应用
    app = Flask(__name__, instance_relative_config=True)
    
    # 加载配置
    if config_class:
        app.config.from_object(config_class)
    else:
        # 从项目根目录导入默认配置
        from config import Config
        app.config.from_object(Config)
    
    # 设置会话安全性配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'binance_manager_secret_key')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # 在开发环境中设为False，生产环境应设为True
    
    # 配置数据目录
    data_dir = os.environ.get('DATA_DIR')
    if not data_dir:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    
    os.makedirs(data_dir, exist_ok=True)
    app.config['DATA_DIR'] = data_dir
    
    # 配置SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    if config_class is None:
        # 如果不是测试，加载实例配置
        app.config.from_pyfile('config.py', silent=True)
    
    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    # 启用CORS，允许所有来源的跨域请求
    CORS(app, resources={r"/*": {
        "origins": "*", 
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }})
    
    # 注册API蓝图
    from app.api import register_blueprints
    register_blueprints(app)
    
    # 定义根路由
    @app.route('/')
    def index():
        from flask import jsonify
        return jsonify({
            "success": True,
            "message": "Binance Subaccount Manager API",
            "version": "1.0.0"
        })
    
    # 注册异常处理
    @app.errorhandler(404)
    def page_not_found(e):
        from flask import jsonify
        return jsonify({"success": False, "error": "API不存在"}), 404

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.exception("未处理的异常: %s", str(e))
        from flask import jsonify
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"}), 500
    
    return app
 