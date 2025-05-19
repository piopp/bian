from flask import Blueprint, jsonify, request, session
from app.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# JWT密钥，从环境变量获取或使用默认值
JWT_SECRET = os.environ.get('JWT_SECRET', 'binance_manager_jwt_secret')
JWT_EXPIRATION = int(os.environ.get('JWT_EXPIRATION', 2592000))  # 默认30天

# 验证Token的装饰器函数
def token_required(f):
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

# login_required装饰器，与token_required功能类似，但不传递用户对象
def login_required(f):
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
            
        # 不传递用户对象，只验证登录状态
        return f(*args, **kwargs)
    return decorated

# 获取当前认证用户信息的函数
def authenticated_user():
    """
    获取当前认证的用户信息
    
    返回:
    - 成功: 包含用户ID和用户名的字典
    - 失败: None
    """
    token = None
    
    # 从请求头获取token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    if not token:
        return None
        
    try:
        # 解码JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # 查询用户
        current_user = User.query.get(user_id)
        if not current_user:
            return None
        
        # 返回用户信息字典
        return {
            'id': current_user.id,
            'username': current_user.username
        }
            
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user or not user.password==password:
        return jsonify({"success": False, "error": "用户名或密码错误"}), 401
    
    # 生成JWT令牌
    token = jwt.encode({
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION)
    }, JWT_SECRET, algorithm='HS256')
    
    # 设置会话
    session['user_id'] = user.id
    session['username'] = user.username
    
    return jsonify({
        "success": True,
        "message": "登录成功",
        "data": {
            "username": user.username,
            "id": user.id,
            "token": token
        }
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({"success": True, "message": "登出成功"})

@auth_bp.route('/status', methods=['GET'])
@token_required
def status(current_user):
    """获取当前登录状态"""
    return jsonify({
        "success": True,
        "data": {
            "logged_in": True,
            "username": current_user.username,
            "id": current_user.id
        }
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    """注册新用户（仅限开发环境使用）"""
    # 获取配置中的环境设置
    from flask import current_app
    if not current_app.config.get('DEBUG', False):
        return jsonify({"success": False, "error": "注册功能仅在开发环境可用"}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    
    # 检查用户是否已存在
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"success": False, "error": "用户名已存在"}), 400
    
    # 创建新用户
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "注册成功",
            "data": {
                "username": new_user.username,
                "id": new_user.id
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"注册失败: {str(e)}"}), 500 