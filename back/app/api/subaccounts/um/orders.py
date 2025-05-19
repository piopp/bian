import time
import logging
from flask import request, jsonify
from .. import subaccounts_bp
from . import um_orders_bp  # 导入正确的蓝图
from app.services.binance_client import get_client_by_email
from flask import current_app
from flask import Blueprint
from app.utils.auth import token_required
from app.utils.logger import log_info, log_error, log_exception, truncate_message

logger = logging.getLogger(__name__)

@um_orders_bp.route('/cancel-order', methods=['POST'])
def cancel_um_order():
    """
    取消子账号的U本位合约订单 - 使用PAPI接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderId": 订单ID
    }
    """
    try:
        data = request.json
        email = data.get('email')
        symbol = data.get('symbol')
        order_id = data.get('orderId')
        
        # 验证必要参数
        if not email:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱"
            }), 400
            
        if not symbol:
            return jsonify({
                "success": False,
                "error": "请提供交易对"
            }), 400
            
        if not order_id:
            return jsonify({
                "success": False,
                "error": "请提供订单ID"
            }), 400
            
        # 获取子账号的API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        # 构建API请求参数
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'recvWindow': 10000,
            'timestamp': int(time.time() * 1000)
        }
            
        # 使用U本位合约取消订单API - PAPI
        endpoint = "/papi/v1/um/order"
        log_info(f"使用U本位合约取消订单API: {endpoint}, 参数: {params}")
        
        response = client._send_request('DELETE', endpoint, signed=True, params=params)
        
        if response.get('success'):
            return jsonify({
                "success": True,
                "data": response.get('data'),
                "message": "U本位合约订单取消成功"
            })
        else:
            error_msg = truncate_message(response.get('error', '取消U本位合约订单失败'))
            log_error(f"取消子账号 {email} U本位合约订单失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"取消U本位合约订单失败: {error_msg}"
            }), 400
            
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"取消U本位合约订单异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"取消U本位合约订单异常: {error_msg}"
        }), 500


@um_orders_bp.route('/place-order', methods=['POST'])
def place_um_order():
    """
    为子账号在U本位合约下单 - 使用PAPI接口
    
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
        "newClientOrderId": "客户端订单ID(可选)"
    }
    
    注意：本系统统一使用双向持仓模式，positionSide参数说明：
    - BOTH: 单一持仓方向（默认）
    - LONG: 多头（双向持仓下）
    - SHORT: 空头（双向持仓下）
    """
    try:
        data = request.json
        email = data.get('email')
        symbol = data.get('symbol')
        side = data.get('side')
        order_type = data.get('type')
        quantity = data.get('quantity')
        
        # 验证必要参数
        if not email:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱"
            }), 400
            
        if not symbol:
            return jsonify({
                "success": False,
                "error": "请提供交易对"
            }), 400
            
        if not side or side not in ['BUY', 'SELL']:
            return jsonify({
                "success": False,
                "error": "请提供有效的交易方向 (BUY 或 SELL)"
            }), 400
            
        if not order_type:
            return jsonify({
                "success": False,
                "error": "请提供订单类型"
            }), 400
            
        if not quantity:
            return jsonify({
                "success": False,
                "error": "请提供交易数量"
            }), 400
            
        # 对于LIMIT订单，验证价格和timeInForce
        if order_type == 'LIMIT':
            price = data.get('price')
            time_in_force = data.get('timeInForce')
            
            if not price:
                return jsonify({
                    "success": False,
                    "error": "限价订单(LIMIT)必须提供价格"
                }), 400
                
            if not time_in_force or time_in_force not in ['GTC', 'IOC', 'FOK']:
                return jsonify({
                    "success": False,
                    "error": "限价订单(LIMIT)必须提供有效的timeInForce参数 (GTC, IOC, 或 FOK)"
                }), 400
        
        # 获取子账号的API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
            
        # 查询用户的持仓模式设置
        try:
            position_mode_params = {
                'timestamp': int(time.time() * 1000)
            }
            position_mode_response = client._send_request(
                'GET', 
                '/papi/v1/um/positionSide/dual', 
                signed=True,
                params=position_mode_params
            )
            
            # 根据用户的持仓模式设置正确的positionSide
            dual_side_position = False
            if position_mode_response.get('success'):
                dual_side_position = position_mode_response.get('data', {}).get('dualSidePosition', False)
                log_info(f"获取账户持仓模式成功: 双向持仓={dual_side_position}")
            else:
                log_error(f"获取账户持仓模式失败: {position_mode_response.get('error')}")
        except Exception as e:
            log_error(f"查询持仓模式异常: {str(e)}")
            # 如果查询失败，继续使用用户指定的持仓方向
            dual_side_position = False
        
        # 构建API请求参数 - 使用U本位合约(UM)接口
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'recvWindow': 10000,
            'timestamp': int(time.time() * 1000)
        }
        
        # 添加其他参数
        if order_type == 'LIMIT':
            params['price'] = data.get('price')
            params['timeInForce'] = data.get('timeInForce')
        
        # 根据持仓模式和用户设置确定positionSide
        if data.get('positionSide'):
            # 用户指定了positionSide
            requested_position_side = data.get('positionSide')
            
            # 检查持仓模式与请求的positionSide是否匹配
            if dual_side_position:
                # 双向持仓模式下，只能使用LONG或SHORT
                if requested_position_side == 'BOTH':
                    # 自动调整为适合的持仓方向
                    params['positionSide'] = 'LONG' if side == 'BUY' else 'SHORT'
                    log_info(f"双向持仓模式下自动调整持仓方向: 从BOTH到{params['positionSide']}")
                else:
                    params['positionSide'] = requested_position_side
            else:
                # 单向持仓模式下，只能使用BOTH
                if requested_position_side != 'BOTH':
                    # 自动调整为BOTH
                    params['positionSide'] = 'BOTH'
                    log_info(f"单向持仓模式下自动调整持仓方向: 从{requested_position_side}到BOTH")
                else:
                    params['positionSide'] = 'BOTH'
        else:
            # 用户未指定positionSide，根据持仓模式选择默认值
            if dual_side_position:
                # 双向持仓模式下，默认为LONG(买入)或SHORT(卖出)
                params['positionSide'] = 'LONG' if side == 'BUY' else 'SHORT'
                log_info(f"双向持仓模式下使用默认持仓方向: {params['positionSide']}")
            else:
                # 单向持仓模式下，只能用BOTH
                params['positionSide'] = 'BOTH'
                log_info(f"单向持仓模式下使用默认持仓方向: BOTH")
        
        # 客户端订单ID
        if data.get('newClientOrderId'):
            params['newClientOrderId'] = data.get('newClientOrderId')
            
        # 使用U本位合约下单API - PAPI
        endpoint = "/papi/v1/um/order"
        log_info(f"使用U本位合约下单API: {endpoint}, 参数: {params}")
        
        response = client._send_request('POST', endpoint, signed=True, params=params)
        
        if response.get('success'):
            return jsonify({
                "success": True,
                "data": response.get('data'),
                "message": "U本位合约下单成功"
            })
        else:
            error_msg = truncate_message(response.get('error', 'U本位合约下单失败'))
            log_error(f"子账号 {email} U本位合约下单失败: {error_msg}")
            
            # 如果是持仓模式不匹配的错误，提供更详细的错误信息
            if "position side does not match" in error_msg:
                return jsonify({
                    "success": False,
                    "error": f"U本位合约下单失败: 持仓方向({params.get('positionSide')})与账户设置({('双向持仓' if dual_side_position else '单向持仓')})不匹配"
                }), 400
            
            return jsonify({
                "success": False,
                "error": f"U本位合约下单失败: {error_msg}"
            }), 400
            
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"U本位合约下单异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"U本位合约下单异常: {error_msg}"
        }), 500


@um_orders_bp.route('/trades', methods=['POST'])
def get_um_trades():
    """
    获取子账号的U本位合约成交历史 - 使用PAPI接口
    
    请求体:
    {
        "email": "子账号邮箱" (单个子账号时使用),
        "emails": ["子账号邮箱1", "子账号邮箱2", ...] (多个子账号时使用),
        "symbol": "交易对",
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "limit": 返回数量(可选, 默认500)
    }
    """
    try:
        data = request.json
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        limit = data.get('limit', 500)
        
        # 验证必要参数
        if not emails or not isinstance(emails, list):
            return jsonify({
                "success": False,
                "error": "请提供至少一个子账号邮箱"
            }), 400
            
        if not symbol:
            return jsonify({
                "success": False,
                "error": "请提供交易对"
            }), 400
        
        # 如果没有提供end_time，使用当前时间
        if not end_time:
            end_time = int(time.time() * 1000)  # 当前时间的毫秒时间戳
        
        results = []
        
        # 对每个子账号分别获取交易历史
        for email in emails:
            try:
                # 获取子账号的API客户端
                client = get_client_by_email(email)
                
                if not client:
                    results.append({
                        "email": email,
                        "success": False,
                        "error": "子账号API未配置或不可用"
                    })
                    continue
                
                # 构建API请求参数 - 使用UM账户成交历史接口
                params = {
                    'symbol': symbol,
                    'recvWindow': 60000,  # 增加接收窗口时间
                    'timestamp': int(time.time() * 1000)
                }
                
                # 添加其他可选参数
                if start_time:
                    params['startTime'] = int(start_time)
                if end_time:
                    params['endTime'] = int(end_time)
                if limit:
                    params['limit'] = int(limit)
                
                # 使用UM账户成交历史接口 - PAPI
                endpoint = "/papi/v1/um/userTrades"
                log_info(f"使用UM合约接口查询成交历史: {endpoint}, 参数: {params}")
                
                response = client._send_request('GET', endpoint, signed=True, params=params)
                
                if not response.get('success'):
                    error_msg = truncate_message(response.get('error', '获取UM账户成交历史失败'))
                    log_error(f"获取UM账户成交历史失败: {error_msg}")
                    
                    results.append({
                        "email": email,
                        "success": False,
                        "error": f"获取交易历史失败: {error_msg}"
                    })
                    continue
                
                trades = response.get('data', [])
                log_info(f"成功获取UM/U本位账户成交历史，条数: {len(trades)}")
                
                # 格式化成交记录数据
                formatted_trades = []
                for trade in trades:
                    # 格式化方向
                    side = '买入' if trade.get('buyer') else '卖出'
                    
                    formatted_trade = {
                        "id": trade.get("id"),
                        "symbol": trade.get("symbol"),
                        "price": trade.get("price"),
                        "qty": trade.get("qty"),
                        "quoteQty": trade.get("quoteQty"),
                        "commission": trade.get("commission"),
                        "commissionAsset": trade.get("commissionAsset"),
                        "time": trade.get("time"),
                        "side": side,
                        "positionSide": trade.get("positionSide"),
                        "buyer": trade.get("buyer"),
                        "maker": trade.get("maker"),
                        "realizedPnl": trade.get("realizedPnl", "0")
                    }
                    formatted_trades.append(formatted_trade)
                
                # 添加结果
                results.append({
                    "email": email,
                    "success": True,
                    "api_endpoint": response.get('endpoint', endpoint),
                    "trades": formatted_trades
                })
                
            except Exception as e:
                error_msg = truncate_message(str(e))
                log_exception(f"获取子账号 {email} 的UM账户成交历史异常: {error_msg}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": f"获取UM账户成交历史异常: {error_msg}"
                })
        
        return jsonify({
            "success": True,
            "data": results
        })
        
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"获取UM账户成交历史异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取UM账户成交历史异常: {error_msg}"
        }), 500


@um_orders_bp.route('/orders', methods=['POST'])
def get_um_orders():
    """
    获取子账号的U本位合约订单列表
    
    请求体:
    {
        "email": "子账号邮箱" (单个子账号时使用),
        "emails": ["子账号邮箱1", "子账号邮箱2", ...] (多个子账号时使用),
        "symbol": "交易对(可选)",
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "limit": 返回数量(可选, 默认500),
        "orderId": 订单ID(可选)
    }
    """
    try:
        data = request.json
        email = data.get('email')
        emails = data.get('emails', [])
        
        # 兼容单个邮箱和多个邮箱的情况
        if email and not emails:
            emails = [email]
        
        # 验证必要参数
        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱(email)或子账号邮箱数组(emails)"
            }), 400
            
        # 提取查询参数
        symbol = data.get('symbol')
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        limit = data.get('limit', 500)
        order_id = data.get('orderId')
        
        # 如果没有提供end_time，使用当前时间
        if not end_time:
            end_time = int(time.time() * 1000)  # 当前时间的毫秒时间戳
        
        # 处理多个子账号请求
        results = []
        
        # 对每个子账号分别获取订单
        for email in emails:
            try:
                # 获取子账号的API客户端
                client = get_client_by_email(email)
                
                if not client:
                    results.append({
                        "email": email,
                        "success": False,
                        "error": "子账号API未配置或不可用"
                    })
                    continue
                
                # 构建API请求参数 - 使用U本位合约(UM)接口
                params = {
                    'recvWindow': 10000,
                    'timestamp': int(time.time() * 1000)
                }
                
                if symbol:
                    params['symbol'] = symbol
                if start_time:
                    params['startTime'] = start_time
                if end_time:
                    params['endTime'] = end_time
                if limit:
                    params['limit'] = limit
                if order_id:
                    params['orderId'] = order_id
                
                # 获取未平仓订单 - 使用U本位合约API - PAPI
                log_info(f"获取U本位合约未平仓订单 (PAPI接口)")
                open_orders_endpoint = "/papi/v1/um/openOrders"
                
                # 确保请求参数中包含合约标识
                open_params = params.copy()
                # 添加合约类型参数(虽然路径已经包含/um/，但在记录日志时有用)
                open_params['contractType'] = 'UM'
                
                open_orders_response = client._send_request('GET', open_orders_endpoint, signed=True, params=open_params)
                
                # 获取历史订单 - 如果指定了symbol
                history_orders_response = None
                if symbol:
                    log_info(f"获取U本位合约历史订单 (PAPI接口)")
                    history_orders_endpoint = "/papi/v1/um/allOrders"
                    
                    # 确保请求参数中包含合约标识
                    history_params = params.copy()
                    # 添加合约类型参数(虽然路径已经包含/um/，但在记录日志时有用)
                    history_params['contractType'] = 'UM'
                    
                    history_orders_response = client._send_request('GET', history_orders_endpoint, signed=True, params=history_params)
                
                # 合并未平仓订单和历史订单
                all_orders = []
                
                # 处理未平仓订单
                if open_orders_response and open_orders_response.get('success'):
                    open_orders = open_orders_response.get('data', [])
                    if not isinstance(open_orders, list):
                        open_orders = [open_orders]
                    
                    for order in open_orders:
                        all_orders.append(order)
                
                # 处理历史订单
                if history_orders_response and history_orders_response.get('success'):
                    history_orders = history_orders_response.get('data', [])
                    if not isinstance(history_orders, list):
                        history_orders = [history_orders]
                        
                    for order in history_orders:
                        # 检查是否已经在未平仓订单中
                        if not any(o.get('orderId') == order.get('orderId') for o in all_orders):
                            all_orders.append(order)
                
                # 格式化订单数据
                formatted_orders = []
                for order in all_orders:
                    formatted_order = {
                        "orderId": order.get("orderId"),
                        "symbol": order.get("symbol"),
                        "status": order.get("status"),
                        "type": order.get("type"),
                        "side": order.get("side"),
                        "price": order.get("price"),
                        "origQty": order.get("origQty"),
                        "executedQty": order.get("executedQty"),
                        "reduceOnly": order.get("reduceOnly", False),
                        "positionSide": order.get("positionSide", "BOTH"),
                        "time": order.get("time") or order.get("updateTime"),
                        "updateTime": order.get("updateTime") or order.get("time")
                    }
                    formatted_orders.append(formatted_order)
                
                # 按时间排序订单（新的在前）
                formatted_orders.sort(key=lambda x: x.get("time", 0), reverse=True)
                
                # 如果指定了limit，限制返回数量
                if limit and len(formatted_orders) > limit:
                    formatted_orders = formatted_orders[:limit]
                
                # 添加结果
                results.append({
                    "email": email,
                    "success": True,
                    "orderCount": len(formatted_orders),
                    "orders": formatted_orders
                })
                
            except Exception as e:
                error_msg = truncate_message(str(e))
                log_exception(f"获取子账号 {email} 的U本位合约订单异常: {error_msg}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": f"获取U本位合约订单异常: {error_msg}"
                })
        
        # 如果只有一个邮箱且email参数存在，保持原有的返回格式兼容性
        if len(emails) == 1 and email:
            return jsonify({
                "success": True,
                "data": results[0] if results else {
                    "email": email,
                    "success": False,
                    "error": "获取U本位合约订单失败"
                }
            })
        else:
            return jsonify({
                "success": True,
                "data": results
            })
                
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"获取U本位合约订单信息异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取U本位合约订单信息异常: {error_msg}"
        }), 500


@um_orders_bp.route('/order', methods=['POST'])
def get_um_order():
    """
    获取子账号的U本位合约(UM)当前交易对挂单信息 - 使用PAPI接口 - 只查询openOrder
    
    请求体:
    {
        "email": "子账号邮箱" (单个子账号时使用),
        "emails": ["子账号邮箱1", "子账号邮箱2", ...] (多个子账号时使用),
        "symbol": "交易对(必须)",
        "limit": 返回数量(可选, 默认50)
    }
    """
    try:
        data = request.json
        email = data.get('email')
        emails = data.get('emails', [])
        
        # 兼容单个邮箱和多个邮箱的情况
        if email and not emails:
            emails = [email]
        
        # 验证必要参数
        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱(email)或子账号邮箱数组(emails)"
            }), 400
            
        # 提取查询参数
        symbol = data.get('symbol')
        
        # symbol是必须的
        if not symbol:
            return jsonify({
                "success": False,
                "error": "请提供交易对(symbol)参数"
            }), 400
            
        limit = data.get('limit', 50)
        
        # 处理多个子账号请求
        results = []
        
        # 对每个子账号分别获取订单
        for email in emails:
            try:
                # 获取子账号的API客户端
                client = get_client_by_email(email)
                
                if not client:
                    results.append({
                        "email": email,
                        "success": False,
                        "error": "子账号API未配置或不可用"
                    })
                    continue
                
                # 构建API请求参数 - 使用U本位合约(UM)接口
                params = {
                    'symbol': symbol,  # symbol是必须的
                    'recvWindow': 10000,
                    'timestamp': int(time.time() * 1000)
                }
                
                if limit:
                    params['limit'] = limit
                
                # 获取未平仓订单 - 使用U本位合约API - PAPI - 只使用openOrder接口
                log_info(f"获取U本位合约未平仓订单 (PAPI接口) 当前交易对: {symbol}")
                open_order_endpoint = "/papi/v1/um/openOrder"
                
                # 确保请求参数中包含合约标识
                open_params = params.copy()
                # 添加合约类型参数(虽然路径已经包含/um/，但在记录日志时有用)
                open_params['contractType'] = 'UM'
                
                open_order_response = client._send_request('GET', open_order_endpoint, signed=True, params=open_params)
                
                # 处理未平仓订单
                all_orders = []
                if open_order_response and open_order_response.get('success'):
                    open_orders = open_order_response.get('data', [])
                    if not isinstance(open_orders, list):
                        open_orders = [open_orders]
                    
                    for order in open_orders:
                        all_orders.append(order)
                
                # 格式化订单数据
                formatted_orders = []
                for order in all_orders:
                    formatted_order = {
                        "orderId": order.get("orderId"),
                        "symbol": order.get("symbol"),
                        "status": order.get("status"),
                        "type": order.get("type"),
                        "side": order.get("side"),
                        "price": order.get("price"),
                        "origQty": order.get("origQty"),
                        "executedQty": order.get("executedQty"),
                        "reduceOnly": order.get("reduceOnly", False),
                        "positionSide": order.get("positionSide", "BOTH"),
                        "time": order.get("time") or order.get("updateTime"),
                        "updateTime": order.get("updateTime") or order.get("time")
                    }
                    formatted_orders.append(formatted_order)
                
                # 按时间排序订单（新的在前）
                formatted_orders.sort(key=lambda x: x.get("time", 0), reverse=True)
                
                # 添加结果
                results.append({
                    "email": email,
                    "success": True,
                    "orderCount": len(formatted_orders),
                    "orders": formatted_orders
                })
                
            except Exception as e:
                error_msg = truncate_message(str(e))
                log_exception(f"获取子账号 {email} 当前交易对的U本位合约挂单异常: {error_msg}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": f"获取U本位合约挂单异常: {error_msg}"
                })
        
        # 如果只有一个邮箱且email参数存在，保持原有的返回格式兼容性
        if len(emails) == 1 and email:
            return jsonify({
                "success": True,
                "data": results[0] if results else {
                    "email": email,
                    "success": False,
                    "error": "获取U本位合约挂单失败"
                }
            })
        else:
            return jsonify({
                "success": True,
                "data": results
            })
                
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"获取U本位合约挂单信息异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取U本位合约挂单信息异常: {error_msg}"
        }), 500 