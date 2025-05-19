# 子账户模块包初始化文件
from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

# 创建主蓝图
subaccounts_bp = Blueprint('subaccounts', __name__, url_prefix='/api/subaccounts')

logger.info("注册子账号模块蓝图，前缀: /api/subaccounts")

# 导入各个子模块的路由
from .base import *
from .assets import *
from .orders import *
from .api_management import *
from .portfolio_margin import *
from .positions import positions_bp
from .um import um_orders_bp
from .cm import cm_orders_bp

# 打印子蓝图的URL前缀
logger.info(f"positions_bp URL前缀: {positions_bp.url_prefix}")
logger.info(f"um_orders_bp URL前缀: {um_orders_bp.url_prefix}")
logger.info(f"cm_orders_bp URL前缀: {cm_orders_bp.url_prefix}")

# 注册子蓝图
subaccounts_bp.register_blueprint(positions_bp)
subaccounts_bp.register_blueprint(um_orders_bp)
subaccounts_bp.register_blueprint(cm_orders_bp)

logger.info("子账号子蓝图注册完成")

# 所有的路由都已经注册到主蓝图 subaccounts_bp 

__all__ = [
    'subaccounts_bp',
    'api_bp',
    'assets_bp',
    'orders_bp',
    'positions_bp',
    'um_orders_bp',
    'cm_orders_bp',
    'portfolio_margin_bp'
] 