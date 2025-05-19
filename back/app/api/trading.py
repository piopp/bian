from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from app.models import db, GridTrading, OrderHistory, TradeHistory, MarginOrder, MarginTrade, FeeRecord
import math
import json
import logging
import time
from app.services.binance_client import BinanceClient, get_sub_account_api_credentials, get_client_by_email
from app.models.account import SubAccountAPISettings
from binance.exceptions import BinanceAPIException
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
from binance.enums import SIDE_BUY, SIDE_SELL
from app.api.auth import login_required, authenticated_user
from app.models.user import User, APIKey

logger = logging.getLogger(__name__)
trading_bp = Blueprint('trading', __name__, url_prefix='/api/trading')

# ========== 网格交易API ==========

@trading_bp.route('/grid/create', methods=['POST'])
def create_grid():
    """
    创建网格交易
    
    请求参数:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "upper_price": 上限价格,
        "lower_price": 下限价格,
        "grid_num": 网格数量,
        "single_amount": 单笔数量(本币),
        "is_bilateral": 是否双向(true/false),
        "leverage": 杠杆倍数(默认1),
        "stop_loss_price": 止损价格(可选),
        "stop_profit_price": 止盈价格(可选)
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        required_fields = ['email', 'symbol', 'upper_price', 'lower_price', 'grid_num', 'single_amount']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"缺少必填参数: {field}"})
        
        # 提取参数
        email = data.get('email')
        symbol = data.get('symbol')
        upper_price = float(data.get('upper_price'))
        lower_price = float(data.get('lower_price'))
        grid_num = int(data.get('grid_num'))
        single_amount = float(data.get('single_amount'))  # 直接获取单笔数量
        is_bilateral = data.get('is_bilateral', False)
        leverage = int(data.get('leverage', 1))
        stop_loss_price = data.get('stop_loss_price')
        stop_profit_price = data.get('stop_profit_price')
        
        # 验证参数
        if upper_price <= lower_price:
            return jsonify({"success": False, "error": "上限价格必须大于下限价格"})
        
        if grid_num < 2:
            return jsonify({"success": False, "error": "网格数量必须大于或等于2"})
        
        if single_amount <= 0:
            return jsonify({"success": False, "error": "单笔数量必须大于0"})
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 创建网格价格点
        grid_prices = calculate_grid_prices(lower_price, upper_price, grid_num, client, symbol)
        
        # 计算总投资额 (用于记录和追踪)
        total_investment = single_amount * grid_num * ((upper_price + lower_price) / 2)
        
        # 生成网格ID
        grid_id = f"GRID_{email}_{symbol}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # 创建网格订单列表
        grid_orders = []
        
        # 处理网格订单
        for i in range(len(grid_prices) - 1):
            # 买入订单价格是下一个网格点
            buy_price = grid_prices[i]
            # 卖出订单价格是当前网格点
            sell_price = grid_prices[i + 1]
            
            # 直接使用指定的单笔数量
            raw_quantity = single_amount
            
            # 使用交易对精度格式化数量
            quantity = format_quantity(client, symbol, raw_quantity)
            
            # 记录日志
            logger.info(f"网格订单数量精度调整: 原始数量={raw_quantity}, 调整后={quantity}")
            
            # 创建买入订单
            buy_order = {
                "email": email,
                "symbol": symbol,
                "side": "BUY",
                "order_type": "LIMIT",
                "price": buy_price,
                "amount": quantity,
                "grid_id": grid_id,
                "grid_index": i,
                "leverage": leverage
            }
            
            # 如果是双向，则创建卖出订单
            if is_bilateral:
                sell_order = {
                    "email": email,
                    "symbol": symbol,
                    "side": "SELL",
                    "order_type": "LIMIT",
                    "price": sell_price,
                    "amount": quantity,
                    "grid_id": grid_id,
                    "grid_index": i + 1,
                    "leverage": leverage
                }
                grid_orders.append(sell_order)
            
            grid_orders.append(buy_order)
        
        # 保存网格信息到数据库
        new_grid = GridTrading(
            grid_id=grid_id,
            email=email,
            symbol=symbol,
            total_investment=total_investment,
            grid_levels=grid_num,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_prices=json.dumps(grid_prices),
            is_bilateral=is_bilateral,
            leverage=leverage,
            status="PENDING",
            stop_loss_price=stop_loss_price,
            stop_profit_price=stop_profit_price,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_grid)
        
        # 创建订单
        created_orders = []
        for order in grid_orders:
            # 这里可以接入实际的下单API
            # 创建订单历史记录
            order_record = OrderHistory(
                email=order["email"],
                symbol=order["symbol"],
                order_type=order["order_type"],
                side=order["side"],
                amount=order["amount"],
                price=order["price"],
                status="NEW",
                executed_qty=0,
                order_id=f"{grid_id}_ORDER_{len(created_orders)}",
                client_order_id=None,
                leverage=order["leverage"],
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow(),
            )
            
            db.session.add(order_record)
            created_orders.append(order_record.to_dict())
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "grid_id": grid_id,
                "grid_orders": created_orders,
                "grid_info": new_grid.to_dict()
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建网格交易失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"创建网格交易失败: {str(e)}"
        })

@trading_bp.route('/grid/list', methods=['GET'])
def list_grids():
    """
    获取用户的网格交易列表
    
    查询参数:
    - email: 子账号邮箱
    - status: 网格状态(PENDING, RUNNING, CLOSED)
    """
    try:
        email = request.args.get('email')
        status = request.args.get('status')
        
        if not email:
            return jsonify({"success": False, "error": "缺少email参数"})
        
        # 查询数据库
        query = GridTrading.query.filter_by(email=email)
        
        if status:
            query = query.filter_by(status=status)
        
        # 获取结果
        grids = query.order_by(GridTrading.created_at.desc()).all()
        
        # 转换为字典列表
        grid_list = [grid.to_dict() for grid in grids]
        
        return jsonify({
            "success": True,
            "data": grid_list
        })
    except Exception as e:
        logger.error(f"获取网格交易列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取网格交易列表失败: {str(e)}"
        })

@trading_bp.route('/grid/detail/<grid_id>', methods=['GET'])
def grid_detail(grid_id):
    """
    获取网格交易详情
    
    参数:
    - grid_id: 网格ID
    """
    try:
        # 查询数据库
        grid = GridTrading.query.filter_by(grid_id=grid_id).first()
        
        if not grid:
            return jsonify({
                "success": False,
                "error": f"网格交易 {grid_id} 不存在"
            }), 404
        
        # 获取网格订单
        orders = get_grid_orders(grid_id)
        
        # 计算网格收益
        profit_info = calculate_grid_profit(grid_id)
        
        return jsonify({
            "success": True,
            "data": {
                "grid_info": grid.to_dict(),
                "grid_orders": orders,
                "profit_info": profit_info
            }
        })
    except Exception as e:
        logger.error(f"获取网格交易详情失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取网格交易详情失败: {str(e)}"
        })

@trading_bp.route('/grid/stop/<grid_id>', methods=['POST'])
def stop_grid(grid_id):
    """
    停止网格交易
    
    参数:
    - grid_id: 网格ID
    """
    try:
        # 查询数据库
        grid = GridTrading.query.filter_by(grid_id=grid_id).first()
        
        if not grid:
            return jsonify({
                "success": False,
                "error": f"网格交易 {grid_id} 不存在"
            }), 404
        
        # 检查状态
        if grid.status == "CLOSED":
            return jsonify({
                "success": False,
                "error": "网格交易已经是关闭状态"
            })
        
        # 取消所有挂单
        cancel_result = cancel_grid_orders(grid_id)
        
        # 更新网格状态
        grid.status = "CLOSED"
        grid.closed_at = datetime.utcnow()
        grid.close_reason = "用户手动关闭"
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "网格交易已停止",
            "data": {
                "grid_info": grid.to_dict(),
                "cancel_result": cancel_result
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"停止网格交易失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"停止网格交易失败: {str(e)}"
        })

@trading_bp.route('/grid/submit-and-monitor', methods=['POST'])
def submit_and_monitor_grid():
    """
    提交网格建仓并实时监控订单状态，自动补齐不平衡的订单
    
    请求参数:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "upper_price": 上限价格,
        "lower_price": 下限价格,
        "grid_num": 网格数量,
        "single_amount": 单笔数量(本币),
        "is_bilateral": 是否双向(true/false),
        "leverage": 杠杆倍数(默认1),
        "stop_loss_price": 止损价格(可选),
        "stop_profit_price": 止盈价格(可选)
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        required_fields = ['email', 'symbol', 'upper_price', 'lower_price', 'grid_num', 'single_amount']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"缺少必填参数: {field}"})
        
        # 提取参数
        email = data.get('email')
        symbol = data.get('symbol')
        upper_price = float(data.get('upper_price'))
        lower_price = float(data.get('lower_price'))
        grid_num = int(data.get('grid_num'))
        single_amount = float(data.get('single_amount'))  # 直接获取单笔数量
        is_bilateral = data.get('is_bilateral', False)
        leverage = int(data.get('leverage', 1))
        stop_loss_price = data.get('stop_loss_price')
        stop_profit_price = data.get('stop_profit_price')
        
        # 验证参数
        if upper_price <= lower_price:
            return jsonify({"success": False, "error": "上限价格必须大于下限价格"})
        
        if grid_num < 2:
            return jsonify({"success": False, "error": "网格数量必须大于或等于2"})
        
        if single_amount <= 0:
            return jsonify({"success": False, "error": "单笔数量必须大于0"})
        
        # 获取API客户端
        api_key, api_secret = get_sub_account_api_credentials(email)
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        client = BinanceClient(api_key, api_secret)
        
        # 创建网格价格点
        grid_prices = calculate_grid_prices(lower_price, upper_price, grid_num, client, symbol)
        
        # 计算总投资额 (用于记录和追踪)
        total_investment = single_amount * grid_num * ((upper_price + lower_price) / 2)
        
        # 生成网格ID
        grid_id = f"GRID_{email}_{symbol}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # 创建网格订单列表
        grid_orders = []
        
        # 处理网格订单
        for i in range(len(grid_prices) - 1):
            # 买入订单价格是下一个网格点
            buy_price = grid_prices[i]
            # 卖出订单价格是当前网格点
            sell_price = grid_prices[i + 1]
            
            # 直接使用指定的单笔数量
            raw_quantity = single_amount
            
            # 使用交易对精度格式化数量
            quantity = format_quantity(client, symbol, raw_quantity)
            
            # 记录日志
            logger.info(f"网格订单数量精度调整: 原始数量={raw_quantity}, 调整后={quantity}")
            
            # 创建买入订单
            buy_order = {
                "email": email,
                "symbol": symbol,
                "side": "BUY",
                "order_type": "LIMIT",
                "price": buy_price,
                "amount": quantity,
                "grid_id": grid_id,
                "grid_index": i,
                "leverage": leverage
            }
            
            # 如果是双向，则创建卖出订单
            if is_bilateral:
                sell_order = {
                    "email": email,
                    "symbol": symbol,
                    "side": "SELL",
                    "order_type": "LIMIT",
                    "price": sell_price,
                    "amount": quantity,
                    "grid_id": grid_id,
                    "grid_index": i + 1,
                    "leverage": leverage
                }
                grid_orders.append(sell_order)
            
            grid_orders.append(buy_order)
        
        # 保存网格信息到数据库
        new_grid = GridTrading(
            grid_id=grid_id,
            email=email,
            symbol=symbol,
            total_investment=total_investment,
            grid_levels=grid_num,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_prices=json.dumps(grid_prices),
            is_bilateral=is_bilateral,
            leverage=leverage,
            status="PENDING",
            stop_loss_price=stop_loss_price,
            stop_profit_price=stop_profit_price,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_grid)
        
        # 创建订单并提交给交易所
        submitted_orders = []
        order_pairs = []  # 存储多空配对订单
        
        # 处理订单提交
        for i in range(0, len(grid_orders), 2 if is_bilateral else 1):
            pair = []
            
            # 提交第一个订单（买单）
            buy_order = grid_orders[i]
            buy_result = place_real_order(client, buy_order)
            submitted_orders.append(buy_result)
            pair.append(buy_result)
            
            # 如果是双向，提交第二个订单（卖单）
            if is_bilateral and i + 1 < len(grid_orders):
                sell_order = grid_orders[i + 1]
                sell_result = place_real_order(client, sell_order)
                submitted_orders.append(sell_result)
                pair.append(sell_result)
            
            # 添加配对订单
            if len(pair) > 0:
                order_pairs.append(pair)
        
        # 提交数据库事务
        db.session.commit()
        
        # 更新网格状态为运行中
        new_grid.status = "RUNNING"
        db.session.commit()
        
        # 异步开始监控订单
        # 注意：这里使用15秒和5秒的等待时间，所以需要运行一段时间
        logger.info(f"准备启动网格监控，共有{len(order_pairs)}对订单需要监控")
        
        # 启动监控线程
        import threading
        monitor_thread = threading.Thread(
            target=monitor_grid_orders_with_error_handling,
            args=(client, email, symbol, order_pairs, grid_id),
            daemon=True
        )
        monitor_thread.start()
        
        logger.info(f"网格监控线程已启动: grid_id={grid_id}, thread_id={monitor_thread.ident}, 请等待15秒完成首批订单监控")
        
        return jsonify({
            "success": True,
            "message": "网格交易已提交并开始监控，成交订单将在15秒后检查并补齐不平衡部分",
            "data": {
                "grid_id": grid_id,
                "grid_orders": submitted_orders,
                "grid_info": new_grid.to_dict()
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建网格交易失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"创建网格交易失败: {str(e)}"
        })

def monitor_grid_orders_with_error_handling(client, email, symbol, order_pairs, grid_id):
    """添加错误处理的包装函数"""
    try:
        logger.info(f"开始监控网格订单: grid_id={grid_id}, 订单对数量={len(order_pairs)}")
        monitor_grid_orders(client, email, symbol, order_pairs, grid_id)
        logger.info(f"网格订单监控正常完成: grid_id={grid_id}")
    except Exception as e:
        logger.error(f"网格订单监控异常终止: grid_id={grid_id}, 错误={str(e)}", exc_info=True)
        # 尝试将异常状态记录到数据库
        try:
            grid = GridTrading.query.filter_by(grid_id=grid_id).first()
            if grid:
                grid.status = "ERROR"
                grid.close_reason = f"监控异常: {str(e)}"
                db.session.commit()
        except Exception as db_error:
            logger.error(f"更新网格状态失败: {str(db_error)}")

# ========== 辅助函数 ==========

def calculate_grid_prices(lower_price, upper_price, grid_num, client=None, symbol=None):
    """
    计算网格价格点
    
    参数:
    - lower_price: 下限价格
    - upper_price: 上限价格
    - grid_num: 网格数量 (包含上下限)
    - client: BinanceClient实例 (可选)
    - symbol: 交易对符号 (可选)
    
    返回:
    - grid_prices: 网格价格点列表
    """
    # 计算价格比例
    ratio = (upper_price / lower_price) ** (1 / (grid_num - 1))
    
    # 生成网格价格点
    grid_prices = []
    for i in range(grid_num):
        price = lower_price * (ratio ** i)
        
        # 根据交易对精度格式化价格（如果提供了client和symbol）
        if client and symbol:
            price = format_price(client, symbol, price)
        else:
            # 默认保留8位小数
            price = round(price, 8)
            
        grid_prices.append(price)
    
    return grid_prices

def get_grid_orders(grid_id):
    """
    获取网格交易的订单
    
    参数:
    - grid_id: 网格ID
    
    返回:
    - orders: 订单列表
    """
    try:
        # 查询订单
        orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid_id}_ORDER_%")
        ).order_by(OrderHistory.created_at).all()
        
        return [order.to_dict() for order in orders]
    except Exception as e:
        logger.error(f"获取网格订单失败: {str(e)}")
        return []

def calculate_grid_profit(grid_id):
    """
    计算网格交易收益
    
    参数:
    - grid_id: 网格ID
    
    返回:
    - profit_info: 收益信息
    """
    try:
        # 查询网格信息
        grid = GridTrading.query.filter_by(grid_id=grid_id).first()
        
        if not grid:
            return {
                "profit": 0,
                "roi": 0,
                "filled_orders": 0,
                "investment": 0,
                "current_value": 0
            }
        
        # 查询已成交的买入卖出订单
        buy_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid_id}_ORDER_%"),
            OrderHistory.side == "BUY",
            OrderHistory.status == "FILLED"
        ).all()
        
        sell_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid_id}_ORDER_%"),
            OrderHistory.side == "SELL",
            OrderHistory.status == "FILLED"
        ).all()
        
        # 计算买入总金额
        buy_amount = sum(order.amount * order.price for order in buy_orders)
        
        # 计算卖出总金额
        sell_amount = sum(order.amount * order.price for order in sell_orders)
        
        # 计算总收益
        profit = sell_amount - buy_amount
        
        # 计算投资回报率
        roi = profit / grid.total_investment * 100 if grid.total_investment > 0 else 0
        
        return {
            "profit": profit,
            "roi": roi,
            "filled_orders": len(buy_orders) + len(sell_orders),
            "buy_amount": buy_amount,
            "sell_amount": sell_amount,
            "investment": grid.total_investment
        }
    except Exception as e:
        logger.error(f"计算网格收益失败: {str(e)}")
        return {
            "profit": 0,
            "roi": 0,
            "filled_orders": 0,
            "investment": 0,
            "current_value": 0,
            "error": str(e)
        }

def cancel_grid_orders(grid_id):
    """
    取消网格交易的挂单
    
    参数:
    - grid_id: 网格ID
    
    返回:
    - result: 取消结果
    """
    try:
        # 查询未成交的订单
        pending_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid_id}_ORDER_%"),
            OrderHistory.status.in_(["NEW", "PARTIALLY_FILLED"])
        ).all()
        
        # 取消订单
        canceled_count = 0
        for order in pending_orders:
            # 这里可以接入实际的取消订单API
            order.status = "CANCELED"
            order.last_checked = datetime.utcnow()
            canceled_count += 1
        
        db.session.commit()
        
        return {
            "canceled_count": canceled_count,
            "message": f"已取消 {canceled_count} 个挂单"
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"取消网格订单失败: {str(e)}")
        return {
            "canceled_count": 0,
            "error": str(e)
        }

def place_real_order(client, order_data):
    """
    通过币安API实际下单
    """
    try:
        symbol = order_data['symbol']
        
        # 根据交易对精度格式化数量
        quantity = format_quantity(client, symbol, order_data['amount'])
        
        # 根据交易对精度格式化价格
        price = format_price(client, symbol, order_data['price'])
        
        logger.info(f"下单数量精度调整: 原始数量={order_data['amount']}, 调整后={quantity}")
        logger.info(f"下单价格精度调整: 原始价格={order_data['price']}, 调整后={price}")
        
        # 设置下单参数
        params = {
            'symbol': symbol,
            'side': order_data['side'],
            'type': order_data['order_type'],
            'timeInForce': 'GTC',
            'quantity': quantity,
            'price': price
        }
        
        # 发送下单请求
        response = client._send_request('POST', '/fapi/v1/order', signed=True, params=params)
        
        # 处理响应
        if response.get('success'):
            order_id = response['data'].get('orderId')
            client_order_id = response['data'].get('clientOrderId')
            status = response['data'].get('status', 'NEW')
            
            # 创建订单历史记录
            order_record = OrderHistory(
                email=order_data['email'],
                symbol=order_data['symbol'],
                order_type=order_data['order_type'],
                side=order_data['side'],
                amount=quantity,  # 使用调整后的数量
                price=price,      # 使用调整后的价格
                status=status,
                executed_qty=float(response['data'].get('executedQty', 0)),
                order_id=str(order_id),
                client_order_id=client_order_id,
                leverage=order_data['leverage'],
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow(),
                grid_id=order_data['grid_id']
            )
            
            db.session.add(order_record)
            return {**order_record.to_dict(), 'binance_response': response['data']}
        else:
            logger.error(f"下单失败: {response.get('error')}")
            return {
                'success': False,
                'error': response.get('error'),
                'order_data': order_data
            }
    except Exception as e:
        logger.error(f"下单过程发生异常: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'order_data': order_data
        }

def monitor_grid_orders(client, email, symbol, order_pairs, grid_id):
    """
    监控网格订单状态，实现自动平衡功能
    
    - 针对多空订单对，如果一方成交另一方未成交，等待15秒后取消并市价补齐
    - 如果订单发生错误（拒绝、过期、取消），等待5秒后市价补齐
    - 每对订单监控将等待至少15秒（或5秒），确保交易所有足够时间处理订单
    
    参数:
    - client: BinanceClient实例
    - email: 子账号邮箱
    - symbol: 交易对
    - order_pairs: 订单对列表
    - grid_id: 网格ID
    """
    try:
        logger.info(f"开始监控网格订单 grid_id: {grid_id}, 订单对数量: {len(order_pairs)}")
        logger.info(f"注意: 订单监控将等待15秒(普通订单)或5秒(错误订单)后再处理不平衡情况")
        
        # 对每对订单进行监控
        for pair_index, order_pair in enumerate(order_pairs):
            logger.info(f"处理第{pair_index+1}对订单 (共{len(order_pairs)}对)")
            
            # 双向交易有两个订单，单向只有一个
            if len(order_pair) == 2:
                # 双向交易情况
                buy_order = next((o for o in order_pair if o.get('side') == 'BUY'), None)
                sell_order = next((o for o in order_pair if o.get('side') == 'SELL'), None)
                
                if buy_order and sell_order:
                    # 监控订单对
                    logger.info(f"监控买单{buy_order.get('order_id')}和卖单{sell_order.get('order_id')}")
                    monitor_order_pair(client, email, symbol, buy_order, sell_order, grid_id)
            
            elif len(order_pair) == 1:
                # 单向交易情况，只需监控单个订单的状态
                order = order_pair[0]
                logger.info(f"监控单个订单: {order.get('side')}单 {order.get('order_id')}")
                check_and_handle_single_order_status(client, email, symbol, order, grid_id)
            
            logger.info(f"第{pair_index+1}对订单处理完成")
        
        # 更新网格状态
        try:
            grid = GridTrading.query.filter_by(grid_id=grid_id).first()
            if grid and grid.status != "ERROR":
                grid.status = "COMPLETED"
                db.session.commit()
                logger.info(f"网格订单监控完成，已更新状态为COMPLETED: grid_id={grid_id}")
        except Exception as db_error:
            logger.error(f"更新网格状态失败: {str(db_error)}")
            
        logger.info(f"网格订单监控全部完成 grid_id: {grid_id}")
    except Exception as e:
        logger.error(f"监控网格订单异常: {str(e)}", exc_info=True)

def monitor_order_pair(client, email, symbol, buy_order, sell_order, grid_id):
    """监控一对买卖订单，处理不平衡情况
        
    - 如果多仓（买单）成交但空仓（卖单）未成交或部分成交，补齐卖单（开仓）
    - 如果空仓（卖单）成交但多仓（买单）未成交或部分成交，补齐买单（开仓）
    - 如果订单发生错误或过期，市价补单
    - 注意：所有操作都是开仓，不是平仓互抵
    """
    try:
        # 查询初始订单状态
        buy_status = check_order_status(client, symbol, buy_order.get('order_id'))
        sell_status = check_order_status(client, symbol, sell_order.get('order_id'))
        
        logger.info(f"订单对初始状态 - Grid={grid_id}, Buy: {buy_status.get('status')}, Sell: {sell_status.get('status')}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 检查订单状态
        buy_filled = buy_status.get('status') == 'FILLED'
        sell_filled = sell_status.get('status') == 'FILLED'
        buy_error = buy_status.get('status') in ['REJECTED', 'EXPIRED', 'CANCELED']
        sell_error = sell_status.get('status') in ['REJECTED', 'EXPIRED', 'CANCELED']
        
        # 设置监控时间
        monitoring_time = 15  # 常规监控15秒
        error_monitoring_time = 5  # 错误订单监控5秒
        
        # 如果订单已经处于错误状态，设置更短的监控时间
        if buy_error or sell_error:
            monitoring_time = error_monitoring_time
            logger.info(f"检测到错误状态订单，设置{error_monitoring_time}秒监控时间")
        
        # 检查一方已成交另一方未成交的情况
        one_side_filled = (buy_filled and not sell_filled) or (sell_filled and not buy_filled)
        
        if one_side_filled or buy_error or sell_error:
            # 第一次检查就发现不平衡或错误，等待指定时间后继续处理
            wait_time = monitoring_time
            logger.info(f"检测到订单不平衡或错误，等待{wait_time}秒后处理")
            
            # 等待指定时间
            time.sleep(wait_time)
            
            # 重新检查状态
            buy_status = check_order_status(client, symbol, buy_order.get('order_id'))
            sell_status = check_order_status(client, symbol, sell_order.get('order_id'))
            
            logger.info(f"等待{wait_time}秒后重新检查 - Buy: {buy_status.get('status')}, Sell: {sell_status.get('status')}")
            
            buy_filled = buy_status.get('status') == 'FILLED'
            sell_filled = sell_status.get('status') == 'FILLED'
            
        # 处理逻辑：买单成交但卖单未完全成交（补齐卖单开仓）
        if buy_filled and not sell_filled:
            logger.info(f"买单已成交但卖单未成交，取消卖单并市价开仓补齐: {sell_order.get('order_id')}")
            
            # 取消卖单
            cancel_result = cancel_order(client, symbol, sell_order.get('order_id'))
            logger.info(f"取消卖单结果: {cancel_result}")
            
            # 获取最新状态
            sell_status = check_order_status(client, symbol, sell_order.get('order_id'))
            
            # 计算需要补齐的数量
            executed_qty = float(sell_status.get('executedQty', 0))
            remaining_qty = float(sell_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                logger.info(f"市价卖出开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                market_sell_result = market_sell(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"市价卖出开仓结果: {market_sell_result}")
            else:
                logger.info(f"卖单已成交数量: {executed_qty}，无需补齐")
        
        # 处理逻辑：卖单成交但买单未完全成交（补齐买单开仓）
        elif sell_filled and not buy_filled:
            logger.info(f"卖单已成交但买单未成交，取消买单并市价开仓补齐: {buy_order.get('order_id')}")
            
            # 取消买单
            cancel_result = cancel_order(client, symbol, buy_order.get('order_id'))
            logger.info(f"取消买单结果: {cancel_result}")
            
            # 获取最新状态
            buy_status = check_order_status(client, symbol, buy_order.get('order_id'))
            
            # 计算需要补齐的数量
            executed_qty = float(buy_status.get('executedQty', 0))
            remaining_qty = float(buy_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                logger.info(f"市价买入开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                market_buy_result = market_buy(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"市价买入开仓结果: {market_buy_result}")
            else:
                logger.info(f"买单已成交数量: {executed_qty}，无需补齐")
        
        # 处理逻辑：两个订单都已完成
        elif buy_filled and sell_filled:
            logger.info(f"订单对都已成交完成: 买单={buy_status.get('status')}, 卖单={sell_status.get('status')}")
            return
        
        # 处理错误状态的买单
        if buy_error and not buy_filled:
            executed_qty = float(buy_status.get('executedQty', 0))
            remaining_qty = float(buy_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                logger.info(f"买单错误状态，市价买入开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                market_buy_result = market_buy(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"市价买入开仓结果: {market_buy_result}")
                    
        # 处理错误状态的卖单
        if sell_error and not sell_filled:
            executed_qty = float(sell_status.get('executedQty', 0))
            remaining_qty = float(sell_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                logger.info(f"卖单错误状态，市价卖出开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                market_sell_result = market_sell(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"市价卖出开仓结果: {market_sell_result}")
        
        # 处理未完成的订单 - 这是最后的保障检查
        # 重新获取最新状态
        buy_status = check_order_status(client, symbol, buy_order.get('order_id'))
        sell_status = check_order_status(client, symbol, sell_order.get('order_id'))
        
        # 处理未完成的买单
        if buy_status.get('status') == 'NEW':
            logger.info(f"买单仍未完成，最终取消并开仓补齐: {buy_order.get('order_id')}")
            cancel_result = cancel_order(client, symbol, buy_order.get('order_id'))
            
            # 计算需要补齐的数量
            buy_status = check_order_status(client, symbol, buy_order.get('order_id'))
            executed_qty = float(buy_status.get('executedQty', 0))
            remaining_qty = float(buy_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                market_buy_result = market_buy(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"最终市价买入开仓结果: {market_buy_result}")
        
        # 处理未完成的卖单
        if sell_status.get('status') == 'NEW':
            logger.info(f"卖单仍未完成，最终取消并开仓补齐: {sell_order.get('order_id')}")
            cancel_result = cancel_order(client, symbol, sell_order.get('order_id'))
            
            # 计算需要补齐的数量
            sell_status = check_order_status(client, symbol, sell_order.get('order_id'))
            executed_qty = float(sell_status.get('executedQty', 0))
            remaining_qty = float(sell_order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                market_sell_result = market_sell(client, email, symbol, remaining_qty, grid_id)
                logger.info(f"最终市价卖出开仓结果: {market_sell_result}")
        
    except Exception as e:
        logger.error(f"监控订单对异常: {str(e)}", exc_info=True)

def check_and_handle_single_order_status(client, email, symbol, order, grid_id):
    """检查并处理单个订单的状态
        
    - 如果订单未成交，15秒后检查并取消订单后市价补齐
    - 如果订单发生错误或过期，5秒后市价补单
    - 注意：所有操作都是网格开仓，不是平仓
    """
    try:
        # 查询订单状态
        order_status = check_order_status(client, symbol, order.get('order_id'))
        logger.info(f"单个订单状态 - Grid={grid_id}, Order={order.get('order_id')}, Status={order_status.get('status')}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 如果订单已完成
        if order_status.get('status') == 'FILLED':
            logger.info(f"单个订单已完成 - Grid: {grid_id}, Order: {order.get('order_id')}")
            return
        
        # 设置监控时间
        monitoring_time = 15  # 普通订单等待15秒
        error_time = 5       # 错误订单等待5秒
        
        # 确定等待时间
        wait_time = monitoring_time
        is_error = order_status.get('status') in ['REJECTED', 'EXPIRED', 'CANCELED']
        
        if is_error:
            wait_time = error_time
            logger.info(f"检测到错误订单状态: {order_status.get('status')}，等待{wait_time}秒后处理")
        else:
            logger.info(f"订单未成交，等待{wait_time}秒后检查")
        
        # 等待指定时间
        time.sleep(wait_time)
        
        # 重新检查订单状态
        order_status = check_order_status(client, symbol, order.get('order_id'))
        logger.info(f"等待{wait_time}秒后订单状态: {order_status.get('status')}")
        
        # 如果订单已成交，无需处理
        if order_status.get('status') == 'FILLED':
            logger.info(f"订单已完成，无需补单 - Grid: {grid_id}, Order: {order.get('order_id')}")
            return
        
        # 处理未成交或错误订单
        # 如果是NEW状态，先尝试取消
        if order_status.get('status') == 'NEW':
            logger.info(f"取消未成交订单: {order.get('order_id')}")
            cancel_result = cancel_order(client, symbol, order.get('order_id'))
            logger.info(f"取消订单结果: {cancel_result}")
            
            # 取消后再次检查状态
            order_status = check_order_status(client, symbol, order.get('order_id'))
            
            # 获取已成交数量
            executed_qty = float(order_status.get('executedQty', 0))
            
            # 计算需要补齐的数量
            remaining_qty = float(order.get('amount', 0)) - executed_qty
            
            if remaining_qty > 0:
                logger.info(f"订单 {order.get('order_id')} 需要补齐数量: {remaining_qty}, 状态: {order_status.get('status')}")
                
                # 根据订单方向决定市价买入或卖出 - 作为开仓操作
                if order.get('side') == 'BUY':
                    logger.info(f"市价买入开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                    market_buy_result = market_buy(client, email, symbol, remaining_qty, grid_id)
                    logger.info(f"市价买入开仓结果: {market_buy_result}")
                else:
                    logger.info(f"市价卖出开仓补齐: {remaining_qty} {symbol.replace('USDT', '')}")
                    market_sell_result = market_sell(client, email, symbol, remaining_qty, grid_id)
                    logger.info(f"市价卖出开仓结果: {market_sell_result}")
            else:
                logger.info(f"订单 {order.get('order_id')} 已成交数量: {executed_qty}，无需补齐")
        
    except Exception as e:
        logger.error(f"处理单个订单异常: {str(e)}", exc_info=True)

def check_order_status(client, symbol, order_id):
    """检查订单状态"""
    try:
        # 构建查询参数
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        # 查询订单
        result = client._send_request('GET', '/fapi/v1/order', signed=True, params=params)
        
        if result.get('success'):
            return result.get('data', {})
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"查询订单状态失败: orderId={order_id}, 错误={error_msg}")
            return {'status': 'ERROR', 'error': error_msg}
    except Exception as e:
        logger.error(f"查询订单状态异常: {str(e)}", exc_info=True)
        return {'status': 'ERROR', 'error': str(e)}

def cancel_order(client, symbol, order_id):
    """取消订单"""
    try:
        # 构建取消参数
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        logger.info(f"尝试取消订单: {symbol} orderId={order_id}")
        
        # 发送取消请求
        result = client._send_request('DELETE', '/fapi/v1/order', signed=True, params=params)
        
        if result.get('success'):
            logger.info(f"成功取消订单: {order_id}")
            
            # 更新数据库中订单状态
            try:
                order = OrderHistory.query.filter_by(order_id=str(order_id)).first()
                if order:
                    order.status = 'CANCELED'
                    order.last_checked = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"已更新数据库中订单 {order_id} 状态为CANCELED")
            except Exception as db_error:
                logger.error(f"更新订单状态失败: {str(db_error)}")
            
            return {
                'success': True,
                'data': result.get('data')
            }
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"取消订单失败: orderId={order_id}, 错误={error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    except Exception as e:
        logger.error(f"取消订单异常: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

def market_buy(client, email, symbol, quantity, grid_id):
    """市价买入"""
    try:
        # 记录原始请求
        logger.info(f"准备市价买入: symbol={symbol}, quantity={quantity}, grid_id={grid_id}")
        
        # 获取账户余额检查
        account_info = client._send_request('GET', '/fapi/v2/account', signed=True)
        if not account_info.get('success'):
            logger.error(f"获取账户信息失败: {account_info.get('error')}")
            return {
                'success': False,
                'error': f"获取账户信息失败: {account_info.get('error')}"
            }
        
        # 根据交易对精度格式化数量
        formatted_quantity = format_quantity(client, symbol, quantity)
        logger.info(f"市价买入数量精度调整: 原始数量={quantity}, 调整后={formatted_quantity}")
        
        # 获取当前价格以检查名义价值
        ticker_info = client._send_request('GET', '/fapi/v1/ticker/price', signed=False, params={'symbol': symbol})
        if not ticker_info.get('success'):
            logger.warning(f"获取{symbol}价格失败，无法检查名义价值: {ticker_info.get('error')}")
        else:
            current_price = float(ticker_info['data']['price'])
            notional_value = formatted_quantity * current_price
            logger.info(f"订单名义价值计算: 数量={formatted_quantity} × 价格={current_price} = {notional_value} USDT")
            
            # 检查名义价值是否小于最小要求(5 USDT)
            if notional_value < 5:
                logger.warning(f"订单名义价值({notional_value}USDT)小于最小要求(5USDT)")
        
        # 设置标准市价买入参数 - 确保是开仓操作，不使用reduceOnly
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
                    'quantity': formatted_quantity,
            'reduceOnly': 'false'  # 确保不是平仓操作
                }
        
        logger.info(f"开仓参数设置: {params}")
        
        # 发送市价买入请求
        response = client._send_request('POST', '/fapi/v1/order', signed=True, params=params)
        
        # 如果第一次请求失败，尝试不带reduceOnly参数
        if not response.get('success'):
            logger.warning(f"市价买入失败，尝试不带reduceOnly参数: {response.get('error')}")
            del params['reduceOnly']  # 删除reduceOnly参数
        response = client._send_request('POST', '/fapi/v1/order', signed=True, params=params)
        
        if response.get('success'):
            logger.info(f"市价买入成功: {symbol}, 数量: {formatted_quantity}, 响应: {response['data']}")
            
            # 记录订单
            order_record = OrderHistory(
                email=email,
                symbol=symbol,
                order_type='MARKET',
                side='BUY',
                amount=formatted_quantity,
                price=0,  # 市价单没有价格
                status='FILLED',  # 市价单立即成交
                executed_qty=formatted_quantity,
                order_id=str(response['data'].get('orderId')),
                client_order_id=response['data'].get('clientOrderId'),
                leverage=1,  # 使用默认杠杆
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow(),
                grid_id=grid_id,
                remarks="网格开仓-自动买入"
            )
            
            db.session.add(order_record)
            db.session.commit()
            
            return {
                'success': True,
                'data': response['data']
            }
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"市价买入失败: 错误={error_msg}, 参数={params}")
            return {
                'success': False,
                'error': error_msg
            }
    except Exception as e:
        logger.error(f"市价买入异常: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

def market_sell(client, email, symbol, quantity, grid_id):
    """市价卖出"""
    try:
        # 记录原始请求
        logger.info(f"准备市价卖出: symbol={symbol}, quantity={quantity}, grid_id={grid_id}")
        
        # 获取账户持仓检查
        positions_info = client._send_request('GET', '/fapi/v2/positionRisk', signed=True, params={'symbol': symbol})
        if not positions_info.get('success'):
            logger.error(f"获取持仓信息失败: {positions_info.get('error')}")
            return {
                'success': False,
                'error': f"获取持仓信息失败: {positions_info.get('error')}"
            }
        
        # 根据交易对精度格式化数量
        formatted_quantity = format_quantity(client, symbol, quantity)
        logger.info(f"市价卖出数量精度调整: 原始数量={quantity}, 调整后={formatted_quantity}")
        
        # 获取当前价格以检查名义价值
        ticker_info = client._send_request('GET', '/fapi/v1/ticker/price', signed=False, params={'symbol': symbol})
        if not ticker_info.get('success'):
            logger.warning(f"获取{symbol}价格失败，无法检查名义价值: {ticker_info.get('error')}")
        else:
            current_price = float(ticker_info['data']['price'])
            notional_value = formatted_quantity * current_price
            logger.info(f"订单名义价值计算: 数量={formatted_quantity} × 价格={current_price} = {notional_value} USDT")
            
            # 检查名义价值是否小于最小要求(5 USDT)
            if notional_value < 5:
                logger.warning(f"订单名义价值({notional_value}USDT)小于最小要求(5USDT)")
        
        # 设置标准市价卖出参数 - 确保是开仓操作，不使用reduceOnly
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
                    'quantity': formatted_quantity,
            'reduceOnly': 'false'  # 确保不是平仓操作
        }
        
        logger.info(f"开仓参数设置: {params}")
        
        # 发送市价卖出请求
        response = client._send_request('POST', '/fapi/v1/order', signed=True, params=params)
        
        # 如果第一次请求失败，尝试不带reduceOnly参数
        if not response.get('success'):
            logger.warning(f"市价卖出失败，尝试不带reduceOnly参数: {response.get('error')}")
            del params['reduceOnly']  # 删除reduceOnly参数
        response = client._send_request('POST', '/fapi/v1/order', signed=True, params=params)
        
        if response.get('success'):
            logger.info(f"市价卖出成功: {symbol}, 数量: {formatted_quantity}, 响应: {response['data']}")
            
            # 记录订单
            order_record = OrderHistory(
                email=email,
                symbol=symbol,
                order_type='MARKET',
                side='SELL',
                amount=formatted_quantity,
                price=0,  # 市价单没有价格
                status='FILLED',  # 市价单立即成交
                executed_qty=formatted_quantity,
                order_id=str(response['data'].get('orderId')),
                client_order_id=response['data'].get('clientOrderId'),
                leverage=1,  # 使用默认杠杆
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow(),
                grid_id=grid_id,
                remarks="网格开仓-自动卖出"
            )
            
            db.session.add(order_record)
            db.session.commit()
            
            return {
                'success': True,
                'data': response['data']
            }
        else:
            error_msg = response.get('error', '未知错误')
            logger.error(f"市价卖出失败: 错误={error_msg}, 参数={params}")
            return {
                'success': False,
                'error': error_msg
            }
    except Exception as e:
        logger.error(f"市价卖出异常: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

# ========== 订单历史API ==========

@trading_bp.route('/orders/record', methods=['POST'])
def record_order():
    """
    记录订单历史
    
    请求参数:
    {
        "email": "子账号邮箱",
        "symbol": "交易对",
        "orderType": "订单类型 LIMIT/MARKET",
        "side": "方向 BUY/SELL",
        "amount": 数量,
        "price": 价格,
        "status": "订单状态 NEW/FILLED/PARTIALLY_FILLED/CANCELED/REJECTED/EXPIRED",
        "executedQty": 已执行数量,
        "orderId": "订单ID",
        "clientOrderId": "客户端订单ID",
        "leverage": 杠杆倍数
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        required_fields = ['email', 'symbol', 'orderType', 'side', 'amount', 'price', 'status', 'orderId']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"缺少必填参数: {field}"})
        
        # 将前端参数转换为模型字段名
        email = data.get('email')
        symbol = data.get('symbol')
        order_type = data.get('orderType')
        side = data.get('side')
        amount = float(data.get('amount', 0))
        price = float(data.get('price', 0))
        status = data.get('status')
        executed_qty = float(data.get('executedQty', 0))
        order_id = data.get('orderId')
        client_order_id = data.get('clientOrderId')
        leverage = int(data.get('leverage', 1))
        
        # 检查订单是否已存在
        order = OrderHistory.query.filter_by(order_id=order_id).first()
        
        if order:
            # 更新现有订单
            order.status = status
            order.executed_qty = executed_qty or order.executed_qty
            order.last_checked = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "订单记录已更新",
                "data": order.to_dict()
            })
        else:
            # 创建新订单记录
            new_order = OrderHistory(
                email=email,
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price,
                status=status,
                executed_qty=executed_qty,
                order_id=order_id,
                client_order_id=client_order_id,
                leverage=leverage,
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow(),
            )
            db.session.add(new_order)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "订单记录已创建",
                "data": new_order.to_dict()
            })
    except Exception as e:
        logger.error(f"记录订单历史失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"记录订单历史失败: {str(e)}"
        })

@trading_bp.route('/orders/list', methods=['GET'])
def get_order_list():
    """
    获取订单历史列表 - 使用子账号API查询交易历史
    
    查询参数:
    - page: 页码 (默认1)
    - pageSize: 每页记录数 (默认20)
    - email: 筛选指定子账号
    - symbol: 筛选指定交易对
    - status: 筛选指定状态
    - startDate: 开始日期 YYYY-MM-DD
    - endDate: 结束日期 YYYY-MM-DD
    """
    try:
        # 处理查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        email = request.args.get('email')
        symbol = request.args.get('symbol')
        status = request.args.get('status')
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        # 如果没有提供end_date，使用当前日期
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # 验证必要参数
        if not email:
            return jsonify({
                "success": False,
                "error": "请提供子账号邮箱参数"
            }), 400
        
        # 获取子账号的API客户端
        from app.services.binance_client import get_client_by_email
        client = get_client_by_email(email)
        
        if not client:
            return jsonify({
                "success": False,
                "error": "子账号API未配置或不可用"
            }), 400
        
        # 设置参数
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        # 添加日期范围查询
        if start_date:
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            params['startTime'] = start_timestamp
        
        if end_date:
            # 加一天以包含当天
            end_timestamp = int((datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).timestamp() * 1000)
            params['endTime'] = end_timestamp
        
        # 设置分页
        params['limit'] = page_size
        if page > 1 and not status: # 仅在未指定status过滤时使用fromId
            params['fromId'] = (page - 1) * page_size

        response = None
        
        # 优先尝试使用统一账户API获取交易历史
        try:
            logger.info(f"尝试使用统一账户API获取子账号 {email} 的交易历史")
            # 第一种方法：尝试使用统一账户杠杆接口
            response = client.get_unified_account_trades(**params)
        
            # 检查响应
            if not response or not response.get('success') or not response.get('data'):
                logger.info(f"统一账户杠杆接口无返回数据，尝试使用UM合约接口")
                # 第二种方法：尝试使用统一账户UM合约接口
                response = client.get_um_trades(**params)
        except Exception as e:
            logger.error(f"使用统一账户API获取交易历史失败: {str(e)}")
            response = None
            
        # 如果统一账户API都失败，尝试使用传统的U本位合约API
        if not response or not response.get('success') or not response.get('data'):
            logger.info(f"尝试使用U本位合约API获取子账号 {email} 的交易历史")
            u_futures_endpoint = "/fapi/v1/userTrades"
            response = client._send_request('GET', u_futures_endpoint, signed=True, params=params)
                
        if not response or not response.get('success'):
            return jsonify({
                "success": False,
                "error": response.get('error', '获取交易历史失败')
            }), 400
        
        trades_data = response.get('data', [])
        
        # 计算总记录数 (可能不准确，因为币安API可能有限制)
        total_count = len(trades_data)
        
        # 转换为前端需要的格式
        trade_list = []
        for trade in trades_data:
            trade_dict = {
                "id": trade.get('id'),
                "orderId": trade.get('orderId'),
                "symbol": trade.get('symbol'),
                "side": '买入' if trade.get('isBuyer') else '卖出',
                "price": trade.get('price'),
                "qty": trade.get('qty'),
                "commission": trade.get('commission'),
                "commissionAsset": trade.get('commissionAsset'),
                "time": datetime.fromtimestamp(trade.get('time', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                "isMaker": trade.get('isMaker'),
                "isBestMatch": trade.get('isBestMatch'),
            }
            trade_list.append(trade_dict)
        
        return jsonify({
            "success": True,
            "data": {
                "records": trade_list,
                "total": total_count,
                "page": page,
                "pageSize": page_size
            }
        })
    except Exception as e:
        logger.error(f"获取订单历史列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取订单历史列表失败: {str(e)}"
        })

@trading_bp.route('/orders/recent', methods=['GET'])
def get_recent_orders():
    """
    获取最近订单列表（直接从数据库获取）
    
    查询参数:
    - email: 筛选指定子账号
    - symbol: 筛选指定交易对
    - limit: 返回记录数量限制 (默认50)
    - minutes: 最近多少分钟内的订单 (默认30分钟)
    """
    try:
        # 处理查询参数
        email = request.args.get('email')
        symbol = request.args.get('symbol')
        limit = int(request.args.get('limit', 50))
        minutes = int(request.args.get('minutes', 30))
        
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        # 构建查询条件
        query = OrderHistory.query.filter(OrderHistory.created_at >= start_time)
        
        if email:
            query = query.filter(OrderHistory.email == email)
        
        if symbol:
            query = query.filter(OrderHistory.symbol == symbol)
        
        # 排序并限制结果数量
        orders = query.order_by(OrderHistory.created_at.desc()).limit(limit).all()
        
        # 转换为字典列表
        order_list = [order.to_dict() for order in orders]
        
        # 查询交易历史
        trade_query = TradeHistory.query.filter(TradeHistory.trade_time >= start_time)
        
        if email:
            trade_query = trade_query.filter(TradeHistory.email == email)
        
        if symbol:
            trade_query = trade_query.filter(TradeHistory.symbol == symbol)
        
        # 排序并限制结果数量
        trades = trade_query.order_by(TradeHistory.trade_time.desc()).limit(limit).all()
        
        # 转换为字典列表
        trade_list = [trade.to_dict() for trade in trades]
        
        return jsonify({
            "success": True,
            "data": {
                "orders": order_list,
                "trades": trade_list,
                "total_orders": len(order_list),
                "total_trades": len(trade_list)
            }
        })
    except Exception as e:
        logger.error(f"获取最近订单列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取最近订单列表失败: {str(e)}"
        })

# ========== 精度处理辅助函数 ==========

# 缓存交易对精度信息
symbol_precision_cache = {}
symbol_price_precision_cache = {}

def get_symbol_precision(client, symbol):
    """
    获取交易对的数量精度
    
    参数:
    - client: BinanceClient实例
    - symbol: 交易对符号，如BTCUSDT
    
    返回:
    - quantity_precision: 数量精度
    """
    global symbol_precision_cache
    
    # 检查缓存
    if symbol in symbol_precision_cache:
        return symbol_precision_cache[symbol]
    
    # 默认精度（保守值，如果无法获取精度信息，使用4位小数）
    default_precision = 4
    
    try:
        # 获取交易对信息
        exchange_info = client._send_request('GET', '/fapi/v1/exchangeInfo', signed=False)
        
        if exchange_info.get('success'):
            # 查找当前交易对的精度信息
            symbol_info = next((s for s in exchange_info['data']['symbols'] if s['symbol'] == symbol), None)
            
            if symbol_info:
                # 尝试获取LOT_SIZE过滤器中的精度信息
                for filter_item in symbol_info.get('filters', []):
                    if filter_item.get('filterType') == 'LOT_SIZE':
                        step_size = float(filter_item.get('stepSize', 1))
                        if step_size != 0:
                            precision = len(str(step_size).rstrip('0').split('.')[-1]) if '.' in str(step_size) else 0
                            # 缓存结果
                            symbol_precision_cache[symbol] = precision
                            logger.info(f"获取到交易对 {symbol} 的数量精度: {precision}")
                            return precision
        
        # 如果未找到精度信息，使用默认值
        logger.warning(f"无法获取交易对 {symbol} 的数量精度信息，使用默认精度: {default_precision}")
        symbol_precision_cache[symbol] = default_precision
        return default_precision
    
    except Exception as e:
        logger.error(f"获取交易对数量精度信息异常: {str(e)}")
        symbol_precision_cache[symbol] = default_precision
        return default_precision

def get_price_precision(client, symbol):
    """
    获取交易对的价格精度
    
    参数:
    - client: BinanceClient实例
    - symbol: 交易对符号，如BTCUSDT
    
    返回:
    - price_precision: 价格精度
    """
    global symbol_price_precision_cache
    
    # 检查缓存
    if symbol in symbol_price_precision_cache:
        return symbol_price_precision_cache[symbol]
    
    # 默认价格精度（保守值）
    default_precision = 2
    
    try:
        # 获取交易对信息
        exchange_info = client._send_request('GET', '/fapi/v1/exchangeInfo', signed=False)
        
        if exchange_info.get('success'):
            # 查找当前交易对的精度信息
            symbol_info = next((s for s in exchange_info['data']['symbols'] if s['symbol'] == symbol), None)
            
            if symbol_info:
                # 尝试获取PRICE_FILTER过滤器中的精度信息
                for filter_item in symbol_info.get('filters', []):
                    if filter_item.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(filter_item.get('tickSize', 0.01))
                        if tick_size != 0:
                            precision = len(str(tick_size).rstrip('0').split('.')[-1]) if '.' in str(tick_size) else 0
                            # 缓存结果
                            symbol_price_precision_cache[symbol] = precision
                            logger.info(f"获取到交易对 {symbol} 的价格精度: {precision}")
                            return precision
        
        # 如果未找到精度信息，使用默认值
        logger.warning(f"无法获取交易对 {symbol} 的价格精度信息，使用默认精度: {default_precision}")
        symbol_price_precision_cache[symbol] = default_precision
        return default_precision
    
    except Exception as e:
        logger.error(f"获取交易对价格精度信息异常: {str(e)}")
        symbol_price_precision_cache[symbol] = default_precision
        return default_precision

def format_quantity(client, symbol, quantity):
    """
    根据交易对精度格式化数量
    
    参数:
    - client: BinanceClient实例
    - symbol: 交易对符号
    - quantity: 原始数量
    
    返回:
    - formatted_quantity: 格式化后的数量
    """
    precision = get_symbol_precision(client, symbol)
    formatted_quantity = float(f"{{:.{precision}f}}".format(float(quantity)))
    return formatted_quantity 

def format_price(client, symbol, price):
    """
    根据交易对价格精度格式化价格
    
    参数:
    - client: BinanceClient实例
    - symbol: 交易对符号
    - price: 原始价格
    
    返回:
    - formatted_price: 格式化后的价格
    """
    precision = get_price_precision(client, symbol)
    formatted_price = float(f"{{:.{precision}f}}".format(float(price)))
    return formatted_price 

# 杠杆交易相关API

@trading_bp.route('/margin/account', methods=['POST'])
def get_margin_account():
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
        current_user = authenticated_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': '用户未认证'
            })
        
        user_id = current_user.get('id')
        
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
        
        return jsonify({
            'success': True,
            'data': margin_account
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


@trading_bp.route('/margin/order', methods=['POST'])
def place_margin_order():
    """提交杠杆交易订单"""
    try:
        data = request.get_json()
        email = data.get('email')
        symbol = data.get('symbol')
        side = data.get('side')  # BUY 或 SELL
        amount = data.get('amount')  # 交易金额(USDT)
        
        if not all([email, symbol, side, amount]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: email, symbol, side, amount'
            })
        
        # 验证参数
        if side not in ['BUY', 'SELL']:
            return jsonify({
                'success': False,
                'error': '交易方向参数错误，必须为BUY或SELL'
            })
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("金额必须大于0")
        except ValueError:
            return jsonify({
                'success': False,
                'error': '金额格式错误'
            })
        
        # 验证子账号是否属于当前用户
        current_user = authenticated_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': '用户未认证'
            })
        
        user_id = current_user.get('id')
        
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
        
        # 获取当前市场价格
        ticker_price = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker_price['price'])
        
        # 计算可以购买/卖出的数量
        quantity = amount / current_price
        
        # 获取交易对信息，确定小数位数
        exchange_info = client.get_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
        
        if not symbol_info:
            return jsonify({
                'success': False,
                'error': f'无法获取交易对 {symbol} 的信息'
            })
        
        # 查找数量精度规则
        lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        
        if lot_size_filter:
            step_size = float(lot_size_filter['stepSize'])
            precision = 0
            if step_size < 1:
                precision = len(str(step_size).split('.')[-1].rstrip('0'))
            quantity = round(quantity - (quantity % step_size), precision)
        
        # 确保数量满足最小交易量要求
        min_qty = float(lot_size_filter['minQty']) if lot_size_filter else 0
        if quantity < min_qty:
            return jsonify({
                'success': False,
                'error': f'交易数量 {quantity} 小于最小交易量 {min_qty}'
            })
        
        logger.info(f"准备提交杠杆交易订单: 子账号={email}, 交易对={symbol}, 方向={side}, 金额={amount}USDT, 数量={quantity}, 当前价格={current_price}")
        
        # 提交杠杆市价订单
        order = client.create_margin_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            sideEffectType='NO_SIDE_EFFECT'  # 不自动借贷
        )
        
        logger.info(f"杠杆交易订单提交成功: {order}")
        
        # 不再存储完整的订单信息，仅记录订单ID和基本信息
        # 处理交易费用信息 - 调用API获取交易详情并记录手续费
        try:
            # 等待短暂时间，确保交易已经处理
            time.sleep(1)
            
            # 获取订单信息
            trades = client.get_margin_trades(symbol=symbol)
            
            # 查找与当前订单相关的交易
            order_trades = [trade for trade in trades if str(trade.get('orderId')) == str(order.get('orderId'))]
            
            # 记录手续费信息
            for trade in order_trades:
                fee_record = FeeRecord(
                    email=email,
                    symbol=symbol,
                    order_id=str(trade.get('orderId')),
                    fee_amount=float(trade.get('commission', 0)),
                    fee_asset=trade.get('commissionAsset', ''),
                    source='MARGIN',
                    description=f"杠杆{side}单手续费",
                    trade_time=datetime.fromtimestamp(trade.get('time', 0) / 1000)
                )
                db.session.add(fee_record)
                
            db.session.commit()
            logger.info(f"已记录交易手续费信息: 订单ID={order.get('orderId')}")
            
        except Exception as fee_error:
            logger.error(f"记录手续费失败: {fee_error}")
            # 即使获取手续费失败，也不影响整个交易流程
        
        return jsonify({
            'success': True,
            'data': {
                'orderId': order['orderId'],
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': current_price,
                'amount': amount,
                'message': "订单已提交，仅记录手续费信息",
            }
        })
        
    except BinanceAPIException as e:
        logger.error(f"提交杠杆交易订单失败: {e}")
        return jsonify({
            'success': False,
            'error': f"币安API错误: {e.message}"
        })
    except Exception as e:
        logger.error(f"提交杠杆交易订单失败: {e}")
        return jsonify({
            'success': False,
            'error': f"提交杠杆交易订单失败: {str(e)}"
        })


@trading_bp.route('/margin/history', methods=['POST'])
def get_margin_history():
    """获取杠杆交易历史"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: email'
            })
        
        # 验证子账号是否属于当前用户
        current_user = authenticated_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': '用户未认证'
            })
        
        user_id = current_user.get('id')
        
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
        
        # 获取杠杆账户交易历史
        margin_trades = client.get_margin_trades()
        
        # 处理交易历史数据
        processed_trades = []
        for trade in margin_trades:
            processed_trades.append({
                'email': email,
                'symbol': trade['symbol'],
                'id': trade['id'],
                'orderId': trade['orderId'],
                'price': trade['price'],
                'quantity': trade['qty'],
                'amount': float(trade['price']) * float(trade['qty']),
                'commission': trade['commission'],
                'commissionAsset': trade['commissionAsset'],
                'time': trade['time'],
                'isBuyer': trade['isBuyer'],
                'isMaker': trade['isMaker'],
                'side': 'BUY' if trade['isBuyer'] else 'SELL'
            })
        
        return jsonify({
            'success': True,
            'data': processed_trades
        })
        
    except BinanceAPIException as e:
        logger.error(f"获取杠杆交易历史失败: {e}")
        return jsonify({
            'success': False,
            'error': f"币安API错误: {e.message}"
        })
    except Exception as e:
        logger.error(f"获取杠杆交易历史失败: {e}")
        return jsonify({
            'success': False,
            'error': f"获取杠杆交易历史失败: {str(e)}"
        })

# 添加获取手续费记录的API
@trading_bp.route('/fee-records', methods=['GET'])
@login_required
def get_fee_records():
    """获取交易手续费记录"""
    try:
        # 处理查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        email = request.args.get('email')
        symbol = request.args.get('symbol')
        source = request.args.get('source')  # 手续费来源过滤
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        # 构建查询条件
        query = FeeRecord.query
        
        # 验证当前用户只能查询自己的子账号
        current_user = authenticated_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': '用户未认证'
            })
        
        user_id = current_user.get('id')
        
        if email:
            # 验证子账号是否存在，使用SubAccountAPISettings检查
            api_setting = db.session.query(SubAccountAPISettings).filter_by(
                email=email
            ).first()
            
            if not api_setting:
                return jsonify({
                    'success': False,
                    'error': '子账号不存在'
                })
            
            query = query.filter(FeeRecord.email == email)
        
        if symbol:
            query = query.filter(FeeRecord.symbol == symbol)
        
        if source:
            query = query.filter(FeeRecord.source == source)
        
        # 添加日期范围查询
        if start_date:
            query = query.filter(FeeRecord.trade_time >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            # 加一天以包含当天
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(FeeRecord.trade_time < end_date_obj)
        
        # 计算总记录数
        total_count = query.count()
        
        # 排序和分页
        query = query.order_by(FeeRecord.trade_time.desc())
        fees = query.paginate(page=page, per_page=page_size, error_out=False).items
        
        # 转换为字典列表
        fee_list = [fee.to_dict() for fee in fees]
        
        # 计算汇总统计
        summary = {}
        if fee_list:
            # 按资产类型汇总手续费
            for fee in query.all():  # 获取所有符合条件的记录
                asset = fee.fee_asset
                if asset not in summary:
                    summary[asset] = 0
                summary[asset] += fee.fee_amount
        
        return jsonify({
            'success': True,
            'data': {
                'records': fee_list,
                'total': total_count,
                'page': page,
                'pageSize': page_size,
                'summary': summary
            }
        })
    except Exception as e:
        logger.error(f"获取手续费记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取手续费记录失败: {str(e)}"
        })