from flask import Blueprint

# 创建U本位合约蓝图
um_orders_bp = Blueprint('um_orders', __name__, url_prefix='/um')
 
# 导入视图函数后才能注册路由
from . import orders 

# 确保路由正确注册
from .orders import (
    cancel_um_order,
    place_um_order,
    get_um_trades,
    get_um_orders,
    get_um_order
) 