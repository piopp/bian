import logging
from datetime import datetime
import json
import threading
from flask import current_app
from app.models import db, GridTrading, OrderHistory
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.binance_client import get_client_by_email

# 初始化日志
logger = logging.getLogger('grid_trading_tasks')

# 全局调度器对象
scheduler = None
# 锁，防止任务并发执行
_lock = threading.Lock()

def init_scheduler(app):
    """初始化调度器"""
    global scheduler
    
    if scheduler:
        return scheduler
    
    logger.info("初始化网格交易调度器")
    scheduler = BackgroundScheduler()
    
    # 添加定时任务，每5秒检查一次网格交易状态
    scheduler.add_job(
        check_grid_trades,
        'interval',
        seconds=30,
        args=[app],
        id='check_grid_trades'
    )
    
    # 启动调度器
    scheduler.start()
    logger.info("网格交易调度器已启动")
    
    return scheduler

def check_grid_trades(app):
    """检查所有运行中的网格交易"""
    with app.app_context():
        try:
            # 使用锁防止并发执行
            if not _lock.acquire(blocking=False):
                logger.debug("上一个网格交易检查任务仍在运行，跳过本次检查")
                return
                
            try:
                logger.debug("开始检查网格交易状态")
                
                # 查询所有运行中的网格交易
                grid_trades = GridTrading.query.filter_by(status="RUNNING").all()
                
                if not grid_trades:
                    logger.debug("没有运行中的网格交易")
                    return
                
                logger.info(f"找到{len(grid_trades)}个运行中的网格交易")
                
                # 逐个处理网格交易
                for grid in grid_trades:
                    process_grid_trade(grid)
                    
            finally:
                _lock.release()
                
        except Exception as e:
            logger.error(f"检查网格交易时发生错误: {str(e)}", exc_info=True)

def process_grid_trade(grid):
    """处理单个网格交易"""
    try:
        logger.debug(f"处理网格交易: {grid.grid_id}")
        
        # 获取币安客户端
        client = get_client_by_email(grid.email)
        if not client:
            logger.error(f"无法获取用户 {grid.email} 的API客户端")
            return
            
        # 1. 检查并更新订单状态
        check_and_update_orders(grid, client)
        
        # 2. 检查止盈止损条件
        check_stop_conditions(grid, client)
        
        # 3. 重建缺失的订单
        recreate_missing_orders(grid, client)
        
    except Exception as e:
        logger.error(f"处理网格交易 {grid.grid_id} 时发生错误: {str(e)}", exc_info=True)

def check_and_update_orders(grid, client):
    """检查并更新订单状态"""
    try:
        # 获取网格相关的所有未成交订单
        pending_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid.grid_id}_ORDER_%"),
            OrderHistory.status == "NEW"
        ).all()
        
        if not pending_orders:
            logger.debug(f"网格交易 {grid.grid_id} 没有待处理的订单")
            return
            
        logger.debug(f"网格交易 {grid.grid_id} 有 {len(pending_orders)} 个待处理订单")
        
        # 批量查询订单状态
        for order in pending_orders:
            # 跳过没有client_order_id的订单（未实际提交到交易所的订单）
            if not order.client_order_id:
                continue
                
            # 查询订单状态
            try:
                order_result = client._send_request(
                    'GET',
                    "/api/v3/order",
                    signed=True,
                    params={
                        'symbol': order.symbol,
                        'orderId': order.client_order_id
                    }
                )
                
                if not order_result.get('success'):
                    logger.error(f"查询订单状态失败: {order_result.get('error')}")
                    continue
                
                order_data = order_result.get('data', {})
                
                # 更新订单状态
                if order_data.get('status') != order.status:
                    order.status = order_data.get('status')
                    order.executed_qty = float(order_data.get('executedQty', 0))
                    order.last_checked = datetime.utcnow()
                    
                    # 如果订单已成交，处理后续逻辑
                    if order.status == "FILLED":
                        handle_filled_order(grid, order, client)
                        
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"查询订单 {order.order_id} 状态时发生错误: {str(e)}")
                
    except Exception as e:
        logger.error(f"检查网格 {grid.grid_id} 订单状态时发生错误: {str(e)}")

def handle_filled_order(grid, order, client):
    """处理已成交的订单"""
    try:
        logger.info(f"处理已成交订单: {order.order_id}")
        
        # 提取网格价格
        grid_prices = json.loads(grid.grid_prices) if isinstance(grid.grid_prices, str) else grid.grid_prices
        
        # 根据订单类型创建相反方向的订单
        if order.side == "BUY":
            # 买单成交后，创建卖单
            # 找到下一个价格点
            current_price_index = -1
            for i, price in enumerate(grid_prices):
                if abs(price - order.price) < 0.000001:  # 浮点数比较
                    current_price_index = i
                    break
                    
            if current_price_index >= 0 and current_price_index < len(grid_prices) - 1:
                # 创建卖单，价格是下一个网格点
                sell_price = grid_prices[current_price_index + 1]
                create_order(grid, "SELL", order.executed_qty, sell_price, current_price_index, client)
                
        elif order.side == "SELL":
            # 卖单成交后，创建买单
            # 找到上一个价格点
            current_price_index = -1
            for i, price in enumerate(grid_prices):
                if abs(price - order.price) < 0.000001:  # 浮点数比较
                    current_price_index = i
                    break
                    
            if current_price_index > 0:
                # 创建买单，价格是上一个网格点
                buy_price = grid_prices[current_price_index - 1]
                
                # 计算可以购买的数量
                buy_amount = (order.executed_qty * order.price) / buy_price
                create_order(grid, "BUY", buy_amount, buy_price, current_price_index-1, client)
                    
    except Exception as e:
        logger.error(f"处理已成交订单时发生错误: {str(e)}")

def create_order(grid, side, amount, price, price_index, client):
    """创建订单"""
    try:
        new_order = OrderHistory(
            email=grid.email,
            symbol=grid.symbol,
            order_type="LIMIT",
            side=side,
            amount=amount,
            price=price,
            status="NEW",
            executed_qty=0,
            order_id=f"{grid.grid_id}_ORDER_{side}_{price_index}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            client_order_id=None,
            leverage=grid.leverage,
            created_at=datetime.utcnow(),
            last_checked=datetime.utcnow(),
            fee_recorded=False
        )
        
        # 提交订单到交易所
        try:
            order_result = client._send_request(
                'POST',
                "/api/v3/order",
                signed=True,
                params={
                    'symbol': grid.symbol,
                    'side': side,
                    'type': 'LIMIT',
                    'timeInForce': 'GTC',
                    'quantity': amount,
                    'price': price
                }
            )
            
            if not order_result.get('success'):
                logger.error(f"创建{side}单失败: {order_result.get('error')}")
                return
                
            order_data = order_result.get('data', {})
            new_order.client_order_id = order_data.get('orderId')
            db.session.add(new_order)
            db.session.commit()
            
            logger.info(f"创建{side}单成功: {new_order.order_id}")
            
        except Exception as e:
            logger.error(f"创建{side}单失败: {str(e)}")
            
    except Exception as e:
        logger.error(f"创建订单时发生错误: {str(e)}")

def check_stop_conditions(grid, client):
    """检查止盈止损条件"""
    try:
        # 如果没有设置止盈止损价格，则跳过
        if not grid.stop_loss_price and not grid.stop_profit_price:
            return
            
        # 获取当前价格
        ticker_result = client._send_request(
            'GET',
            "/api/v3/ticker/price",
            params={'symbol': grid.symbol}
        )
        
        if not ticker_result.get('success'):
            logger.error(f"获取价格失败: {ticker_result.get('error')}")
            return
            
        ticker_data = ticker_result.get('data', {})
        current_price = float(ticker_data.get('price', 0))
        
        if current_price <= 0:
            logger.error(f"获取到的价格无效: {current_price}")
            return
        
        # 检查止损条件
        if grid.stop_loss_price and current_price <= grid.stop_loss_price:
            logger.info(f"网格交易 {grid.grid_id} 触发止损，当前价格: {current_price}, 止损价格: {grid.stop_loss_price}")
            stop_grid_trading(grid, client, "止损触发")
            return
            
        # 检查止盈条件
        if grid.stop_profit_price and current_price >= grid.stop_profit_price:
            logger.info(f"网格交易 {grid.grid_id} 触发止盈，当前价格: {current_price}, 止盈价格: {grid.stop_profit_price}")
            stop_grid_trading(grid, client, "止盈触发")
            return
            
    except Exception as e:
        logger.error(f"检查止盈止损条件时发生错误: {str(e)}")

def recreate_missing_orders(grid, client):
    """重建缺失的订单"""
    try:
        # 提取网格价格
        grid_prices = json.loads(grid.grid_prices) if isinstance(grid.grid_prices, str) else grid.grid_prices
        
        if not grid_prices:
            logger.error(f"网格 {grid.grid_id} 没有有效的网格价格")
            return
            
        # 获取当前价格
        ticker_result = client._send_request(
            'GET',
            "/api/v3/ticker/price",
            params={'symbol': grid.symbol}
        )
        
        if not ticker_result.get('success'):
            logger.error(f"获取价格失败: {ticker_result.get('error')}")
            return
            
        ticker_data = ticker_result.get('data', {})
        current_price = float(ticker_data.get('price', 0))
        
        if current_price <= 0:
            logger.error(f"获取到的价格无效: {current_price}")
            return
            
        # 找到当前价格所在的网格区间
        current_grid_index = -1
        for i in range(len(grid_prices) - 1):
            if grid_prices[i] <= current_price <= grid_prices[i + 1]:
                current_grid_index = i
                break
                
        if current_grid_index == -1:
            logger.warning(f"当前价格 {current_price} 不在网格范围内，跳过订单检查")
            return
            
        # 查询现有订单
        existing_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid.grid_id}_ORDER_%"),
            OrderHistory.status == "NEW"
        ).all()
        
        # 检查是否需要创建买单（下方网格点）
        has_buy_order = False
        for order in existing_orders:
            if order.side == "BUY" and abs(order.price - grid_prices[current_grid_index]) < 0.000001:
                has_buy_order = True
                break
                
        if not has_buy_order:
            # 计算每个网格的投资金额
            grid_investment = grid.total_investment / (len(grid_prices) - 1)
            # 需要创建买单
            buy_price = grid_prices[current_grid_index]
            buy_amount = grid_investment / buy_price
            create_order(grid, "BUY", buy_amount, buy_price, current_grid_index, client)
                
        # 检查是否需要创建卖单（上方网格点）
        has_sell_order = False
        for order in existing_orders:
            if order.side == "SELL" and abs(order.price - grid_prices[current_grid_index + 1]) < 0.000001:
                has_sell_order = True
                break
                
        if not has_sell_order and grid.is_bilateral:
            # 计算每个网格的投资金额
            grid_investment = grid.total_investment / (len(grid_prices) - 1)
            # 需要创建卖单
            sell_price = grid_prices[current_grid_index + 1]
            sell_amount = grid_investment / grid_prices[current_grid_index]
            create_order(grid, "SELL", sell_amount, sell_price, current_grid_index+1, client)
                
    except Exception as e:
        logger.error(f"重建缺失订单时发生错误: {str(e)}")

def stop_grid_trading(grid, client, reason):
    """停止网格交易"""
    try:
        logger.info(f"停止网格交易 {grid.grid_id}，原因: {reason}")
        
        # 更新网格状态
        grid.status = "CLOSED"
        grid.closed_at = datetime.utcnow()
        grid.close_reason = reason
        db.session.commit()
        
        # 取消所有未成交的订单
        pending_orders = OrderHistory.query.filter(
            OrderHistory.order_id.like(f"{grid.grid_id}_ORDER_%"),
            OrderHistory.status == "NEW"
        ).all()
        
        for order in pending_orders:
            if order.client_order_id:
                try:
                    # 取消交易所订单
                    cancel_result = client._send_request(
                        'DELETE',
                        "/api/v3/order",
                        signed=True,
                        params={
                            'symbol': order.symbol,
                            'orderId': order.client_order_id
                        }
                    )
                    
                    if not cancel_result.get('success'):
                        logger.error(f"取消订单 {order.order_id} 失败: {cancel_result.get('error')}")
                except Exception as e:
                    logger.error(f"取消订单 {order.order_id} 失败: {str(e)}")
                    
            # 更新订单状态为已取消
            order.status = "CANCELED"
            
        db.session.commit()
        logger.info(f"网格交易 {grid.grid_id} 已停止")
        
    except Exception as e:
        logger.error(f"停止网格交易时发生错误: {str(e)}") 