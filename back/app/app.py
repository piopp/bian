from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from app.config import config

# 初始化扩展
db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 初始化应用日志
    config[config_name].init_app(app)
    
    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    
    # 导入蓝图
    from app.api.users import users_bp
    from app.api.system import system_bp
    from app.api.subaccounts import subaccounts_bp
    from app.api.positions import positions_bp
    from app.api.trading_pairs import trading_pairs_bp
    from app.api.trades import trades_bp
    from app.api.orders import orders_bp
    from app.api.settings import settings_bp
    
    # 注册蓝图
    app.register_blueprint(users_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(subaccounts_bp)
    app.register_blueprint(positions_bp)
    app.register_blueprint(trading_pairs_bp)
    app.register_blueprint(trades_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(settings_bp)
    
    # 初始化订单同步
    with app.app_context():
        from app.tasks.order_sync import init_scheduler
        init_scheduler(app)
    
    return app

app = create_app() 