import time
import requests
from datetime import datetime
from flask import Blueprint, jsonify, current_app, redirect, url_for, request
from app.services.binance_client import get_binance_client

server_bp = Blueprint('server', __name__, url_prefix='/api/server')

# 添加一个额外的blueprint用于处理/api/time路径
time_bp = Blueprint('time', __name__, url_prefix='/api')

@time_bp.route('/time', methods=['GET'])
def redirect_to_time():
    """重定向到/api/server/time端点"""
    # 简单地返回相同的数据而不是重定向
    now = datetime.now()
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
    
    return jsonify({
        'success': True,
        'data': {
            'timestamp': timestamp,
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': time.tzname[0] if time.tzname else 'UTC'
        }
    })

# 币安API基础URL
BINANCE_API_URL = "https://api.binance.com"

def get_binance_server_time():
    """获取币安服务器时间"""
    try:
        response = requests.get(f"{BINANCE_API_URL}/api/v3/time")
        if response.status_code == 200:
            data = response.json()
            return data.get("serverTime")
        else:
            current_app.logger.error(f"币安API请求失败: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        current_app.logger.error(f"获取币安服务器时间错误: {str(e)}")
        return None

@server_bp.route('/binance_time', methods=['GET'])
def get_server_time():
    """获取币安服务器时间与本地时间的对比"""
    start_time = int(time.time() * 1000)
    
    # 获取币安服务器时间
    binance_time = get_binance_server_time()
    
    if binance_time:
        return jsonify({
            "success": True,
            "data": {
                "server_time": binance_time,
                "local_time": start_time,
                "time_diff": binance_time - start_time,
                "source": "binance"
            }
        })
    else:
        # 如果币安API请求失败，回退到本地时间
        current_time = int(time.time() * 1000)
        return jsonify({
            "success": False,
            "error": "无法连接到币安服务器",
            "data": {
                "server_time": current_time,
                "local_time": start_time,
                "source": "local"
            }
        })

@server_bp.route('/time', methods=['GET'])
def get_current_time():
    """
    获取服务器当前时间
    
    返回:
        timestamp: 毫秒级时间戳
        formatted: 格式化的时间字符串
    """
    now = datetime.now()
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
    
    return jsonify({
        'success': True,
        'data': {
            'timestamp': timestamp,
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': time.tzname[0] if time.tzname else 'UTC'
        }
    })

@server_bp.route('/status', methods=['GET'])
def get_server_status():
    """获取服务器状态信息"""
    try:
        # 获取系统信息
        import psutil
        import platform
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        return jsonify({
            'success': True,
            'data': {
                'system': platform.system(),
                'release': platform.release(),
                'cpu_usage': f"{cpu_percent}%",
                'memory_usage': f"{memory.percent}%",
                'memory_available': f"{memory.available / (1024 * 1024):.2f} MB",
                'api_status': 'online',
                'uptime': time.time() - psutil.boot_time()
            }
        })
    except ImportError:
        # 如果psutil不可用
        return jsonify({
            'success': True,
            'data': {
                'system': platform.system() if 'platform' in globals() else 'Unknown',
                'release': platform.release() if 'platform' in globals() else 'Unknown',
                'api_status': 'online'
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取服务器状态错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取服务器状态失败: {str(e)}'
        }), 500 

@server_bp.route('/sync_time', methods=['GET'])
def sync_binance_time():
    """
    同步本地时间与币安服务器时间
    
    返回:
        - success: 同步是否成功
        - data: 同步结果数据，包含本地时间、服务器时间、偏移量等
    """
    try:
        # 从认证令牌获取用户ID
        user_id = None
        auth_header = request.headers.get('Authorization')
        current_app.logger.info(f"收到同步时间请求，Authorization头: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # 解码JWT token
                from app.utils.auth import JWT_SECRET
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                current_app.logger.info(f"从token中获取到用户ID: {user_id}")
            except Exception as e:
                current_app.logger.warning(f"解析token失败: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": "无效的认证令牌"
                }), 401
        
        if not user_id:
            current_app.logger.warning("未找到用户ID")
            return jsonify({
                "success": False,
                "error": "未找到用户ID，请确保已登录"
            }), 401
        
        # 获取币安客户端
        current_app.logger.info(f"尝试获取用户 {user_id} 的币安客户端")
        client = get_binance_client(user_id)
        
        if not client:
            current_app.logger.error(f"无法获取用户 {user_id} 的币安客户端")
            return jsonify({
                "success": False,
                "error": "无法获取币安客户端，请确保已配置API密钥"
            }), 500
        
        # 同步时间
        current_app.logger.info("开始同步时间")
        result = client.sync_time()
        current_app.logger.info(f"时间同步结果: {result}")
        
        # 返回同步结果
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"同步币安服务器时间异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"同步币安服务器时间异常: {str(e)}"
        }), 500 