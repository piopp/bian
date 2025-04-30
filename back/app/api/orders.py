from flask import Blueprint, jsonify, request, current_app
from app.tasks.order_sync import (
    get_websocket_status, restart_websocket, restart_all_websockets,
    connect_user_websocket, sync_user_orders, check_api_permissions
)
from app.tasks.websocket_client import create_websocket_client
from flask_jwt_extended import jwt_required
from app.models.account import SubAccountAPISettings
from datetime import datetime, timedelta

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/api/orders/websocket/status', methods=['GET'])
@jwt_required()
def websocket_status():
    """获取WebSocket连接状态"""
    email = request.args.get('email')
    return jsonify(get_websocket_status(email))

@orders_bp.route('/api/orders/websocket/restart', methods=['POST'])
@jwt_required()
def restart_ws():
    """重启WebSocket连接"""
    data = request.get_json() or {}
    email = data.get('email')
    
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
        
    # 重启WebSocket连接
    result = restart_websocket(email, current_app)
    return jsonify(result)

@orders_bp.route('/api/orders/websocket/restart-all', methods=['POST'])
@jwt_required()
def restart_all_ws():
    """重启所有WebSocket连接"""
    return jsonify(restart_all_websockets(current_app))

@orders_bp.route('/api/orders/websocket/connect', methods=['POST'])
@jwt_required()
def connect_ws():
    """为子账号建立WebSocket连接"""
    data = request.get_json() or {}
    email = data.get('email')
    
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
        
    # 建立WebSocket连接
    result = connect_user_websocket(email, current_app)
    
    if result:
        return jsonify({
            'success': True,
            'message': f'已为子账号 {email} 建立WebSocket连接'
        })
    else:
        return jsonify({
            'success': False,
            'error': f'为子账号 {email} 建立WebSocket连接失败'
        }), 500
        
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
        
    # 同步订单
    try:
        count = sync_user_orders(email, symbol=symbol, start_time=None if days is None else int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000))
        
        return jsonify({
            'success': True,
            'message': f'已同步 {count} 个订单',
            'count': count
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
        
    # 检查API权限
    result = check_api_permissions(email)
    return jsonify(result)

@orders_bp.route('/api/orders/ws/query', methods=['POST'])
@jwt_required()
def query_order_ws():
    """通过WebSocket查询订单"""
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
        
    # 创建WebSocket客户端
    client = create_websocket_client(email)
    if not client:
        return jsonify({
            'success': False,
            'error': '创建WebSocket客户端失败'
        }), 500
        
    # 查询订单
    try:
        result = client.query_order(symbol, order_id, client_order_id)
        client.close()  # 关闭连接
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@orders_bp.route('/api/orders/ws/open-orders', methods=['GET'])
@jwt_required()
def query_open_orders_ws():
    """通过WebSocket查询当前挂单"""
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
        
    # 创建WebSocket客户端
    client = create_websocket_client(email)
    if not client:
        return jsonify({
            'success': False,
            'error': '创建WebSocket客户端失败'
        }), 500
        
    # 查询挂单
    try:
        result = client.query_open_orders(symbol)
        client.close()  # 关闭连接
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 