import os

class Config:
    """基本配置类，所有环境共享的配置"""
    
    # 应用名称
    APP_NAME = 'Binance Subaccount Manager'
    
    # 数据目录
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
    
    # 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'binance_manager_secret_key')
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_HTTPONLY = True
    
    # SQLAlchemy配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 币安API默认设置
    DEFAULT_API_KEY = ''
    DEFAULT_API_SECRET = ''
    
    # 代理设置 - 如果需要使用代理访问币安API，请设置以下变量
    # 示例: {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
    PROXIES = None
    
    # 自动设置代理（如果有环境变量）
    if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
        PROXIES = {}
        if os.environ.get('HTTP_PROXY'):
            PROXIES['http'] = os.environ.get('HTTP_PROXY')
        if os.environ.get('HTTPS_PROXY'):
            PROXIES['https'] = os.environ.get('HTTPS_PROXY')
    
    @classmethod
    def as_dict(cls):
        """将配置类转换为字典"""
        return {key: value for key, value in cls.__dict__.items()
                if not key.startswith('__') and not callable(value)}

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # 开发环境中允许HTTP

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = False
    TESTING = True
    SESSION_COOKIE_SECURE = False  # 测试环境中允许HTTP
    
    # 使用内存数据库进行测试
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # 生产环境强制HTTPS
    
    # 生产环境可以使用环境变量覆盖数据库路径
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(self.DATA_DIR, 'app.db'))

# 默认配置
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig
} 