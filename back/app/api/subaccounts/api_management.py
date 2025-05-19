import time
import logging
import secrets
import string
import hashlib
import json
import csv
import io
from flask import request, jsonify, Response, send_file
from app.models import db
from app.models.account import SubAccountAPISettings
from app.utils.auth import token_required
from . import subaccounts_bp
from app.services.binance_client import BinanceClient, get_main_account_api_credentials
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_api_key_format(api_key, api_secret):
    """
    验证API密钥格式是否有效
    
    参数:
    - api_key: API密钥
    - api_secret: API密钥密码
    
    返回:
    - (bool, str): (是否有效, 错误信息)
    """
    # 清理可能的空格和换行符
    if api_key:
        api_key = api_key.strip()
    if api_secret:
        api_secret = api_secret.strip()
    
    # 验证API密钥
    if not api_key:
        return False, "API密钥不能为空"
    
    # 币安API密钥通常为64位长度
    if len(api_key) < 10 or len(api_key) > 128:
        return False, "API密钥格式无效，长度应在10-128个字符之间"
    
    # 验证API密钥密码
    if not api_secret:
        return False, "API密钥密码不能为空"
    
    # 币安API密钥密码通常为64位长度
    if len(api_secret) < 10 or len(api_secret) > 128:
        return False, "API密钥密码格式无效，长度应在10-128个字符之间"
    
    # 验证格式（币安API密钥通常包含特定字符）
    import re
    
    # 币安API密钥通常只包含字母和数字
    if not re.match(r'^[A-Za-z0-9]+$', api_key):
        return False, "API密钥格式无效，包含非法字符，只允许字母和数字"
    
    # 币安API密钥密码通常只包含字母和数字
    if not re.match(r'^[A-Za-z0-9]+$', api_secret):
        return False, "API密钥密码格式无效，包含非法字符，只允许字母和数字"
    
    # 验证通过
    logger.info("API密钥格式验证通过")
    return True, ""

@subaccounts_bp.route('/api-keys', methods=['GET'])
@token_required
def get_api_keys(current_user):
    """
    获取所有子账号的API密钥设置
    """
    try:
        # 获取所有子账号API设置
        api_settings = SubAccountAPISettings.query.all()
        
        result = []
        for setting in api_settings:
            result.append({
                'id': setting.id,
                'email': setting.email,
                'api_key': setting.api_key[:8] + '*' * 8 if setting.api_key else '',
                'has_secret': bool(setting.api_secret),
                'created_at': setting.created_at.strftime('%Y-%m-%d %H:%M:%S') if setting.created_at else '',
                'updated_at': setting.updated_at.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_at else '',
                'permissions': setting.permissions
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.exception(f"获取API密钥设置异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取API密钥设置异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-keys/<email>', methods=['GET'])
@token_required
def get_api_key_by_email(current_user, email):
    """
    获取指定子账号的API密钥设置
    """
    try:
        # 获取子账号API设置
        setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        if not setting:
            return jsonify({
                'success': False,
                'error': f"未找到子账号 {email} 的API设置"
            }), 404
        
        result = {
            'id': setting.id,
            'email': setting.email,
            'api_key': setting.api_key[:8] + '*' * 8 if setting.api_key else '',
            'has_secret': bool(setting.api_secret),
            'created_at': setting.created_at.strftime('%Y-%m-%d %H:%M:%S') if setting.created_at else '',
            'updated_at': setting.updated_at.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_at else '',
            'permissions': setting.permissions
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.exception(f"获取子账号API密钥设置异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取子账号API密钥设置异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-keys', methods=['POST'])
@token_required
def save_api_key(current_user):
    """
    保存子账号API密钥设置
    
    请求体:
    {
        "email": "子账号邮箱",
        "api_key": "API密钥",
        "api_secret": "API密钥",
        "permissions": "API权限(可选)"
    }
    """
    try:
        data = request.json
        email = data.get('email')
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        permissions = data.get('permissions', 'READ_INFO,ENABLE_SPOT,ENABLE_FUTURES')
        
        # 验证必要参数
        if not email:
            return jsonify({
                'success': False,
                'error': "邮箱不能为空"
            }), 400
        
        # 验证API密钥格式
        is_valid, error_msg = validate_api_key_format(api_key, api_secret)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
        # 验证API密钥
        api_key = api_key.strip()
        api_secret = api_secret.strip()
        
        # 检查API密钥是否有效
        try:
            logger.info(f"验证子账号 {email} 的API密钥有效性")
            client = BinanceClient(api_key, api_secret)
            
            # 尝试获取账户信息，验证API密钥
            account_info = client.get_account_info()
            
            if not account_info.get('success'):
                logger.error(f"API密钥验证失败: {account_info.get('error')}")
                return jsonify({
                    'success': False,
                    'error': f"API密钥验证失败: {account_info.get('error')}"
                }), 400
                
            logger.info(f"成功验证API密钥有效性")
        except Exception as e:
            logger.error(f"API密钥验证异常: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"API密钥验证异常: {str(e)}"
            }), 400
        
        # 查找是否已存在该邮箱的设置
        setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        if setting:
            # 更新已有记录
            setting.api_key = api_key
            setting.api_secret = api_secret
            setting.permissions = permissions
            setting.updated_at = datetime.now()
            
            db.session.commit()
            logger.info(f"更新子账号 {email} 的API设置")
            
            return jsonify({
                'success': True,
                'message': f"成功更新子账号 {email} 的API设置",
                'data': {
                    'id': setting.id,
                    'email': setting.email,
                    'updated_at': setting.updated_at.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_at else ''
                }
            })
        else:
            # 创建新记录
            new_setting = SubAccountAPISettings(
                email=email,
                api_key=api_key,
                api_secret=api_secret,
                permissions=permissions,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(new_setting)
            db.session.commit()
            logger.info(f"创建子账号 {email} 的API设置")
            
            return jsonify({
                'success': True,
                'message': f"成功保存子账号 {email} 的API设置",
                'data': {
                    'id': new_setting.id,
                    'email': new_setting.email,
                    'created_at': new_setting.created_at.strftime('%Y-%m-%d %H:%M:%S') if new_setting.created_at else ''
                }
            })
    
    except Exception as e:
        db.session.rollback()
        logger.exception(f"保存API设置异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"保存API设置异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-keys/<email>', methods=['DELETE'])
@token_required
def delete_api_key(current_user, email):
    """
    删除子账号API密钥设置
    """
    try:
        # 查找是否存在该邮箱的设置
        setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        if not setting:
            return jsonify({
                'success': False,
                'error': f"未找到子账号 {email} 的API设置"
            }), 404
        
        # 删除记录
        db.session.delete(setting)
        db.session.commit()
        logger.info(f"删除子账号 {email} 的API设置")
        
        return jsonify({
            'success': True,
            'message': f"成功删除子账号 {email} 的API设置"
        })
    
    except Exception as e:
        db.session.rollback()
        logger.exception(f"删除API设置异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"删除API设置异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/diagnose', methods=['POST'])
def diagnose_api():
    """
    诊断子账号API设置和连接问题
    
    请求体:
    {
        "email": "子账号邮箱",
        "api_key": "API密钥(可选)",
        "api_secret": "API密钥(可选)"
    }
    """
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'error': "邮箱不能为空"
            }), 400
        
        # 检查是否提供了API密钥
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        
        # 如果没有提供API密钥，则尝试从数据库获取
        if not api_key or not api_secret:
            # 从数据库获取API设置
            setting = SubAccountAPISettings.query.filter_by(email=email).first()
            
            if not setting or not setting.api_key or not setting.api_secret:
                return jsonify({
                    'success': False,
                    'error': f"未找到子账号 {email} 的有效API设置，请提供API密钥或先保存设置"
                }), 400
                
            api_key = setting.api_key
            api_secret = setting.api_secret
        
        # 开始诊断
        logger.info(f"开始诊断子账号 {email} 的API设置")
        
        # 创建客户端
        client = BinanceClient(api_key, api_secret)
        
        # 测试1: 获取账户信息
        logger.info("测试1: 获取账户信息")
        account_info_result = client.get_account_info()
        test1_success = account_info_result.get('success', False)
        test1_error = account_info_result.get('error', '')
        
        # 测试2: 获取余额
        logger.info("测试2: 获取账户余额")
        balance_result = client.get_account_balance()
        test2_success = balance_result.get('success', False)
        test2_error = balance_result.get('error', '')
        
        # 测试3: 获取交易权限
        logger.info("测试3: 获取交易权限")
        permissions_result = client.check_trade_permission()
        test3_success = permissions_result.get('success', False)
        test3_error = permissions_result.get('error', '')
        
        # 汇总诊断结果
        diagnosis = {
            'email': email,
            'api_key_masked': api_key[:8] + '*' * 8 if api_key else '',
            'tests': [
                {
                    'name': '账户信息',
                    'success': test1_success,
                    'error': test1_error,
                    'details': account_info_result.get('data', {}) if test1_success else {}
                },
                {
                    'name': '账户余额',
                    'success': test2_success,
                    'error': test2_error,
                    'details': balance_result.get('data', {}) if test2_success else {}
                },
                {
                    'name': '交易权限',
                    'success': test3_success,
                    'error': test3_error,
                    'details': permissions_result.get('data', {}) if test3_success else {}
                }
            ],
            'overall_status': '正常' if (test1_success and test2_success) else '异常',
            'suggestions': []
        }
        
        # 根据测试结果提供建议
        if not test1_success:
            if 'Invalid API-key' in str(test1_error):
                diagnosis['suggestions'].append("API密钥无效，请检查是否输入正确")
            elif 'signature' in str(test1_error).lower():
                diagnosis['suggestions'].append("API密钥密码不正确，请重新检查")
            else:
                diagnosis['suggestions'].append(f"账户信息获取失败: {test1_error}")
                
        if not test2_success and test1_success:
            diagnosis['suggestions'].append(f"账户余额获取失败: {test2_error}")
            
        if not test3_success and test1_success:
            if 'permission' in str(test3_error).lower():
                diagnosis['suggestions'].append("API密钥权限不足，请在币安网站上为此API密钥启用交易权限")
            else:
                diagnosis['suggestions'].append(f"交易权限检查失败: {test3_error}")
                
        if test1_success and test2_success and test3_success:
            diagnosis['suggestions'].append("API密钥设置正常，可以正常使用")
        
        return jsonify({
            'success': True,
            'data': diagnosis
        })
    
    except Exception as e:
        logger.exception(f"API诊断异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"API诊断异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/create-api-key', methods=['POST'])
def create_binance_api_key():
    """
    为主账号创建新的API密钥
    
    请求体:
    {
        "user_id": "用户ID",
        "permission_types": ["SPOT", "MARGIN", "FUTURES"] (可选),
        "ip_restriction": "IP限制(可选)"
    }
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': "用户ID不能为空"
            }), 400
            
        # 获取主账号API凭证
        api_key, api_secret = get_main_account_api_credentials(user_id)
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': "未找到有效的主账号API凭证"
            }), 400
            
        # 创建客户端
        client = BinanceClient(api_key, api_secret)
        
        # 准备创建API密钥的参数
        params = {}
        
        # 添加权限
        permission_types = data.get('permission_types', ["SPOT", "FUTURES"])
        if permission_types:
            permissions = ""
            
            if "SPOT" in permission_types:
                permissions += "SPOT"
            if "MARGIN" in permission_types:
                if permissions: permissions += ","
                permissions += "MARGIN"
            if "FUTURES" in permission_types:
                if permissions: permissions += ","
                permissions += "FUTURES"
                
            if permissions:
                params['permissions'] = permissions
        
        # 添加IP限制
        ip_restriction = data.get('ip_restriction')
        if ip_restriction:
            params['ip'] = ip_restriction
            
        # 添加API密钥名称
        api_name = generate_api_name()
        params['name'] = api_name
            
        # 调用创建API密钥的接口
        endpoint = "/sapi/v1/apiBinanceManagement/createBinanceApiKey"
        result = client._send_request('POST', endpoint, params=params, signed=True)
        
        if result.get('success'):
            api_data = result.get('data', {})
            
            return jsonify({
                'success': True,
                'message': "成功创建API密钥",
                'data': {
                    'api_key': api_data.get('apiKey', ''),
                    'api_secret': api_data.get('secretKey', ''),
                    'name': api_name,
                    'permissions': params.get('permissions', '')
                }
            })
        else:
            error_msg = result.get('error', '创建API密钥失败')
            logger.error(f"创建API密钥失败: {error_msg}")
            return jsonify({
                'success': False,
                'error': f"创建API密钥失败: {error_msg}"
            }), 400
    
    except Exception as e:
        logger.exception(f"创建API密钥异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"创建API密钥异常: {str(e)}"
        }), 500


def generate_api_name():
    """生成API密钥名称"""
    timestamp = time.strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"AUTO_CREATED_{timestamp}_{random_suffix}"


@subaccounts_bp.route('/batch-test-keys', methods=['POST'])
def batch_test_api_keys():
    """
    批量测试子账号API密钥
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...]
    }
    """
    try:
        data = request.json
        emails = data.get('emails', [])
        
        if not emails:
            return jsonify({
                'success': False,
                'error': "请提供子账号邮箱列表"
            }), 400
            
        results = []
        
        # 测试每个子账号的API密钥
        for email in emails:
            # 从数据库获取API设置
            setting = SubAccountAPISettings.query.filter_by(email=email).first()
            
            if not setting or not setting.api_key or not setting.api_secret:
                results.append({
                    'email': email,
                    'success': False,
                    'status': 'NOT_CONFIGURED',
                    'message': "未找到API设置"
                })
                continue
                
            # 创建客户端
            client = BinanceClient(setting.api_key, setting.api_secret)
            
            try:
                # 测试API连接
                account_info = client.get_account_info()
                
                if account_info.get('success'):
                    results.append({
                        'email': email,
                        'success': True,
                        'status': 'WORKING',
                        'message': "API密钥工作正常",
                        'account_details': {
                            'makerCommission': account_info.get('data', {}).get('makerCommission'),
                            'takerCommission': account_info.get('data', {}).get('takerCommission'),
                            'canTrade': account_info.get('data', {}).get('canTrade', False),
                            'canDeposit': account_info.get('data', {}).get('canDeposit', False),
                            'canWithdraw': account_info.get('data', {}).get('canWithdraw', False)
                        }
                    })
                else:
                    error_msg = account_info.get('error', '未知错误')
                    
                    status = 'ERROR'
                    if 'Invalid API-key' in str(error_msg):
                        status = 'INVALID_KEY'
                    elif 'signature' in str(error_msg).lower():
                        status = 'INVALID_SECRET'
                    elif 'permission' in str(error_msg).lower():
                        status = 'INSUFFICIENT_PERMISSIONS'
                        
                    results.append({
                        'email': email,
                        'success': False,
                        'status': status,
                        'message': error_msg
                    })
            except Exception as e:
                results.append({
                    'email': email,
                    'success': False,
                    'status': 'ERROR',
                    'message': str(e)
                })
                
        # 汇总结果
        success_count = len([r for r in results if r.get('success')])
        
        return jsonify({
            'success': True,
            'data': {
                'total': len(emails),
                'success_count': success_count,
                'fail_count': len(emails) - success_count,
                'results': results
            }
        })
    
    except Exception as e:
        logger.exception(f"批量测试API密钥异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"批量测试API密钥异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-export', methods=['GET'])
@token_required
def export_api_keys(current_user):
    """
    导出子账号API密钥配置
    
    查询参数:
    - format: 导出格式，可选 'json' 或 'csv'，默认为 'json'
    - include_secret: 是否包含密钥，可选 'true' 或 'false'，默认为 'false'
    """
    try:
        # 获取查询参数
        export_format = request.args.get('format', 'json').lower()
        include_secret = request.args.get('include_secret', 'false').lower() == 'true'
        
        # 获取所有子账号API设置
        api_settings = SubAccountAPISettings.query.all()
        
        # 准备导出数据
        exported_data = []
        for setting in api_settings:
            api_data = {
                'id': setting.id,
                'email': setting.email,
                'api_key': setting.api_key,
                'created_at': setting.created_at.strftime('%Y-%m-%d %H:%M:%S') if setting.created_at else '',
                'updated_at': setting.updated_at.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_at else ''
            }
            
            # 根据参数决定是否包含密钥
            if include_secret:
                api_data['api_secret'] = setting.api_secret
            else:
                api_data['has_secret'] = bool(setting.api_secret)
                
            exported_data.append(api_data)
        
        # 根据请求格式返回不同类型的响应
        if export_format == 'csv':
            # 创建CSV内存文件
            csv_data = io.StringIO()
            
            # 确定CSV字段
            fieldnames = ['id', 'email', 'api_key']
            if include_secret:
                fieldnames.append('api_secret')
            else:
                fieldnames.append('has_secret')
                
            fieldnames.extend(['created_at', 'updated_at'])
            
            # 创建CSV写入器
            writer = csv.DictWriter(csv_data, fieldnames=fieldnames)
            writer.writeheader()
            
            # 写入数据
            for data in exported_data:
                writer.writerow(data)
            
            # 准备响应
            csv_data.seek(0)
            timestamp = time.strftime('%Y%m%d%H%M%S')
            return Response(
                csv_data.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=binance_api_keys_{timestamp}.csv'
                }
            )
        else:  # json格式（默认）
            timestamp = time.strftime('%Y%m%d%H%M%S')
            return Response(
                json.dumps({
                    'success': True,
                    'data': exported_data,
                    'count': len(exported_data),
                    'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'include_secret': include_secret
                }, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename=binance_api_keys_{timestamp}.json'
                }
            )
    
    except Exception as e:
        logger.exception(f"导出API密钥设置异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"导出API密钥设置异常: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-keys/<email>/update', methods=['PUT'])
@token_required
def update_api_key(current_user, email):
    """
    修改子账号API密钥设置
    
    请求体:
    {
        "api_key": "新的API密钥",
        "api_secret": "新的API密钥密码",
        "permissions": "API权限(可选)"
    }
    """
    try:
        data = request.json
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        permissions = data.get('permissions')
        
        # 验证必要参数
        if not email:
            return jsonify({
                'success': False,
                'error': "邮箱不能为空"
            }), 400
        
        # 验证API密钥格式
        is_valid, error_msg = validate_api_key_format(api_key, api_secret)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
        # 验证API密钥
        api_key = api_key.strip()
        api_secret = api_secret.strip()
        
        # 验证API密钥有效性
        try:
            logger.info(f"验证子账号 {email} 的新API密钥有效性")
            client = BinanceClient(api_key, api_secret)
            
            # 尝试获取账户信息，验证API密钥
            test_response = client.get_account_balance()
            
            if not test_response.get('success'):
                error_msg = test_response.get('error', '未知错误')
                logger.error(f"API密钥验证失败: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': f"API密钥验证失败: {error_msg}"
                }), 400
                
            logger.info(f"成功验证API密钥有效性")
        except Exception as e:
            logger.error(f"API密钥验证异常: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"API密钥验证异常: {str(e)}"
            }), 400
        
        # 查找是否存在该邮箱的设置
        setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        if not setting:
            return jsonify({
                'success': False,
                'error': f"未找到子账号 {email} 的API设置"
            }), 404
        
        # 更新记录
        setting.api_key = api_key
        setting.api_secret = api_secret
        
        # 只有在提供了权限时才更新权限
        if permissions:
            setting.permissions = permissions
            
        setting.updated_at = datetime.now()
        
        db.session.commit()
        logger.info(f"更新子账号 {email} 的API设置")
        
        return jsonify({
            'success': True,
            'message': f"成功更新子账号 {email} 的API设置",
            'data': {
                'id': setting.id,
                'email': setting.email,
                'updated_at': setting.updated_at.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_at else '',
                'permissions': setting.permissions
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logger.exception(f"修改子账号API密钥异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"修改子账号API密钥异常: {str(e)}"
        }), 500 