from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app.models import db, FeeStatistics
import logging

logger = logging.getLogger(__name__)
statistics_bp = Blueprint('statistics', __name__, url_prefix='/api/statistics')

@statistics_bp.route('/fee-trend', methods=['GET'])
def get_fee_trend():
    """
    获取手续费趋势数据
    
    查询参数:
    - period: 时间周期 day/week/month（默认day)
    - email: 筛选指定子账号（可选，不提供时返回所有子账号数据）
    - symbol: 筛选指定交易对
    - page: 页码
    - pageSize: 每页记录数
    """
    try:
        period = request.args.get('period', 'day')
        email = request.args.get('email')
        symbol = request.args.get('symbol')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        
        # 构建基础查询条件
        query_filter = []
        
        # 筛选条件
        if email:
            query_filter.append(FeeStatistics.email == email)
        
        if symbol:
            query_filter.append(FeeStatistics.symbol == symbol)
            
        # 获取分页的历史记录
        query = FeeStatistics.query
        
        # 应用筛选条件
        if query_filter:
            query = query.filter(*query_filter)
            
        # 按时间降序排序并分页
        total = query.count()
        records = query.order_by(FeeStatistics.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
            
        # 构建响应数据
        records_data = []
        for record in records:
            records_data.append({
                'id': record.id,
                'email': record.email,
                'symbol': record.symbol,
                'side': '买入' if record.side == 'BUY' else '卖出',
                'price': float(record.price) if record.price else 0,
                'amount': float(record.executed_qty) if record.executed_qty else 0,
                'fee': float(record.fee) if record.fee else 0,
                'feeCurrency': record.fee_currency,
                'feeUSDT': float(record.fee_usdt) if record.fee_usdt else 0,
                'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else None,
                'type': '市价单' if record.order_type == 'MARKET' else '限价单'
            })
            
        return jsonify({
            "success": True,
            "data": {
                "records": records_data,
                "total": total,
                "page": page,
                "pageSize": page_size
            }
        })
    except Exception as e:
        logger.error(f"获取手续费趋势数据失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取手续费趋势数据失败: {str(e)}"
        })

@statistics_bp.route('/fee-summary', methods=['GET'])
def get_fee_summary():
    """
    获取手续费汇总统计
    
    查询参数:
    - email: 筛选指定子账号（可选，不提供时返回所有子账号汇总）
    - days: 统计天数，默认为30天
    """
    try:
        email = request.args.get('email')
        days = int(request.args.get('days', 30))
        
        # 计算开始时间
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # 构建基础查询条件
        query_filter = [FeeStatistics.created_at >= start_time]
        
        # 如果指定了email，则添加过滤条件
        if email:
            query_filter.append(FeeStatistics.email == email)
        
        # 统计总手续费
        total_fee = db.session.query(
            func.sum(FeeStatistics.fee_usdt).label('total_fee')
        ).filter(
            *query_filter
        ).scalar() or 0
        
        # 按币种统计
        fee_by_coin = db.session.query(
            FeeStatistics.fee_currency,
            func.sum(FeeStatistics.fee).label('fee_amount'),
            func.sum(FeeStatistics.fee_usdt).label('fee_usdt')
        ).filter(
            *query_filter
        ).group_by(FeeStatistics.fee_currency).all()
        
        # 格式化币种汇总
        coin_summary = []
        for item in fee_by_coin:
            coin_summary.append({
                'currency': item[0],
                'amount': float(item[1]) if item[1] else 0,
                'usdt_value': float(item[2]) if item[2] else 0
            })
        
        # 按交易对统计
        fee_by_symbol = db.session.query(
            FeeStatistics.symbol,
            func.sum(FeeStatistics.fee_usdt).label('fee_usdt')
        ).filter(
            *query_filter
        ).group_by(FeeStatistics.symbol).all()
        
        # 格式化交易对汇总
        symbol_summary = []
        for item in fee_by_symbol:
            symbol_summary.append({
                'symbol': item[0],
                'fee_usdt': float(item[1]) if item[1] else 0
            })
        
        return jsonify({
            "success": True,
            "data": {
                "total_fee_usdt": float(total_fee),
                "period_days": days,
                "by_coin": coin_summary,
                "by_symbol": symbol_summary
            }
        })
    except Exception as e:
        logger.error(f"获取手续费汇总统计失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取手续费汇总统计失败: {str(e)}"
        }), 500 