from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from app.models.account import SubAccountAPISettings
from datetime import datetime, timedelta
from app.services.binance_client import BinanceClient, get_client_by_email
from app.api.subaccounts import get_sub_account_api_credentials

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/api/orders/websocket/status', methods=['GET'])
@jwt_required()
def websocket_status():
    """获取WebSocket连接状态 - 已废弃"""
    return jsonify({
        'success': False,
        'message': '此API已废弃，WebSocket功能已移除'
    })

@orders_bp.route('/api/orders/websocket/restart', methods=['POST'])
@jwt_required()
def restart_ws():
    """重启WebSocket连接 - 已废弃"""
    return jsonify({
        'success': False,
        'message': '此API已废弃，WebSocket功能已移除'
    })

@orders_bp.route('/api/orders/websocket/restart-all', methods=['POST'])
@jwt_required()
def restart_all_ws():
    """重启所有WebSocket连接 - 已废弃"""
    return jsonify({
        'success': False,
        'message': '此API已废弃，WebSocket功能已移除'
    })

@orders_bp.route('/api/orders/websocket/connect', methods=['POST'])
@jwt_required()
def connect_ws():
    """为子账号建立WebSocket连接 - 已废弃"""
    return jsonify({
        'success': False,
        'message': '此API已废弃，WebSocket功能已移除'
    })
        
@orders_bp.route('/api/orders/sync', methods=['POST'])
@jwt_required()
def sync_orders():
    """手动同步订单"""
    data = request.get_json() or {}
    email = data.get('email')
    days = data.get('days', 1)
    symbol = data.get('symbol')
    
    if not email:
        return jsonify({
            'success': False,
            'error': '缺少email参数'
        }), 400
        
    # 验证子账号是否存在
    account = SubAccountAPISettings.query.filter_by(email=email).first()
    if not account:
        return jsonify({
            'success': False,
            'error': '子账号不存在或未配置API'
        }), 404
        
    # 同步订单 - 直接使用BinanceClient获取订单
    try:
        # 获取子账号API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': '子账号API未配置或不可用'
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        params = {}
        if symbol:
            params['symbol'] = symbol
        if days:
            params['startTime'] = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        
        # 调用API获取订单
        result = client._send_request('GET', '/fapi/v1/allOrders', signed=True, params=params)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', '获取订单失败')
            }), 500
        
        return jsonify({
            'success': True,
            'data': result.get('data', []),
            'count': len(result.get('data', []))
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@orders_bp.route('/api/orders/check-api', methods=['GET'])
@jwt_required()
def check_api():
    """检查子账号API权限"""
    email = request.args.get('email')
    
    if not email:
        return jsonify({
            'success': False,
            'error': '缺少email参数'
        }), 400
        
    # 验证子账号是否存在
    account = SubAccountAPISettings.query.filter_by(email=email).first()
    if not account:
        return jsonify({
            'success': False,
            'error': '子账号不存在或未配置API'
        }), 404
        
    # 检查API权限 - 直接使用BinanceClient测试API
    try:
        # 获取子账号API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': '子账号API未配置或不可用'
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 测试账户权限
        account_result = client._send_request('GET', '/fapi/v2/account', signed=True)
        
        # 测试订单权限
        order_result = client._send_request('GET', '/fapi/v1/openOrders', signed=True)
        
        return jsonify({
            'success': True,
            'permissions': {
                'readAccount': account_result.get('success', False),
                'readOrders': order_result.get('success', False)
            },
            'message': '子账号API权限检查完成'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'API权限检查失败: {str(e)}'
        }), 500

@orders_bp.route('/api/orders/ws/query', methods=['POST'])
@jwt_required()
def query_order_ws():
    """查询订单 - 已改为REST API实现"""
    data = request.get_json() or {}
    email = data.get('email')
    symbol = data.get('symbol')
    order_id = data.get('orderId')
    client_order_id = data.get('clientOrderId')
    
    if not email:
        return jsonify({
            'success': False,
            'error': '缺少email参数'
        }), 400
        
    if not symbol:
        return jsonify({
            'success': False,
            'error': '缺少symbol参数'
        }), 400
        
    if not order_id and not client_order_id:
        return jsonify({
            'success': False,
            'error': '缺少orderId或clientOrderId参数'
        }), 400
        
    # 验证子账号是否存在
    account = SubAccountAPISettings.query.filter_by(email=email).first()
    if not account:
        return jsonify({
            'success': False,
            'error': '子账号不存在或未配置API'
        }), 404
        
    # 使用REST API查询订单
    try:
        # 获取子账号API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': '子账号API未配置或不可用'
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 构建查询参数
        params = {'symbol': symbol}
        if order_id:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        
        # 查询订单
        result = client._send_request('GET', '/fapi/v1/order', signed=True, params=params)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'查询订单失败: {str(e)}'
        }), 500

@orders_bp.route('/api/orders/ws/open-orders', methods=['GET'])
@jwt_required()
def query_open_orders_ws():
    """查询挂单 - 已改为REST API实现"""
    email = request.args.get('email')
    symbol = request.args.get('symbol')
    
    if not email:
        return jsonify({
            'success': False,
            'error': '缺少email参数'
        }), 400
        
    # 验证子账号是否存在
    account = SubAccountAPISettings.query.filter_by(email=email).first()
    if not account:
        return jsonify({
            'success': False,
            'error': '子账号不存在或未配置API'
        }), 404
        
    # 使用REST API查询挂单
    try:
        # 获取子账号API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': '子账号API未配置或不可用'
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 构建查询参数
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        # 查询挂单
        result = client._send_request('GET', '/fapi/v1/openOrders', signed=True, params=params)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'查询挂单失败: {str(e)}'
        }), 500 