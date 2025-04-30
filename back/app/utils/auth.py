"""
认证工具模块
"""
import os
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from app.models import User

# JWT密钥，从环境变量获取或使用默认值
JWT_SECRET = os.environ.get('JWT_SECRET', 'binance_manager_jwt_secret')

def token_required(f):
    """
    验证JWT令牌的装饰器
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从请求头获取token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'success': False,
                'error': '未提供认证令牌'
            }), 401
            
        try:
            # 解码JWT token
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
            
            # 查询用户
            current_user = User.query.get(user_id)
            if not current_user:
                return jsonify({
                    'success': False,
                    'error': '无效的认证令牌'
                }), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': '认证令牌已过期'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': '无效的认证令牌'
            }), 401
            
        # 将当前用户传递给被装饰的函数
        return f(current_user, *args, **kwargs)
    return decorated 