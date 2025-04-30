from flask import Blueprint, jsonify, request, current_app
from app.models import User, db, APIKey
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/', methods=['GET'])
def get_all_users():
    """获取所有用户列表"""
    try:
        users = User.query.all()
        users_list = []
        
        for user in users:
            users_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.create_time.isoformat() if user.create_time else None
                # 出于安全考虑，不返回密码
            })
        
        return jsonify({
            'success': True,
            'data': users_list
        })
    except Exception as e:
        logger.error(f"获取用户列表出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取用户列表失败: {str(e)}'
        }), 500

@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """获取指定用户信息"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': f'用户ID {user_id} 不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.create_time.isoformat() if user.create_time else None
            }
        })
    except Exception as e:
        logger.error(f"获取用户信息出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取用户信息失败: {str(e)}'
        }), 500

@users_bp.route('/<int:user_id>/api_keys', methods=['GET'])
def get_user_api_keys(user_id):
    """获取用户的API密钥信息"""
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': f'用户ID {user_id} 不存在'
            }), 404
            
        # 查找用户的API密钥
        api_key = APIKey.query.filter_by(user_id=user_id).first()
        
        if api_key:
            return jsonify({
                'success': True,
                'data': {
                    'id': api_key.id,
                    'user_id': api_key.user_id,
                    'api_key': api_key.api_key,
                    'has_api_secret': bool(api_key.api_secret),
                    'is_active': api_key.is_active,
                    'created_at': api_key.created_at.isoformat() if api_key.created_at else None
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': '未找到API密钥'
            })
    except Exception as e:
        logger.error(f"获取用户API密钥出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取用户API密钥失败: {str(e)}'
        }), 500

@users_bp.route('/<int:user_id>/api_keys', methods=['POST'])
def save_user_api_keys(user_id):
    """保存或更新用户的API密钥"""
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': f'用户ID {user_id} 不存在'
            }), 404
            
        data = request.get_json()
        if not data or 'api_key' not in data or 'api_secret' not in data:
            return jsonify({
                'success': False,
                'error': '请提供api_key和api_secret字段'
            }), 400
            
        api_key_value = data.get('api_key')
        api_secret_value = data.get('api_secret')
        
        # 查找现有的API密钥记录
        existing_key = APIKey.query.filter_by(user_id=user_id).first()
        
        if existing_key:
            # 更新现有记录
            existing_key.api_key = api_key_value
            existing_key.api_secret = api_secret_value
            existing_key.is_active = True
        else:
            # 创建新记录
            new_key = APIKey(
                user_id=user_id,
                api_key=api_key_value,
                api_secret=api_secret_value,
                is_active=True
            )
            db.session.add(new_key)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API密钥保存成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"保存用户API密钥出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'保存API密钥失败: {str(e)}'
        }), 500

@users_bp.route('/<int:user_id>/api_keys', methods=['DELETE'])
def delete_user_api_keys(user_id):
    """删除用户的API密钥"""
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': f'用户ID {user_id} 不存在'
            }), 404
            
        # 查找用户的API密钥
        api_key = APIKey.query.filter_by(user_id=user_id).first()
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': '未找到API密钥'
            }), 404
            
        db.session.delete(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API密钥已删除'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除用户API密钥出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除API密钥失败: {str(e)}'
        }), 500 