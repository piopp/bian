from flask import Blueprint

# 创建主API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

def register_blueprints(app):
    """注册所有蓝图"""
    # 导入蓝图
    from app.api.auth import auth_bp
    from app.api.subaccounts import subaccounts_bp
    from app.api.settings import settings_bp
    from app.api.trading import trading_bp
    from app.api.market import market_bp
    from app.api.trading_pairs import trading_pairs_bp
    from app.api.statistics import statistics_bp
    from app.api.main_account import main_account_bp
    from app.api.server import server_bp
    from app.api.portfolio import portfolio_bp
    from app.api.margin import margin_bp
    from app.api.account import account_bp
    from app.api.binance import binance_bp
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(subaccounts_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(trading_pairs_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(main_account_bp)
    app.register_blueprint(server_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(margin_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(binance_bp)

    # 创建一个catch-all路由，确保所有请求都被拦截和处理
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return {
            "success": True,
            "message": "Binance Withdraw System API is running.",
            "version": "1.0.0"
        }
    
    return app 