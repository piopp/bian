import time
import logging
from flask import Blueprint, request, jsonify, current_app
from app.services.binance_client import get_binance_client, get_client_by_email
from app.utils.logger import log_info, log_error, log_exception, truncate_message

margin_bp = Blueprint('margin', __name__, url_prefix='/api/margin')
logger = logging.getLogger(__name__)

@margin_bp.route('/orders', methods=['POST'])
def get_margin_orders():
    """
    获取杠杆账户订单信息 - 使用/papi/v1/margin/allOrders接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderId": 订单ID(可选),
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "limit": 返回数量限制(可选，默认500)
    }
    
    返回体:
    {
        "success": true,
        "data": 订单信息对象或数组
    }
    """
    try:
        data = request.json
        email = data.get('email')
        user_id = data.get('user_id')
        symbol = data.get('symbol')
        order_id = data.get('orderId')
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        limit = data.get('limit', 500)
        
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
        
        # 如果没有提供end_time，使用当前时间
        if not end_time:
            end_time = int(time.time() * 1000)  # 当前时间的毫秒时间戳
        
        # 首先尝试获取子账号API客户端
        client = get_client_by_email(email)
        if not client:
            log_info(f"子账号 {email} 的API未配置或不可用，尝试使用主账号API")
            # 如果子账号API不可用，尝试使用主账号API
            client = get_binance_client(user_id)
            if not client:
                return jsonify({
                    "success": False,
                    "error": "API未配置或不可用"
                }), 400
        
        # 构建API请求参数 - 确保参数格式正确
        params = {
            'symbol': symbol,
            'recvWindow': 60000
        }
        
        # 添加可选参数
        if order_id:
            params['orderId'] = int(order_id)  # 确保是整数
        if start_time:
            params['startTime'] = int(start_time)
            log_info(f"查询开始时间: {start_time}，格式化后: {params['startTime']}，对应日期: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(start_time)/1000))}")
        if end_time:
            params['endTime'] = int(end_time)
            log_info(f"查询结束时间: {end_time}，格式化后: {params['endTime']}，对应日期: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(end_time)/1000))}")
        if limit:
            params['limit'] = int(limit)
            
        # 获取服务器时间并同步
        try:
            time_response = client._send_request('GET', '/api/v3/time', signed=False)
            if time_response.get('success'):
                server_time = time_response.get('data', {}).get('serverTime')
                if server_time:
                    params['timestamp'] = server_time
                    log_info(f"使用币安服务器时间: {server_time}")
                else:
                    params['timestamp'] = int(time.time() * 1000)
                    log_info(f"使用本地时间: {params['timestamp']}")
            else:
                params['timestamp'] = int(time.time() * 1000)
                log_info(f"获取服务器时间失败，使用本地时间: {params['timestamp']}")
        except Exception as e:
            params['timestamp'] = int(time.time() * 1000)
            log_error(f"获取服务器时间异常: {str(e)}，使用本地时间: {params['timestamp']}")
        
        # 杠杆账户所有订单查询接口
        endpoint = "/papi/v1/margin/allOrders"
        log_info(f"使用账号 {email} 请求杠杆账户订单: {endpoint}, 参数: {params}")
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            orders = response.get('data', [])
            log_info(f"成功获取杠杆账户订单，数量: {len(orders)}")
            
            # 格式化订单数据，保留完整字段
            formatted_orders = []
            for order in orders:
                formatted_order = {
                    "orderId": order.get("orderId"),
                    "clientOrderId": order.get("clientOrderId"),
                    "symbol": order.get("symbol"),
                    "status": order.get("status"),
                    "price": order.get("price"),
                    "origQty": order.get("origQty"),
                    "executedQty": order.get("executedQty"),
                    "cummulativeQuoteQty": order.get("cummulativeQuoteQty"),
                    "type": order.get("type"),
                    "side": order.get("side"),
                    "stopPrice": order.get("stopPrice"),
                    "icebergQty": order.get("icebergQty"),
                    "time": order.get("time"),
                    "updateTime": order.get("updateTime"),
                    "isWorking": order.get("isWorking"),
                    "timeInForce": order.get("timeInForce"),
                    "accountId": order.get("accountId"),
                    "selfTradePreventionMode": order.get("selfTradePreventionMode"),
                    "preventedMatchId": order.get("preventedMatchId"),
                    "preventedQuantity": order.get("preventedQuantity")
                }
                formatted_orders.append(formatted_order)
            
            return jsonify({
                "success": True,
                "data": formatted_orders
            })
        else:
            error_msg = truncate_message(response.get('error', '获取杠杆订单失败'))
            log_error(f"获取杠杆订单失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
            
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"获取杠杆订单异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取杠杆订单异常: {error_msg}"
        }), 500

@margin_bp.route('/trades', methods=['POST'])
def get_margin_trades():
    """
    获取杠杆账户交易历史 - 使用/papi/v1/margin/myTrades接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderId": 订单ID(可选),
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "fromId": 起始交易ID(可选),
        "limit": 返回数量限制(可选，默认500)
    }
    
    返回体:
    {
        "success": true,
        "data": 交易历史记录数组
    }
    """
    try:
        data = request.json
        email = data.get('email')
        user_id = data.get('user_id')
        symbol = data.get('symbol')
        from_id = data.get('fromId')
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        limit = data.get('limit', 500)
        
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
        
        # 如果没有提供end_time，使用当前时间
        if not end_time:
            end_time = int(time.time() * 1000)  # 当前时间的毫秒时间戳
        
        # 检查是否为币本位合约符号 (如DOGEUSD_PERP, BTCUSD_PERP等)
        if "_PERP" in symbol or (symbol.endswith("USD") and not symbol.endswith("USDT")):
            log_info(f"检测到币本位合约符号: {symbol}，杠杆交易历史API不支持此类符号")
            return jsonify({
                "success": False,
                "error": f"币本位合约 {symbol} 不支持杠杆交易，无法查询杠杆交易历史"
            }), 400
        
        # 首先尝试获取子账号API客户端
        client = get_client_by_email(email)
        if not client:
            log_info(f"子账号 {email} 的API未配置或不可用，尝试使用主账号API")
            # 如果子账号API不可用，尝试使用主账号API
            client = get_binance_client(user_id)
            if not client:
                return jsonify({
                    "success": False,
                    "error": "API未配置或不可用"
                }), 400
        
        # 构建API请求参数 - 确保参数格式正确
        params = {
            'symbol': symbol,
            'recvWindow': 60000
        }
        
        # 添加可选参数（若提供）
        if from_id:
            params['fromId'] = int(from_id)
        if start_time:
            params['startTime'] = int(start_time)
        if end_time:
            params['endTime'] = int(end_time)
        if limit:
            params['limit'] = int(limit)
            
        # 使用统一账户API的杠杆交易历史接口
        endpoint = "/papi/v1/margin/myTrades"
        log_info(f"使用统一账户API请求杠杆交易历史: {endpoint}, 参数: {params}")
        
        # 获取杠杆交易历史
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if not response.get('success'):
            error_msg = truncate_message(response.get('error', '获取杠杆交易历史失败'))
            log_error(f"统一账户API获取杠杆交易历史失败: {error_msg}")
            
            # 不再尝试降级到旧版杠杆API
            return jsonify({
                "success": False,
                "error": f"获取杠杆交易历史失败: {error_msg}"
            }), 400
            
        trades = response.get('data', [])
        log_info(f"成功获取杠杆账户交易历史，数量: {len(trades)}")
        
        # 格式化交易记录数据
        formatted_trades = []
        for trade in trades:
            formatted_trade = {
                "id": trade.get("id"),
                "orderId": trade.get("orderId"),
                "symbol": trade.get("symbol"),
                "price": trade.get("price"),
                "qty": trade.get("qty"),
                "commission": trade.get("commission"),
                "commissionAsset": trade.get("commissionAsset"),
                "time": trade.get("time"),
                "isBuyer": trade.get("isBuyer"),
                "isMaker": trade.get("isMaker"),
                "isBestMatch": trade.get("isBestMatch")
            }
            formatted_trades.append(formatted_trade)
        
        return jsonify({
            "success": True,
            "data": formatted_trades
        })
            
    except Exception as e:
        error_msg = truncate_message(str(e))
        log_exception(f"获取杠杆交易历史异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取杠杆交易历史异常: {error_msg}"
        }), 500 