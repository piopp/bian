import os
import logging
from flask import Flask
from flask_cors import CORS
from app.models import db
from loguru import logger
from flask_jwt_extended import JWTManager

# 配置日志 - 在开发环境使用更详细的日志级别
logging.basicConfig(
    level=logging.DEBUG,  # 从WARNING改为DEBUG以获取更多调试信息
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
    
    # 配置JWT扩展
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'binance_manager_jwt_secret')
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 24*60*60  # 24小时
    
    # 初始化JWT
    jwt = JWTManager(app)
    
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
    
    # 在开发环境中启用调试工具栏
    if app.config.get('ENV') == 'development' or app.config.get('DEBUG'):
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
            app.config['DEBUG_TB_PROFILER_ENABLED'] = True
            app.config['DEBUG_TB_TEMPLATE_EDITOR_ENABLED'] = True
            toolbar = DebugToolbarExtension(app)
            logger.info("已启用Flask调试工具栏")
        except ImportError:
            logger.warning("未安装flask-debugtoolbar，跳过调试工具栏初始化")
    
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
    
    # 输出启动信息
    logger.info(f"应用已启动，环境: {os.environ.get('FLASK_ENV', '未设置')}")
    logger.debug(f"调试模式: {app.debug}")
    
    return app
 