import time
import requests
from datetime import datetime
from flask import Blueprint, jsonify, current_app, redirect, url_for

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