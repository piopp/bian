import logging
from flask import Blueprint, request, jsonify, redirect, url_for
from app.utils.auth import token_required
from app.services.binance_client import BinanceClient
import time

# 修改蓝图定义，添加URL前缀
market_bp = Blueprint('market', __name__, url_prefix='/api/market')
logger = logging.getLogger(__name__)

def get_subaccount_api_keys(email):
    """
    获取子账号API密钥
    
    参数:
    - email: 子账号邮箱
    
    返回:
    - (api_key, api_secret): 子账号API密钥对
    """
    from app.services.binance_client import get_sub_account_api_credentials
    
    # 从数据库获取子账号API密钥
    api_key, api_secret = get_sub_account_api_credentials(email)
    
    if not api_key or not api_secret:
        logger.error(f"未找到子账号 {email} 的API密钥设置，无法进行交易")
        return None, None
        
    logger.info(f"已获取子账号 {email} 的API密钥设置，将使用子账号自己的API密钥进行交易")
    return api_key, api_secret

@market_bp.route('/trade', methods=['POST'])
@token_required
def execute_trade(current_user):
    """
    执行交易
    
    请求体:
    {
        "email": "子账号邮箱",
        "marketType": "市场类型 (spot, margin, futures, portfolio_margin, portfolio_margin_um)",
        "symbol": "交易对",
        "side": "交易方向 (BUY, SELL)",
        "type": "订单类型 (LIMIT, MARKET)",
        "quantity": 数量,
        "price": 价格 (LIMIT订单必填),
        "useSubAccountApi": 是否强制使用子账号API (可选，布尔值),
        "leverage": 杠杆倍数 (可选，整数)
    }
    """
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体数据"
        }), 400
    
    try:
        # 获取请求参数
        email = data.get('email')
        market_type = data.get('marketType')
        symbol = data.get('symbol')
        side = data.get('side')
        order_type = data.get('type')
        quantity = data.get('quantity')
        price = data.get('price')
        quote_order_qty = data.get('quoteOrderQty')
        use_subaccount_api = data.get('useSubAccountApi', False)  # 新参数，默认False
        leverage = data.get('leverage')  # 新增杠杆倍数参数
        
        # 验证必要参数
        if not email:
            return jsonify({
                "success": False,
                "error": "必须提供子账号邮箱"
            }), 400
            
        if not market_type:
            return jsonify({
                "success": False,
                "error": "必须提供市场类型"
            }), 400
            
        if not symbol:
            return jsonify({
                "success": False,
                "error": "必须提供交易对"
            }), 400
            
        if side not in ['BUY', 'SELL']:
            return jsonify({
                "success": False,
                "error": f"无效的交易方向: {side}"
            }), 400
            
        if order_type not in ['LIMIT', 'MARKET']:
            return jsonify({
                "success": False,
                "error": f"无效的订单类型: {order_type}"
            }), 400
            
        if order_type == 'LIMIT' and not price:
            return jsonify({
                "success": False,
                "error": "LIMIT订单必须提供价格"
            }), 400
        
        # 验证数量参数
        if not quantity and not quote_order_qty:
            return jsonify({
                "success": False,
                "error": "必须提供交易数量(quantity)或交易金额(quoteOrderQty)参数中的至少一个"
            }), 400
        
        # 获取客户端实例
        # 如果use_subaccount_api为True，强制使用子账号API
        if use_subaccount_api:
            logger.info(f"按前端要求强制使用子账号API: {email}")
            api_key, api_secret = get_subaccount_api_keys(email)
            
            if not api_key or not api_secret:
                return jsonify({
                    "success": False,
                    "error": f"未找到子账号 {email} 的API密钥设置"
                }), 400
                
            client = BinanceClient(api_key, api_secret)
            client.is_subaccount = True
            client.subaccount_email = email
            logger.info(f"成功创建子账号 {email} 的API客户端")
        else:
            # 使用原来的客户端获取逻辑
            from app.services.binance_client import get_client_by_email
            client = get_client_by_email(email)
            
            if not client:
                return jsonify({
                    "success": False,
                    "error": f"无法获取子账号 {email} 的API客户端"
                }), 400
        
        # 构建通用请求参数
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
        }
        
        # 优化参数，确保格式正确
        trade_params = {
            'symbol': symbol,
            'side': side,
            'order_type': order_type,
            'price': price if order_type == 'LIMIT' else None,
            'time_in_force': data.get('timeInForce', 'GTC') if order_type == 'LIMIT' else None
        }
        
        # 添加数量参数 - 优先使用quantity，其次使用quoteOrderQty
        if quantity:
            # 确保quantity是字符串格式
            trade_params['quantity'] = str(quantity)
            logger.info(f"使用数量参数: quantity={trade_params['quantity']}")
        elif quote_order_qty:
            # 确保quoteOrderQty是字符串格式
            trade_params['quoteOrderQty'] = str(quote_order_qty)
            logger.info(f"使用金额参数: quoteOrderQty={trade_params['quoteOrderQty']}")
        
        # 根据市场类型调用不同的API
        if market_type == 'portfolio_margin':
            # 统一账户杠杆交易API
            logger.info(f"使用统一账户杠杆API下单: {trade_params}")
            result = client.place_portfolio_margin_order(**trade_params)
        elif market_type == 'portfolio_margin_um':
            # 统一账户UM合约交易API
            logger.info(f"使用统一账户UM合约API下单: {trade_params}")
            # 添加合约特有参数
            if data.get('reduceOnly'):
                params['reduceOnly'] = 'true'
                
            # 检查并确认是使用子账号的API
            if not hasattr(client, 'is_subaccount') or not client.is_subaccount:
                logger.warning(f"警告: 合约操作未使用子账号API，尝试将客户端标记为子账号API")
                client.is_subaccount = True
                client.subaccount_email = email
                
            logger.info(f"合约操作确认使用子账号 {email} 的API密钥")
            
            # 优化参数，确保格式正确
            trade_params = {
                'symbol': symbol,
                'side': side,
                'order_type': order_type,
                'price': price if order_type == 'LIMIT' else None,
                'time_in_force': data.get('timeInForce', 'GTC') if order_type == 'LIMIT' else None
            }
            
            # 添加数量参数 - 优先使用quantity，其次使用quoteOrderQty
            if quantity:
                # 确保quantity是字符串格式
                trade_params['quantity'] = str(quantity)
                logger.info(f"合约交易使用数量参数: quantity={trade_params['quantity']}")
            elif quote_order_qty:
                # 确保quoteOrderQty是字符串格式
                trade_params['quoteOrderQty'] = str(quote_order_qty)
                logger.info(f"合约交易使用金额参数: quoteOrderQty={trade_params['quoteOrderQty']}")
            
            # 将其他参数添加到trade_params
            for key, value in params.items():
                if key not in ['symbol', 'side', 'type', 'quantity', 'price', 'timeInForce', 'quoteOrderQty']:
                    trade_params[key] = value
            
            # 调用U本位合约下单接口
            result = client.place_portfolio_margin_order_um(**trade_params)
        elif market_type == 'portfolio_margin_cm':
            # 统一账户CM币本位合约交易API
            logger.info(f"使用统一账户CM币本位合约API下单: {trade_params}")
            
            # 检查并确认是使用子账号的API
            if not hasattr(client, 'is_subaccount') or not client.is_subaccount:
                logger.warning(f"警告: 币本位合约操作未使用子账号API，尝试将客户端标记为子账号API")
                client.is_subaccount = True
                client.subaccount_email = email
                
            logger.info(f"币本位合约操作确认使用子账号 {email} 的API密钥")
            
            # 如果指定了杠杆倍数，先设置杠杆倍数
            if leverage is not None:
                try:
                    # 当symbol格式为BTCUSD_PERP时，需要去掉_PERP后缀
                    if "_PERP" in symbol:
                        leverage_symbol = symbol.split("_")[0]
                    else:
                        leverage_symbol = symbol
                        
                    logger.info(f"设置{leverage_symbol}币本位合约杠杆倍数为: {leverage}x")
                    leverage_result = client.set_coin_futures_leverage(
                        symbol=leverage_symbol,
                        leverage=leverage
                    )
                    logger.info(f"设置杠杆倍数结果: {leverage_result}")
                except Exception as e:
                    logger.warning(f"设置杠杆倍数失败: {e}，将继续使用默认杠杆倍数")
            
            # 调用币本位合约下单接口(使用统一账户API)
            try:
                # 使用cm_new_order方法
                if quantity:
                    # 使用数量参数
                    result = client.cm_new_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        quantity=str(quantity),
                        price=price if order_type == 'LIMIT' else None,
                        timeInForce=data.get('timeInForce', 'GTC') if order_type == 'LIMIT' else None
                    )
                    logger.info(f"币本位合约交易使用数量参数: quantity={quantity}")
                else:
                    return jsonify({
                        "success": False,
                        "error": "币本位合约交易必须提供quantity参数"
                    }), 400
                
                # 处理响应结果
                if isinstance(result, dict) and "data" in result:
                    logger.info(f"币本位合约下单成功: {result}")
                    return jsonify({
                        "success": True,
                        "data": result["data"]
                    })
                else:
                    logger.error(f"币本位合约下单返回格式异常: {result}")
                    return jsonify(result)
            except Exception as e:
                logger.error(f"币本位合约下单异常: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"币本位合约下单异常: {str(e)}"
                })
        elif market_type == 'spot':
            # 现货市场
            logger.info(f"使用现货API下单: {trade_params}")
            result = client.place_order(**trade_params)
        else:
            return jsonify({
                "success": False,
                "error": f"不支持的市场类型: {market_type}，系统已升级为仅支持统一账户交易"
            }), 400
        
        if not result.get('success'):
            logger.error(f"下单失败: {result.get('error')}")
            return jsonify({
                "success": False,
                "error": f"下单失败: {result.get('error')}"
            }), 400
            
        # 记录订单
        try:
            # TODO: 添加订单记录到数据库
            pass
        except Exception as e:
            logger.error(f"记录订单信息时出错: {str(e)}")
            # 不影响主流程，继续返回成功结果
        
        return jsonify({
            "success": True,
            "data": result.get('data', {})
        })
            
    except Exception as e:
        logger.exception(f"执行交易时出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"执行交易时出错: {str(e)}"
        }), 500

@market_bp.route('/batch-trade', methods=['POST'])
@token_required
def execute_batch_trade(current_user):
    """
    批量执行交易
    
    请求体:
    {
        "accounts": ["子账号邮箱1", "子账号邮箱2", ...],
        "marketType": "市场类型 (portfolio_margin, portfolio_margin_um)",
        "symbol": "交易对",
        "side": "交易方向 (BUY, SELL)",
        "type": "订单类型 (LIMIT, MARKET)",
        "quantity": 数量,
        "price": 价格 (LIMIT订单必填),
        "useSubAccountApi": 是否强制使用子账号API (可选，布尔值),
        "useAsset": 使用的资产 (自定义参数，不直接传递给API),
        "margin_accounts": ["杠杆账户邮箱1", "杠杆账户邮箱2", ...],
        "leverage": 杠杆倍数 (可选，整数)
    }
    """
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体数据"
        }), 400
    
    # 验证必要参数
    required_fields = ['accounts', 'marketType', 'symbol', 'side', 'type']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"缺少必要参数: {field}"
            }), 400
    
    accounts = data.get('accounts', [])
    market_type = data.get('marketType')
    symbol = data.get('symbol')
    side = data.get('side')
    order_type = data.get('type')
    quantity = data.get('quantity')
    price = data.get('price')
    quote_order_qty = data.get('quoteOrderQty') # USDT金额
    use_subaccount_api = data.get('useSubAccountApi', False)  # 新参数，默认False
    use_asset = data.get('useAsset')
    leverage = data.get('leverage')  # 新增杠杆倍数参数
    
    # 获取前端传递的useAsset参数（合约交易时使用的资产）
    if use_asset:
        logger.info(f"批量交易: 前端请求使用资产 {use_asset} 进行交易，但此参数不直接传递给币安API")
    
    # 验证参数值
    if not accounts:
        return jsonify({
            "success": False,
            "error": "账号列表不能为空"
        }), 400
        
    if market_type not in ['portfolio_margin', 'portfolio_margin_um']:
        return jsonify({
            "success": False,
            "error": f"不支持的市场类型: {market_type}，系统已升级为仅支持统一账户交易"
        }), 400
        
    if side not in ['BUY', 'SELL']:
        return jsonify({
            "success": False,
            "error": f"无效的交易方向: {side}"
        }), 400
        
    if order_type not in ['LIMIT', 'MARKET']:
        return jsonify({
            "success": False,
            "error": f"无效的订单类型: {order_type}"
        }), 400
        
    if order_type == 'LIMIT' and not price:
        return jsonify({
            "success": False,
            "error": "LIMIT订单必须提供价格"
        }), 400
    
    # 验证数量参数
    if not quantity and not quote_order_qty:
        return jsonify({
            "success": False,
            "error": "必须提供交易数量(quantity)或交易金额(quoteOrderQty)参数中的至少一个"
        }), 400
    
    # 处理结果
    batch_result = []
    success_count = 0
    fail_count = 0
    
    # 批量执行交易
    for email in accounts:
        try:
            # 获取子账号API密钥
            api_key, api_secret = get_subaccount_api_keys(email)
            
            if not api_key or not api_secret:
                batch_result.append({
                    'email': email,
                    'symbol': symbol,
                    'success': False,
                    'error': "未找到子账号API密钥设置"
                })
                fail_count += 1
                continue
            
            # 创建客户端并强制标记为子账号API
            client = BinanceClient(api_key, api_secret)
            client.is_subaccount = True
            client.subaccount_email = email
            
            logger.info(f"批量交易: 强制使用子账号 {email} 的API密钥执行交易, 市场类型: {market_type}")
            
            # 构建通用请求参数
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
            }
            
            # 优化参数，确保格式正确
            trade_params = {
                'symbol': symbol,
                'side': side,
                'order_type': order_type,
                'price': price if order_type == 'LIMIT' else None,
                'time_in_force': data.get('timeInForce', 'GTC') if order_type == 'LIMIT' else None
            }
            
            # 添加数量参数 - 优先使用quantity，其次使用quoteOrderQty
            if quantity:
                # 确保quantity是字符串格式
                trade_params['quantity'] = str(quantity)
                logger.info(f"使用数量参数: quantity={trade_params['quantity']}")
            elif quote_order_qty:
                # 确保quoteOrderQty是字符串格式
                trade_params['quoteOrderQty'] = str(quote_order_qty)
                logger.info(f"使用金额参数: quoteOrderQty={trade_params['quoteOrderQty']}")
            
            # 根据不同市场类型执行交易
            if market_type == 'portfolio_margin':
                # 统一账户杠杆交易
                # 使用封装好的方法下单
                local_result = client.place_portfolio_margin_order(**trade_params)
                
                batch_result.append({
                    'email': email,
                    'symbol': symbol,
                    'success': local_result.get('success', False),
                    'data': local_result.get('data'),
                    'error': local_result.get('error')
                })
                
                if local_result.get('success', False):
                    success_count += 1
                else:
                    fail_count += 1
                
                # 跳过下面的处理，直接处理下一个订单
                continue
                
            elif market_type == 'portfolio_margin_um':
                # 统一账户UM合约交易
                
                # 添加合约特有参数
                if data.get('reduceOnly'):
                    params['reduceOnly'] = 'true'
                
                # 检查quantity是否存在，这是必须的
                if not quantity and quote_order_qty:
                    # 如果只提供了quoteOrderQty，需要计算quantity
                    try:
                        # 获取当前价格，计算数量
                        ticker_response = client._send_request(
                            'GET', 
                            '/api/v3/ticker/price', 
                            params={'symbol': symbol}
                        )
                        
                        if ticker_response.get('success'):
                            current_price = float(ticker_response.get('data', {}).get('price', 0))
                            if current_price > 0:
                                # 计算数量
                                calculated_quantity = float(quote_order_qty) / current_price
                                # 简单取整处理
                                quantity = str(round(calculated_quantity, 8))
                                logger.info(f"按USDT金额交易: 交易对={symbol}, 金额={quote_order_qty}USDT, 当前价格={current_price}, 计算数量={quantity}")
                    except Exception as e:
                        logger.error(f"计算交易数量出错: {str(e)}")
                
                # 如果仍然没有quantity，则报错
                if not quantity:
                    batch_result.append({
                        'email': email,
                        'symbol': symbol,
                        'success': False,
                        'error': "必须提供交易数量(quantity)"
                    })
                    fail_count += 1
                    continue
                
                # 优化参数，确保格式正确
                trade_params = {
                    'symbol': symbol,
                    'side': side,
                    'order_type': order_type,
                    'quantity': quantity,  # 确保quantity存在
                    'price': price if order_type == 'LIMIT' else None,
                    'time_in_force': data.get('timeInForce', 'GTC') if order_type == 'LIMIT' else None
                }
                
                # 将其他参数添加到trade_params
                for key, value in params.items():
                    if key not in ['symbol', 'side', 'type', 'quantity', 'price', 'timeInForce', 'quoteOrderQty']:
                        trade_params[key] = value
                
                # 调用U本位合约下单接口
                result = client.place_portfolio_margin_order_um(**trade_params)
                
                batch_result.append({
                    'email': email,
                    'symbol': symbol,
                    'success': result.get('success', False),
                    'data': result.get('data'),
                    'error': result.get('error')
                })
                
                if result.get('success', False):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                # 不支持的市场类型
                batch_result.append({
                    'email': email,
                    'symbol': symbol,
                    'success': False,
                    "error": f"不支持的市场类型: {market_type}，系统已升级为仅支持统一账户交易"
                })
                fail_count += 1
                continue
                
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"为账号 {email} 执行交易时出错: {error_msg}")
            batch_result.append({
                "email": email,
                "success": False,
                "error": error_msg
            })
            fail_count += 1
    
    return jsonify({
        "success": True,
        "data": {
            "total": len(accounts),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": batch_result,
            "request": {
                "marketType": market_type,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "price": price
            }
        }
    })

@market_bp.route('/ticker', methods=['GET'])
@token_required
def get_ticker(current_user):
    """
    获取交易对的价格信息 - 兼容性路由
    现在我们推荐使用 /api/trading-pairs/with-price 接口获取带价格的交易对数据
    
    查询参数:
    - symbol: 交易对 (例如: BTCUSDT, ETHUSDT)
    - type: 市场类型 (可选，例如：coin_futures, portfolio_margin_um)
    - email: 子账号邮箱 (可选)
    
    返回:
    - success: True/False
    - data: 包含价格信息的对象
    """
    try:
        # 获取查询参数
        symbol = request.args.get('symbol')
        market_type = request.args.get('type', 'spot')  # 默认为现货市场
        email = request.args.get('email')  # 子账号邮箱，可选
        
        # 参数验证
        if not symbol:
            return jsonify({
                "success": False,
                "error": "必须提供交易对参数symbol"
            }), 400
            
        logger.info(f"获取交易对 {symbol} 价格, 市场类型: {market_type}, 子账号: {email}")
        
        # 创建客户端
        client = None
        if email:
            # 尝试获取子账号API密钥
            from app.services.binance_client import get_client_by_email
            client = get_client_by_email(email)
            
        # 如果没有提供email或找不到子账号API密钥，使用主账号API
        if not client:
            from app.services.binance_client import get_binance_client
            client = get_binance_client(current_user.id)
            
        # 如果仍然没有客户端（API密钥不可用），则创建无API密钥的客户端
        if not client:
            logger.warning(f"无法获取有效的API客户端，使用无密钥客户端获取公开数据")
            client = BinanceClient('', '')
        
        # 标准化市场类型
        market_type = market_type.lower()
        
        # 市场类型映射
        coin_futures_types = ['coin_futures', 'dcoin_futures', 'coin-futures', 'delivery', 'delivery_futures']
        usdt_futures_types = ['futures', 'usdt_futures', 'usdt-futures', 'portfolio_margin_um', 'um']
        portfolio_margin_types = ['portfolio_margin', 'portfolio', 'margin']
        
        # 根据市场类型选择不同的API端点
        if market_type in coin_futures_types:
            # 币本位合约
            endpoint = 'dapi/v1/ticker/price'
            
            # 如果symbol不包含D（币本位标识），且不是特定指数，添加永续后缀
            if 'USDT' in symbol and '_' not in symbol and 'PERP' not in symbol:
                # 移除USDT并添加币本位后缀
                base_asset = symbol.replace('USDT', '')
                symbol = f"{base_asset}USD_PERP"  # 币本位永续合约的格式
                logger.info(f"转换为币本位合约格式: {symbol}")
                
            params = {'symbol': symbol}
            logger.info(f"使用币本位合约API查询价格，端点: {endpoint}, 参数: {params}")
            result = client._send_request('GET', endpoint, params=params)
            
        elif market_type in usdt_futures_types:
            # U本位合约
            endpoint = 'fapi/v1/ticker/price'
            params = {'symbol': symbol}
            logger.info(f"使用U本位合约API查询价格，端点: {endpoint}, 参数: {params}")
            result = client._send_request('GET', endpoint, params=params)
            
        elif market_type in portfolio_margin_types:
            # 统一账户/杠杆交易
            endpoint = 'api/v3/ticker/price'
            params = {'symbol': symbol}
            logger.info(f"使用统一账户API查询价格，端点: {endpoint}, 参数: {params}")
            result = client._send_request('GET', endpoint, params=params)
            
        else:
            # 默认使用现货市场
            params = {'symbol': symbol}
            endpoint = 'api/v3/ticker/price'
            logger.info(f"使用现货API查询价格，端点: {endpoint}, 参数: {params}")
            result = client._send_request('GET', endpoint, params=params)
            
        if not result.get('success'):
            logger.error(f"获取 {symbol} 价格失败: {result.get('error')}")
            return jsonify(result), 400
            
        # 记录结果
        logger.info(f"获取 {symbol} 价格成功: {result.get('data')}")
            
        # 尝试获取交易对的基础货币价格（如果需要）
        # 例如：如果请求BTCUSD但需要BTCUSDT价格
        if 'USDT' not in symbol and market_type == 'spot':
            try:
                # 构建USDT交易对并获取价格
                base_asset = symbol.split('USD')[0]
                if base_asset:
                    usdt_symbol = f"{base_asset}USDT"
                    
                    logger.info(f"尝试获取基础资产 {base_asset} 的USDT价格，使用交易对 {usdt_symbol}")
                    
                    usdt_params = {'symbol': usdt_symbol}
                    usdt_result = client._send_request('GET', endpoint, params=usdt_params)
                    
                    if usdt_result.get('success'):
                        # 将USDT价格添加到结果中
                        result['data']['usdt_price'] = usdt_result['data']['price']
                        logger.info(f"获取 {usdt_symbol} 价格成功: {usdt_result['data']['price']}")
            except Exception as e:
                logger.warning(f"获取USDT价格时出错 (非严重): {str(e)}")
                # 忽略此错误，不影响主流程
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"获取交易对价格失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取交易对价格失败: {str(e)}"
        }), 500

@market_bp.route('/binance/ticker-price', methods=['GET'])
@token_required
def get_binance_ticker_price(current_user):
    """
    获取币安实时价格
    
    查询参数:
    - symbol: 交易对 (例如: BTCUSDT, ETHUSDT)
    
    返回:
    - success: True/False
    - data: 包含价格信息的对象
    """
    try:
        # 获取查询参数
        symbol = request.args.get('symbol')
        
        # 参数验证
        if not symbol:
            return jsonify({
                "success": False,
                "error": "必须提供交易对参数symbol"
            }), 400
            
        logger.info(f"获取币安实时价格: {symbol}")
        
        # 创建无API密钥的客户端获取公开数据
        from app.services.binance_client import BinanceClient
        client = BinanceClient('', '')
        
        # 根据交易对确定市场类型
        endpoint = 'api/v3/ticker/price'  # 默认使用现货API
        params = {'symbol': symbol}
        
        # 检查是否为期货交易对
        if 'PERP' in symbol:
            # 币本位合约
            endpoint = 'dapi/v1/ticker/price'
        elif symbol.endswith('USDT') and any(c in symbol for c in ['BTC', 'ETH', 'BNB']):
            # 常见的U本位合约交易对
            # 尝试U本位合约API
            endpoint = 'fapi/v1/ticker/price'
        
        logger.info(f"使用API查询实时价格，端点: {endpoint}, 参数: {params}")
        result = client._send_request('GET', endpoint, params=params)
        
        if not result.get('success'):
            # 如果第一次尝试失败，尝试其他市场类型
            if endpoint == 'fapi/v1/ticker/price':
                # 尝试现货市场
                endpoint = 'api/v3/ticker/price'
                logger.info(f"U本位合约查询失败，尝试现货API，端点: {endpoint}")
                result = client._send_request('GET', endpoint, params=params)
            elif endpoint == 'api/v3/ticker/price':
                # 尝试U本位合约
                endpoint = 'fapi/v1/ticker/price'
                logger.info(f"现货API查询失败，尝试U本位合约API，端点: {endpoint}")
                result = client._send_request('GET', endpoint, params=params)
        
        if not result.get('success'):
            logger.error(f"获取 {symbol} 实时价格失败: {result.get('error')}")
            return jsonify(result), 400
            
        # 记录结果
        logger.info(f"获取 {symbol} 实时价格成功: {result.get('data')}")
            
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"获取币安实时价格失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取币安实时价格失败: {str(e)}"
        }), 500
