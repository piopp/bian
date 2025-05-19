import time
import logging
from flask import request, jsonify
from . import subaccounts_bp
from app.services.binance_client import get_client_by_email
from flask import current_app
from app.utils.logger import log_info, log_error, log_exception, truncate_message

logger = logging.getLogger(__name__)

@subaccounts_bp.route('/cancel-order', methods=['POST'])
def cancel_order():
    """
    取消子账号的合约订单 - 根据合约类型转发到对应接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderId": 订单ID,
        "contractType": 合约类型 "UM"(U本位)或"CM"(币本位)
    }
    """
    data = request.json
    contract_type = data.get('contractType', 'UM')
    
    if contract_type == 'UM':
        from .um.orders import cancel_um_order
        return cancel_um_order()
    elif contract_type == 'CM':
        from .cm.orders import cancel_cm_order
        return cancel_cm_order()
    else:
        log_error(f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)")
        return jsonify({
            "success": False,
            "error": f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)"
                }), 400


@subaccounts_bp.route('/place-order', methods=['POST'])
def place_order():
    """
    为子账号下合约订单 - 根据合约类型转发到对应接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "side": "BUY 或 SELL",
        "type": "订单类型，如 LIMIT, MARKET",
        "quantity": "数量",
        "price": "价格(LIMIT订单必须)",
        "timeInForce": "GTC, IOC, FOK (LIMIT订单需要)",
        "positionSide": "持仓方向(默认BOTH单向持仓，双向持仓使用LONG/SHORT)",
        "newClientOrderId": "客户端订单ID(可选)",
        "contractType": 合约类型 "UM"(U本位)或"CM"(币本位)
    }
    
    注意：本系统统一使用双向持仓模式，positionSide参数说明：
    - BOTH: 单一持仓方向（默认）
    - LONG: 多头（双向持仓下）
    - SHORT: 空头（双向持仓下）
    """
    data = request.json
    contract_type = data.get('contractType', 'UM')
    
    if contract_type == 'UM':
        from .um.orders import place_um_order
        return place_um_order()
    elif contract_type == 'CM':
        from .cm.orders import place_cm_order
        return place_cm_order()
    else:
        log_error(f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)")
        return jsonify({
            "success": False,
            "error": f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)"
        }), 400


@subaccounts_bp.route('/futures-trades', methods=['POST'])
def get_futures_trades():
    """
    获取子账号的合约成交历史 - 根据合约类型转发到对应接口
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "symbol": "交易对",
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "limit": 返回数量(可选, 默认500),
        "contractType": 合约类型 "UM"(U本位)或"CM"(币本位)
    }
    """
    data = request.json
    contract_type = data.get('contractType', 'UM')
    
    if contract_type == 'UM':
        from .um.orders import get_um_trades
        return get_um_trades()
    elif contract_type == 'CM':
        from .cm.orders import get_cm_trades
        return get_cm_trades()
    else:
        log_error(f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)")
        return jsonify({
            "success": False,
            "error": f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)"
        }), 400


@subaccounts_bp.route('/futures-orders', methods=['POST'])
def get_futures_orders():
    """
    获取子账号的合约订单信息 - 根据合约类型转发到对应接口
    
    请求体:
    {
        "email": "子账号邮箱" (单个子账号时使用),
        "emails": ["子账号邮箱1", "子账号邮箱2", ...] (多个子账号时使用),
        "symbol": "交易对(可选)",
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "limit": 返回数量(可选, 默认500),
        "orderId": 订单ID(可选),
        "contractType": 合约类型 "UM"(U本位)或"CM"(币本位)
    }
    """
    data = request.json
    contract_type = data.get('contractType', 'UM')
    
    if contract_type == 'UM':
        from .um.orders import get_um_orders
        return get_um_orders()
    elif contract_type == 'CM':
        from .cm.orders import get_cm_orders
        return get_cm_orders()
    else:
        log_error(f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)")
        return jsonify({
            "success": False,
            "error": f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)"
            }), 400

@subaccounts_bp.route('/futures-order', methods=['POST'])
def get_futures_order():
    """
    获取子账号的当前交易对合约挂单信息 - 根据合约类型转发到对应接口
    
    请求体:
    {
        "email": "子账号邮箱" (单个子账号时使用),
        "emails": ["子账号邮箱1", "子账号邮箱2", ...] (多个子账号时使用),
        "symbol": "交易对(必须)",
        "limit": 返回数量(可选, 默认50),
        "contractType": 合约类型 "UM"(U本位)或"CM"(币本位)
    }
    """
    data = request.json
    contract_type = data.get('contractType', 'UM')
    
    if contract_type == 'UM':
        from .um.orders import get_um_order
        return get_um_order()
    elif contract_type == 'CM':
        from .cm.orders import get_cm_order
        return get_cm_order()
    else:
        log_error(f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)")
        return jsonify({
            "success": False,
            "error": f"不支持的合约类型: {contract_type}, 仅支持UM(U本位)或CM(币本位)"
            }), 400
            
# 保留原有的um-*路由函数作为向后兼容，但现在它们应该使用对应UM模块中的函数
@subaccounts_bp.route('/um-cancel-order', methods=['POST'])
def um_cancel_order():
    """兼容旧版接口 - 转发到UM模块"""
    from .um.orders import cancel_um_order
    return cancel_um_order()

@subaccounts_bp.route('/um-place-order', methods=['POST'])
def um_place_order():
    """兼容旧版接口 - 转发到UM模块"""
    from .um.orders import place_um_order
    return place_um_order()

@subaccounts_bp.route('/um-futures-trades', methods=['POST'])
def um_futures_trades():
    """兼容旧版接口 - 转发到UM模块"""
    from .um.orders import get_um_trades
    return get_um_trades()

@subaccounts_bp.route('/um-futures-orders', methods=['POST'])
def um_futures_orders():
    """兼容旧版接口 - 转发到UM模块"""
    from .um.orders import get_um_orders
    return get_um_orders()

# 添加CM-*路由函数作为向后兼容
@subaccounts_bp.route('/cm-cancel-order', methods=['POST'])
def cm_cancel_order():
    """兼容旧版接口 - 转发到CM模块"""
    from .cm.orders import cancel_cm_order
    return cancel_cm_order()

@subaccounts_bp.route('/cm-place-order', methods=['POST'])
def cm_place_order():
    """兼容旧版接口 - 转发到CM模块"""
    from .cm.orders import place_cm_order
    return place_cm_order()

@subaccounts_bp.route('/cm-futures-trades', methods=['POST'])
def cm_futures_trades():
    """兼容旧版接口 - 转发到CM模块"""
    from .cm.orders import get_cm_trades
    return get_cm_trades()

@subaccounts_bp.route('/cm-futures-orders', methods=['POST'])
def cm_futures_orders():
    """兼容旧版接口 - 转发到CM模块"""
    from .cm.orders import get_cm_orders
    return get_cm_orders()