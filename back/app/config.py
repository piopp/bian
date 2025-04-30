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
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'app.log'
    
    # API日志配置
    API_LOG_LEVEL = logging.DEBUG
    API_LOG_FILE = 'api_requests.log'
    
    # WebSocket日志配置
    WS_LOG_LEVEL = logging.DEBUG
    WS_LOG_FILE = 'websocket.log'
    
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
        
class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    LOG_LEVEL = logging.WARNING
    
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 