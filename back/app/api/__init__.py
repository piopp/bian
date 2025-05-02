def register_blueprints(app):
    """注册所有API蓝图"""
    from app.api.auth import auth_bp
    from app.api.subaccounts import subaccounts_bp
    from app.api.settings import settings_bp
    from app.api.trading import trading_bp
    from app.api.trading_pairs import trading_pairs_bp
    from app.api.server import server_bp, time_bp
    from app.api.users import users_bp
    from app.api.misc import misc_bp
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(subaccounts_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(trading_pairs_bp)
    app.register_blueprint(server_bp)
    app.register_blueprint(time_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(misc_bp) 