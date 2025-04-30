from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from app.models import db, GridTrading, OrderHistory, FeeStatistics, TradeHistory
from app.services.fee_calculator import calculate_order_fee
import math
import json
import logging

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
        "total_investment": 总投资额,
        "is_bilateral": 是否双向(true/false),
        "leverage": 杠杆倍数(默认1),
        "stop_loss_price": 止损价格(可选),
        "stop_profit_price": 止盈价格(可选)
    }
    """
    try:
        data = request.json
        
        # 检查必填参数
        required_fields = ['email', 'symbol', 'upper_price', 'lower_price', 'grid_num', 'total_investment']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"缺少必填参数: {field}"})
        
        # 提取参数
        email = data.get('email')
        symbol = data.get('symbol')
        upper_price = float(data.get('upper_price'))
        lower_price = float(data.get('lower_price'))
        grid_num = int(data.get('grid_num'))
        total_investment = float(data.get('total_investment'))
        is_bilateral = data.get('is_bilateral', False)
        leverage = int(data.get('leverage', 1))
        stop_loss_price = data.get('stop_loss_price')
        stop_profit_price = data.get('stop_profit_price')
        
        # 验证参数
        if upper_price <= lower_price:
            return jsonify({"success": False, "error": "上限价格必须大于下限价格"})
        
        if grid_num < 2:
            return jsonify({"success": False, "error": "网格数量必须大于或等于2"})
        
        if total_investment <= 0:
            return jsonify({"success": False, "error": "投资总额必须大于0"})
        
        # 创建网格价格点
        grid_prices = calculate_grid_prices(lower_price, upper_price, grid_num)
        
        # 计算每个网格的投资金额
        per_grid_investment = total_investment / (grid_num - 1)
        
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
            
            # 每个网格点需要购买的数量
            quantity = per_grid_investment / buy_price
            
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
                fee_recorded=False
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

# ========== 辅助函数 ==========

def calculate_grid_prices(lower_price, upper_price, grid_num):
    """
    计算网格价格点
    
    参数:
    - lower_price: 下限价格
    - upper_price: 上限价格
    - grid_num: 网格数量 (包含上下限)
    
    返回:
    - grid_prices: 网格价格点列表
    """
    # 计算价格比例
    ratio = (upper_price / lower_price) ** (1 / (grid_num - 1))
    
    # 生成网格价格点
    grid_prices = []
    for i in range(grid_num):
        price = lower_price * (ratio ** i)
        grid_prices.append(round(price, 8))  # 保留8位小数
    
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
            
            # 如果订单状态变为已完成或部分完成且尚未记录手续费，则计算并记录手续费
            if (status in ['FILLED', 'PARTIALLY_FILLED']) and not order.fee_recorded:
                record_fee(order)
                order.fee_recorded = True
            
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
                fee_recorded=False
            )
            
            db.session.add(new_order)
            db.session.commit()
            
            # 如果订单已完成或部分完成，则记录手续费
            if status in ['FILLED', 'PARTIALLY_FILLED']:
                record_fee(new_order)
                new_order.fee_recorded = True
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
    获取订单历史列表
    
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
        
        # 构建查询条件
        query = OrderHistory.query
        
        if email:
            query = query.filter(OrderHistory.email == email)
        
        if symbol:
            query = query.filter(OrderHistory.symbol == symbol)
        
        if status:
            query = query.filter(OrderHistory.status == status)
        
        # 添加日期范围查询
        if start_date:
            query = query.filter(OrderHistory.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            # 加一天以包含当天
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OrderHistory.created_at < end_date_obj)
        
        # 计算总记录数
        total_count = query.count()
        
        # 排序和分页
        query = query.order_by(OrderHistory.created_at.desc())
        orders = query.paginate(page=page, per_page=page_size, error_out=False).items
        
        # 转换为字典列表
        order_list = [order.to_dict() for order in orders]
        
        return jsonify({
            "success": True,
            "data": {
                "records": order_list,
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

def record_fee(order):
    """
    记录订单手续费
    
    参数:
    - order: 订单对象
    """
    try:
        # 计算手续费
        order_data = {
            'symbol': order.symbol,
            'order_type': order.order_type,
            'product_type': 'SPOT',  # 默认现货
            'amount': order.amount,
            'price': order.price,
            'status': order.status,
            'is_maker': False  # 默认taker
        }
        
        fee_result = calculate_order_fee(order_data)
        
        # 创建手续费记录
        fee_record = FeeStatistics(
            email=order.email,
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            executed_qty=order.executed_qty,
            price=order.price,
            fee=fee_result['fee'],
            fee_currency=order.symbol.split('USDT')[0] if 'USDT' in order.symbol else 'USDT',
            fee_usdt=fee_result['fee_usdt'],
            created_at=datetime.utcnow(),
            order_created_at=order.created_at
        )
        
        db.session.add(fee_record)
        
    except Exception as e:
        logger.error(f"记录订单手续费失败: {str(e)}")
        # 不抛出异常，让调用方可以继续处理 