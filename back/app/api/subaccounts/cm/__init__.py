from flask import Blueprint

# 创建币本位合约蓝图
cm_orders_bp = Blueprint('cm_orders', __name__, url_prefix='/cm')
 
# 导入视图函数后才能注册路由
from . import orders 

# 确保路由正确注册
from .orders import (
    cancel_cm_order,
    place_cm_order,
    get_cm_trades,
    get_cm_orders,
    get_cm_order
) 