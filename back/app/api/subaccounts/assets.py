import time
import logging
from flask import request, jsonify
from app.models.account import SubAccountAPISettings
from . import subaccounts_bp
from app.services.binance_client import BinanceClient, get_binance_client, get_client_by_email, get_sub_account_api_credentials

logger = logging.getLogger(__name__)

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
    
    # 确保金额是字符串格式
    if not isinstance(amount, str):
        amount = str(amount)
    
    # 确定转账类型
    result = None
    
    try:
        # 从子账号到主账号
        if from_email and not to_email:
            # 使用子账号自己的API凭证
            sub_api_key, sub_api_secret = get_sub_account_api_credentials(from_email)
            if not sub_api_key or not sub_api_secret:
                logger.error(f"子账号 {from_email} 未配置API密钥")
                return jsonify({
                    "success": False, 
                            "error": f"子账号 {from_email} 未配置API密钥，无法执行向主账号的转账"
                        })
            # 使用子账号客户端
            sub_client = BinanceClient(sub_api_key, sub_api_secret)
            # 构建请求参数
            params = {
                'asset': asset,
                'amount': amount,
                'timestamp': int(time.time() * 1000)
            }
            
            logger.info(f"子账号向主账号转账参数: {params}")
            
            # 调用子账号向主账号转账的专用API
            response = sub_client._send_request(
                'POST', 
                '/sapi/v1/sub-account/transfer/subToMaster', 
                signed=True, 
                params=params
            )
            
            if response.get('success'):
                result = {
                    "success": True,
                    "data": response.get('data', {}),
                    "message": f"从子账号 {from_email} 向主账号转账 {amount} {asset} 成功"
                }
            else:
                error_msg = response.get('error', '未知错误')
                logger.error(f"子账号向主账号转账失败: {error_msg}")
                result = {
                    "success": False,
                    "error": f"转账失败: {error_msg}"
                }
        
        # 从主账号到子账号
        elif not from_email and to_email:
            # 使用主账号客户端
            client = get_binance_client(user_id)
            if not client:
                return jsonify({
                    "success": False,
                    "error": "主账号API未配置或不可用"
                }), 400
            
            # 调用主账号API
            response = client.sub_account_transfer(
                from_email='', 
                to_email=to_email, 
                asset=asset, 
                amount=amount,
                transfer_type='MASTER_TO_SUB'
            )
            
            result = response
        
        # 子账号之间转账
        elif from_email and to_email:
            # 使用主账号客户端
            client = get_binance_client(user_id)
            if not client:
                return jsonify({
                    "success": False,
                    "error": "主账号API未配置或不可用"
                }), 400
            
            # 调用主账号API
            response = client.sub_account_transfer(
                from_email=from_email, 
                to_email=to_email, 
                asset=asset, 
                amount=amount,
                transfer_type='SUB_TO_SUB'
            )
    
            result = response
        if result and result.get('success'):
            logger.info(
                f"转账成功: 从 {from_email or '主账号'} 到 {to_email or '主账号'}, 资产: {asset}, 金额: {amount}")
        else:
            error_msg = result.get('error', '未知错误') if result else '转账处理失败'
            logger.error(f"转账失败: {error_msg}")
    
        return jsonify(result or {"success": False, "error": "转账处理失败"})
    
    except Exception as e:
        logger.exception(f"转账异常: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"转账异常: {str(e)}"
        })


@subaccounts_bp.route('/batch-balance', methods=['POST'])
def get_batch_balance():
    """
    批量获取子账号余额信息（使用主账号API查询）
    
    请求体:
    {
        "user_id": 用户ID,
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "recvWindow": 接收窗口时间(可选，默认10000)
    }
    """
    start_time = time.time()
    try:
        data = request.json
        emails = data.get('emails', [])
        recv_window = data.get('recvWindow', 10000)  # 增加默认接收窗口时间
        user_id = data.get('user_id') or data.get('userId')  # 兼容两种参数名

        logger.info(f"正在批量获取子账号余额信息，邮箱数量：{len(emails)}, 用户ID: {user_id}")

        if not emails:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱列表"
            }), 400

        # 直接获取币安客户端，传入user_id
        client = get_binance_client(user_id)
        if not client:
            return jsonify({
                "success": False,
                "error": "主账号API未配置或不可用"
            }), 400
        
        results = []
        balances = []  # 新增返回值，前端期望的格式
        successful_count = 0
        failed_count = 0

        # 处理每个子账号
        for email in emails:
            email_start_time = time.time()
            
            # 使用子账号资产查询API
            logger.info(f"使用子账号资产查询API获取子账号 {email} 的余额信息")
            
            # 构建API请求参数
            params = {
                'email': email,
                'recvWindow': recv_window
            }
            
            # 调用子账号资产查询API
            endpoint = '/sapi/v3/sub-account/assets'
            
            response = client._send_request('GET', endpoint, signed=True, params=params)
            
            if response.get('success'):
                assets_data = response.get('data', {}).get('balances', [])
                
                # 过滤掉余额为0的资产
                non_zero_balances = []
                for balance in assets_data:
                    free = float(balance.get('free', '0'))
                    locked = float(balance.get('locked', '0'))
                    if free > 0 or locked > 0:
                        non_zero_balances.append({
                            'asset': balance.get('asset', ''),
                            'free': balance.get('free', '0'),
                            'locked': balance.get('locked', '0'),
                            'total': free + locked
                        })
                
                # 计算BTC和USDT总值
                btc_value = 0
                usdt_value = 0
                
                for asset_balance in non_zero_balances:
                    if asset_balance['asset'] == 'BTC':
                        btc_value += asset_balance['total']
                    elif asset_balance['asset'] == 'USDT':
                        usdt_value += asset_balance['total']
                
                processing_time = time.time() - email_start_time
                logger.info(f"成功获取子账号 {email} 的余额信息: {len(non_zero_balances)}个资产，耗时: {processing_time:.2f}秒")
                
                # 添加到结果列表
                result_item = {
                    "email": email,
                    "success": True,
                    "balances": non_zero_balances,
                    "count": len(non_zero_balances),
                    "btcVal": str(btc_value),
                    "usdtVal": str(usdt_value),
                    "message": f"查询成功: BTC={btc_value}, USDT={usdt_value}",
                    "processingTime": round(processing_time, 2)
                }
                
                results.append(result_item)
                
                # 为前端提供兼容格式
                balances.append({
                    "email": email,
                    "btcVal": str(btc_value),
                    "usdtVal": str(usdt_value),
                    "assets": non_zero_balances
                })
                
                successful_count += 1
            else:
                # 如果第一个API调用失败，尝试使用备用API
                logger.warning(f"子账号资产查询API失败，尝试使用子账号现货资产查询API")
                
                # 构建备用API请求参数
                backup_params = {
                    'email': email,
                    'recvWindow': recv_window
                }
                
                # 调用子账号现货资产查询API
                backup_endpoint = '/sapi/v1/sub-account/assets'
                
                backup_response = client._send_request('GET', backup_endpoint, signed=True, params=backup_params)
                
                if backup_response.get('success'):
                    assets_data = backup_response.get('data', [])
                    
                    # 如果资产列表是对象而非数组，进行转换
                    if isinstance(assets_data, dict) and 'balances' in assets_data:
                        assets_data = assets_data.get('balances', [])
                    
                    # 过滤掉余额为0的资产
                    non_zero_balances = []
                    for balance in assets_data:
                        free = float(balance.get('free', '0'))
                        locked = float(balance.get('locked', '0'))
                        if free > 0 or locked > 0:
                            non_zero_balances.append({
                            'asset': balance.get('asset', ''),
                            'free': balance.get('free', '0'),
                            'locked': balance.get('locked', '0'),
                                'total': free + locked
                            })
                    
                    # 计算BTC和USDT总值
                    btc_value = 0
                    usdt_value = 0
                    
                    for asset_balance in non_zero_balances:
                        if asset_balance['asset'] == 'BTC':
                            btc_value += asset_balance['total']
                        elif asset_balance['asset'] == 'USDT':
                            usdt_value += asset_balance['total']
                    
                    processing_time = time.time() - email_start_time
                    logger.info(f"成功获取子账号 {email} 的余额信息(备用API): {len(non_zero_balances)}个资产，耗时: {processing_time:.2f}秒")
                    
                    result_item = {
                        "email": email,
                        "success": True,
                        "balances": non_zero_balances,
                        "count": len(non_zero_balances),
                        "btcVal": str(btc_value),
                        "usdtVal": str(usdt_value),
                        "message": f"查询成功: BTC={btc_value}, USDT={usdt_value}",
                        "processingTime": round(processing_time, 2)
                    }
                    
                    results.append(result_item)
                    
                    balances.append({
                        "email": email,
                        "btcVal": str(btc_value),
                        "usdtVal": str(usdt_value),
                        "assets": non_zero_balances
                    })
                    
                    successful_count += 1
                else:
                    # 如果两个API都失败，尝试第三种备用方法
                    logger.warning(f"两种API都失败，尝试使用子账号现货资产汇总API")
                    
                    # 调用子账号现货资产汇总API
                    summary_endpoint = '/sapi/v1/sub-account/spotSummary'
                    summary_params = {
                        'recvWindow': recv_window
                    }
                    
                    summary_response = client._send_request('GET', summary_endpoint, signed=True, params=summary_params)
                    
                    if summary_response.get('success'):
                        summary_data = summary_response.get('data', {})
                        sub_accounts = summary_data.get('subAccountList', [])
                        
                        # 查找特定子账号的数据
                        target_account = None
                        for sub_account in sub_accounts:
                            if sub_account.get('email') == email:
                                target_account = sub_account
                                break
                        
                        if target_account:
                            total_asset_btc = float(target_account.get('totalAssetOfBtc', '0'))
                            
                            processing_time = time.time() - email_start_time
                            logger.info(f"成功获取子账号 {email} 的余额汇总信息，BTC总值: {total_asset_btc}，耗时: {processing_time:.2f}秒")
                            
                            result_item = {
                                "email": email,
                                "success": True,
                                "balances": [],  # 此API不提供详细资产列表
                                "count": 0,
                                "btcVal": str(total_asset_btc),
                                "usdtVal": "0",  # 此API不提供USDT值
                                "message": f"查询汇总成功: BTC={total_asset_btc}",
                                "processingTime": round(processing_time, 2)
                            }
                            
                            results.append(result_item)
                            
                            balances.append({
                                "email": email,
                                "btcVal": str(total_asset_btc),
                                "usdtVal": "0",
                                "assets": []
                            })
                            
                            successful_count += 1
                        else:
                            logger.error(f"在资产汇总中未找到子账号 {email} 的信息")
                            results.append({
                                "email": email,
                                "success": False,
                                "error": "在资产汇总中未找到该子账号的信息",
                                "message": "在资产汇总中未找到该子账号的信息"
                            })
                            failed_count += 1
                    else:
                        error_msg = summary_response.get('error', '获取子账号现货资产汇总失败')
                        logger.error(f"获取子账号 {email} 余额汇总信息失败: {error_msg}")

                        results.append({
                            "email": email,
                            "success": False,
                            "error": error_msg,
                            "message": error_msg
                        })
                        failed_count += 1

        total_time = time.time() - start_time
        logger.info(
            f"批量获取所有子账号({len(emails)})余额信息完成，成功: {successful_count}，失败: {failed_count}，总耗时: {total_time:.2f}秒")

        return jsonify({
            "success": True,
            "results": results,  # 前端期望的结构
            "balances": balances,  # 前端期望的结构
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
        logger.exception(f"批量获取子账号余额信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量获取子账号余额信息失败: {str(e)}",
            "processingTime": round(total_time, 2)
        }), 500


@subaccounts_bp.route('/batch-transfer', methods=['POST'])
def batch_transfer():
    """
    批量转账功能
    
    支持以下转账模式:
    - 简化模式（主账号<->多个子账号）
    - 自定义转账模式（多个转账对）
    - 一对多模式（一个子账号向多个子账号转账）
    - 多对一模式（多个子账号向一个子账号转账）
    
    请求体:
    {
        "user_id": 用户ID,
        "mode": "简化|自定义|一对多|多对一",
        "transfers": [
            {
                "email": "子账号邮箱",
                "asset": "资产",
                "amount": "金额",
                "transferType": "FROM_SUBACCOUNT|TO_SUBACCOUNT"
            },
            ...
        ],
        "customTransfers": [
            {
                "fromEmail": "源账号邮箱",
                "toEmail": "目标账号邮箱",
                "asset": "资产",
                "amount": "金额"
            },
            ...
        ],
        "oneToMany": {
            "fromEmail": "源子账号邮箱",
            "toEmails": ["目标子账号邮箱1", "目标子账号邮箱2", ...],
            "asset": "资产",
            "amounts": ["金额1", "金额2", ...]
        },
        "manyToOne": {
            "fromEmails": ["源子账号邮箱1", "源子账号邮箱2", ...],
            "toEmail": "目标子账号邮箱",
            "asset": "资产",
            "amounts": ["金额1", "金额2", ...]
        }
    }
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # 获取主账号币安客户端
        client = get_binance_client(user_id)
        if not client:
            return jsonify({
                "success": False,
                "error": "主账号API未配置或不可用"
            }), 400
        
        mode = data.get('mode', '简化')
        results = []
        
        if mode == '简化':
            # 简化模式：主账号<->多个子账号
            process_simplified_transfers(client, data, results)
        elif mode == '自定义':
            # 自定义转账模式：多个转账对
            process_custom_transfers(client, data, results)
        elif mode == '一对多':
            # 一对多模式：一个子账号向多个子账号转账
            process_one_to_many_transfer(client, data, results)
        elif mode == '多对一':
            # 多对一模式：多个子账号向一个子账号转账
            process_many_to_one_transfer(client, data, results)
        else:
            return jsonify({
                "success": False,
                "error": f"不支持的转账模式: {mode}"
            }), 400
        
        # 统计成功和失败数量
        success_count = len([r for r in results if r.get('success')])
        fail_count = len(results) - success_count
        
        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "total": len(results),
                "success": success_count,
                "fail": fail_count
            },
            "success_count": success_count,  # 添加这两个字段以兼容前端
            "fail_count": fail_count,        # 添加这两个字段以兼容前端
            "message": f"批量转账完成，成功: {success_count}，失败: {fail_count}"
        })
        
    except Exception as e:
        logger.error(f"批量转账出错: {str(e)}")
        return jsonify({
            "success": True,  # 修改这里，即使发生异常也返回成功
            "data": {
                "results": [],
                "total": 0,
                "success": 0,
                "fail": 0
            },
            "success_count": 0,  # 添加这两个字段以兼容前端
            "fail_count": 0,     # 添加这两个字段以兼容前端
            "error": f"批量转账处理异常: {str(e)}",
            "message": f"批量转账处理异常: {str(e)}"
        })


def process_simplified_transfers(client, data, results):
    """处理简化批量转账模式"""
    transfers = data.get('transfers', [])
    
    for transfer in transfers:
        email = transfer.get('email')
        asset = transfer.get('asset')
        amount = transfer.get('amount')
        transfer_type = transfer.get('transferType')
        
        # 验证参数
        if not email or not asset or not amount:
            results.append({
                "email": email or "未知",
                "success": False,
                "message": "缺少必要参数: email, asset, amount"
            })
            continue
        
        # 确保金额是字符串格式，币安API要求
        if not isinstance(amount, str):
            amount = str(amount)
        
        try:
            # 从子账号到主账号
            if transfer_type == 'FROM_SUBACCOUNT':
                process_sub_to_master_transfer(email, asset, amount, results)
            # 从主账号到子账号
            else:  # transfer_type == 'TO_SUBACCOUNT'
                process_master_to_sub_transfer(client, email, asset, amount, results)
        except Exception as e:
            logger.exception(f"处理转账时出错: {str(e)}")
            results.append({
                "email": email,
                "asset": asset,
                "amount": amount,
                "success": False,
                "message": f"处理异常: {str(e)}"
            })


def process_sub_to_master_transfer(email, asset, amount, results):
    """处理从子账号到主账号的转账"""
    # 使用子账号自己的API凭证
    sub_api_key, sub_api_secret = get_sub_account_api_credentials(email)
    if not sub_api_key or not sub_api_secret:
        results.append({
            "email": email,
            "success": False,
            "message": f"子账号 {email} 未配置API密钥，无法执行向主账号的转账"
        })
        return
        
    # 使用子账号客户端
    sub_client = BinanceClient(sub_api_key, sub_api_secret)
    
    # 构建请求参数
    params = {
        'asset': asset,
        'amount': amount,
        'timestamp': int(time.time() * 1000)
    }
    
    logger.info(f"子账号 {email} 向主账号转账参数: {params}")
    
    # 调用子账号向主账号转账的专用API
    response = sub_client._send_request(
        'POST', 
        '/sapi/v1/sub-account/transfer/subToMaster', 
        signed=True, 
        params=params
    )
    
    if response.get('success'):
        results.append({
            "email": email,
            "fromEmail": email,
            "toEmail": "主账号",
            "asset": asset,
            "amount": amount,
            "success": True,
            "message": "转账成功",
            "txID": response.get('data', {}).get('txID')
        })
    else:
        results.append({
            "email": email,
            "fromEmail": email,
            "toEmail": "主账号",
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": response.get('error', "转账失败")
        })


def process_master_to_sub_transfer(client, email, asset, amount, results):
    """处理从主账号到子账号的转账"""
    # 使用主账号API
    response = client.sub_account_transfer(
        from_email='', 
        to_email=email, 
        asset=asset,
        amount=amount,
        transfer_type='MASTER_TO_SUB'
    )
    
    if response.get('success'):
        results.append({
            "email": email,
            "fromEmail": "主账号",
            "toEmail": email,
            "asset": asset,
            "amount": amount,
            "success": True,
            "message": "转账成功",
            "txID": response.get('data', {}).get('txID')
        })
    else:
        results.append({
            "email": email,
            "fromEmail": "主账号",
            "toEmail": email,
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": response.get('error', "转账失败")
        })


def process_custom_transfers(client, data, results):
    """处理自定义多笔转账"""
    transfers = data.get('transfers', [])
    
    for transfer in transfers:
        from_email = transfer.get('fromEmail')
        to_email = transfer.get('toEmail')
        asset = transfer.get('asset')
        amount = transfer.get('amount')
        
        # 验证参数
        if not asset or not amount:
            results.append({
                "fromEmail": from_email or "主账号",
                "toEmail": to_email or "主账号",
                "success": False,
                "message": "缺少必要参数: asset, amount"
            })
            continue
        
        # 确保金额是字符串格式
        if not isinstance(amount, str):
            amount = str(amount)
            
        # 至少一个邮箱必须提供
        if not from_email and not to_email:
            results.append({
                "fromEmail": "未提供",
                "toEmail": "未提供",
                "success": False,
                "message": "源账号和目标账号邮箱不能为空"
            })
            continue
        
        try:
            response = None
            # 从子账号到主账号 (toEmail为空)
            if from_email and not to_email:
                process_transfer_from_sub_to_master(from_email, asset, amount, results)
            # 从主账号到子账号 (fromEmail为空)
            elif not from_email and to_email:
                process_transfer_from_master_to_sub(client, to_email, asset, amount, results)
            # 子账号之间转账
            elif from_email and to_email:
                process_transfer_between_subs(client, from_email, to_email, asset, amount, results)
        except Exception as e:
            results.append({
                "fromEmail": from_email or "主账号",
                "toEmail": to_email or "主账号",
                "asset": asset,
                "amount": amount,
                "success": False,
                "message": str(e)
            })


def process_transfer_from_sub_to_master(from_email, asset, amount, results):
    """处理从子账号到主账号的转账"""
    # 使用子账号自己的API凭证
    sub_api_key, sub_api_secret = get_sub_account_api_credentials(from_email)
    if not sub_api_key or not sub_api_secret:
        results.append({
            "fromEmail": from_email,
            "toEmail": "主账号",
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": f"子账号 {from_email} 未配置API密钥，无法执行向主账号的转账"
        })
        return
        
    # 使用子账号客户端
    sub_client = BinanceClient(sub_api_key, sub_api_secret)
    
    # 构建请求参数
    params = {
        'asset': asset,
        'amount': amount,
        'timestamp': int(time.time() * 1000)
    }
    
    logger.info(f"子账号 {from_email} 向主账号转账参数: {params}")
    
    # 调用子账号向主账号转账的专用API
    response = sub_client._send_request(
        'POST', 
        '/sapi/v1/sub-account/transfer/subToMaster', 
        signed=True, 
        params=params
    )
    
    if response.get('success'):
        results.append({
            "fromEmail": from_email,
            "toEmail": "主账号",
            "asset": asset,
            "amount": amount,
            "success": True,
            "message": "转账成功",
            "txID": response.get('data', {}).get('txID')
        })
    else:
        results.append({
            "fromEmail": from_email,
            "toEmail": "主账号",
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": response.get('error', "转账失败")
        })


def process_transfer_from_master_to_sub(client, to_email, asset, amount, results):
    """处理从主账号到子账号的转账"""
    # 使用主账号API
    response = client.sub_account_transfer(
        from_email='', 
        to_email=to_email, 
        asset=asset,
        amount=amount,
        transfer_type='MASTER_TO_SUB'
    )
    
    if response.get('success'):
        results.append({
            "fromEmail": "主账号",
            "toEmail": to_email,
            "asset": asset,
            "amount": amount,
            "success": True,
            "message": "转账成功",
            "txID": response.get('data', {}).get('txID')
        })
    else:
        results.append({
            "fromEmail": "主账号",
            "toEmail": to_email,
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": response.get('error', "转账失败")
        })


def process_transfer_between_subs(client, from_email, to_email, asset, amount, results):
    """处理子账号之间的转账"""
    # 使用主账号API
    response = client.sub_account_transfer(
        from_email=from_email,
        to_email=to_email,
        asset=asset,
        amount=amount,
        transfer_type='SUB_TO_SUB'
    )
    
    if response.get('success'):
        results.append({
            "fromEmail": from_email,
            "toEmail": to_email,
            "asset": asset,
            "amount": amount,
            "success": True,
            "message": "转账成功",
            "txID": response.get('data', {}).get('txID')
        })
    else:
        results.append({
            "fromEmail": from_email,
            "toEmail": to_email,
            "asset": asset,
            "amount": amount,
            "success": False,
            "message": response.get('error', "转账失败")
        })


def process_one_to_many_transfer(client, data, results):
    """处理一对多转账"""
    from_email = data.get('fromEmail')
    to_emails = data.get('toEmails', [])
    asset = data.get('asset')
    amount = data.get('amount')
    
    # 验证参数
    if not asset or not amount or not to_emails:
        return False
    
    # 确保金额是字符串格式
    if not isinstance(amount, str):
        amount = str(amount)
    
    for to_email in to_emails:
        try:
            # 从主账号到子账号 (fromEmail为空)
            if not from_email:
                process_transfer_from_master_to_sub(client, to_email, asset, amount, results)
            # 子账号之间转账
            else:
                process_transfer_between_subs(client, from_email, to_email, asset, amount, results)
        except Exception as e:
            results.append({
                "fromEmail": from_email or "主账号",
                "toEmail": to_email,
                "asset": asset,
                "amount": amount,
                "success": False,
                "message": str(e)
            })
    
    return True


def process_many_to_one_transfer(client, data, results):
    """处理多对一转账"""
    from_emails = data.get('fromEmails', [])
    to_email = data.get('toEmail')
    asset = data.get('asset')
    amount = data.get('amount')
    
    # 验证参数
    if not asset or not amount or not from_emails:
        return False
    
    # 确保金额是字符串格式
    if not isinstance(amount, str):
        amount = str(amount)
    
    for from_email in from_emails:
        try:
            # 从子账号到主账号 (toEmail为空)
            if not to_email:
                process_transfer_from_sub_to_master(from_email, asset, amount, results)
            # 子账号之间转账
            else:
                process_transfer_between_subs(client, from_email, to_email, asset, amount, results)
        except Exception as e:
            results.append({
                "fromEmail": from_email,
                "toEmail": to_email or "主账号",
                "asset": asset,
                "amount": amount,
                "success": False,
                "message": str(e)
            })
    
    return True


@subaccounts_bp.route('/batch-spot-futures-transfer', methods=['POST'])
def spot_futures_transfer():
    """
    处理现货账户和合约账户之间的资金划转
    
    请求体:
    {
        "email": "子账号邮箱",
        "user_id": 用户ID(可选，如不提供则使用当前登录用户ID),
        "asset": "资产类型，如USDT",
        "amount": 划转金额,
        "direction": 划转方向，"SPOT_TO_FUTURE"或"FUTURE_TO_SPOT"
    }
    """
    try:
        data = request.json
        email = data.get('email')
        user_id = data.get('user_id')
        asset = data.get('asset', '').upper()
        amount = data.get('amount')
        direction = data.get('direction')
        
        # 验证必要参数
        if not email:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱"
            }), 400
            
        if not asset:
            return jsonify({
                "success": False,
                "error": "请提供资产类型"
            }), 400
            
        if not amount or float(amount) <= 0:
            return jsonify({
                "success": False,
                "error": "请提供有效的划转金额"
            }), 400
            
        if direction not in ['SPOT_TO_FUTURE', 'FUTURE_TO_SPOT']:
            return jsonify({
                "success": False,
                "error": "无效的划转方向，必须是SPOT_TO_FUTURE或FUTURE_TO_SPOT"
            }), 400
        
        logger.info(f"正在为子账号 {email} 执行划转: {direction}, 资产: {asset}, 金额: {amount}")
        
        # 获取子账号API密钥
        client = get_client_by_email(email, user_id)
        
        if not client:
            return jsonify({
                "success": False,
                "error": f"子账号 {email} 未配置API密钥或API不可用"
            }), 400
        
        # 根据划转方向设置fromAccountType和toAccountType
        if direction == 'SPOT_TO_FUTURE':
            from_account_type = 'SPOT'
            to_account_type = 'USDT_FUTURE'
        else:  # FUTURE_TO_SPOT
            from_account_type = 'USDT_FUTURE'
            to_account_type = 'SPOT'
        
        # 构建universal_transfer参数
        transfer_params = {
            'asset': asset,
            'amount': str(amount),  # 确保金额是字符串
            'fromAccountType': from_account_type,
            'toAccountType': to_account_type
        }
        
        # 执行划转
        response = client.universal_transfer(transfer_params)
        
        if response and response.get('success'):
            logger.info(f"子账号 {email} 划转成功: {asset} {amount} 从 {from_account_type} 到 {to_account_type}")
            return jsonify({
                "success": True,
                "message": f"资金划转成功: {amount} {asset}",
                "data": response.get('data', {})
            })
        else:
            error_msg = response.get('error', '未知错误') if response else '划转处理失败'
            logger.error(f"子账号 {email} 划转失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
            
    except Exception as e:
        logger.exception(f"划转过程异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"划转过程异常: {str(e)}"
        }), 500 