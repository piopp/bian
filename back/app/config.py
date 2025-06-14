import os
import logging
from datetime import timedelta

class Config:
    """应用配置基类"""
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # 日志配置 - 提高级别以减少日志输出
    LOG_LEVEL = logging.WARNING  # 由INFO改为WARNING
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'app.log'
    
    # API日志配置 - 提高级别以减少日志输出
    API_LOG_LEVEL = logging.WARNING  # 由DEBUG改为WARNING
    API_LOG_FILE = 'api_requests.log'
    
    # WebSocket日志配置 - 提高级别以减少日志输出
    WS_LOG_LEVEL = logging.WARNING  # 由DEBUG改为WARNING
    WS_LOG_FILE = 'websocket.log'
    
    # 币安API配置
    # 如果需要使用代理访问币安API，请设置此选项，格式为 'http://host:port' 或 'socks5://host:port'
    BINANCE_PROXY = os.environ.get('BINANCE_PROXY', None)
    
    # 默认API密钥(主账号)
    DEFAULT_API_KEY = os.environ.get('DEFAULT_API_KEY', '')
    DEFAULT_API_SECRET = os.environ.get('DEFAULT_API_SECRET', '')
    
    # 综合日志处理器
    @staticmethod
    def init_app(app):
        # 配置根日志
        logging.basicConfig(
            level=Config.LOG_LEVEL,
            format=Config.LOG_FORMAT,
            filename=Config.LOG_FILE,
            filemode='a'
        )
        
        # 配置API请求日志
        api_logger = logging.getLogger('app.services.binance_client')
        api_handler = logging.FileHandler(Config.API_LOG_FILE)
        api_handler.setLevel(Config.API_LOG_LEVEL)
        api_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        api_handler.setFormatter(api_formatter)
        api_logger.addHandler(api_handler)
        api_logger.propagate = False  # 避免日志重复
        
        # 配置WebSocket日志
        ws_logger = logging.getLogger('order_sync_tasks')
        ws_handler = logging.FileHandler(Config.WS_LOG_FILE)
        ws_handler.setLevel(Config.WS_LOG_LEVEL)
        ws_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ws_handler.setFormatter(ws_formatter)
        ws_logger.addHandler(ws_handler)
        ws_logger.propagate = False  # 避免日志重复
        
        # 配置websocket-client库的日志
        websocket_logger = logging.getLogger('websocket')
        websocket_handler = logging.FileHandler(Config.WS_LOG_FILE)
        websocket_handler.setLevel(Config.WS_LOG_LEVEL)
        websocket_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        websocket_handler.setFormatter(websocket_formatter)
        websocket_logger.addHandler(websocket_handler)
        websocket_logger.propagate = False  # 避免日志重复
        
        # 打印代理设置信息只在ERROR以上级别
        if Config.BINANCE_PROXY:
            app.logger.error(f"使用代理访问币安API: {Config.BINANCE_PROXY}")
        
class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = logging.WARNING  # 由DEBUG改为WARNING
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    LOG_LEVEL = logging.ERROR  # 由WARNING改为ERROR
    
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 