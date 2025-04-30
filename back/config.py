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
    SQLALCHEMY_BINDS = {
        'fee_statistics': 'sqlite:///' + os.path.join(DATA_DIR, 'fee_statistics.db')
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 币安API默认设置
    DEFAULT_API_KEY = ''
    DEFAULT_API_SECRET = ''
    
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
    SQLALCHEMY_BINDS = {}  # 测试时不使用绑定

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