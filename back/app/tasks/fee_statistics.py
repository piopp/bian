import logging
from datetime import datetime, timedelta
import json
from flask import current_app
from app.models import db, User, OrderHistory, FeeStatistics
from app.services.binance_client import get_client_by_email
from apscheduler.schedulers.background import BackgroundScheduler

# 初始化日志
logger = logging.getLogger('fee_statistics_tasks')

# 全局调度器对象
scheduler = None

def init_scheduler(app):
    """初始化调度器"""
    global scheduler
    
    if scheduler:
        return scheduler
    
    logger.info("初始化费用统计调度器")
    scheduler = BackgroundScheduler()
    
    # 添加每日费用统计任务，每天凌晨1点执行
    scheduler.add_job(
        daily_fee_statistics,
        'cron',
        hour=1,
        minute=0,
        args=[app],
        id='daily_fee_statistics'
    )
    
    # 添加每周费用统计任务，每周一凌晨2点执行
    scheduler.add_job(
        weekly_fee_statistics,
        'cron',
        day_of_week='mon',
        hour=2,
        minute=0,
        args=[app],
        id='weekly_fee_statistics'
    )
    
    # 添加每月费用统计任务，每月1日凌晨3点执行
    scheduler.add_job(
        monthly_fee_statistics,
        'cron',
        day=1,
        hour=3,
        minute=0,
        args=[app],
        id='monthly_fee_statistics'
    )
    
    # 启动调度器
    scheduler.start()
    logger.info("费用统计调度器已启动")
    
    return scheduler

def daily_fee_statistics(app):
    """每日费用统计任务"""
    with app.app_context():
        try:
            logger.info("开始执行每日费用统计")
            
            # 获取当前日期和昨天的日期
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            yesterday_start = datetime.combine(yesterday, datetime.min.time())
            yesterday_end = datetime.combine(yesterday, datetime.max.time())
            
            # 查询所有用户
            users = User.query.all()
            
            for user in users:
                try:
                    logger.debug(f"处理用户 {user.email} 的每日费用统计")
                    
                    # 检查是否已存在昨天的统计记录
                    existing_stat = FeeStatistics.query.filter_by(
                        email=user.email, 
                        period_type='daily',
                        period_start=yesterday_start
                    ).first()
                    
                    if existing_stat:
                        logger.debug(f"用户 {user.email} 的昨日费用统计已存在，跳过")
                        continue
                    
                    # 统计用户昨天的交易手续费
                    fee_data = compute_user_fees(user.email, yesterday_start, yesterday_end)
                    
                    if not fee_data or not fee_data.get('total_fee'):
                        logger.debug(f"用户 {user.email} 昨日没有交易手续费")
                        continue
                    
                    # 创建统计记录
                    new_stat = FeeStatistics(
                        email=user.email,
                        period_type='daily',
                        period_start=yesterday_start,
                        period_end=yesterday_end,
                        fee_amount=fee_data['total_fee'],
                        fee_breakdown=json.dumps(fee_data['fee_by_coin']),
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(new_stat)
                    db.session.commit()
                    logger.info(f"用户 {user.email} 的昨日费用统计已完成，总费用: {fee_data['total_fee']} USDT")
                    
                except Exception as e:
                    logger.error(f"处理用户 {user.email} 的每日费用统计时发生错误: {str(e)}", exc_info=True)
            
            logger.info("每日费用统计任务已完成")
            
        except Exception as e:
            logger.error(f"执行每日费用统计任务时发生错误: {str(e)}", exc_info=True)

def weekly_fee_statistics(app):
    """每周费用统计任务"""
    with app.app_context():
        try:
            logger.info("开始执行每周费用统计")
            
            # 获取上周的开始和结束日期
            today = datetime.utcnow().date()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            
            week_start = datetime.combine(last_monday, datetime.min.time())
            week_end = datetime.combine(last_sunday, datetime.max.time())
            
            # 查询所有用户
            users = User.query.all()
            
            for user in users:
                try:
                    logger.debug(f"处理用户 {user.email} 的每周费用统计")
                    
                    # 检查是否已存在上周的统计记录
                    existing_stat = FeeStatistics.query.filter_by(
                        email=user.email, 
                        period_type='weekly',
                        period_start=week_start
                    ).first()
                    
                    if existing_stat:
                        logger.debug(f"用户 {user.email} 的上周费用统计已存在，跳过")
                        continue
                    
                    # 统计用户上周的交易手续费
                    fee_data = compute_user_fees(user.email, week_start, week_end)
                    
                    if not fee_data or not fee_data.get('total_fee'):
                        logger.debug(f"用户 {user.email} 上周没有交易手续费")
                        continue
                    
                    # 创建统计记录
                    new_stat = FeeStatistics(
                        email=user.email,
                        period_type='weekly',
                        period_start=week_start,
                        period_end=week_end,
                        fee_amount=fee_data['total_fee'],
                        fee_breakdown=json.dumps(fee_data['fee_by_coin']),
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(new_stat)
                    db.session.commit()
                    logger.info(f"用户 {user.email} 的上周费用统计已完成，总费用: {fee_data['total_fee']} USDT")
                    
                except Exception as e:
                    logger.error(f"处理用户 {user.email} 的每周费用统计时发生错误: {str(e)}", exc_info=True)
            
            logger.info("每周费用统计任务已完成")
            
        except Exception as e:
            logger.error(f"执行每周费用统计任务时发生错误: {str(e)}", exc_info=True)

def monthly_fee_statistics(app):
    """每月费用统计任务"""
    with app.app_context():
        try:
            logger.info("开始执行每月费用统计")
            
            # 获取上个月的开始和结束日期
            today = datetime.utcnow().date()
            
            # 获取上个月的第一天
            if today.month == 1:
                last_month_start = today.replace(year=today.year-1, month=12, day=1)
            else:
                last_month_start = today.replace(month=today.month-1, day=1)
            
            # 获取上个月的最后一天
            if last_month_start.month == 12:
                last_month_end = last_month_start.replace(year=last_month_start.year+1, month=1, day=1) - timedelta(days=1)
            else:
                last_month_end = last_month_start.replace(month=last_month_start.month+1, day=1) - timedelta(days=1)
            
            month_start = datetime.combine(last_month_start, datetime.min.time())
            month_end = datetime.combine(last_month_end, datetime.max.time())
            
            # 查询所有用户
            users = User.query.all()
            
            for user in users:
                try:
                    logger.debug(f"处理用户 {user.email} 的每月费用统计")
                    
                    # 检查是否已存在上月的统计记录
                    existing_stat = FeeStatistics.query.filter_by(
                        email=user.email, 
                        period_type='monthly',
                        period_start=month_start
                    ).first()
                    
                    if existing_stat:
                        logger.debug(f"用户 {user.email} 的上月费用统计已存在，跳过")
                        continue
                    
                    # 统计用户上月的交易手续费
                    fee_data = compute_user_fees(user.email, month_start, month_end)
                    
                    if not fee_data or not fee_data.get('total_fee'):
                        logger.debug(f"用户 {user.email} 上月没有交易手续费")
                        continue
                    
                    # 创建统计记录
                    new_stat = FeeStatistics(
                        email=user.email,
                        period_type='monthly',
                        period_start=month_start,
                        period_end=month_end,
                        fee_amount=fee_data['total_fee'],
                        fee_breakdown=json.dumps(fee_data['fee_by_coin']),
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(new_stat)
                    db.session.commit()
                    logger.info(f"用户 {user.email} 的上月费用统计已完成，总费用: {fee_data['total_fee']} USDT")
                    
                except Exception as e:
                    logger.error(f"处理用户 {user.email} 的每月费用统计时发生错误: {str(e)}", exc_info=True)
            
            logger.info("每月费用统计任务已完成")
            
        except Exception as e:
            logger.error(f"执行每月费用统计任务时发生错误: {str(e)}", exc_info=True)

def compute_user_fees(email, start_time, end_time):
    """计算用户在指定时间段内的交易手续费
    
    Args:
        email: 用户邮箱
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        dict: 包含总费用和按币种分类的费用
    """
    try:
        # 获取用户的API客户端
        client = get_client_by_email(email)
        if not client:
            logger.error(f"无法获取用户 {email} 的API客户端")
            return None
        
        # 从本地数据库获取订单历史
        orders = OrderHistory.query.filter(
            OrderHistory.email == email,
            OrderHistory.status == "FILLED",
            OrderHistory.created_at >= start_time,
            OrderHistory.created_at <= end_time,
            OrderHistory.fee_recorded == False
        ).all()
        
        if not orders:
            logger.debug(f"用户 {email} 在指定时间段内没有已成交且未记录费用的订单")
            
            # 尝试从交易所获取费用信息
            try:
                # 转换时间格式为毫秒时间戳
                start_timestamp = int(start_time.timestamp() * 1000)
                end_timestamp = int(end_time.timestamp() * 1000)
                
                # 查询交易所的费用历史
                result = client._send_request(
                    'GET',
                    "/sapi/v1/asset/tradeFee",
                    signed=True,
                    params={
                        'startTime': start_timestamp,
                        'endTime': end_timestamp
                    }
                )
                
                if not result.get('success'):
                    logger.error(f"查询交易所费用历史失败: {result.get('error')}")
                    return None
                
                fees_data = result.get('data', [])
                if not fees_data:
                    logger.debug(f"交易所返回的费用数据为空")
                    return None
                
                # 处理费用数据
                total_fee = 0
                fee_by_coin = {}
                
                for fee in fees_data:
                    fee_coin = fee.get('feeCoin', '')
                    fee_amount = float(fee.get('fee', 0))
                    
                    if fee_coin and fee_amount > 0:
                        # 如果费用币种不是USDT，需要转换
                        if fee_coin != 'USDT':
                            # 查询币种对USDT的价格
                            price_result = client._send_request(
                                'GET',
                                "/api/v3/ticker/price",
                                params={'symbol': f"{fee_coin}USDT"}
                            )
                            
                            if price_result.get('success'):
                                price_data = price_result.get('data', {})
                                price = float(price_data.get('price', 0))
                                if price > 0:
                                    fee_in_usdt = fee_amount * price
                                else:
                                    fee_in_usdt = 0
                            else:
                                fee_in_usdt = 0
                        else:
                            fee_in_usdt = fee_amount
                        
                        total_fee += fee_in_usdt
                        
                        if fee_coin in fee_by_coin:
                            fee_by_coin[fee_coin] += fee_amount
                        else:
                            fee_by_coin[fee_coin] = fee_amount
                
                return {
                    'total_fee': total_fee,
                    'fee_by_coin': fee_by_coin
                }
                
            except Exception as e:
                logger.error(f"从交易所获取费用信息时发生错误: {str(e)}")
                return None
        
        # 处理本地订单
        total_fee = 0
        fee_by_coin = {}
        
        for order in orders:
            try:
                # 查询订单详情获取手续费
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
                    logger.error(f"查询订单详情失败: {order_result.get('error')}")
                    continue
                
                order_data = order_result.get('data', {})
                
                # 从交易所获取交易费用
                trade_result = client._send_request(
                    'GET',
                    "/api/v3/myTrades",
                    signed=True,
                    params={
                        'symbol': order.symbol,
                        'orderId': order.client_order_id
                    }
                )
                
                if not trade_result.get('success'):
                    logger.error(f"查询交易详情失败: {trade_result.get('error')}")
                    continue
                
                trades_data = trade_result.get('data', [])
                
                for trade in trades_data:
                    fee_coin = trade.get('commissionAsset', '')
                    fee_amount = float(trade.get('commission', 0))
                    
                    if fee_coin and fee_amount > 0:
                        # 如果费用币种不是USDT，需要转换
                        if fee_coin != 'USDT':
                            # 查询币种对USDT的价格
                            price_result = client._send_request(
                                'GET',
                                "/api/v3/ticker/price",
                                params={'symbol': f"{fee_coin}USDT"}
                            )
                            
                            if price_result.get('success'):
                                price_data = price_result.get('data', {})
                                price = float(price_data.get('price', 0))
                                if price > 0:
                                    fee_in_usdt = fee_amount * price
                                else:
                                    fee_in_usdt = 0
                            else:
                                fee_in_usdt = 0
                        else:
                            fee_in_usdt = fee_amount
                        
                        total_fee += fee_in_usdt
                        
                        if fee_coin in fee_by_coin:
                            fee_by_coin[fee_coin] += fee_amount
                        else:
                            fee_by_coin[fee_coin] = fee_amount
                
                # 标记订单费用已记录
                order.fee_recorded = True
                
            except Exception as e:
                logger.error(f"处理订单 {order.order_id} 费用时发生错误: {str(e)}")
        
        # 提交数据库更改
        db.session.commit()
        
        return {
            'total_fee': total_fee,
            'fee_by_coin': fee_by_coin
        }
        
    except Exception as e:
        logger.error(f"计算用户 {email} 的交易手续费时发生错误: {str(e)}")
        return None 