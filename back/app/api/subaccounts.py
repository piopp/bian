import random
import string
import time
import json
import os
import logging
from flask import Blueprint, request, jsonify, session, current_app, send_file
from app.models import db, APIKey
from app.models.account import SubAccountAPISettings
from app.services.binance_client import BinanceClient, get_client_by_email
from app.utils.auth import token_required
import jwt

logger = logging.getLogger(__name__)
subaccounts_bp = Blueprint('subaccounts', __name__,
                           url_prefix='/api/subaccounts')


def get_main_account_api_credentials(user_id=None):
    """
    获取主账号API凭证
    
    参数:
        user_id: 用户ID，如果为None则查找最新的活跃密钥
    返回:
        (api_key, api_secret) 元组
    """
    try:
        query = APIKey.query.filter_by(is_active=True)
        
        # 如果指定了user_id
        if user_id and str(user_id).isdigit():
            query = query.filter_by(user_id=int(user_id))
            
        # 如果是用户名，尝试查找对应的user_id
        elif user_id and not str(user_id).isdigit():
            from app.models.user import User
            user = User.query.filter_by(username=user_id).first()
            if user:
                query = query.filter_by(user_id=user.id)
        
        # 获取最新的一个处于活跃状态的API密钥
        active_api_key = query.order_by(APIKey.created_at.desc()).first()
        
        if active_api_key:
            logger.info(f"从APIKey表获取到主账号API密钥 [user_id={user_id}]")
            return active_api_key.api_key, active_api_key.api_secret
        else:
            logger.warning(f"没有找到主账号的活跃API密钥，将使用默认值")
            # 从环境变量或配置获取默认值
            default_api_key = current_app.config.get('DEFAULT_API_KEY', '')
            default_api_secret = current_app.config.get(
                'DEFAULT_API_SECRET', '')
            return default_api_key, default_api_secret
    except Exception as e:
        logger.error(f"获取主账号API凭证失败: {str(e)}")
        return '', ''


def get_sub_account_api_credentials(email):
    """
    获取子账号API凭证
    
    参数:
        email: 子账号邮箱
    返回:
        (api_key, api_secret) 元组
    """
    try:
        if not email:
            logger.warning("未提供子账号邮箱")
            return '', ''
            
        # 使用email查询API设置
        api_setting = SubAccountAPISettings.query.filter_by(
            email=email).first()
        if api_setting and api_setting.api_key and api_setting.api_secret:
            logger.info(f"从SubAccountAPISettings表获取到子账号API密钥 [email={email}]")
            return api_setting.api_key, api_setting.api_secret
        else:
            logger.warning(
                f"未在SubAccountAPISettings表中找到子账号API密钥 [email={email}]")
            return '', ''
    except Exception as e:
        logger.error(f"获取子账号API凭证失败: {str(e)}")
        return '', ''

# 向下兼容的包装函数，根据参数类型调用正确的API获取函数


def get_api_credentials(user_id=None):
    """
    通过用户ID或邮箱获取API凭证（兼容旧代码）
    
    参数:
        user_id: 用户ID或邮箱
    返回:
        (api_key, api_secret) 元组
    """
    # 判断是主账号还是子账号
    if user_id is None or str(user_id).isdigit():
        # 数字ID被视为主账号
        return get_main_account_api_credentials(user_id)
    else:
        # 邮箱被视为子账号
        return get_sub_account_api_credentials(user_id)


@subaccounts_bp.route('/', methods=['GET'])
def get_subaccounts():
    """
    获取子账号列表
    
    查询参数:
    - page: 页码，默认1
    - limit: 每页数量，默认10
    - user_id: (可选)用户ID或邮箱，如果不提供则尝试从token获取
               可以传入数字ID或邮箱地址，系统会自动处理
    """
    start_time = time.time()
    
    # 尝试从认证令牌获取用户ID
    user_id = None
    token = None
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            # 解码JWT token
            from app.utils.auth import JWT_SECRET
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except Exception as e:
            logger.warning(f"解析token失败: {str(e)}")
    
    # 如果从token中找不到user_id，尝试从请求参数获取
    if not user_id:
        # 尝试获取user_id参数，不转换类型，因为可能是邮箱
        user_id = request.args.get('user_id')
    
    # 获取主账号API凭证
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    logger.info(f"正在获取子账号列表，页码：{page}，每页数量：{limit}，user_id: {user_id}")
    
    client = BinanceClient(api_key, api_secret)
    result = client.get_sub_accounts(page, limit)
    
    # 日志记录API响应时间和结果
    elapsed = time.time() - start_time
    logger.info(f"获取子账号列表API响应时间：{elapsed:.2f}秒")
    
    if result.get('success') and 'data' in result:
        # 规范化数据结构
        if 'subAccounts' in result['data']:
            result['data']['subaccounts'] = result['data'].pop('subAccounts')
            logger.info(f"获取到 {len(result['data']['subaccounts'])} 个子账号")
        else:
            logger.warning(
                f"API返回数据结构中没有subAccounts字段: {list(result['data'].keys())}")
    else:
        error_msg = result.get('error', '未知错误')
        logger.error(f"API请求失败: {error_msg}")
    
    return jsonify(result)


@subaccounts_bp.route('/', methods=['POST'])
def create_subaccount():
    """
    创建新的子账号
    
    请求体:
    {
        "user_id": 用户ID,
        "subaccount_name": "子账号名称"
    }
    """
    # 从请求数据中获取user_id
    data = request.json
    user_id = data.get('user_id')
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    subaccount_name = data.get('subaccount_name', '')
    
    if not subaccount_name:
        return jsonify({
            "success": False, 
            "error": "子账号名称不能为空"
        })
    
    # 验证名称长度
    if len(subaccount_name) > 20:
        return jsonify({
            "success": False, 
            "error": "子账号名称不能超过20个字符"
        })
    
    client = BinanceClient(api_key, api_secret)
    result = client.create_virtual_sub_account(subaccount_name)
    
    return jsonify(result)


@subaccounts_bp.route('/batch-create', methods=['POST'])
def batch_create_subaccounts():
    """
    批量创建子账号
    
    请求体:
    {
        "user_id": 用户ID,
        "prefix": "账号前缀",
        "count": 创建数量
    }
    """
    # 从请求数据中获取user_id
    data = request.json
    user_id = data.get('user_id')
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    prefix = data.get('prefix', 'user_')
    count = data.get('count', 5)
    
    # 验证参数
    if not prefix:
        return jsonify({
            "success": False, 
            "error": "账号前缀不能为空"
        })
    
    if not 1 <= count <= 20:
        return jsonify({
            "success": False, 
            "error": "创建数量必须在1-20之间"
        })
    
    # 生成随机子账号名称列表
    account_names = []
    for _ in range(count):
        # 计算可用的随机字符数量，确保总长度不超过20
        random_length = min(10, 20 - len(prefix))
        if random_length <= 0:
            return jsonify({
                "success": False, 
                "error": "账号前缀过长，无法生成有效的随机账号"
            })
        
        # 生成随机字符串
        random_str = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(random_length))
        account_name = f"{prefix}{random_str}"
        account_names.append(account_name)
    
    # 批量创建子账号
    client = BinanceClient(api_key, api_secret)
    results = []
    
    for name in account_names:
        result = client.create_virtual_sub_account(name)
        results.append({
            "name": name,
            "result": result
        })
    
    # 统计成功和失败的数量
    success_count = sum(1 for r in results if r["result"]["success"]
                        and "data" in r["result"] and "email" in r["result"]["data"])
    
    return jsonify({
        "success": True,
        "total": count,
        "success_count": success_count,
        "fail_count": count - success_count,
        "results": results
    })


@subaccounts_bp.route('/futures/enable', methods=['POST'])
@token_required
def enable_futures(current_user):
    """
    为子账号开通期货交易
    
    请求体:
    {
        "email": "子账号邮箱"
    }
    """
    # 使用当前登录用户的ID
    user_id = current_user.id
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    data = request.json
    email = data.get('email', '')
    
    if not email:
        return jsonify({
            "success": False, 
            "error": "子账号邮箱不能为空"
        })
    
    logger.info(f"正在为子账号 {email} 开通期货交易")
    
    client = BinanceClient(api_key, api_secret)
    result = client.enable_subaccount_futures(email)
    
    if result.get('success'):
        logger.info(f"为子账号 {email} 开通期货交易成功")
    else:
        error_msg = result.get('error', '未知错误')
        logger.error(f"为子账号 {email} 开通期货交易失败: {error_msg}")
    
    return jsonify(result)


@subaccounts_bp.route('/margin/enable', methods=['POST'])
@token_required
def enable_margin(current_user):
    """
    为子账号开通杠杆交易
    
    请求体:
    {
        "email": "子账号邮箱"
    }
    """
    # 使用当前登录用户的ID
    user_id = current_user.id
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    data = request.json
    email = data.get('email', '')
    
    if not email:
        return jsonify({
            "success": False, 
            "error": "子账号邮箱不能为空"
        })
    
    logger.info(f"正在为子账号 {email} 开通杠杆交易")
    
    client = BinanceClient(api_key, api_secret)
    result = client.enable_subaccount_margin(email)
    
    if result.get('success'):
        logger.info(f"为子账号 {email} 开通杠杆交易成功")
    else:
        error_msg = result.get('error', '未知错误')
        logger.error(f"为子账号 {email} 开通杠杆交易失败: {error_msg}")
    
    return jsonify(result)


@subaccounts_bp.route('/batch-enable', methods=['POST'])
@token_required
def batch_enable_feature(current_user):
    """
    批量为子账号开通功能
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "feature": "futures" 或 "margin"
    }
    """
    # 使用当前登录用户的ID
    user_id = current_user.id
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    data = request.json
    emails = data.get('emails', [])
    feature = data.get('feature', '')
    
    if not emails:
        return jsonify({
            "success": False, 
            "error": "请提供子账号邮箱列表"
        })
        
    if feature not in ['futures', 'margin']:
        return jsonify({
            "success": False, 
            "error": "功能类型必须是 'futures' 或 'margin'"
        })
    
    client = BinanceClient(api_key, api_secret)
    results = []
    success_count = 0
    
    for email in emails:
        try:
            if feature == 'futures':
                result = client.enable_subaccount_futures(email)
            else:  # margin
                result = client.enable_subaccount_margin(email)
                
            success = result.get('success', False)
            if success:
                success_count += 1
                
            results.append({
                'email': email,
                'success': success,
                'message': result.get('error', '操作成功') if not success else '操作成功'
            })
        except Exception as e:
            logger.error(f"为子账号 {email} 开通 {feature} 失败: {str(e)}")
            results.append({
                'email': email,
                'success': False,
                'message': f'操作异常: {str(e)}'
            })
    
    return jsonify({
        'success': True,
        'total': len(emails),
        'success_count': success_count,
        'fail_count': len(emails) - success_count,
        'results': results
    })


@subaccounts_bp.route('/transfer', methods=['POST'])
def transfer_funds():
    """
    在主账号和子账号之间转账
    
    请求体:
    {
        "user_id": 用户ID,
        "fromEmail": "源账号邮箱",
        "toEmail": "目标账号邮箱",
        "asset": "资产",
        "amount": 金额
    }
    """
    data = request.json
    user_id = data.get('user_id')
    api_key, api_secret = get_main_account_api_credentials(user_id)
    
    from_email = data.get('fromEmail', '')
    to_email = data.get('toEmail', '')
    asset = data.get('asset', '')
    amount = data.get('amount', 0)
    
    # 验证参数
    if not from_email or not to_email:
        return jsonify({
            "success": False, 
            "error": "源账号和目标账号邮箱不能为空"
        })
    
    if not asset:
        return jsonify({
            "success": False, 
            "error": "资产名称不能为空"
        })
    
    if amount <= 0:
        return jsonify({
            "success": False, 
            "error": "转账金额必须大于0"
        })
    
    logger.info(
        f"正在进行转账: 从 {from_email} 到 {to_email}, 资产: {asset}, 金额: {amount}")
    
    client = BinanceClient(api_key, api_secret)
    result = client.sub_account_transfer(from_email, to_email, asset, amount)
    
    if result.get('success'):
        logger.info(
            f"转账成功: 从 {from_email} 到 {to_email}, 资产: {asset}, 金额: {amount}")
    else:
        error_msg = result.get('error', '未知错误')
        logger.error(f"转账失败: {error_msg}")
    
    return jsonify(result)


@subaccounts_bp.route('/api-export', methods=['GET'])
def export_api_settings():
    """
    导出API设置
    
    查询参数:
    - include_master: 是否包含主账号API设置 (可选，默认为false)
    """
    try:
        # 获取查询参数
        include_master = request.args.get(
            'include_master', 'false').lower() == 'true'
        
        # 从数据库查询所有子账户API设置
        api_settings = SubAccountAPISettings.query.all()
        
        # 只返回邮箱和apiKey，不返回apiSecret
        safe_settings = {}
        for setting in api_settings:
            safe_settings[setting.email] = {
                "apiKey": setting.api_key,
                "hasApiSecret": bool(setting.api_secret)
            }
        
        # 如果需要包含主账号API设置
        if include_master:
            # 获取认证信息
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    # 解码JWT token
                    from app.utils.auth import JWT_SECRET
                    payload = jwt.decode(
                        token, JWT_SECRET, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    
                    # 获取主账号API设置
                    master_api = APIKey.query.filter_by(
                        user_id=user_id, is_active=True).first()
                    if master_api:
                        safe_settings['master_account'] = {
                            "apiKey": master_api.api_key,
                            "hasApiSecret": bool(master_api.api_secret)
                        }
                except Exception as e:
                    logger.error(f"解析token失败: {str(e)}")
        
        return jsonify({
            "success": True,
            "data": safe_settings
        })
    except Exception as e:
        logger.error(f"导出API设置失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"导出API设置失败: {str(e)}"
        }), 500


@subaccounts_bp.route('/api-import', methods=['POST'])
def import_api_settings():
    """
    导入API设置
    
    请求体:
    {
        "settings": {
            "email1@example.com": {"apiKey": "key1", "apiSecret": "secret1"},
            "email2@example.com": {"apiKey": "key2", "apiSecret": "secret2"}
        },
        "is_master_account": false // 是否导入到主账号，默认false
    }
    """
    try:
        data = request.json
        settings = data.get('settings', {})
        is_master_account = data.get('is_master_account', False)
        
        if not settings:
            return jsonify({
                "success": False,
                "error": "没有提供设置数据"
            }), 400
        
        # 导入计数
        import_count = 0
        
        # 如果是导入到主账号
        if is_master_account:
            # 获取token用户信息
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    # 解码JWT token
                    from app.utils.auth import JWT_SECRET
                    payload = jwt.decode(
                        token, JWT_SECRET, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    
                    # 只获取第一个子账号的API设置
                    if settings and len(settings) > 0:
                        # 获取第一个子账号邮箱和API设置
                        email, api_data = next(iter(settings.items()))
                        
                        if not isinstance(api_data, dict):
                            return jsonify({
                                "success": False,
                                "error": "API设置格式无效"
                            }), 400
                            
                        api_key = api_data.get('apiKey', '')
                        api_secret = api_data.get('apiSecret', '')
                        
                        if api_key and api_secret:
                            # 查找现有记录
                            existing = APIKey.query.filter_by(
                                user_id=user_id).first()
                            
                            if existing:
                                # 更新现有记录
                                existing.api_key = api_key
                                existing.api_secret = api_secret
                                existing.is_active = True
                            else:
                                # 创建新记录
                                new_setting = APIKey(
                                    user_id=user_id,
                                    api_key=api_key,
                                    api_secret=api_secret,
                                    is_active=True
                                )
                                db.session.add(new_setting)
                            
                            import_count = 1
                            db.session.commit()
                            
                            return jsonify({
                                "success": True,
                                "message": "主账号API设置导入成功",
                                "count": import_count
                            })
                    
                except Exception as e:
                    logger.error(f"解析token或保存API密钥失败: {str(e)}")
                    return jsonify({
                        "success": False,
                        "error": f"导入主账号API密钥失败: {str(e)}"
                    }), 500
            
            return jsonify({
                "success": False,
                "error": "导入主账号API密钥需要提供有效的认证信息"
            }), 401
        
        # 处理子账号API设置 - 确保保存到SubAccountAPISettings表
        for email, api_data in settings.items():
            if not email or not isinstance(api_data, dict):
                continue
                
            api_key = api_data.get('apiKey', '')
            api_secret = api_data.get('apiSecret', '')
            
            if api_key and api_secret:
                # 查找现有记录
                existing = SubAccountAPISettings.query.filter_by(
                    email=email).first()
                
                if existing:
                    # 更新现有记录
                    existing.api_key = api_key
                    existing.api_secret = api_secret
                else:
                    # 创建新记录
                    new_setting = SubAccountAPISettings(
                        email=email,
                        api_key=api_key,
                        api_secret=api_secret
                    )
                    db.session.add(new_setting)
                
                import_count += 1
        
        # 提交事务
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "子账号API设置导入成功",
            "count": import_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"导入API设置失败: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"导入API设置失败: {str(e)}"
        }), 500
    
    
@subaccounts_bp.route('/futures-balance', methods=['POST'])
def get_futures_balance():
    """
    获取子账号的合约余额信息
    
    请求体:
    {
        "email": "子账号邮箱",
        "userId": "用户ID",
        "asset": "资产类型(可选)"
    }
    """
    try:
        data = request.json
        email = data.get('email')
        user_id = data.get('userId')
        asset = data.get('asset')
        
        if not email:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱"
            }), 400
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "请提供主账号ID"
            }), 400
            
        # 获取主账号API凭证
        api_key, api_secret = get_main_account_api_credentials(user_id)
        
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "获取主账号API凭证失败"
            }), 400
        
        # 创建主账号客户端
        client = BinanceClient(api_key, api_secret)
        
        # 使用主账号API查询子账号合约资产信息
        logger.info(f"使用主账号查询子账号 {email} 的合约余额")
        
        # 方法1: 使用子账号合约账户API
        response = client.get_sub_account_futures_balance(email)
        
        if response.get('success'):
            futures_data = response.get('data', {})
            # 从futures_data中提取余额信息
            assets_data = []
            
            # 尝试获取USDT合约账户信息
            if 'assets' in futures_data:
                assets_data = futures_data.get('assets', [])
            # 尝试获取币本位合约账户
            elif 'futureAccountResp' in futures_data:
                assets_data = futures_data.get(
                    'futureAccountResp', {}).get('assets', [])
            
            # 过滤余额数据
            valid_balances = []
            
            for balance in assets_data:
                # 如果指定了资产类型，只返回该资产的余额
                if asset and balance.get('asset') != asset:
                    continue
                    
                # 转换为浮点数以进行比较
                wallet_balance = float(balance.get('walletBalance', '0'))
                
                # 只返回余额大于0的资产
                if wallet_balance > 0:
                    valid_balances.append({
                        'asset': balance.get('asset', ''),
                        'balance': balance.get('walletBalance', '0'),
                        'availableBalance': balance.get('availableBalance', '0'),
                        'marginBalance': balance.get('marginBalance', '0'),
                        'unrealizedProfit': balance.get('unrealizedProfit', '0')
                    })
            
            # 如果第一个方法没有结果，尝试第二个方法
            if len(valid_balances) == 0:
                logger.info(f"方法1未找到数据，尝试方法2查询子账号 {email} 的合约余额")
                
                # 方法2: 使用子账号资金概览API
                backup_response = client.get_sub_account_futures_summary()
                
                if backup_response.get('success'):
                    summary_data = backup_response.get('data', {})
                    sub_accounts = summary_data.get('subAccountList', [])
                    
                    # 在子账号列表中查找指定email的账号
                    for sub_account in sub_accounts:
                        if sub_account.get('email') == email:
                            # 提取该子账号的合约余额信息
                            total_balance = float(
                                sub_account.get('totalWalletBalance', '0'))
                            
                            if total_balance > 0:
                                valid_balances.append({
                                    'asset': 'USDT',  # 这个API只返回USDT总余额
                                    'balance': str(total_balance),
                                    'availableBalance': sub_account.get('totalAvailableBalance', '0'),
                                    'marginBalance': sub_account.get('totalMarginBalance', '0'),
                                    'unrealizedProfit': sub_account.get('totalUnrealizedProfit', '0')
                                })
            
            # 如果两种方法都没有结果，尝试第三个方法
            if len(valid_balances) == 0 and not asset:
                logger.info(f"方法2未找到数据，尝试方法3查询子账号 {email} 的财务快照")
                
                # 方法3: 使用账户快照API
                third_response = client.get_sub_account_snapshot(
                    email, 'FUTURES', 7)
                
                if third_response.get('success'):
                    snapshot_data = third_response.get('data', {})
                    snapshots = snapshot_data.get('snapshotVos', [])
                    
                    if snapshots and len(snapshots) > 0:
                        # 获取最新的快照
                        latest_snapshot = snapshots[0]
                        snapshot_data = latest_snapshot.get('data', {})
                        
                        # 从快照中提取资产信息
                        if 'assets' in snapshot_data:
                            assets = snapshot_data.get('assets', [])
                            
                            for asset_data in assets:
                                asset_name = asset_data.get('asset')
                                asset_amount = float(
                                    asset_data.get('walletBalance', '0'))
                                
                                if asset_amount > 0:
                                    valid_balances.append({
                                        'asset': asset_name,
                                        'balance': str(asset_amount),
                                        'availableBalance': asset_data.get('availableBalance', '0'),
                                        'unrealizedProfit': '0'  # 快照API可能没有该字段
                                    })
            
            return jsonify({
                "success": True,
                "data": valid_balances
            })
        else:
            error_msg = response.get('error', '获取合约余额失败')
            logger.error(f"获取子账号 {email} 的合约余额失败: {error_msg}")
            
            # 尝试方法2
            logger.info(f"尝试备用方法获取 {email} 的合约余额")
            backup_response = client.get_sub_account_futures_summary()
            
            if backup_response.get('success'):
                summary_data = backup_response.get('data', {})
                sub_accounts = summary_data.get('subAccountList', [])
                valid_balances = []
                
                # 在子账号列表中查找指定email的账号
                for sub_account in sub_accounts:
                    if sub_account.get('email') == email:
                        # 提取该子账号的合约余额信息
                        total_balance = float(
                            sub_account.get('totalWalletBalance', '0'))
                        
                        if total_balance > 0 and (not asset or asset == 'USDT'):
                            valid_balances.append({
                                'asset': 'USDT',  # 这个API只返回USDT总余额
                                'balance': str(total_balance),
                                'availableBalance': sub_account.get('totalAvailableBalance', '0')
                            })
                
                return jsonify({
                    "success": True,
                    "data": valid_balances
                })
            else:
                backup_error = backup_response.get('error', '备用方法也失败')
                logger.error(f"备用方法也失败: {backup_error}")
                return jsonify({
                    "success": False,
                    "error": f"获取合约余额失败: {error_msg}，备用方法也失败: {backup_error}"
                }), 500
            
    except Exception as e:
        logger.exception(f"获取合约余额信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取合约余额信息失败: {str(e)}"
        }), 500
    
    
@subaccounts_bp.route('/futures-positions', methods=['POST'])
def get_futures_positions():
    """
    获取子账号的合约持仓信息
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "symbol": "交易对(可选)"
    }
    """
    start_time = time.time()
    try:
        data = request.json
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        
        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400
            
        results = []
        successful_count = 0
        failed_count = 0

        # 处理每个子账号 - 使用子账号自己的API密钥
        for email in emails:
            logger.info(f"获取子账号 {email} 的合约持仓")

            # 获取子账号的API客户端
            client = get_client_by_email(email)
        
            if not client:
                logger.warning(f"获取子账号 {email} API客户端失败，无法查询持仓")
                results.append({
                    "email": email,
                "success": False,
                    "error": "获取API凭证失败，请先配置子账号API密钥"
                })
                failed_count += 1
                continue

            # 直接使用子账户API获取持仓信息
            # 构建请求参数
            params = {
                'recvWindow': 5000  # 增加接收窗口，提高请求成功率
            }

            # 添加交易对参数（如果有）
            if symbol:
                params['symbol'] = symbol

            # 调用合约API获取持仓信息 - 使用正确的端点
            # 使用v2的API端点获取持仓信息
            endpoint = "fapi/v2/positionRisk"
            logger.info(f"请求合约API获取持仓信息: {endpoint}")
            response = client._send_request(
                'GET', endpoint, signed=True, params=params)

            # 如果v2端点失败，尝试v1端点
            if not response.get('success') and '404' in str(response.get('error', '')):
                logger.warning(f"v2端点失败，尝试v1端点获取持仓")
                endpoint = "fapi/v1/positionRisk"
                response = client._send_request(
                    'GET', endpoint, signed=True, params=params)

            # 如果以上都失败，尝试使用账户端点
            if not response.get('success') and ('404' in str(response.get('error', '')) or '<!DOCTYPE html>' in str(response.get('error', ''))):
                logger.warning(f"尝试通过账户信息端点获取持仓")
                endpoint = "fapi/v2/account"
                account_response = client._send_request(
                    'GET', endpoint, signed=True, params=params)

                if account_response.get('success'):
                    # 从账户信息中提取持仓
                    account_data = account_response.get('data', {})
                    positions_data = account_data.get('positions', [])
                    response = {
                        'success': True,
                        'data': positions_data
                    }
            
            if response.get('success'):
                positions_data = response.get('data', [])
                # 处理持仓数据，只保留有真实持仓(持仓数量不为0)的记录
                valid_positions = []
                
                for position in positions_data:
                    # 过滤掉空仓位 (positionAmt为0)
                    position_amt = float(position.get('positionAmt', '0'))
                    
                    if position_amt != 0:
                        # 格式化数据
                        entry_price = position.get('entryPrice', '0')
                        mark_price = position.get('markPrice', '0')
                        
                        formatted_position = {
                            'symbol': position.get('symbol', ''),
                            'positionAmt': str(position_amt),
                            'entryPrice': entry_price,
                            'markPrice': mark_price,
                            'unRealizedProfit': position.get('unRealizedProfit', '0'),
                            'liquidationPrice': position.get('liquidationPrice', '0'),
                            'leverage': position.get('leverage', '1'),
                            'marginType': position.get('marginType', 'isolated'),
                            'side': '多头' if position_amt > 0 else '空头',
                        }
                        
                        # 计算收益率
                        try:
                            entry_price_float = float(entry_price)
                            mark_price_float = float(mark_price)
                            
                            if entry_price_float > 0 and position_amt != 0:
                                if position_amt > 0:  # 多头
                                    pnl_percentage = (
                                        (mark_price_float - entry_price_float) / entry_price_float) * 100
                                else:  # 空头
                                    pnl_percentage = (
                                        (entry_price_float - mark_price_float) / entry_price_float) * 100
                                
                                formatted_position['pnlPercentage'] = pnl_percentage
                            else:
                                formatted_position['pnlPercentage'] = 0
                        except Exception as e:
                            formatted_position['pnlPercentage'] = 0
                            logger.error(f"计算收益率异常: {str(e)}")
                        
                        valid_positions.append(formatted_position)
                
                results.append({
                    "email": email,
                    "success": True,
                    "positions": valid_positions,
                    "count": len(valid_positions)
                })
                successful_count += 1
            else:
                error_msg = response.get('error', '获取持仓信息失败')
                logger.error(f"获取子账号 {email} 持仓失败: {error_msg}")

                # 提供更友好的错误信息
                user_error = error_msg

                # 检查是否是Web页面而不是API响应
                if '<!DOCTYPE html>' in str(error_msg) or '<html>' in str(error_msg):
                    user_error = "收到了网页而不是API响应，API的URL可能不正确或币安服务器返回了错误页面"
                    logger.error(f"收到HTML响应而非API数据: {str(error_msg)[:200]}...")
                # 常见错误类型处理
                elif '404' in str(error_msg):
                    user_error = "API端点不存在(404)，请检查网络连接或联系支持团队"
                elif 'Invalid API-key' in str(error_msg):
                    user_error = "API密钥无效，请更新API设置"
                elif 'signature' in str(error_msg).lower():
                    user_error = "API签名验证失败，请检查API密钥设置是否正确"
                elif 'permission' in str(error_msg).lower():
                    user_error = "API权限不足，请确保启用了读取权限"
                elif '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                    user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"

                results.append({
                    "email": email,
                    "success": False,
                    "error": user_error
                })
                failed_count += 1
        
        total_time = time.time() - start_time
        return jsonify({
            "success": True,
            "data": results,
            "summary": {
                "total": len(emails),
                "successful": successful_count,
                "failed": failed_count
            },
            "processingTime": round(total_time, 2)
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"获取合约持仓信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取合约持仓信息失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500


@subaccounts_bp.route('/futures-limit-orders', methods=['POST'])
def get_futures_limit_orders():
    """
    获取子账号的合约限价单(当前挂单)

    注意：根据币安官方文档，必须使用子账号自己的API密钥查询其订单，
    母账号API无法查询子账号订单
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "symbol": "交易对(可选)",
        "recvWindow": 接收窗口时间(可选，默认5000)
    }
    """
    start_time = time.time()
    try:
        data = request.json
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        recv_window = data.get('recvWindow', 5000)

        logger.info(f"正在获取子账号合约限价单，邮箱数量：{len(emails)}，交易对：{symbol or '所有'}")
        
        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400
        
        if len(emails) > 10:
            logger.warning(f"请求查询的子账号数量过多: {len(emails)}，可能需要较长时间处理")
        
        results = []
        successful_count = 0
        failed_count = 0

        # 处理每个子账号 - 使用子账号自己的API密钥
        for email in emails:
            email_start_time = time.time()

            # 获取子账号的API客户端
            logger.info(f"使用子账号 {email} 自身的API查询合约挂单")
            client = get_client_by_email(email)
            
            if not client:
                logger.warning(f"获取子账号 {email} API客户端失败，无法查询挂单")
                results.append({
                        "email": email,
                        "success": False,
                    "error": "获取API凭证失败，请先配置子账号API密钥"
                    })
                failed_count += 1
                continue
                
            # 构建查询参数
            params = {
                'recvWindow': recv_window
            }
            # 添加可选参数
            if symbol:
                params['symbol'] = symbol
            
            # 直接调用子账号客户端获取当前挂单
            endpoint = "/fapi/v1/openOrders"
            response = client._send_request(
                'GET', endpoint, signed=True, params=params)
            
            # 处理响应
            if response.get('success'):
                orders_data = response.get('data', [])
                # 格式化订单数据
                formatted_orders = []
                
                for order in orders_data:
                    # 获取关键状态文本的中文翻译
                    status_text = order.get('status', '')
                    status_zh = {
                        'NEW': '新建',
                        'PARTIALLY_FILLED': '部分成交',
                        'FILLED': '全部成交',
                        'CANCELED': '已取消',
                        'REJECTED': '已拒绝',
                        'EXPIRED': '已过期'
                    }.get(status_text, status_text)

                    formatted_order = {
                        'orderId': order.get('orderId', ''),
                        '订单编号': order.get('orderId', ''),
                        'symbol': order.get('symbol', ''),
                        'status': order.get('status', ''),
                        '状态': status_zh,
                        'price': order.get('price', '0'),
                        'origQty': order.get('origQty', '0'),
                        'executedQty': order.get('executedQty', '0'),
                        '已成交量': order.get('executedQty', '0'),
                        'type': order.get('type', 'LIMIT'),
                        'side': order.get('side', ''),
                        '方向': '开多' if order.get('side') == 'BUY' else '开空' if order.get('side') == 'SELL' else '',
                        'time': order.get('time', 0),
                        'updateTime': order.get('updateTime', 0),
                        'reduceOnly': order.get('reduceOnly', False),
                        'positionSide': order.get('positionSide', 'BOTH'),
                        'workingType': order.get('workingType', 'CONTRACT_PRICE'),
                        'priceProtect': order.get('priceProtect', False),
                    }
                    
                    formatted_orders.append(formatted_order)
                
                processing_time = time.time() - email_start_time
                logger.info(
                    f"成功获取子账号 {email} 的挂单列表: {len(formatted_orders)}个，耗时: {processing_time:.2f}秒")
                results.append({
                    "email": email,
                    "success": True,
                    "orders": formatted_orders,
                    "count": len(formatted_orders),
                    "processingTime": round(processing_time, 2)
                })
                successful_count += 1
            else:
                error_msg = response.get('error', '获取挂单信息失败')
                logger.error(f"获取子账号 {email} 合约挂单失败: {error_msg}")

                # 提供更友好的错误信息
                user_error = error_msg
                if '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                    user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
                elif 'Invalid API-key' in str(error_msg):
                    user_error = "API密钥无效，请更新API设置"
                elif 'signature' in str(error_msg).lower():
                    user_error = "API签名验证失败，请检查API密钥设置是否正确"
                elif 'permission' in str(error_msg).lower():
                    user_error = "API权限不足，需要启用读取权限"

                results.append({
                    "email": email,
                    "success": False,
                    "error": user_error
                })
                failed_count += 1

        total_time = time.time() - start_time
        logger.info(
            f"获取所有子账号({len(emails)})合约挂单完成，成功: {successful_count}，失败: {failed_count}，总耗时: {total_time:.2f}秒")

        return jsonify({
            "success": True,
            "data": results,
            "summary": {
                "total": len(emails),
                "successful": successful_count,
                "failed": failed_count
            },
            "processingTime": round(total_time, 2)
        })

    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"获取合约挂单信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取合约挂单信息失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500


@subaccounts_bp.route('/api-diagnose', methods=['POST'])
def diagnose_api_settings():
    """
    诊断子账号API设置问题
    
    请求体:
    {
        "email": "子账号邮箱(可选，不提供则诊断所有子账号)"
    }
    """
    try:
        data = request.json or {}
        email = data.get('email')
        
        if email:
            # 诊断特定子账号
            try:
                # 获取子账号API密钥
                api_key, api_secret = get_sub_account_api_credentials(email)
                if not api_key or not api_secret:
                    return jsonify({
                        "success": False,
                        "error": f"子账号 {email} 未配置API密钥"
                    }), 400
        
                # 创建客户端
                client = BinanceClient(api_key, api_secret)
                
                # 测试API权限
                account_result = client._send_request('GET', '/fapi/v2/account', signed=True)
                position_result = client._send_request('GET', '/fapi/v2/positionRisk', signed=True)
                order_result = client._send_request('GET', '/fapi/v1/openOrders', signed=True)
                
                diagnosis = {
                    "api_configured": True,
                    "account_access": account_result.get('success', False),
                    "position_access": position_result.get('success', False),
                    "order_access": order_result.get('success', False),
                    "overall_status": "正常" if (account_result.get('success', False) and 
                                              order_result.get('success', False)) else "异常",
                    "error_details": {}
                }
                
                # 收集错误信息
                if not account_result.get('success', False):
                    diagnosis["error_details"]["account_error"] = account_result.get('error', '未知错误')
                if not position_result.get('success', False):
                    diagnosis["error_details"]["position_error"] = position_result.get('error', '未知错误')
                if not order_result.get('success', False):
                    diagnosis["error_details"]["order_error"] = order_result.get('error', '未知错误')
                
                return jsonify({
                    "success": True,
                    "data": {
                        "email": email,
                        "diagnosis": diagnosis
                    }
                })
                
            except Exception as e:
                logger.exception(f"诊断子账号 {email} API失败: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"诊断子账号API失败: {str(e)}"
                }), 500
        else:
            # 获取所有子账号API设置
            api_settings = SubAccountAPISettings.query.all()
            
            results = []
            for setting in api_settings:
                email = setting.email
                api_key = setting.api_key
                api_secret = setting.api_secret
                
                if not api_key or not api_secret:
                    results.append({
                        "email": email,
                        "diagnosis": {
                            "api_configured": False,
                            "overall_status": "未配置API",
                            "account_access": False,
                            "position_access": False,
                            "order_access": False
                        }
                    })
                    continue
                
                try:
                    # 创建客户端
                    client = BinanceClient(api_key, api_secret)
                    
                    # 测试API权限
                    account_result = client._send_request('GET', '/fapi/v2/account', signed=True)
                    position_result = client._send_request('GET', '/fapi/v2/positionRisk', signed=True)
                    order_result = client._send_request('GET', '/fapi/v1/openOrders', signed=True)
                    
                    diagnosis = {
                        "api_configured": True,
                        "account_access": account_result.get('success', False),
                        "position_access": position_result.get('success', False),
                        "order_access": order_result.get('success', False),
                        "overall_status": "正常" if (account_result.get('success', False) and 
                                                    order_result.get('success', False)) else "异常",
                        "error_details": {}
                    }
                    
                    # 收集错误信息
                    if not account_result.get('success', False):
                        diagnosis["error_details"]["account_error"] = account_result.get('error', '未知错误')
                    if not position_result.get('success', False):
                        diagnosis["error_details"]["position_error"] = position_result.get('error', '未知错误')
                    if not order_result.get('success', False):
                        diagnosis["error_details"]["order_error"] = order_result.get('error', '未知错误')
                    
                    results.append({
                        "email": email,
                        "diagnosis": diagnosis
                    })
                    
                except Exception as e:
                    logger.exception(f"诊断子账号 {email} API失败: {str(e)}")
                    results.append({
                        "email": email,
                        "diagnosis": {
                            "api_configured": True,
                            "overall_status": "异常",
                            "account_access": False,
                            "position_access": False,
                            "order_access": False,
                            "error": str(e)
                        }
            })
        
        return jsonify({
            "success": True,
            "data": results
        })
        
    except Exception as e:
        logger.exception(f"诊断所有子账号API失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"诊断所有子账号API失败: {str(e)}"
        }), 500

@subaccounts_bp.route('/test-master-api', methods=['POST'])
def test_master_api():
    """
    测试主账号API访问子账号数据的功能
    
    请求体:
    {
        "email": "子账号邮箱(可选，不提供则测试所有子账号)",
        "symbol": "交易对(可选，默认为BTCUSDT)"
    }
    """
    try:
        data = request.json or {}
        email = data.get('email')
        symbol = data.get('symbol', 'BTCUSDT')
        
        # 获取主账号API凭证
        api_key, api_secret = get_main_account_api_credentials()
            
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "主账号API未配置"
            }), 400
            
        # 创建主账号客户端
        client = BinanceClient(api_key, api_secret)
        
        # 测试主账号API访问子账号数据
        results = {}
        
        # 首先测试获取子账号列表
        sub_accounts_result = client.get_sub_accounts()
        results["sub_accounts"] = {
            "success": sub_accounts_result.get('success', False),
            "count": len(sub_accounts_result.get('data', {}).get('subaccounts', [])) if sub_accounts_result.get('success', False) else 0,
            "error": sub_accounts_result.get('error', None)
        }
        
        # 如果指定了email，测试访问特定子账号数据
        if email:
            # 测试获取子账号状态
            status_result = client.get_subaccount_status(email)
            results["status"] = {
                "success": status_result.get('success', False),
                "error": status_result.get('error', None)
            }
            
            # 测试获取子账号合约账户
            futures_balance_result = client.get_sub_account_futures_balance(email)
            results["futures_balance"] = {
                "success": futures_balance_result.get('success', False),
                "error": futures_balance_result.get('error', None)
            }
            
            # 测试获取子账号合约持仓
            futures_positions_result = client.get_sub_account_futures_positions(email, symbol)
            results["futures_positions"] = {
                "success": futures_positions_result.get('success', False),
                "error": futures_positions_result.get('error', None)
            }
            
            # 测试获取子账号合约挂单
            futures_orders_result = client.get_sub_account_futures_open_orders(email, symbol)
            results["futures_orders"] = {
                "success": futures_orders_result.get('success', False),
                "error": futures_orders_result.get('error', None)
            }
        
        # 测试获取所有子账号合约汇总
        futures_summary_result = client.get_sub_account_futures_summary()
        results["futures_summary"] = {
            "success": futures_summary_result.get('success', False),
            "error": futures_summary_result.get('error', None)
        }
        
        # 计算整体成功率
        success_count = sum(1 for key, value in results.items() if value.get('success', False))
        total_count = len(results)
        
        overall_status = {
            "success_rate": f"{success_count}/{total_count}",
            "overall_status": "正常" if success_count == total_count else "部分正常" if success_count > 0 else "异常"
        }
        
        return jsonify({
            "success": True,
            "data": {
                "overall": overall_status,
                "tests": results
            }
        })
        
    except Exception as e:
        logger.exception(f"测试主账号API访问失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"测试主账号API访问失败: {str(e)}"
        }), 500

@subaccounts_bp.route('/batch-close', methods=['POST'])
def batch_close_positions():
    """
    批量平仓子账号的持仓
    
    请求体:
    {
        "positions": [
            {
                "email": "子账号邮箱",
                "symbol": "交易对",
                "positionAmt": "持仓数量",
                "side": "方向" // 多头或空头
            }
        ]
    }
    
    或者：
    {
        "emails": ["子账号邮箱1", "子账号邮箱2"...],
        "symbol": "交易对",
        "closeType": "ALL" // 全部平仓
    }
    """
    try:
        data = request.json
        positions = data.get('positions', [])
        
        # 支持前端直接传递emails、symbol和closeType的格式
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        close_type = data.get('closeType')
        
        # 如果使用第二种格式（emails + symbol），则转换为第一种格式（positions数组）
        if not positions and emails and symbol:
            logger.info(f"使用emails+symbol格式请求平仓: emails={emails}, symbol={symbol}, closeType={close_type}")
            
            # 为每个email创建一个position对象
            for email in emails:
                # 不需要position_amount和side，将由后续代码通过API查询获取
                positions.append({
                    "email": email,
                    "symbol": symbol,
                    "close_all": close_type == "ALL"
                })
        
        if not positions:
            return jsonify({
                "success": False,
                "error": "没有提供持仓信息"
            }), 400
        
        results = []
        
        # 处理每个持仓
        for position in positions:
            email = position.get('email')
            symbol = position.get('symbol')
            position_amount = position.get('positionAmt')
            side = position.get('side')
            close_all = position.get('close_all', False)
            
            # 验证参数
            if not email or not symbol:
                results.append({
                    "email": email,
                    "symbol": symbol,
                    "success": False,
                    "error": "邮箱或交易对不能为空"
                })
                continue
                
            api_key, api_secret = get_sub_account_api_credentials(email)
            
            if not api_key or not api_secret:
                    results.append({
                        "email": email,
                        "symbol": symbol,
                        "success": False,
                        "error": "未找到有效的API密钥"
                    })
                    continue
                # 创建客户端
            client = BinanceClient(api_key, api_secret)
            
            # 如果设置了close_all或者没有提供position_amount，则查询当前持仓信息
            if close_all or not position_amount:
                # 查询持仓
                params = {
                    'symbol': symbol,
                    'recvWindow': 5000
                }
                position_response = client._send_request('GET', 'fapi/v2/positionRisk', signed=True, params=params)
                
                if not position_response.get('success'):
                    # 尝试使用v1端点
                    position_response = client._send_request('GET', 'fapi/v1/positionRisk', signed=True, params=params)
                
                if position_response.get('success'):
                    positions_data = position_response.get('data', [])
                    
                    # 找到对应symbol的持仓
                    target_position = None
                    for pos in positions_data:
                        if pos.get('symbol') == symbol and float(pos.get('positionAmt', '0')) != 0:
                            target_position = pos
                            break
                    
                    if target_position:
                        position_amount = target_position.get('positionAmt', '0')
                        side = '多头' if float(position_amount) > 0 else '空头'
                    else:
                        results.append({
                            "email": email,
                            "symbol": symbol,
                            "success": False,
                            "error": f"未找到{symbol}的有效持仓"
                        })
                        continue
                else:
                    results.append({
                        "email": email,
                        "symbol": symbol,
                        "success": False,
                        "error": f"查询持仓失败: {position_response.get('error', '未知错误')}"
                    })
                    continue
                
                # 计算平仓订单参数
                # 如果是多头，则需要卖出相同数量
                # 如果是空头，则需要买入相同数量
                close_side = "SELL" if side == "多头" or side == "BUY" or float(position_amount) > 0 else "BUY"
                close_quantity = abs(float(position_amount))
                
                if close_quantity <= 0:
                    results.append({
                        "email": email,
                        "symbol": symbol,
                        "success": False,
                        "error": "持仓数量必须大于0"
                    })
                    continue
                
                # 发送市价平仓订单
                order_params = {
                    "symbol": symbol,
                    "side": close_side,
                    "type": "MARKET",
                    "quantity": close_quantity,
                    "reduceOnly": True,  # 确保这是平仓单
                    "timestamp": int(time.time() * 1000)
                }
                
                # 执行下单
                endpoint = "/fapi/v1/order"
                response = client._send_request('POST', endpoint, signed=True, params=order_params)
                
                if response.get('success'):
                    results.append({
                        "email": email,
                        "symbol": symbol,
                        "success": True,
                        "order_id": response.get('data', {}).get('orderId'),
                        "message": "平仓成功"
                    })
                else:
                    results.append({
                        "email": email,
                        "symbol": symbol,
                        "success": False,
                        "error": response.get('error', '平仓失败')
                    })
                    
        
        # 计算成功率
        success_count = len([r for r in results if r.get('success')])
        
        return jsonify({
            "success": True,
            "data": {
                "total": len(positions),
                "success_count": success_count,
                "fail_count": len(positions) - success_count,
                "results": results
            }
        })
        
    except Exception as e:
        logger.exception(f"批量平仓失败: {str(e)}")
        return jsonify({
                    "success": False,
            "error": f"批量平仓失败: {str(e)}"
        }), 500

@subaccounts_bp.route('/cancel-order', methods=['POST'])
def cancel_futures_order():
    """
    取消子账号的合约订单
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对，例如BTCUSDT",
        "orderId": 订单ID(可选，与clientOrderId二选一),
        "clientOrderId": 客户端订单ID(可选，与orderId二选一)
    }
    """
    start_time = time.time()
    try:
        data = request.json
        email = data.get('email')
        symbol = data.get('symbol')
        order_id = data.get('orderId')
        client_order_id = data.get('clientOrderId')
        
        logger.info(f"正在取消子账号 {email} 的合约订单，交易对：{symbol}，订单ID：{order_id or client_order_id}")
            
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
            
        if not order_id and not client_order_id:
            return jsonify({
                "success": False,
                "error": "请提供订单ID或客户端订单ID"
            }), 400
            
        # 获取子账号的API客户端
        client = get_client_by_email(email)
        
        if not client:
            logger.warning(f"获取子账号 {email} API客户端失败，无法取消订单")
            return jsonify({
                "success": False,
                "error": "获取API凭证失败，请先配置子账号API密钥"
            }), 400
        
        # 构建请求参数
        params = {
            'symbol': symbol,
            'recvWindow': 5000  # 增加接收窗口，提高请求成功率
        }
        
        # 添加订单标识符
        if order_id:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        
        # 调用API取消订单
        endpoint = "fapi/v1/order"  # 合约取消订单的端点
        response = client._send_request('DELETE', endpoint, signed=True, params=params)
        
        # 处理响应
        if response.get('success'):
            order_data = response.get('data', {})
            # 精简日志输出，避免控制台过于冗余
            logger.info(f"成功取消子账号 {email} 的订单，ID: {order_data.get('orderId')}")
            
            # 格式化响应数据
            status_text = order_data.get('status', '')
            status_zh = {
                'NEW': '新建',
                'PARTIALLY_FILLED': '部分成交',
                'FILLED': '全部成交',
                'CANCELED': '已取消',
                'REJECTED': '已拒绝',
                'EXPIRED': '已过期'
            }.get(status_text, status_text)
            
            # 构建格式化的订单信息
            formatted_order = {
                'orderId': order_data.get('orderId', ''),
                '订单编号': order_data.get('orderId', ''),
                'symbol': order_data.get('symbol', ''),
                'status': order_data.get('status', ''),
                '状态': status_zh,
                'price': order_data.get('price', '0'),
                'origQty': order_data.get('origQty', '0'),
                'executedQty': order_data.get('executedQty', '0'),
                '成交量': order_data.get('executedQty', '0'),
                'type': order_data.get('type', ''),
                'side': order_data.get('side', ''),
                '方向': '开多' if order_data.get('side') == 'BUY' else '开空' if order_data.get('side') == 'SELL' else '',
                'time': order_data.get('time', 0),
                'updateTime': order_data.get('updateTime', 0),
            }
            
            total_time = time.time() - start_time
            return jsonify({
                "success": True,
                "message": "订单取消成功",
                "data": formatted_order,
                "processingTime": round(total_time, 2)
            })
        else:
            error_msg = response.get('error', '取消订单失败')
            logger.error(f"取消子账号 {email} 订单失败: {error_msg}")
            
            # 提供更友好的错误信息
            user_error = error_msg
            if 'Order does not exist' in str(error_msg):
                user_error = "订单不存在，可能已经被取消或者已经成交"
            elif 'Invalid API-key' in str(error_msg):
                user_error = "API密钥无效，请更新API设置"
            elif 'signature' in str(error_msg).lower():
                user_error = "API签名验证失败，请检查API密钥设置是否正确"
            elif 'permission' in str(error_msg).lower():
                user_error = "API权限不足，请确保启用了交易权限"
            elif '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
            
            total_time = time.time() - start_time
            return jsonify({
                "success": False,
                "error": user_error,
                "processingTime": round(total_time, 2)
            }), 400
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"取消订单处理过程异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"取消订单处理异常: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500

@subaccounts_bp.route('/cancel-all-orders', methods=['POST'])
def cancel_all_futures_orders():
    """
    取消子账号的所有合约订单
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对，例如BTCUSDT"
    }
    """
    start_time = time.time()
    try:
        data = request.json
        email = data.get('email')
        symbol = data.get('symbol')
        
        logger.info(f"正在取消子账号 {email} 的所有合约订单，交易对：{symbol}")
        
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
            
        # 获取子账号的API客户端
        client = get_client_by_email(email)
            
        if not client:
            logger.warning(f"获取子账号 {email} API客户端失败，无法取消订单")
            return jsonify({
                "success": False,
                "error": "获取API凭证失败，请先配置子账号API密钥"
            }), 400
        
        # 构建请求参数
        params = {
            'symbol': symbol,
            'recvWindow': 5000  # 增加接收窗口，提高请求成功率
        }
        
        # 调用API取消所有订单
        endpoint = "fapi/v1/allOpenOrders"  # 取消所有开放订单的端点
        response = client._send_request('DELETE', endpoint, signed=True, params=params)
        
        # 处理响应
        if response.get('success'):
            # 成功响应通常是一个{}对象或一个消息
            # 精简日志输出
            logger.info(f"成功取消子账号 {email} 的所有{symbol}订单")
            
            total_time = time.time() - start_time
            return jsonify({
                "success": True,
                "message": f"成功取消子账号 {email} 的所有{symbol}订单",
                "processingTime": round(total_time, 2)
            })
        else:
            error_msg = response.get('error', '取消所有订单失败')
            logger.error(f"取消子账号 {email} 所有订单失败: {error_msg}")
            
            # 提供更友好的错误信息
            user_error = error_msg
            if 'No open orders' in str(error_msg) or 'Order does not exist' in str(error_msg):
                user_error = "没有可取消的开放订单"
            elif 'Invalid API-key' in str(error_msg):
                user_error = "API密钥无效，请更新API设置"
            elif 'signature' in str(error_msg).lower():
                user_error = "API签名验证失败，请检查API密钥设置是否正确"
            elif 'permission' in str(error_msg).lower():
                user_error = "API权限不足，请确保启用了交易权限"
            elif '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
            
            total_time = time.time() - start_time
            return jsonify({
                "success": False,
                "error": user_error,
                "processingTime": round(total_time, 2)
            }), 400
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"取消所有订单处理过程异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"取消所有订单处理异常: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500

@subaccounts_bp.route('/futures-orders', methods=['POST'])
def get_futures_orders():
    """
    获取子账号的合约订单历史（包括市价单）
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "symbol": "交易对(可选)",
        "limit": 最大返回数量(可选，默认500),
        "startTime": 开始时间戳(可选),
        "endTime": 结束时间戳(可选),
        "recvWindow": 接收窗口时间(可选，默认5000)
    }
    """
    start_time = time.time()
    try:
        data = request.json
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        limit = data.get('limit', 500)
        start_timestamp = data.get('startTime')
        end_timestamp = data.get('endTime')
        recv_window = data.get('recvWindow', 5000)

        logger.info(f"正在获取子账号合约订单历史，邮箱数量：{len(emails)}，交易对：{symbol or '所有'}")

        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400

        results = []
        successful_count = 0
        failed_count = 0

        # 处理每个子账号 - 使用子账号自己的API密钥
        for email in emails:
            email_start_time = time.time()

            # 获取子账号的API客户端
            logger.info(f"使用子账号 {email} 自身的API查询合约订单历史")
            client = get_client_by_email(email)

            if not client:
                logger.warning(f"获取子账号 {email} API客户端失败，无法查询订单历史")
                results.append({
                    "email": email,
                    "success": False,
                "error": "获取API凭证失败，请先配置子账号API密钥"
                })
                failed_count += 1
                continue
                
            # 构建查询参数
            params = {
                'recvWindow': recv_window,
                'limit': limit
            }

            # 添加可选参数
            if symbol:
                    params['symbol'] = symbol
            if start_timestamp:
                params['startTime'] = start_timestamp
            if end_timestamp:
                params['endTime'] = end_timestamp
                
            # 调用API获取订单历史
            endpoint = "/fapi/v1/allOrders"
            response = client._send_request('GET', endpoint, signed=True, params=params)
            
            # 处理响应
            if response.get('success'):
                orders_data = response.get('data', [])
                # 格式化订单数据
                formatted_orders = []
                
                for order in orders_data:
                    # 获取关键状态文本的中文翻译
                    status_text = order.get('status', '')
                    status_zh = {
                        'NEW': '新建',
                        'PARTIALLY_FILLED': '部分成交',
                        'FILLED': '全部成交',
                        'CANCELED': '已取消',
                        'REJECTED': '已拒绝',
                        'EXPIRED': '已过期'
                    }.get(status_text, status_text)

                    formatted_order = {
                        'orderId': order.get('orderId', ''),
                        '订单编号': order.get('orderId', ''),
                        'symbol': order.get('symbol', ''),
                        'status': order.get('status', ''),
                        '状态': status_zh,
                        'price': order.get('price', '0'),
                        'origQty': order.get('origQty', '0'),
                        'executedQty': order.get('executedQty', '0'),
                        '已成交量': order.get('executedQty', '0'),
                        'type': order.get('type', 'LIMIT'),
                        'side': order.get('side', ''),
                        '方向': '开多' if order.get('side') == 'BUY' else '开空' if order.get('side') == 'SELL' else '',
                        'time': order.get('time', 0),
                        'updateTime': order.get('updateTime', 0),
                        'reduceOnly': order.get('reduceOnly', False),
                        'positionSide': order.get('positionSide', 'BOTH'),
                        'avgPrice': order.get('avgPrice', '0'),
                        'cumQuote': order.get('cumQuote', '0'),
                        'workingType': order.get('workingType', 'CONTRACT_PRICE'),
                        'timeInForce': order.get('timeInForce', 'GTC'),
                    }
                    
                    formatted_orders.append(formatted_order)
                
                processing_time = time.time() - email_start_time
                logger.info(
                    f"成功获取子账号 {email} 的订单历史: {len(formatted_orders)}个，耗时: {processing_time:.2f}秒")
                results.append({
                    "email": email,
                    "success": True,
                    "orders": formatted_orders,
                    "count": len(formatted_orders),
                    "processingTime": round(processing_time, 2)
                })
                successful_count += 1
            else:
                error_msg = response.get('error', '获取订单历史失败')
                logger.error(f"获取子账号 {email} 合约订单历史失败: {error_msg}")

                # 提供更友好的错误信息
                user_error = error_msg
                if '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                    user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
                elif 'Invalid API-key' in str(error_msg):
                    user_error = "API密钥无效，请更新API设置"
                elif 'signature' in str(error_msg).lower():
                    user_error = "API签名验证失败，请检查API密钥设置是否正确"
                elif 'permission' in str(error_msg).lower():
                    user_error = "API权限不足，需要启用读取权限"

                results.append({
                    "email": email,
                    "success": False,
                    "error": user_error
                })
                failed_count += 1

        total_time = time.time() - start_time
        logger.info(
            f"获取所有子账号({len(emails)})合约订单历史完成，成功: {successful_count}，失败: {failed_count}，总耗时: {total_time:.2f}秒")
        
        return jsonify({
            "success": True,
            "data": results,
            "summary": {
                "total": len(emails),
                "successful": successful_count,
                "failed": failed_count
            },
            "processingTime": round(total_time, 2)
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"获取合约订单历史失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取合约订单历史失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500

@subaccounts_bp.route('/futures-trades', methods=['POST'])
def get_futures_trades():
    """
    获取子账号的合约历史成交记录（包含手续费信息）
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "symbol": "交易对(必须提供)",
        "limit": 最大返回数量(可选，默认500),
        "fromId": 起始成交ID(可选),
        "startTime": 开始时间戳(可选),
        "endTime": 结束时间戳(可选),
        "recvWindow": 接收窗口时间(可选，默认5000)
    }
    
    注意：
    - 如果startTime和endTime均未提供，只会返回最近7天的数据
    - startTime和endTime的最大间隔为7天
    - 本接口仅支持最近6个月历史交易的查询
    """
    start_time = time.time()
    try:
        data = request.json
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        limit = data.get('limit', 500)
        from_id = data.get('fromId')
        start_timestamp = data.get('startTime')
        end_timestamp = data.get('endTime')
        recv_window = data.get('recvWindow', 5000)

        logger.info(f"正在获取子账号合约历史成交记录，邮箱数量：{len(emails)}，交易对：{symbol or '无'}")

        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400
            
        if not symbol:
            return jsonify({
                "success": False,
                "error": "交易对参数(symbol)必须提供"
            }), 400
            
        # 验证时间范围
        if start_timestamp and end_timestamp:
            # 计算时间差（毫秒转为天）
            diff_days = (int(end_timestamp) - int(start_timestamp)) / (1000 * 86400)
            if diff_days > 7:
                return jsonify({
                    "success": False,
                    "error": "时间范围不能超过7天"
                }), 400
        # 如果未提供时间范围，默认查询最近7天
        if not start_timestamp and not end_timestamp:
            end_timestamp = int(time.time() * 1000)  # 当前时间毫秒时间戳
            start_timestamp = end_timestamp - (7 * 24 * 60 * 60 * 1000)  # 7天前

        results = []
        successful_count = 0
        failed_count = 0

        # 处理每个子账号 - 使用子账号自己的API密钥
        for email in emails:
            email_start_time = time.time()

            # 获取子账号的API客户端
            logger.info(f"使用子账号 {email} 自身的API查询合约成交历史")
            client = get_client_by_email(email)

            if not client:
                logger.warning(f"获取子账号 {email} API客户端失败，无法查询成交历史")
                results.append({
                    "email": email,
                    "success": False,
                    "error": "获取API凭证失败，请先配置子账号API密钥"
                })
                failed_count += 1
                continue

            # 构建查询参数
            params = {
                'symbol': symbol,
                'recvWindow': recv_window,
                'limit': limit
            }

            # 添加可选参数
            if from_id:
                params['fromId'] = from_id
            if start_timestamp:
                params['startTime'] = start_timestamp
            if end_timestamp:
                params['endTime'] = end_timestamp

            # 调用API获取成交历史
            endpoint = "/fapi/v1/userTrades"
            response = client._send_request('GET', endpoint, signed=True, params=params)

            # 处理响应
            if response.get('success'):
                trades_data = response.get('data', [])
                # 格式化成交数据
                formatted_trades = []

                for trade in trades_data:
                    # 格式化成交记录
                    formatted_trade = {
                        'symbol': trade.get('symbol', ''),
                        'id': trade.get('id', ''),
                        'orderId': trade.get('orderId', ''),
                        '订单编号': trade.get('orderId', ''),
                        'price': trade.get('price', '0'),
                        '成交价格': trade.get('price', '0'),
                        'qty': trade.get('qty', '0'),
                        '成交数量': trade.get('qty', '0'),
                        'quoteQty': trade.get('quoteQty', '0'),
                        'commission': trade.get('commission', '0'),
                        '手续费': trade.get('commission', '0'),
                        'commissionAsset': trade.get('commissionAsset', ''),
                        '手续费资产': trade.get('commissionAsset', ''),
                        'time': trade.get('time', 0),
                        '成交时间': trade.get('time', 0),
                        'side': trade.get('side', ''),
                        '方向': '买入' if trade.get('side') == 'BUY' else '卖出',
                        'positionSide': trade.get('positionSide', 'BOTH'),
                        'maker': trade.get('maker', False),
                        '是否挂单方': '是' if trade.get('maker') else '否',
                        'buyer': trade.get('buyer', False),
                        'realizedPnl': trade.get('realizedPnl', '0'),
                        '已实现盈亏': trade.get('realizedPnl', '0')
                    }

                    formatted_trades.append(formatted_trade)

                processing_time = time.time() - email_start_time
                logger.info(
                    f"成功获取子账号 {email} 的成交历史: {len(formatted_trades)}条，耗时: {processing_time:.2f}秒")
                results.append({
                    "email": email,
                    "success": True,
                    "trades": formatted_trades,
                    "count": len(formatted_trades),
                    "processingTime": round(processing_time, 2)
                })
                successful_count += 1
            else:
                error_msg = response.get('error', '获取成交历史失败')
                logger.error(f"获取子账号 {email} 合约成交历史失败: {error_msg}")

                # 提供更友好的错误信息
                user_error = error_msg
                if '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                    user_error = "访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
                elif 'Invalid API-key' in str(error_msg):
                    user_error = "API密钥无效，请更新API设置"
                elif 'signature' in str(error_msg).lower():
                    user_error = "API签名验证失败，请检查API密钥设置是否正确"
                elif 'permission' in str(error_msg).lower():
                    user_error = "API权限不足，需要启用读取权限"

                results.append({
                    "email": email,
                    "success": False,
                    "error": user_error
                })
                failed_count += 1

        total_time = time.time() - start_time
        logger.info(
            f"获取所有子账号({len(emails)})合约成交历史完成，成功: {successful_count}，失败: {failed_count}，总耗时: {total_time:.2f}秒")
        
        return jsonify({
            "success": True,
            "data": results,
            "summary": {
                "total": len(emails),
                "successful": successful_count,
                "failed": failed_count
            },
            "processingTime": round(total_time, 2)
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"获取合约成交历史失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取合约成交历史失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500