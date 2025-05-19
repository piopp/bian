from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
import time
from app.services.binance_client import BinanceClient, get_sub_account_api_credentials
from app.models.account import SubAccountAPISettings
from binance.exceptions import BinanceAPIException
from app.api.auth import login_required, authenticated_user
from app.utils.logger import log_info, log_error, log_warning, log_parallel_execution

logger = logging.getLogger(__name__)
portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/api/portfolio')

@portfolio_bp.route('/cm/grid-trade', methods=['POST'])
def cm_grid_trade():
    """
    统一账户下的币本位合约网格交易
    
    请求参数:
    {
        "email": "子账号邮箱",
        "user_id": "用户ID",
        "symbol": "交易对",
        "price": "限价单价格",
        "order_type": "订单类型(LIMIT)",
        "leverage": "杠杆倍数",
        "single_amount": "单笔数量",
        "orders_count": "订单数量",
        "interval": "时间间隔(秒)",
        "contract_type": "合约类型(coin_futures)",
        "both_sides": "是否同时建立多空仓位"
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        required_fields = ['email', 'symbol', 'price', 'single_amount', 'orders_count']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"缺少必填参数: {field}"})
        
        # 提取参数
        email = data.get('email')
        symbol = data.get('symbol')
        price = float(data.get('price'))
        single_amount = float(data.get('single_amount'))
        orders_count = int(data.get('orders_count'))
        interval = int(data.get('interval', 5))
        leverage = int(data.get('leverage', 1))
        both_sides = data.get('both_sides', True)
        
        # 验证参数
        if price <= 0:
            return jsonify({"success": False, "message": "价格必须大于0"})
        
        if single_amount <= 0:
            return jsonify({"success": False, "message": "单笔数量必须大于0"})
        
        if orders_count <= 0:
            return jsonify({"success": False, "message": "订单数量必须大于0"})
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "message": "子账号API未配置或不可用"
            })
        
        client = BinanceClient(api_key, api_secret)
        
        # 尝试使用统一账户API创建网格订单
        try:
            # 创建多个订单
            created_orders = []
            
            # 计算总订单数
            total_orders = orders_count
            
            for i in range(total_orders):
                if both_sides:
                    # 买入订单（多仓）
                    buy_order = client.cm_new_order(
                        symbol=symbol,
                        side="BUY",
                        type="LIMIT",
                        quantity=single_amount,
                        price=price,
                        timeInForce="GTC"
                    )
                    created_orders.append({
                        "side": "BUY",
                        "order_id": buy_order.get('orderId'),
                        "price": price,
                        "quantity": single_amount
                    })
                    
                    # 卖出订单（空仓）
                    sell_order = client.cm_new_order(
                        symbol=symbol,
                        side="SELL",
                        type="LIMIT",
                        quantity=single_amount,
                        price=price,
                        timeInForce="GTC"
                    )
                    created_orders.append({
                        "side": "SELL",
                        "order_id": sell_order.get('orderId'),
                        "price": price,
                        "quantity": single_amount
                    })
                else:
                    # 只创建买入订单
                    buy_order = client.cm_new_order(
                        symbol=symbol,
                        side="BUY",
                        type="LIMIT",
                        quantity=single_amount,
                        price=price,
                        timeInForce="GTC"
                    )
                    created_orders.append({
                        "side": "BUY",
                        "order_id": buy_order.get('orderId'),
                        "price": price,
                        "quantity": single_amount
                    })
                
                # 添加时间间隔
                if i < total_orders - 1:
                    time.sleep(interval)
            
            return jsonify({
                "success": True,
                "message": f"成功创建{len(created_orders)}个网格订单",
                "data": {
                    "orders": created_orders
                }
            })
        
        except BinanceAPIException as e:
            if "not supported" in str(e).lower() or "upgraded" in str(e).lower():
                # 币安API不支持直接操作币本位合约，需要通过统一账户API
                return jsonify({
                    "success": False,
                    "message": "不支持的市场类型: coin_futures，系统已升级为仅支持统一账户交易"
                })
            else:
                logger.error(f"币安API错误: {e}")
                return jsonify({
                    "success": False,
                    "message": f"币安API错误: {e}"
                })
    
    except Exception as e:
        logger.error(f"创建网格交易失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"创建网格交易失败: {str(e)}"
        })

@portfolio_bp.route('/um/new-order', methods=['POST'])
def um_new_order():
    """
    统一账户下的U本位合约下单
    
    请求参数:
    {
        "email": "子账号邮箱",
        "orders": [
            {
                "symbol": "交易对",
                "side": "BUY或SELL",
                "type": "订单类型(LIMIT,MARKET等)",
                "quantity": "数量",
                "price": "价格(LIMIT订单必填，若不提供则自动获取最新标记价)",
                "timeInForce": "订单有效期(GTC,IOC,FOK)",
                "leverage": "杠杆倍数(可选)",
                "positionSide": "持仓方向(LONG或SHORT，双向持仓模式必填)"
            },
            // 更多订单...
        ]
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        if not data.get('email'):
            return jsonify({"success": False, "error": "缺少必填参数: email"})
        
        if not data.get('orders') or not isinstance(data.get('orders'), list):
            return jsonify({"success": False, "error": "缺少必填参数: orders 或格式不正确"})
        
        # 提取参数
        email = data.get('email')
        orders = data.get('orders')
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            })
        
        client = BinanceClient(api_key, api_secret)
        
        # 直接设置为双向持仓模式，不再检测
        is_dual_side_position = True
        logger.info("默认使用双向持仓模式处理订单")
            
        # 处理订单
        buy_order_result = None
        sell_order_result = None
        
        # 查找BUY和SELL订单
        buy_order_params = None
        sell_order_params = None
        
        for order in orders:
            if order.get('side') == 'BUY':
                buy_order_params = order
            elif order.get('side') == 'SELL':
                sell_order_params = order
        
        # 验证订单参数
        if buy_order_params and not buy_order_params.get('symbol'):
            return jsonify({"success": False, "error": "多仓订单缺少交易对参数"})
        
        if buy_order_params and not buy_order_params.get('quantity'):
            return jsonify({"success": False, "error": "多仓订单缺少数量参数"})
        
        if sell_order_params and not sell_order_params.get('symbol'):
            return jsonify({"success": False, "error": "空仓订单缺少交易对参数"})
        
        if sell_order_params and not sell_order_params.get('quantity'):
            return jsonify({"success": False, "error": "空仓订单缺少数量参数"})
        
        # 获取当前交易对的最新价格
        symbol = None
        if buy_order_params:
            symbol = buy_order_params.get('symbol')
        elif sell_order_params:
            symbol = sell_order_params.get('symbol')
            
        if symbol:
            try:
                # 获取最新标记价格
                mark_price_params = {
                    'symbol': symbol,
                    'timestamp': int(time.time() * 1000)
                }
                mark_price_response = client._send_request('GET', '/fapi/v1/premiumIndex', params=mark_price_params)
                
                if mark_price_response.get('success'):
                    mark_price = mark_price_response.get('data', {}).get('markPrice')
                    logger.info(f"获取交易对 {symbol} 最新标记价: {mark_price}")
                    
                    # 对标记价进行精度控制 - 四舍五入保留2位小数
                    if mark_price:
                        mark_price = round(float(mark_price), 5)
                        
                        # 更新买单价格
                        if buy_order_params and (not buy_order_params.get('price') or buy_order_params.get('type') == 'MARKET'):
                            buy_order_params['price'] = str(mark_price)
                            logger.info(f"自动为多仓订单设置价格: {mark_price}")
            
                            # 如果是MARKET订单，修改为LIMIT订单以提高成功率
                            if buy_order_params.get('type') == 'MARKET':
                                buy_order_params['type'] = 'LIMIT'
                                buy_order_params['timeInForce'] = 'GTC'
                                logger.info(f"将多仓市价单转换为限价单，价格: {mark_price}")
                        
                        # 更新卖单价格
                        if sell_order_params and (not sell_order_params.get('price') or sell_order_params.get('type') == 'MARKET'):
                            sell_order_params['price'] = str(mark_price)
                            logger.info(f"自动为空仓订单设置价格: {mark_price}")
                            
                            # 如果是MARKET订单，修改为LIMIT订单以提高成功率
                            if sell_order_params.get('type') == 'MARKET':
                                sell_order_params['type'] = 'LIMIT'
                                sell_order_params['timeInForce'] = 'GTC'
                                logger.info(f"将空仓市价单转换为限价单，价格: {mark_price}")
                else:
                    logger.warning(f"获取标记价格失败: {mark_price_response.get('error')}")
            except Exception as e:
                logger.error(f"获取标记价格出错: {str(e)}")
            
        # 使用并行执行方式同时提交买单和卖单
        import threading
        import queue
        
        order_results = queue.Queue()
        
        def execute_buy_order():
            """执行买单的线程函数"""
            try:
                if not buy_order_params:
                    order_results.put(("buy", None))
                    return
                
                # 准备下单参数
                order_params = {
                    'symbol': buy_order_params.get('symbol'),
                    'side': 'BUY',
                    'order_type': buy_order_params.get('type', 'LIMIT'),
                    'quantity': buy_order_params.get('quantity'),
                    'price': buy_order_params.get('price'),
                    'time_in_force': buy_order_params.get('timeInForce', 'GTC')
                }
                
                # 添加持仓方向参数 - 双向持仓模式
                position_side = buy_order_params.get('positionSide', 'LONG')
                order_params['position_side'] = position_side
                logger.info(f"多仓下单使用持仓方向: {position_side}")
                
                result = client.place_portfolio_margin_order_um(**order_params)
                logger.info(f"多仓下单结果: {result}")
                order_results.put(("buy", result))
            except Exception as e:
                logger.error(f"多仓下单失败: {str(e)}")
                error_result = {
                    "success": False,
                    "error": f"API错误: {str(e)}"
                }
                order_results.put(("buy", error_result))
        
        def execute_sell_order():
            """执行卖单的线程函数"""
            try:
                if not sell_order_params:
                    order_results.put(("sell", None))
                    return
                
                # 准备下单参数
                order_params = {
                    'symbol': sell_order_params.get('symbol'),
                    'side': 'SELL',
                    'order_type': sell_order_params.get('type', 'LIMIT'),
                    'quantity': sell_order_params.get('quantity'),
                    'price': sell_order_params.get('price'),
                    'time_in_force': sell_order_params.get('timeInForce', 'GTC')
                }
                
                # 添加持仓方向参数 - 双向持仓模式
                position_side = sell_order_params.get('positionSide', 'SHORT')
                order_params['position_side'] = position_side
                logger.info(f"空仓下单使用持仓方向: {position_side}")
                
                result = client.place_portfolio_margin_order_um(**order_params)
                logger.info(f"空仓下单结果: {result}")
                order_results.put(("sell", result))
            except Exception as e:
                logger.error(f"空仓下单失败: {str(e)}")
                error_result = {
                    "success": False,
                    "error": f"API错误: {str(e)}"
                }
                order_results.put(("sell", error_result))
        
        # 创建并启动线程
        buy_thread = threading.Thread(target=execute_buy_order)
        sell_thread = threading.Thread(target=execute_sell_order)
        
        # 记录开始时间
        parallel_start_time = time.time()
        logger.info("开始并行执行买单和卖单")
        
        # 启动线程
        buy_thread.start()
        sell_thread.start()
        
        # 等待两个线程都完成
        buy_thread.join()
        sell_thread.join()
        
        # 记录结束时间
        parallel_end_time = time.time()
        logger.info("买单和卖单并行执行完成")
        
        # 获取结果
        results = {}
        while not order_results.empty():
            order_type, result = order_results.get()
            results[order_type] = result
        
        buy_order_result = results.get("buy")
        sell_order_result = results.get("sell")
        
        # 记录并行执行的详细日志
        log_parallel_execution("UM", parallel_start_time, parallel_end_time, buy_order_result, sell_order_result)
        
        # 判断整体成功状态
        is_success = (buy_order_result and buy_order_result.get('success')) or (sell_order_result and sell_order_result.get('success'))
        
        # 返回结果
        return jsonify({
            "success": is_success,
            "message": "统一账户U本位合约下单已处理",
            "data": {
                "buyOrder": buy_order_result.get('data') if buy_order_result and buy_order_result.get('success') else None,
                "sellOrder": sell_order_result.get('data') if sell_order_result and sell_order_result.get('success') else None,
                "buyOrderError": buy_order_result.get('error') if buy_order_result and not buy_order_result.get('success') else None,
                "sellOrderError": sell_order_result.get('error') if sell_order_result and not sell_order_result.get('success') else None,
                "positionMode": "双向持仓"
            }
        })
    
    except Exception as e:
        logger.error(f"统一账户U本位合约下单失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"统一账户U本位合约下单失败: {str(e)}"
        })

@portfolio_bp.route('/cm/new-order', methods=['POST'])
def cm_new_order():
    """
    统一账户下的币本位合约下单
    
    请求参数:
    {
        "email": "子账号邮箱",
        "orders": [
            {
                "symbol": "交易对",
                "side": "BUY或SELL",
                "type": "订单类型(LIMIT,MARKET等)",
                "quantity": "数量",
                "price": "价格(LIMIT订单必填，若不提供则自动获取最新标记价)",
                "timeInForce": "订单有效期(GTC,IOC,FOK)",
                "leverage": "杠杆倍数(可选)",
                "positionSide": "持仓方向(LONG或SHORT，双向持仓模式必填)"
            },
            // 更多订单...
        ]
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        if not data.get('email'):
            return jsonify({"success": False, "error": "缺少必填参数: email"})
        
        if not data.get('orders') or not isinstance(data.get('orders'), list):
            return jsonify({"success": False, "error": "缺少必填参数: orders 或格式不正确"})
        
        # 提取参数
        email = data.get('email')
        orders = data.get('orders')
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            })
        
        client = BinanceClient(api_key, api_secret)
        
        # 直接设置为双向持仓模式，不再检测
        is_dual_side_position = True
        logger.info("默认使用双向持仓模式处理订单")
        
        # 处理订单
        buy_order_result = None
        sell_order_result = None
        
        # 查找BUY和SELL订单
        buy_order_params = None
        sell_order_params = None
        
        for order in orders:
            if order.get('side') == 'BUY':
                buy_order_params = order
            elif order.get('side') == 'SELL':
                sell_order_params = order
        
        # 验证订单参数
        if buy_order_params and not buy_order_params.get('symbol'):
            return jsonify({"success": False, "error": "多仓订单缺少交易对参数"})
        
        if buy_order_params and not buy_order_params.get('quantity'):
            return jsonify({"success": False, "error": "多仓订单缺少数量参数"})
        
        if sell_order_params and not sell_order_params.get('symbol'):
            return jsonify({"success": False, "error": "空仓订单缺少交易对参数"})
        
        if sell_order_params and not sell_order_params.get('quantity'):
            return jsonify({"success": False, "error": "空仓订单缺少数量参数"})
        
        # 获取当前交易对的最新价格
        symbol = None
        if buy_order_params:
            symbol = buy_order_params.get('symbol')
        elif sell_order_params:
            symbol = sell_order_params.get('symbol')
            
        if symbol:
            try:
                # 获取最新标记价格 - 币本位使用/dapi/v1/premiumIndex接口
                mark_price_params = {
                    'symbol': symbol,
                    'timestamp': int(time.time() * 1000)
                }
                mark_price_response = client._send_request('GET', '/dapi/v1/premiumIndex', params=mark_price_params)
                
                if mark_price_response.get('success'):
                    mark_price = mark_price_response.get('data', {}).get('markPrice')
                    logger.info(f"获取交易对 {symbol} 最新标记价: {mark_price}")
                    
                    # 对标记价进行精度控制 - 四舍五入保留2位小数
                    if mark_price:
                        mark_price = round(float(mark_price), 5)
                        
                        # 更新买单价格
                        if buy_order_params and (not buy_order_params.get('price') or buy_order_params.get('type') == 'MARKET'):
                            buy_order_params['price'] = str(mark_price)
                            logger.info(f"自动为多仓订单设置价格: {mark_price}")
            
                            # 如果是MARKET订单，修改为LIMIT订单以提高成功率
                            if buy_order_params.get('type') == 'MARKET':
                                buy_order_params['type'] = 'LIMIT'
                                buy_order_params['timeInForce'] = 'GTC'
                                logger.info(f"将多仓市价单转换为限价单，价格: {mark_price}")
                        
                        # 更新卖单价格
                        if sell_order_params and (not sell_order_params.get('price') or sell_order_params.get('type') == 'MARKET'):
                            sell_order_params['price'] = str(mark_price)
                            logger.info(f"自动为空仓订单设置价格: {mark_price}")
                            
                            # 如果是MARKET订单，修改为LIMIT订单以提高成功率
                            if sell_order_params.get('type') == 'MARKET':
                                sell_order_params['type'] = 'LIMIT'
                                sell_order_params['timeInForce'] = 'GTC'
                                logger.info(f"将空仓市价单转换为限价单，价格: {mark_price}")
                else:
                    logger.warning(f"获取标记价格失败: {mark_price_response.get('error')}")
            except Exception as e:
                logger.error(f"获取标记价格出错: {str(e)}")
            
        # 使用并行执行方式同时提交买单和卖单
        import threading
        import queue
        
        order_results = queue.Queue()
        
        def execute_buy_order():
            """执行买单的线程函数"""
            try:
                if not buy_order_params:
                    order_results.put(("buy", None))
                    return
                
                result = client.cm_new_order(
                    symbol=buy_order_params.get('symbol'),
                    side='BUY',
                    type=buy_order_params.get('type', 'LIMIT'),
                    quantity=buy_order_params.get('quantity'),
                    price=buy_order_params.get('price'),
                    timeInForce=buy_order_params.get('timeInForce', 'GTC')
                )
                
                if isinstance(result, dict) and result.get('orderId'):
                    buy_order_success = True
                else:
                    buy_order_success = False
                    
                formatted_result = {
                    "success": buy_order_success,
                    "data": result
                }
                
                logger.info(f"多仓下单结果: {formatted_result}")
                order_results.put(("buy", formatted_result))
            except Exception as e:
                logger.error(f"多仓下单失败: {str(e)}")
                error_result = {
                    "success": False,
                    "error": f"多仓下单异常: {str(e)}"
                }
                order_results.put(("buy", error_result))
        
        def execute_sell_order():
            """执行卖单的线程函数"""
            try:
                if not sell_order_params:
                    order_results.put(("sell", None))
                    return
                
                result = client.cm_new_order(
                    symbol=sell_order_params.get('symbol'),
                    side='SELL',
                    type=sell_order_params.get('type', 'LIMIT'),
                    quantity=sell_order_params.get('quantity'),
                    price=sell_order_params.get('price'),
                    timeInForce=sell_order_params.get('timeInForce', 'GTC')
                )
                
                if isinstance(result, dict) and result.get('orderId'):
                    sell_order_success = True
                else:
                    sell_order_success = False
                    
                formatted_result = {
                    "success": sell_order_success,
                    "data": result
                }
                
                logger.info(f"空仓下单结果: {formatted_result}")
                order_results.put(("sell", formatted_result))
            except Exception as e:
                logger.error(f"空仓下单失败: {str(e)}")
                error_result = {
                    "success": False,
                    "error": f"空仓下单异常: {str(e)}"
                }
                order_results.put(("sell", error_result))
        
        # 创建并启动线程
        buy_thread = threading.Thread(target=execute_buy_order)
        sell_thread = threading.Thread(target=execute_sell_order)
        
        # 记录开始时间
        parallel_start_time = time.time()
        logger.info("开始并行执行币本位合约买单和卖单")
        
        # 启动线程
        buy_thread.start()
        sell_thread.start()
        
        # 等待两个线程都完成
        buy_thread.join()
        sell_thread.join()
        
        # 记录结束时间
        parallel_end_time = time.time()
        logger.info("币本位合约买单和卖单并行执行完成")
        
        # 获取结果
        results = {}
        while not order_results.empty():
            order_type, result = order_results.get()
            results[order_type] = result
        
        buy_order_result = results.get("buy")
        sell_order_result = results.get("sell")
        
        # 记录并行执行的详细日志
        log_parallel_execution("CM", parallel_start_time, parallel_end_time, buy_order_result, sell_order_result)
        
        # 判断整体成功状态
        is_success = (buy_order_result and buy_order_result.get('success')) or (sell_order_result and sell_order_result.get('success'))
        
        # 返回结果
        return jsonify({
            "success": is_success,
            "message": "统一账户币本位合约下单已处理",
            "data": {
                "buyOrder": buy_order_result.get('data') if buy_order_result and buy_order_result.get('success') else None,
                "sellOrder": sell_order_result.get('data') if sell_order_result and sell_order_result.get('success') else None,
                "buyOrderError": buy_order_result.get('error') if buy_order_result and not buy_order_result.get('success') else None,
                "sellOrderError": sell_order_result.get('error') if sell_order_result and not sell_order_result.get('success') else None
            }
        })
    
    except Exception as e:
        logger.error(f"统一账户币本位合约下单失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"统一账户币本位合约下单失败: {str(e)}"
        })

@portfolio_bp.route('/papi/v1/auto-collection', methods=['POST'])
@login_required
def auto_collection():
    """
    统一账户资金归集接口，将子账号资金归集到主账户
    请求参数: { "email": "子账号邮箱" }
    """
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({"success": False, "error": "缺少必填参数: email"}), 400
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({"success": False, "error": "子账号API未配置或不可用"}), 400
        client = BinanceClient(api_key, api_secret)
        # 实际调用币安资金归集API（如无则mock）
        try:
            # 假设BinanceClient有auto_collection方法
            result = client.auto_collection()  # 真实实现需对接币安PAPI
            return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"资金归集失败: {str(e)}")
            return jsonify({"success": False, "error": f"资金归集失败: {str(e)}"})
    except Exception as e:
        logger.error(f"资金归集接口异常: {str(e)}")
        return jsonify({"success": False, "error": f"资金归集接口异常: {str(e)}"}) 

@portfolio_bp.route('/papi/v1/repay-futures-switch', methods=['POST'])
@login_required
def repay_futures_switch():
    """
    统一账户设置合约还款模式（自动/手动）
    
    请求参数:
    {
        "email": "子账号邮箱",
        "autoRepay": true或false (true为自动还款，false为手动还款)
    }
    
    参考文档: https://developers.binance.com/docs/zh-CN/derivatives/portfolio-margin/account/Change-Auto-repay-futures-Status
    """
    try:
        data = request.json
        
        # 检查必填参数
        if not data.get('email'):
            return jsonify({"success": False, "error": "缺少必填参数: email"})
        
        # 提取参数
        email = data.get('email')
        auto_repay = data.get('autoRepay', False)
        
        log_info(f"设置子账号 {email} 还款模式为{'自动' if auto_repay else '手动'}还款")
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            })
        
        client = BinanceClient(api_key, api_secret)
        
        # 准备请求参数
        params = {
            'autoRepay': 'true' if auto_repay else 'false',
            'timestamp': int(time.time() * 1000)
        }
        
        try:
            # 调用币安API设置还款模式
            response = client._request_margin_api('POST', 'papi/v1/repay-futures-switch', True, data=params)
            
            return jsonify({
                "success": True,
                "message": f"已成功为子账号 {email} 设置{'自动' if auto_repay else '手动'}还款模式",
                "data": response
            })
            
        except BinanceAPIException as e:
            log_error(f"设置还款模式失败: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"币安API异常: {str(e)}"
            })
            
    except Exception as e:
        log_error(f"设置还款模式失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"设置还款模式失败: {str(e)}"
        })

@portfolio_bp.route('/papi/v1/repay-futures-switch', methods=['GET'])
@login_required
def get_repay_futures_switch():
    """
    查询自动清还合约负余额模式(USER_DATA)
    
    请求参数: 
    - email: 子账号邮箱
    
    返回值:
    {
        "autoRepay": true/false  // true代表自动清还合约负余额; false代表关闭自动清还合约负余额
    }
    
    参考文档: https://developers.binance.com/docs/zh-CN/derivatives/portfolio-margin/account/Change-Auto-repay-futures-Status
    """
    try:
        email = request.args.get('email')
        
        # 检查必填参数
        if not email:
            return jsonify({"success": False, "error": "缺少必填参数: email"}), 400
        
        log_info(f"查询子账号 {email} 的合约还款模式")
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 准备请求参数
        params = {
            'timestamp': int(time.time() * 1000),
            'recvWindow': 60000
        }
        
        try:
            # 调用币安API查询还款模式
            response = client._request_margin_api('GET', 'papi/v1/repay-futures-switch', True, data=params)
            
            if isinstance(response, dict) and 'autoRepay' in response:
                return jsonify({
                    "success": True,
                    "data": {
                        "autoRepay": response.get('autoRepay')
                    }
                })
            else:
                return jsonify({
                    "success": True,
                    "data": response
                })
            
        except BinanceAPIException as e:
            log_error(f"查询还款模式失败: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"币安API异常: {str(e)}"
            }), 400
            
    except Exception as e:
        log_error(f"查询还款模式失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"查询还款模式失败: {str(e)}"
        }), 500

@portfolio_bp.route('/papi/v1/futures-repay', methods=['POST'])
@login_required
def repay_futures_negative_balance():
    """
    手动偿还合约负余额 (全仓保证金模式)
    
    请求参数:
    {
        "email": "子账号邮箱",
        "coin": "还款币种，如USDT",
        "amount": "还款金额(可选)", 
        "allDebt": true或false (是否全额还款，true则忽略amount参数)
    }
    
    参考文档: https://developers.binance.com/docs/zh-CN/derivatives/portfolio-margin/account/Repay-futures-Negative-Balance
    """
    try:
        data = request.json
        
        # 检查必填参数
        if not data.get('email'):
            return jsonify({"success": False, "error": "缺少必填参数: email"}), 400
        
        if not data.get('coin'):
            return jsonify({"success": False, "error": "缺少必填参数: coin"}), 400
        
        # 提取参数
        email = data.get('email')
        coin = data.get('coin')
        amount = data.get('amount')
        all_debt = data.get('allDebt', False)
        
        log_info(f"为子账号 {email} 执行合约负余额还款，币种: {coin}, 全额还款: {all_debt}")
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 准备请求参数
        params = {
            'coin': coin,
            'timestamp': int(time.time() * 1000),
            'recvWindow': 60000
        }
        
        # 如果不是全额还款，添加金额参数
        if not all_debt and amount:
            params['amount'] = amount
        
        try:
            # 调用币安API执行还款
            response = client._request_margin_api('POST', 'papi/v1/repay-futures-negative-balance', True, data=params)
            
            if isinstance(response, dict) and 'status' in response:
                success = response.get('status') == 'SUCCESS' or response.get('status') == 'OK'
                return jsonify({
                    "success": success,
                    "message": "还款请求已处理",
                    "data": response
                })
            else:
                return jsonify({
                    "success": True,
                    "message": "还款请求已发送",
                    "data": response
                })
            
        except BinanceAPIException as e:
            log_error(f"执行合约负余额还款失败: {str(e)}")
            return jsonify({
                "success": False, 
                "error": f"币安API异常: {str(e)}"
            }), 400
            
    except Exception as e:
        log_error(f"执行合约负余额还款失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"执行合约负余额还款失败: {str(e)}"
        }), 500 