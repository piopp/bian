import os
import json
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError
from app.models import db, Setting
from app.models.account import SubAccountAPISettings
from app.models.user import User, APIKey
import logging
import traceback

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.route('/', methods=['GET'])
def get_all_settings():
    """获取所有设置项"""
    try:
        settings = Setting.query.all()
        return jsonify({
            'success': True,
            'data': [setting.to_dict() for setting in settings]
        })
    except SQLAlchemyError as e:
        logger.error(f"数据库错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取设置失败: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取设置失败: {str(e)}'
        }), 500

@settings_bp.route('/<string:key>', methods=['GET'])
def get_setting(key):
    """获取指定设置项"""
    try:
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({
                'success': False,
                'error': f'设置项 {key} 不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'data': setting.to_dict()
        })
    except SQLAlchemyError as e:
        logger.error(f"数据库错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取设置失败: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取设置失败: {str(e)}'
        }), 500

@settings_bp.route('/', methods=['POST'])
def create_setting():
    """创建设置项"""
    try:
        data = request.get_json()
        
        if not data or 'key' not in data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': '请提供key和value字段'
            }), 400
            
        # 检查设置项是否已存在
        existing = Setting.query.filter_by(key=data['key']).first()
        if existing:
            return jsonify({
                'success': False,
                'error': f'设置项 {data["key"]} 已存在'
            }), 409
            
        # 创建新设置项
        setting = Setting(
            key=data['key'],
            value=data['value'],
            description=data.get('description', '')
        )
        
        db.session.add(setting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '设置项创建成功',
            'data': setting.to_dict()
        }), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'创建设置失败: {str(e)}'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"未知错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'创建设置失败: {str(e)}'
        }), 500

@settings_bp.route('/<string:key>', methods=['PUT'])
def update_setting(key):
    """更新设置项"""
    try:
        data = request.get_json()
        
        if not data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': '请提供value字段'
            }), 400
            
        # 查找设置项
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({
                'success': False,
                'error': f'设置项 {key} 不存在'
            }), 404
            
        # 更新设置项
        setting.value = data['value']
        if 'description' in data:
            setting.description = data['description']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '设置项更新成功',
            'data': setting.to_dict()
        })
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'更新设置失败: {str(e)}'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"未知错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'更新设置失败: {str(e)}'
        }), 500

@settings_bp.route('/<string:key>', methods=['DELETE'])
def delete_setting(key):
    """删除设置项"""
    try:
        # 查找设置项
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({
                'success': False,
                'error': f'设置项 {key} 不存在'
            }), 404
            
        # 删除设置项
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'设置项 {key} 已删除'
        })
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除设置失败: {str(e)}'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"未知错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除设置失败: {str(e)}'
        }), 500

@settings_bp.route('/api-keys/<string:user_id>', methods=['GET'])
def get_api_key(user_id):
    """获取指定用户ID的API密钥信息"""
    logger.info(f"获取指定用户ID的API密钥信息: {user_id}")
    try:
        # 检查user_id是否为有效的整数
        try:
            user_id_int = int(user_id)
            logger.info(f"转换后的用户ID: {user_id_int}")
        except ValueError as e:
            logger.error(f"用户ID转换失败: {e}")
            return jsonify({
                'success': False,
                'error': f'无效的用户ID: {user_id}'
            }), 400

        # 检查用户是否存在
        user = User.query.get(user_id_int)
        if not user:
            logger.error(f"用户ID {user_id_int} 不存在")
            return jsonify({
                'success': False,
                'error': f'用户ID {user_id_int} 不存在'
            }), 404

        # 直接使用导入的APIKey模型
        try:
            logger.info(f"开始查询APIKey，用户ID: {user_id_int}")
            # 添加错误处理,避免datetime格式问题
            try:
                api_key = APIKey.query.filter_by(user_id=user_id_int, is_active=True).first()
                logger.info(f"API密钥信息: {api_key}")
            except TypeError as e:
                # 记录详细错误
                logger.error(f"查询API密钥时发生TypeError: {str(e)}")
                logger.error(traceback.format_exc())
                # 使用更安全的查询方法
                api_key_data = db.session.execute(
                    db.select(APIKey).filter_by(user_id=user_id_int, is_active=True).limit(1)
                ).first()
                api_key = api_key_data[0] if api_key_data else None
                logger.info(f"安全方式查询到的API密钥信息: {api_key}")
        except SQLAlchemyError as e:
            logger.error(f"SQL查询错误: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'数据库查询错误: {str(e)}'
            }), 500
        
        if api_key:
            logger.info(f"找到用户 {user_id_int} 的API密钥")
            return jsonify({
                'success': True,
                'data': {
                    'id': user_id,
                    'apiKey': api_key.api_key,
                    'hasApiSecret': bool(api_key.api_secret),
                    'type': 'master'
                }
            })
        else:
            logger.info(f"未找到用户 {user_id_int} 的API密钥")
            return jsonify({
                'success': True,
                'data': {
                    'id': user_id,
                    'apiKey': '',
                    'hasApiSecret': False,
                    'type': 'master'
                }
            })
    except Exception as e:
        logger.error(f"获取API密钥错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'获取API密钥信息失败: {str(e)}'
        }), 500

@settings_bp.route('/api-keys/<string:user_id>', methods=['POST'])
def update_api_keys(user_id):
    """更新指定用户ID的API密钥"""
    print(f"更新指定用户ID的API密钥: {user_id}")
    try:
        # 检查user_id是否为有效的整数
        try:
            user_id_int = int(user_id)
            print(f"转换后的用户ID: {user_id_int}")
        except ValueError as e:
            print(f"用户ID转换失败: {e}")
            return jsonify({
                'success': False,
                'error': f'无效的用户ID: {user_id}'
            }), 400
            
        data = request.get_json()
        
        if not data or 'apiKey' not in data or 'apiSecret' not in data:
            return jsonify({
                'success': False,
                'error': '请提供apiKey和apiSecret字段'
            }), 400
        
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        
        # 查找现有的API密钥记录
        try:
            print(f"开始查询APIKey，用户ID: {user_id_int}")
            existing_key = APIKey.query.filter_by(user_id=user_id_int).first()
            print(f"现有API密钥: {existing_key}")
        except SQLAlchemyError as e:
            print(f"SQL查询错误: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'数据库查询错误: {str(e)}'
            }), 500
        
        if existing_key:
            # 更新现有记录
            existing_key.api_key = api_key
            existing_key.api_secret = api_secret
            existing_key.is_active = True
        else:
            # 创建新记录
            new_key = APIKey(
                user_id=user_id_int,
                api_key=api_key,
                api_secret=api_secret,
                is_active=True
            )
            db.session.add(new_key)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'用户ID {user_id} 的API密钥已更新',
            'data': {
                'id': user_id,
                'apiKey': api_key,
                'hasApiSecret': bool(api_secret),
                'type': 'master'
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"更新API密钥错误: {str(e)}")
        print(traceback.format_exc())
        logger.error(f"更新API密钥失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'更新API密钥失败: {str(e)}'
        }), 500

@settings_bp.route('/api-keys/<string:user_id>', methods=['DELETE'])
def delete_api_keys(user_id):
    """删除指定用户ID的API密钥"""
    print(f"删除指定用户ID的API密钥: {user_id}")
    try:
        # 检查user_id是否为有效的整数
        try:
            user_id_int = int(user_id)
            print(f"转换后的用户ID: {user_id_int}")
        except ValueError as e:
            print(f"用户ID转换失败: {e}")
            return jsonify({
                'success': False,
                'error': f'无效的用户ID: {user_id}'
            }), 400
            
        # 查找API密钥记录
        try:
            print(f"开始查询APIKey，用户ID: {user_id_int}")
            api_key = APIKey.query.filter_by(user_id=user_id_int).first()
            print(f"要删除的API密钥: {api_key}")
        except SQLAlchemyError as e:
            print(f"SQL查询错误: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'数据库查询错误: {str(e)}'
            }), 500
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': f'未找到用户ID {user_id} 的API密钥'
            }), 404
        
        # 删除或设为非活跃
        db.session.delete(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'用户ID {user_id} 的API密钥已删除'
        })
    except Exception as e:
        db.session.rollback()
        print(f"删除API密钥错误: {str(e)}")
        print(traceback.format_exc())
        logger.error(f"删除API密钥失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除API密钥失败: {str(e)}'
        }), 500 