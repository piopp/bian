import logging
import json
import math
from flask import request, jsonify, current_app
from app.utils.auth import token_required
from app.services.binance_client import get_client_by_email
from app.models.account import SubAccountAPISettings
from . import subaccounts_bp

# 设置日志
logger = logging.getLogger(__name__)

@subaccounts_bp.route('/portfolio-margin/account', methods=['POST'])
@token_required
def get_portfolio_margin_account(current_user):
    """
    获取子账号的统一账户(Portfolio Margin)信息
    
    请求体:
    {
        "email": "子账号邮箱"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        logger.info(f"准备获取子账号 {email} 的统一账户信息")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API获取统一账户信息
        params = {}
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/papi/v1/account'  # 币安统一账户信息API端点
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            account_data = response.get('data', {})
            
            # 处理返回数据，确保包含必要字段
            result = {
                "accountType": account_data.get('accountType', 'PM'),  # 默认PM表示Portfolio Margin
                "totalWalletBalance": account_data.get('totalWalletBalance', '0'),
                "totalUnrealizedProfit": account_data.get('totalUnrealizedProfit', '0'),
                "totalMarginBalance": account_data.get('totalMarginBalance', '0'),
                "totalInitialMargin": account_data.get('totalInitialMargin', '0'),
                "totalMaintMargin": account_data.get('totalMaintMargin', '0'),
                "totalAvailableBalance": account_data.get('totalAvailableBalance', '0'),
                "maxWithdrawAmount": account_data.get('maxWithdrawAmount', '0'),
                "assets": account_data.get('assets', []),
                "portfolioMarginEnabled": True  # 如果能调用此API，说明已启用统一账户
            }
            
            logger.info(f"成功获取子账号 {email} 的统一账户信息")
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"获取统一账户信息失败: {error_msg}")
            
            # 如果返回特定错误码，说明未开通统一账户
            if "not found" in error_msg.lower() or "no permission" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": {
                        "portfolioMarginEnabled": False,
                        "message": "该账号未开通统一账户"
                    }
                })
            
            return jsonify({
                "success": False,
                "error": f"获取统一账户信息失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"获取统一账户信息异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取统一账户信息异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/close-position', methods=['POST'])
@token_required
def close_portfolio_margin_position(current_user):
    """
    统一账户平仓功能
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对，如BTCUSDT",
        "positionSide": "持仓方向，可选值: BOTH, LONG, SHORT",
        "percentage": 平仓比例，100表示全平
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        required_fields = ['email', 'symbol']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必要参数: {field}"
                }), 400

        email = data.get('email')
        symbol = data.get('symbol')
        position_side = data.get('positionSide', None)  # 可选
        percentage = data.get('percentage', 100)  # 默认全平
        
        # 获取子账户API客户端（提前）
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 校验positionSide逻辑优化
        # 先获取持仓信息
        is_coin_margined = False
        if "_PERP" in symbol or "USD_" in symbol:  # 币本位合约符号特征
            is_coin_margined = True
            logger.info(f"检测到币本位合约: {symbol}")
        if is_coin_margined:
            positions_response = client._send_request('GET', '/papi/v1/cm/account', signed=True)
        else:
            positions_response = client._send_request('GET', '/papi/v1/um/account', signed=True)
        if not positions_response.get('success'):
            return jsonify({
                "success": False,
                "error": f"获取持仓信息失败: {positions_response.get('error')}"
            }), 400
        account_data = positions_response.get('data', {})
        positions = account_data.get('positions', [])
        # 自动推断positionSide
        if not position_side:
            # 统计当前symbol下的持仓方向
            long_pos = [pos for pos in positions if pos.get('symbol') == symbol and float(pos.get('positionAmt', '0')) > 0]
            short_pos = [pos for pos in positions if pos.get('symbol') == symbol and float(pos.get('positionAmt', '0')) < 0]
            if len(long_pos) + len(short_pos) == 1:
                # 只有一个方向，自动推断
                if long_pos:
                    position_side = 'LONG'
                else:
                    position_side = 'SHORT'
            else:
                return jsonify({
                    "success": False,
                    "error": "必须指定positionSide，且只能为LONG或SHORT（双向持仓模式）"
                }), 400
        if position_side not in ['LONG', 'SHORT']:
            return jsonify({
                "success": False,
                "error": "必须指定positionSide，且只能为LONG或SHORT（双向持仓模式）"
            }), 400
        logger.info(f"准备平仓: 账户={email}, 交易对={symbol}, 方向={position_side}, 比例={percentage}%")

        # 如果是BOTH，则平掉该交易对的所有持仓
        if position_side == 'BOTH':
            logger.info(f"检测到BOTH方向，将平掉所有方向的持仓")
            all_results = []
            
            # 先平LONG方向
            long_results = process_close_position(client, symbol, 'LONG', percentage, is_coin_margined)
            if long_results:
                all_results.extend(long_results)
            
            # 再平SHORT方向
            short_results = process_close_position(client, symbol, 'SHORT', percentage, is_coin_margined)
            if short_results:
                all_results.extend(short_results)
            
            if not all_results:
                return jsonify({
                    "success": False,
                    "error": f"未找到交易对 {symbol} 的任何持仓"
                }), 404
            
            # 返回合并的平仓结果
            success_count = len([r for r in all_results if r.get('status') == 'SUCCESS'])
            failed_count = len(all_results) - success_count
            
            return jsonify({
                "success": True,
                "data": {
                    "results": all_results,
                    "total": len(all_results),
                    "success_count": success_count,
                    "failed_count": failed_count
                }
            })
            
        if position_side not in ['LONG', 'SHORT']:
            return jsonify({
                "success": False,
                "error": "必须指定positionSide，且只能为LONG、SHORT或BOTH"
            }), 400
            
        # 确定是U本位还是币本位合约
        is_coin_margined = False
        if "_PERP" in symbol or "USD_" in symbol:  # 币本位合约符号特征
            is_coin_margined = True
            logger.info(f"检测到币本位合约: {symbol}")
            
        # 获取持仓信息 - 根据合约类型选择不同的API
        if is_coin_margined:
            positions_response = client._send_request('GET', '/papi/v1/cm/account', signed=True)
        else:
            positions_response = client._send_request('GET', '/papi/v1/um/account', signed=True)
            
        if not positions_response.get('success'):
            return jsonify({
                "success": False,
                "error": f"获取持仓信息失败: {positions_response.get('error')}"
            }), 400

        account_data = positions_response.get('data', {})
        positions = account_data.get('positions', [])
        
        # 按交易对和持仓方向筛选持仓
        target_positions = []
        for pos in positions:
            if pos.get('symbol') == symbol:
                pos_amount = float(pos.get('positionAmt', '0'))
                if pos_amount == 0:
                    continue
                # 只筛选对应方向
                if position_side == 'LONG' and pos_amount > 0:
                    target_positions.append(pos)
                elif position_side == 'SHORT' and pos_amount < 0:
                    target_positions.append(pos)

        if not target_positions:
            return jsonify({
                "success": False,
                "error": f"未找到交易对 {symbol} 的 {position_side} 方向持仓"
            }), 404

        # 处理每个持仓
        results = []
        for position in target_positions:
            pos_amount = float(position.get('positionAmt', '0'))
            # 根据比例计算平仓数量
            close_amount = abs(pos_amount) * percentage / 100
            # 保留精度
            close_amount = float(format(close_amount, '.8f').rstrip('0').rstrip('.'))
            
            # 确定平仓方向
            close_side = 'SELL' if position_side == 'LONG' else 'BUY'  # 平多用SELL，平空用BUY
            
            logger.info(f"执行平仓: {symbol} 方向={close_side}, 数量={close_amount}, positionSide={position_side}")
            
            # 执行平仓
            order_params = {
                'symbol': symbol,
                'side': close_side,
                'type': 'MARKET',
                'quantity': str(close_amount),
            }
            
            # 如果是U本位合约，才添加positionSide参数
            if not is_coin_margined:
                order_params['positionSide'] = position_side
            
            logger.info(f"平仓请求参数: {json.dumps(order_params)}")
            
            # 根据合约类型选择不同的API端点
            if is_coin_margined:
                endpoint = '/papi/v1/cm/order'  # 币本位合约API端点
            else:
                endpoint = '/papi/v1/um/order'  # U本位合约API端点
                
            # 发送平仓请求
            order_response = client._send_request('POST', endpoint, params=order_params, signed=True)
            
            if order_response.get('success'):
                results.append({
                    "symbol": symbol,
                    "side": close_side,
                    "amount": close_amount,
                    "status": "SUCCESS",
                    "orderId": order_response.get('data', {}).get('orderId', None),
                    "message": f"成功平仓 {close_amount} {symbol}"
                })
            else:
                error_msg = order_response.get('error', '未知错误')
                results.append({
                    "symbol": symbol,
                    "side": close_side,
                    "amount": close_amount,
                    "status": "FAILED",
                    "message": f"平仓失败: {error_msg}"
                })

        # 返回平仓结果
        success_count = len([r for r in results if r.get('status') == 'SUCCESS'])
        failed_count = len(results) - success_count
        
        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "total": len(results),
                "success_count": success_count,
                "failed_count": failed_count
            }
        })

    except Exception as e:
        logger.exception(f"统一账户平仓操作出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"统一账户平仓操作出错: {str(e)}"
        }), 500

def process_close_position(client, symbol, position_side, percentage, is_coin_margined):
    """
    处理指定方向的平仓操作
    
    参数:
    - client: API客户端
    - symbol: 交易对
    - position_side: 持仓方向 LONG或SHORT
    - percentage: 平仓比例
    - is_coin_margined: 是否币本位合约
    
    返回:
    - 平仓结果列表
    """
    # 获取持仓信息 - 根据合约类型选择不同的API
    if is_coin_margined:
        positions_response = client._send_request('GET', '/papi/v1/cm/account', signed=True)
    else:
        positions_response = client._send_request('GET', '/papi/v1/um/account', signed=True)
        
    if not positions_response.get('success'):
        logger.error(f"获取持仓信息失败: {positions_response.get('error')}")
        return []

    account_data = positions_response.get('data', {})
    positions = account_data.get('positions', [])
    
    # 按交易对和持仓方向筛选持仓
    target_positions = []
    for pos in positions:
        if pos.get('symbol') == symbol:
            pos_amount = float(pos.get('positionAmt', '0'))
            if pos_amount == 0:
                continue
            # 只筛选对应方向
            if position_side == 'LONG' and pos_amount > 0:
                target_positions.append(pos)
            elif position_side == 'SHORT' and pos_amount < 0:
                target_positions.append(pos)

    if not target_positions:
        logger.info(f"未找到交易对 {symbol} 的 {position_side} 方向持仓")
        return []

    # 处理每个持仓
    results = []
    for position in target_positions:
        pos_amount = float(position.get('positionAmt', '0'))
        # 根据比例计算平仓数量
        close_amount = abs(pos_amount) * percentage / 100
        # 保留精度
        close_amount = float(format(close_amount, '.8f').rstrip('0').rstrip('.'))
        
        # 确定平仓方向
        close_side = 'SELL' if position_side == 'LONG' else 'BUY'  # 平多用SELL，平空用BUY
        
        logger.info(f"执行平仓: {symbol} 方向={close_side}, 数量={close_amount}, positionSide={position_side}")
        
        # 执行平仓
        order_params = {
            'symbol': symbol,
            'side': close_side,
            'type': 'MARKET',
            'quantity': str(close_amount),
        }
        
        # 如果是U本位合约，才添加positionSide参数
        if not is_coin_margined:
            order_params['positionSide'] = position_side
        
        logger.info(f"平仓请求参数: {json.dumps(order_params)}")
        
        # 根据合约类型选择不同的API端点
        if is_coin_margined:
            endpoint = '/papi/v1/cm/order'  # 币本位合约API端点
        else:
            endpoint = '/papi/v1/um/order'  # U本位合约API端点
            
        # 发送平仓请求
        order_response = client._send_request('POST', endpoint, params=order_params, signed=True)
        
        if order_response.get('success'):
            results.append({
                "symbol": symbol,
                "side": close_side,
                "amount": close_amount,
                "status": "SUCCESS",
                "orderId": order_response.get('data', {}).get('orderId', None),
                "message": f"成功平仓 {close_amount} {symbol}"
            })
        else:
            error_msg = order_response.get('error', '未知错误')
            results.append({
                "symbol": symbol,
                "side": close_side,
                "amount": close_amount,
                "status": "FAILED",
                "message": f"平仓失败: {error_msg}"
            })
    
    return results

@subaccounts_bp.route('/portfolio-margin/balance', methods=['POST'])
@token_required
def get_portfolio_margin_balance(current_user):
    """
    获取子账号的统一账户余额信息
    
    请求体:
    {
        "email": "子账号邮箱"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        logger.info(f"准备获取子账号 {email} 的统一账户余额信息")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API获取统一账户信息
        params = {}
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/papi/v1/balance'  # 币安统一账户余额API端点
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            balance_data = response.get('data', [])
            
            # 过滤零余额资产
            non_zero_balances = []
            for asset in balance_data:
                # 计算总余额
                wallet_balance = float(asset.get('walletBalance', '0'))
                cross_margin_balance = float(asset.get('crossMarginBalance', '0'))
                um_unrealized_pnl = float(asset.get('umUnrealizedPnL', '0'))
                
                # 只保留有余额的资产
                if wallet_balance > 0 or cross_margin_balance > 0 or abs(um_unrealized_pnl) > 0:
                    non_zero_balances.append(asset)
            
            logger.info(f"成功获取子账号 {email} 的统一账户余额信息，共 {len(non_zero_balances)} 种资产")
            return jsonify({
                "success": True,
                "data": non_zero_balances
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"获取统一账户余额信息失败: {error_msg}")
            
            # 如果返回特定错误码，说明未开通统一账户
            if "not found" in error_msg.lower() or "no permission" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": [],
                    "message": "该账号未开通统一账户或没有余额"
                })
            
            return jsonify({
                "success": False,
                "error": f"获取统一账户余额信息失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"获取统一账户余额信息异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取统一账户余额信息异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/um/positions', methods=['POST'])
@token_required
def get_portfolio_margin_positions_um(current_user):
    """
    获取子账号的统一账户合约持仓信息
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对符号(可选)"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        symbol = data.get('symbol')  # 可选参数
        
        logger.info(f"准备获取子账号 {email} 的统一账户合约持仓信息 {f'symbol={symbol}' if symbol else ''}")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API获取统一账户持仓信息
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/papi/v1/um/account'  # 币安统一账户UM合约API端点
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            account_data = response.get('data', {})
            positions = account_data.get('positions', [])
            
            # 过滤零仓位
            non_zero_positions = []
            for position in positions:
                position_amt = float(position.get('positionAmt', '0'))
                # 只保留有仓位的交易对
                if position_amt != 0:
                    non_zero_positions.append(position)
            
            logger.info(f"成功获取子账号 {email} 的统一账户合约持仓信息，共 {len(non_zero_positions)} 个持仓")
            return jsonify({
                "success": True,
                "data": non_zero_positions
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"获取统一账户合约持仓信息失败: {error_msg}")
            
            # 如果返回特定错误码，说明未开通统一账户
            if "not found" in error_msg.lower() or "no permission" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": [],
                    "message": "该账号未开通统一账户或没有持仓"
                })
            
            return jsonify({
                "success": False,
                "error": f"获取统一账户合约持仓信息失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"获取统一账户合约持仓信息异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取统一账户合约持仓信息异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/transfer-history', methods=['POST'])
@token_required
def get_portfolio_margin_transfer_history(current_user):
    """
    获取子账号的统一账户资金划转历史
    
    请求体:
    {
        "email": "子账号邮箱",
        "limit": 可选，返回记录数量限制
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        limit = data.get('limit', 50)  # 默认限制50条记录
        
        logger.info(f"准备获取子账号 {email} 的统一账户资金划转历史，限制 {limit} 条")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API获取统一账户划转历史
        params = {
            'limit': limit
        }
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/papi/v1/um/transfer'  # 币安统一账户UM合约划转历史API端点
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            transfer_data = response.get('data', [])
            
            logger.info(f"成功获取子账号 {email} 的统一账户资金划转历史，共 {len(transfer_data)} 条记录")
            return jsonify({
                "success": True,
                "data": transfer_data
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"获取统一账户资金划转历史失败: {error_msg}")
            
            # 如果返回特定错误码，说明未开通统一账户或无记录
            if "not found" in error_msg.lower() or "no permission" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": [],
                    "message": "该账号未开通统一账户或无划转记录"
                })
            
            return jsonify({
                "success": False,
                "error": f"获取统一账户资金划转历史失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"获取统一账户资金划转历史异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取统一账户资金划转历史异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/enable', methods=['POST'])
@token_required
def enable_portfolio_margin(current_user):
    """
    为子账号开通统一账户功能
    
    请求体:
    {
        "email": "子账号邮箱"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        logger.info(f"准备为子账号 {email} 开通统一账户功能")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API开通统一账户功能
        params = {}
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/sapi/v1/portfolio/pm/enable'  # 币安开通统一账户API端点
        
        response = client._send_request('POST', endpoint, signed=True, params=params)
        
        if response.get('success'):
            result_data = response.get('data', {})
            
            logger.info(f"成功为子账号 {email} 开通统一账户功能")
            return jsonify({
                "success": True,
                "data": result_data,
                "message": "成功开通统一账户功能"
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"开通统一账户功能失败: {error_msg}")
            
            # 如果已经开通，给出友好提示
            if "already" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": {"alreadyEnabled": True},
                    "message": "该账号已开通统一账户功能"
                })
            
            return jsonify({
                "success": False,
                "error": f"开通统一账户功能失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"开通统一账户功能异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"开通统一账户功能异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/um/leverage', methods=['POST'])
@token_required
def change_um_leverage(current_user):
    """
    为指定子账号调整U本位合约杠杆倍数
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对，例如BTCUSDT",
        "leverage": 整数杠杆倍数(1-125)
    }
    """
    try:
        data = request.json

        # 验证必需参数
        required_params = ['email', 'symbol', 'leverage']
        for param in required_params:
            if param not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必需参数: {param}"
                }), 400

        email = data.get('email')
        symbol = data.get('symbol')
        leverage = int(data.get('leverage'))
        
        # 验证杠杆倍数范围
        if leverage < 1 or leverage > 125:
            return jsonify({
                "success": False,
                "error": "杠杆倍数必须在1-125之间"
            }), 400
            
        logger.info(f"准备为子账号 {email} 的 {symbol} 调整杠杆倍数为 {leverage}")

        # 获取子账号客户端
        client = get_client_by_email(email)
        
        if not client:
            return jsonify({
                "success": False,
                "error": f"无法获取子账号 {email} 的API客户端"
            }), 400

        try:
            # 发送杠杆调整请求
            params = {
                'symbol': symbol,
                'leverage': leverage
            }
        
            # 使用API端点直接发送请求
            endpoint = '/papi/v1/um/leverage'  # 币安调整UM杠杆倍数API端点
            result = client._send_request('POST', endpoint, params=params, signed=True)
            
            # 记录并返回成功响应
            logger.info(f"成功调整子账号 {email} 的 {symbol} 杠杆倍数为 {leverage}")
            return jsonify({
                "success": True,
                "data": result,
                "message": f"成功调整 {symbol} 杠杆倍数为 {leverage}"
            })
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"调整杠杆倍数失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"调整杠杆倍数失败: {error_msg}"
            }), 400
    except Exception as e:
        logger.error(f"调整杠杆倍数接口异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/um/batch-leverage', methods=['POST'])
@token_required
def batch_change_um_leverage(current_user):
    """
    批量设置多个子账号的U本位合约杠杆倍数
    
    请求体:
    {
        "emails": ["子账号1邮箱", "子账号2邮箱", ...],
        "symbol": "交易对，例如BTCUSDT",
        "leverage": 整数杠杆倍数(1-125),
        "contractType": "合约类型，UM(U本位)或CM(币本位)"
    }
    """
    try:
        data = request.json
        
        # 验证必需参数
        required_params = ['emails', 'symbol', 'leverage']
        for param in required_params:
            if param not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必需参数: {param}"
                }), 400
        
        emails = data.get('emails', [])
        symbol = data.get('symbol')
        leverage = int(data.get('leverage'))
        contract_type = data.get('contractType', 'UM').upper()  # 默认为U本位
        
        # 验证emails参数
        if not isinstance(emails, list) or len(emails) == 0:
            return jsonify({
                "success": False,
                "error": "emails必须是非空数组"
            }), 400
        
        # 验证杠杆倍数范围
        if leverage < 1 or leverage > 125:
            return jsonify({
                "success": False,
                "error": "杠杆倍数必须在1-125之间"
            }), 400
            
        # 验证合约类型
        if contract_type not in ['UM', 'CM']:
            return jsonify({
                "success": False,
                "error": "合约类型必须为UM(U本位)或CM(币本位)"
            }), 400
        
        logger.info(f"准备为{len(emails)}个子账号批量设置{contract_type}合约杠杆倍数")
        
        # 结果存储
        results = []
        success_count = 0
        failed_count = 0
        
        # 逐个处理子账号
        for email in emails:
            try:
                # 获取子账号客户端
                client = get_client_by_email(email)
                
                if not client:
                    failed_count += 1
                    results.append({
                        "email": email,
                        "success": False,
                        "error": "无法获取API客户端"
                    })
                    continue
                
                # 根据合约类型选择不同的API端点和函数
                if contract_type == 'UM':
                    # U本位合约
                    result = client.set_um_leverage(symbol, leverage)
                else:
                    # 币本位合约
                    # 对于币本位合约，可能需要调整交易对格式
                    cm_symbol = symbol
                    if symbol.endswith('USDT'):
                        # 将BTCUSDT转换为BTCUSD_PERP格式
                        cm_symbol = symbol.replace('USDT', 'USD_PERP')
                        
                    result = client.set_coin_futures_leverage(cm_symbol, leverage)
                
                # 记录成功
                success_count += 1
                results.append({
                    "email": email,
                    "success": True,
                    "data": result
                })
                logger.info(f"成功为子账号 {email} 设置{contract_type}合约杠杆倍数 {leverage}")

            except Exception as e:
                        error_msg = str(e)
                        failed_count += 1
                        results.append({
                            "email": email,
                            "success": False,
                            "error": error_msg
                        })
                        logger.error(f"为子账号 {email} 设置杠杆倍数失败: {error_msg}")
        
        # 返回批量处理结果
        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "success_count": success_count,
                "failed_count": failed_count,
                "total": len(emails)
            },
            "message": f"批量设置杠杆倍数完成: 成功 {success_count} 个, 失败 {failed_count} 个"
        })
        
    except Exception as e:
        logger.error(f"批量设置杠杆倍数接口异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/cm/positions', methods=['POST'])
@token_required
def get_portfolio_margin_positions_cm(current_user):
    """
    获取子账号的统一账户币本位合约持仓信息
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对符号(可选)"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400

        # 验证必要参数
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少必要参数: email"
            }), 400

        email = data.get('email')
        symbol = data.get('symbol')  # 可选参数
        
        logger.info(f"准备获取子账号 {email} 的统一账户币本位合约持仓信息 {f'symbol={symbol}' if symbol else ''}")

        # 获取子账户API客户端
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400

        # 调用币安API获取统一账户币本位持仓信息
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        # 使用客户端直接发送请求到币安API
        endpoint = '/papi/v1/cm/account'  # 币安统一账户CM合约API端点
        
        response = client._send_request('GET', endpoint, signed=True, params=params)
        
        if response.get('success'):
            account_data = response.get('data', {})
            positions = account_data.get('positions', [])
            
            # 过滤零仓位
            non_zero_positions = []
            for position in positions:
                position_amt = float(position.get('positionAmt', '0'))
                # 只保留有仓位的交易对
                if position_amt != 0:
                    non_zero_positions.append(position)
            
            logger.info(f"成功获取子账号 {email} 的统一账户币本位合约持仓信息，共 {len(non_zero_positions)} 个持仓")
            return jsonify({
                "success": True,
                "data": non_zero_positions
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"获取统一账户币本位合约持仓信息失败: {error_msg}")
            
            # 如果返回特定错误码，说明未开通统一账户
            if "not found" in error_msg.lower() or "no permission" in error_msg.lower():
                return jsonify({
                    "success": True,
                    "data": [],
                    "message": "该账号未开通统一账户或没有币本位合约持仓"
                })
            
            return jsonify({
                "success": False,
                "error": f"获取统一账户币本位合约持仓信息失败: {error_msg}"
            })

    except Exception as e:
        logger.exception(f"获取统一账户币本位合约持仓信息异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取统一账户币本位合约持仓信息异常: {str(e)}"
        }), 500

@subaccounts_bp.route('/portfolio-margin/close-cm-position', methods=['POST'])
@token_required
def close_portfolio_margin_cm_position(current_user):
    """
    平仓子账号的统一账户币本位合约持仓
    
    请求体:
    {
        "email": "子账号邮箱",
        "symbol": "交易对符号",
        "positionAmt": "持仓数量",
        "positionSide": "持仓方向，必须为LONG或SHORT"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少请求体数据"
            }), 400
        required_fields = ['email', 'symbol', 'positionAmt', 'positionSide']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必要参数: {field}"
                }), 400
        email = data.get('email')
        symbol = data.get('symbol')
        position_amt = float(data.get('positionAmt'))
        position_side = data.get('positionSide')
        if position_side not in ['LONG', 'SHORT']:
            return jsonify({
                "success": False,
                "error": "必须指定positionSide，且只能为LONG或SHORT（双向持仓模式）"
            }), 400
        if position_amt == 0:
            return jsonify({
                "success": False,
                "error": "持仓数量不能为零"
            }), 400
        side = 'SELL' if position_side == 'LONG' else 'BUY'
        quantity = abs(position_amt)
        logger.info(f"准备平仓子账号 {email} 的币本位合约持仓: {symbol}, 数量: {quantity}, 方向: {side}, positionSide={position_side}")
        client = get_client_by_email(email)
        if not client:
            return jsonify({
                "success": False,
                "error": f"未找到子账号 {email} 的API密钥"
            }), 400
        positions_response = client._send_request('GET', '/papi/v1/cm/account', signed=True)
        if not positions_response.get('success'):
            return jsonify({
                "success": False,
                "error": f"获取持仓信息失败: {positions_response.get('error')}"
            }), 400
        account_data = positions_response.get('data', {})
        positions = account_data.get('positions', [])
        target_position = None
        for pos in positions:
            if pos.get('symbol') == symbol and float(pos.get('positionAmt', '0')) != 0:
                # 方向匹配
                if position_side == 'LONG' and float(pos.get('positionAmt', '0')) > 0:
                    target_position = pos
                    break
                elif position_side == 'SHORT' and float(pos.get('positionAmt', '0')) < 0:
                    target_position = pos
                    break
        if not target_position:
            return jsonify({
                "success": False,
                "error": f"未找到交易对 {symbol} 的 {position_side} 持仓"
            }), 404
        logger.info(f"已找到持仓: {target_position}")
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': str(quantity)
            # 币本位合约不需要positionSide参数
        }
        logger.info(f"币本位平仓请求参数: {json.dumps(params)}")
        endpoint = '/papi/v1/cm/order'
        response = client._send_request('POST', endpoint, params=params, signed=True)
        if response.get('success'):
            logger.info(f"成功平仓子账号 {email} 的币本位合约持仓: {symbol}")
            return jsonify({
                "success": True,
                "data": response.get('data')
            })
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"平仓币本位合约持仓失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"平仓币本位合约持仓失败: {error_msg}"
            })
    except Exception as e:
        logger.exception(f"平仓币本位合约持仓异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"平仓币本位合约持仓异常: {str(e)}"
        }), 500 