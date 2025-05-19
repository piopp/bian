import random
import string
import time
import logging
import json
from flask import request, jsonify, Blueprint, current_app, redirect, url_for
from app.models import db
from app.services.binance_client import BinanceClient
from . import subaccounts_bp
from app.services.binance_client import get_binance_client
from app.utils.auth import token_required
from app.models.account import SubAccountAPISettings
from app.api.auth import authenticated_user
from binance.client import Client
from binance.exceptions import BinanceAPIException
from ..margin import get_margin_trades

logger = logging.getLogger(__name__)

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
            import jwt
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id')
            logger.info(f"从token中获取到用户ID: {user_id}")
        except Exception as e:
            logger.warning(f"解析token失败: {str(e)}")
    
    # 如果从token中找不到user_id，尝试从请求参数获取
    if not user_id:
        # 尝试获取user_id参数，不转换类型，因为可能是邮箱
        user_id = request.args.get('user_id')
        logger.info(f"从请求参数获取到用户ID: {user_id}")
    
    if not user_id:
        logger.error("未能获取到用户ID")
        return jsonify({
            "success": False,
            "error": "未能获取到用户ID"
        }), 400
    
    # 获取主账号币安客户端
    client = get_binance_client(user_id)
    if not client:
        logger.error(f"用户 {user_id} 的主账号API未配置或不可用")
        return jsonify({
            "success": False,
            "error": "主账号API未配置或不可用"
        }), 400
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    logger.info(f"正在获取子账号列表，页码：{page}，每页数量：{limit}，user_id: {user_id}")
    
    result = client.get_sub_accounts(page, limit)
    
    # 日志记录API响应时间和结果
    elapsed = time.time() - start_time
    logger.info(f"获取子账号列表API响应时间：{elapsed:.2f}秒")
    
    if result.get('success') and 'data' in result:
        # 规范化数据结构
        # 检查返回的数据结构，确保包含子账号列表，并放入subaccounts字段中
        data = result['data']
        
        # 处理不同的响应结构
        subaccounts_list = []
        if isinstance(data, list):
            # 如果data直接是列表，将整个列表视为子账号列表
            subaccounts_list = data
            logger.info(f"API返回列表结构，获取到 {len(subaccounts_list)} 个子账号")
        elif isinstance(data, dict):
            # 如果data是字典，检查可能的子账号列表字段
            if 'subAccounts' in data:
                subaccounts_list = data.pop('subAccounts')
                logger.info(f"获取到 {len(subaccounts_list)} 个子账号")
            elif 'subAccountList' in data:
                # 另一种可能的字段名
                subaccounts_list = data.pop('subAccountList')
                logger.info(f"从subAccountList获取到 {len(subaccounts_list)} 个子账号")
            elif 'subaccounts' in data:
                # 如果已经有subaccounts字段
                subaccounts_list = data['subaccounts']
                logger.info(f"从subaccounts获取到 {len(subaccounts_list)} 个子账号")
            elif not any(key for key in data.keys() if 'account' in key.lower() or 'list' in key.lower()):
                # 如果没有明显包含子账号的字段，将整个对象包装成列表
                logger.warning(f"API返回数据没有明确的子账号字段: {list(data.keys())}")
                subaccounts_list = [data]
        else:
            # 如果是其他类型，记录警告并返回空列表
            logger.warning(f"API返回的数据格式无法识别: {type(data).__name__}")
            subaccounts_list = []
            
        # 为每个子账号添加API密钥状态字段
        enriched_subaccounts = []
        for account in subaccounts_list:
            if isinstance(account, dict) and 'email' in account:
                email = account['email']
                # 查询数据库获取API设置
                api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
                # 添加API状态字段
                account['has_api_key'] = bool(api_setting and api_setting.api_key and api_setting.api_secret)
                account['api_key'] = api_setting.api_key if api_setting else None
                account['api_secret_masked'] = '******' if (api_setting and api_setting.api_secret) else None
                enriched_subaccounts.append(account)
            else:
                enriched_subaccounts.append(account)
                
        # 更新结果
        result['data'] = enriched_subaccounts
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
        "subaccount_name": "子账号名称",
        "accountType": "账号类型",
        "features": ["futures", "margin", "options"] # 可选功能列表
    }
    """
    # 从请求数据中获取user_id
    data = request.json
    logger.info(f"接收到创建子账号请求: {json.dumps(data)}")
    
    user_id = data.get('user_id')
    logger.info(f"从请求数据中提取user_id: {user_id}")
    
    # 如果前端没有提供user_id，则尝试从Token中获取
    if not user_id:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # 解码JWT token
                from app.utils.auth import JWT_SECRET
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                logger.info(f"从token中获取到用户ID: {user_id}")
            except Exception as e:
                logger.warning(f"解析token失败: {str(e)}")
    
    # 获取主账号币安客户端
    client = get_binance_client(user_id)
    if not client:
        logger.error(f"用户 {user_id} 的主账号API未配置或不可用")
        return jsonify({
            "success": False,
            "error": "主账号API未配置或不可用"
        }), 400
    
    subaccount_name = data.get('subaccount_name', '')
    account_type = data.get('accountType', 'standard')
    features = data.get('features', [])
    
    logger.info(f"准备创建子账号: 名称={subaccount_name}, 类型={account_type}, 功能={features}")
    
    if not subaccount_name:
        logger.error("子账号名称不能为空")
        return jsonify({
            "success": False, 
            "error": "子账号名称不能为空"
        })
    
    # 验证名称长度
    if len(subaccount_name) > 20:
        logger.error("子账号名称不能超过20个字符")
        return jsonify({
            "success": False, 
            "error": "子账号名称不能超过20个字符"
        })
    
    # 创建子账号
    result = client.create_virtual_sub_account(subaccount_name)
    
    # 如果创建成功且需要开通额外功能
    if result.get('success') and features and 'data' in result and 'email' in result['data']:
        email = result['data']['email']
        logger.info(f"子账号创建成功: {email}, 开始开通附加功能")
        
        # 开通期货功能
        if 'futures' in features:
            logger.info(f"为子账号 {email} 开通期货功能")
            futures_result = client.enable_subaccount_futures(email)
            if not futures_result.get('success'):
                logger.warning(f"为子账号 {email} 开通期货功能失败: {futures_result.get('error')}")
        
        # 开通杠杆功能
        if 'margin' in features:
            logger.info(f"为子账号 {email} 开通杠杆功能")
            margin_result = client.enable_subaccount_margin(email)
            if not margin_result.get('success'):
                logger.warning(f"为子账号 {email} 开通杠杆功能失败: {margin_result.get('error')}")
        
        # 开通期权功能
        if 'options' in features:
            logger.info(f"为子账号 {email} 开通期权功能")
            options_result = client.enable_subaccount_options(email)
            if not options_result.get('success'):
                logger.warning(f"为子账号 {email} 开通期权功能失败: {options_result.get('error')}")
    
    return jsonify(result)


@subaccounts_bp.route('/batch', methods=['POST'])
def batch_create_subaccounts():
    """
    批量创建子账号
    
    请求体:
    {
        "user_id": 用户ID,
        "prefix": "账号前缀",
        "count": 创建数量,
        "accountType": "账号类型",
        "features": ["futures", "margin", "options"] # 可选功能列表
    }
    """
    # 从请求数据中获取user_id
    data = request.json
    logger.info(f"接收到批量创建子账号请求: {json.dumps(data)}")
    
    user_id = data.get('user_id')
    logger.info(f"从请求数据中提取user_id: {user_id}")
    
    # 如果前端没有提供user_id，则尝试从Token中获取
    if not user_id:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # 解码JWT token
                from app.utils.auth import JWT_SECRET
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                logger.info(f"从token中获取到用户ID: {user_id}")
            except Exception as e:
                logger.warning(f"解析token失败: {str(e)}")
    
    # 获取主账号币安客户端
    client = get_binance_client(user_id)
    if not client:
        logger.error(f"用户 {user_id} 的主账号API未配置或不可用")
        return jsonify({
            "success": False,
            "error": "主账号API未配置或不可用"
        }), 400
    
    prefix = data.get('prefix', 'user_')
    count = data.get('count', 5)
    account_type = data.get('accountType', 'standard')
    features = data.get('features', [])
    
    logger.info(f"准备批量创建子账号: 前缀={prefix}, 数量={count}, 类型={account_type}, 功能={features}")
    
    # 验证参数
    if not prefix:
        logger.error("账号前缀不能为空")
        return jsonify({
            "success": False, 
            "error": "账号前缀不能为空"
        })
    
    if not 1 <= count <= 20:
        logger.error("创建数量必须在1-20之间")
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
            logger.error("账号前缀过长，无法生成有效的随机账号")
            return jsonify({
                "success": False, 
                "error": "账号前缀过长，无法生成有效的随机账号"
            })
        
        # 生成随机字符串
        random_str = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(random_length))
        account_name = f"{prefix}{random_str}"
        account_names.append(account_name)
    
    logger.info(f"生成的随机账号名列表: {account_names}")
    
    # 批量创建子账号
    results = []
    successful_accounts = []
    
    for name in account_names:
        logger.info(f"正在创建子账号: {name}")
        result = client.create_virtual_sub_account(name)
        
        # 记录结果
        results.append({
            "name": name,
            "result": result
        })
        
        # 如果创建成功且需要开通额外功能
        if result.get('success') and features and 'data' in result and 'email' in result['data']:
            email = result['data']['email']
            logger.info(f"子账号 {name} 创建成功: {email}, 开始开通附加功能")
            successful_accounts.append(result['data'])
            
            # 开通期货功能
            if 'futures' in features:
                logger.info(f"为子账号 {email} 开通期货功能")
                futures_result = client.enable_subaccount_futures(email)
                if not futures_result.get('success'):
                    logger.warning(f"为子账号 {email} 开通期货功能失败: {futures_result.get('error')}")
            
            # 开通杠杆功能
            if 'margin' in features:
                logger.info(f"为子账号 {email} 开通杠杆功能")
                margin_result = client.enable_subaccount_margin(email)
                if not margin_result.get('success'):
                    logger.warning(f"为子账号 {email} 开通杠杆功能失败: {margin_result.get('error')}")
            
            # 开通期权功能
            if 'options' in features:
                logger.info(f"为子账号 {email} 开通期权功能")
                options_result = client.enable_subaccount_options(email)
                if not options_result.get('success'):
                    logger.warning(f"为子账号 {email} 开通期权功能失败: {options_result.get('error')}")
    
    # 统计成功和失败的数量
    success_count = sum(1 for r in results if r["result"]["success"]
                        and "data" in r["result"] and "email" in r["result"]["data"])
    
    logger.info(f"批量创建完成，成功: {success_count}/{count}")
    
    return jsonify({
        "success": True,
        "data": {
        "total": count,
        "success_count": success_count,
        "fail_count": count - success_count,
            "accounts": successful_accounts
        },
        "message": f"成功创建了 {success_count}/{count} 个子账号"
    })


@subaccounts_bp.route('/status', methods=['POST'])
def get_subaccount_status():
    """
    获取子账号状态
    
    请求体:
    {
        "email": "子账号邮箱",
        "user_id": "用户ID"
    }
    """
    # 获取请求数据
    data = request.json
    email = data.get('email')
    user_id = data.get('user_id')
    
    if not email:
        return jsonify({
            "success": False,
            "error": "子账号邮箱不能为空"
        })
    
    # 获取主账号币安客户端
    client = get_binance_client(user_id)
    if not client:
        return jsonify({
            "success": False,
            "error": "主账号API未配置或不可用"
        }), 400
    
    try:
        # 获取子账号状态
        result = client.get_subaccount_status(email)
        
        # 处理结果
        if result.get('success') and 'data' in result:
            return jsonify({
                "success": True,
                "data": result['data']
            })
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"获取子账号状态失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            })
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取子账号状态异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取子账号状态异常: {error_msg}"
        })


@subaccounts_bp.route('/batch-details', methods=['POST'])
def get_batch_details():
    """
    批量获取子账号详细信息（包括账户类型和状态）
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "recvWindow": 接收窗口时间(可选，默认5000),
        "user_id": 用户ID(可选)
    }
    """
    start_time = time.time()
    try:
        from app.models.account import SubAccountAPISettings
        
        data = request.json
        emails = data.get('emails', [])
        recv_window = data.get('recvWindow', 5000)
        user_id = data.get('user_id')

        logger.info(f"正在批量获取子账号详细信息，邮箱数量：{len(emails)}, 用户ID：{user_id}")

        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400

        # 获取主账号币安客户端
        client = get_binance_client(user_id)
        if not client:
            return jsonify({
                "success": False,
                "error": "主账号API未配置或不可用"
            }), 400
            
        results = []
        accounts = []  # 新增返回值，前端期望的格式
        successful_count = 0
        failed_count = 0

        # 首先获取所有子账号的基本信息列表
        list_params = {
            'recvWindow': recv_window
        }
        
        # 调用子账号列表API获取所有子账号信息
        list_endpoint = '/sapi/v1/sub-account/list'
        
        list_response = client._send_request('GET', list_endpoint, signed=True, params=list_params)
        
        # 检查响应类型并安全处理
        if not isinstance(list_response, dict):
            logger.error(f"获取子账号列表返回非字典响应: {list_response}")
            return jsonify({
                "success": False,
                "error": f"获取子账号列表失败: 不期望的响应格式 ({type(list_response).__name__})"
            }), 500
        
        if not list_response.get('success'):
            error_msg = list_response.get('error', '未知错误')
            logger.error(f"获取子账号列表失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"获取子账号列表失败: {error_msg}"
            }), 500
        
        # 安全获取子账号列表数据
        list_data = list_response.get('data')
        if not isinstance(list_data, list):
            # 如果data不是列表，可能是API返回格式发生变化
            if isinstance(list_data, dict) and 'subAccountList' in list_data:
                all_subaccounts = list_data.get('subAccountList', [])
            else:
                logger.error(f"子账号列表格式异常: {list_data}")
                all_subaccounts = []
        else:
            all_subaccounts = list_data
            
        # 创建一个邮箱到账号信息的映射
        email_to_account = {}
        
        for account in all_subaccounts:
            if isinstance(account, dict):
                email = account.get('email', '')
                if email:
                    email_to_account[email] = account
        
        # 获取所有子账号功能状态信息
        status_params = {
            'recvWindow': recv_window
        }
        
        status_endpoint = '/sapi/v1/sub-account/status'
        
        status_response = client._send_request('GET', status_endpoint, signed=True, params=status_params)
        
        # 创建一个邮箱到功能状态的映射
        email_to_status = {}
        
        # 安全处理状态响应
        if isinstance(status_response, dict) and status_response.get('success'):
            status_data = status_response.get('data')
            if isinstance(status_data, list):
                status_list = status_data
            else:
                # 如果data不是列表，可能包含在下一级字段
                status_list = status_data.get('statusList', []) if isinstance(status_data, dict) else []
                
            for status in status_list:
                if isinstance(status, dict):
                    email = status.get('email', '')
                    if email:
                        email_to_status[email] = status
        else:
            error_msg = status_response.get('error', '未知错误') if isinstance(status_response, dict) else str(status_response)
            logger.warning(f"获取子账号功能状态失败: {error_msg}")
        
        # 处理请求的每个子账号
        for email in emails:
            email_start_time = time.time()
            
            # 从已获取的数据中查找子账号信息
            account_info = email_to_account.get(email, {})
            status_info = email_to_status.get(email, {})
            
            if not account_info:
                # 如果在主查询中找不到，尝试单独查询该子账号
                try:
                    single_params = {
                        'email': email,
                        'recvWindow': recv_window
                    }
                    
                    single_endpoint = '/sapi/v1/sub-account/status'
                    single_response = client._send_request('GET', single_endpoint, signed=True, params=single_params)
                    
                    if isinstance(single_response, dict) and single_response.get('success'):
                        single_data = single_response.get('data')
                        if isinstance(single_data, list) and len(single_data) > 0:
                            # 找到了指定的子账号
                            status_info = single_data[0]
                            account_info = {
                                'email': email,
                                'activated': True  # 假设存在的账号是已激活的
                            }
                        else:
                            logger.warning(f"单独查询子账号 {email} 状态返回空数据")
                    else:
                        logger.warning(f"单独查询子账号 {email} 失败")
                except Exception as single_err:
                    logger.error(f"单独查询子账号 {email} 出错: {str(single_err)}")
            
            if not account_info:
                logger.warning(f"未找到子账号 {email} 的基本信息")
                results.append({
                    "email": email,
                    "success": False,
                    "error": "未找到子账号信息",
                    "message": "未找到子账号信息"
                })
                failed_count += 1
                continue
                
            # 获取子账号的API设置信息
            api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
            has_api = bool(api_setting and api_setting.api_key and api_setting.api_secret)
                
            # 安全获取子账号ID
            sub_id = ''
            if isinstance(account_info, dict):
                sub_id = account_info.get('subaccountId', '') or account_info.get('subAccountId', '')
                
            # 格式化子账号详细信息
            detail = {
                "email": email,
                "id": sub_id,
                "createTime": account_info.get('createTime', 0) if isinstance(account_info, dict) else 0,
                "status": account_info.get('status', '') if isinstance(account_info, dict) else '',
                "activated": account_info.get('activated', False) if isinstance(account_info, dict) else False,
                "mobile": account_info.get('mobile', '') if isinstance(account_info, dict) else '',
                "isFreeze": account_info.get('isFreeze', False) if isinstance(account_info, dict) else False,
                "isManaged": account_info.get('isManaged', False) if isinstance(account_info, dict) else False,
                "hasApiKey": has_api
            }
            
            # 添加功能状态信息（如果有）
            if status_info and isinstance(status_info, dict):
                detail.update({
                    "enableMargin": status_info.get('enableMargin', False),
                    "enableFutures": status_info.get('enableFutures', False),
                    "marginLevel": status_info.get('marginLevel', 0),
                    "marginEnable": status_info.get('marginEnable', False),
                    "futuresEnable": status_info.get('futuresEnable', False)
                })
                
            processing_time = time.time() - email_start_time
            logger.info(f"成功获取子账号 {email} 的详细信息，耗时: {processing_time:.2f}秒")
            
            # 添加到结果列表
            result_item = {
                "email": email,
                "success": True,
                "details": detail,
                "message": "查询详情成功",
                "processingTime": round(processing_time, 2)
            }
            
            results.append(result_item)
            
            # 为前端提供兼容格式
            accounts.append({
                "email": email,
                **detail  # 展开详情对象
            })
            
            successful_count += 1

        total_time = time.time() - start_time
        logger.info(
            f"批量获取所有子账号({len(emails)})详细信息完成，成功: {successful_count}，失败: {failed_count}，总耗时: {total_time:.2f}秒")

        return jsonify({
            "success": True,
            "results": results,  # 前端期望的结构
            "accounts": accounts,  # 前端期望的结构
            "data": results,     # 保持兼容性
            "summary": {
                "total": len(emails),
                "successful": successful_count,
                "failed": failed_count
            },
            "processingTime": round(total_time, 2)
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"批量获取子账号详细信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量获取子账号详细信息失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500 

@subaccounts_bp.route('/margin-account', methods=['POST'])
@token_required
def get_margin_account_proxy(current_user):
    """获取杠杆账户信息"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: email'
            })
        
        # 验证子账号是否属于当前用户
        auth_user = authenticated_user()
        if not auth_user:
            return jsonify({
                'success': False,
                'error': '用户未认证'
            })
        
        user_id = auth_user.get('id')
        
        # 检查子账号API设置是否存在
        api_setting = db.session.query(SubAccountAPISettings).filter_by(
            email=email
        ).first()
        
        if not api_setting:
            return jsonify({
                'success': False,
                'error': '子账号不存在'
            })
        
        # 验证API设置是否有效
        if not api_setting.api_key or not api_setting.api_secret:
            return jsonify({
                'success': False,
                'error': '子账号API设置未配置'
            })
        
        # 创建Binance客户端
        client = Client(api_setting.api_key, api_setting.api_secret)
        
        # 获取杠杆账户信息
        margin_account = client.get_margin_account()
        
        # 将margin_account转换为数组格式，因为前端期望的是数组
        # 我们将账户信息作为数组中的第一个元素返回
        return jsonify({
            'success': True,
            'data': [margin_account]  # 包装为数组
        })
        
    except BinanceAPIException as e:
        logger.error(f"获取杠杆账户信息失败: {e}")
        return jsonify({
            'success': False,
            'error': f"币安API错误: {e.message}"
        })
    except Exception as e:
        logger.error(f"获取杠杆账户信息失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取杠杆账户信息失败: {str(e)}"
        }) 

@subaccounts_bp.route('/margin-trades', methods=['POST'])
def subaccount_margin_trades():
    """
    获取杠杆账户交易历史 - 代理到/api/margin/trades接口
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderId": 订单ID(可选),
        "startTime": 开始时间(可选, 毫秒时间戳),
        "endTime": 结束时间(可选, 毫秒时间戳),
        "fromId": 起始交易ID(可选),
        "limit": 返回数量限制(可选，默认500)
    }
    
    返回体:
    {
        "success": true,
        "data": 交易历史记录数组
    }
    """
    # 直接调用margin模块的接口函数
    return get_margin_trades() 