from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app.models import db
import logging
from app.models.trading import FeeRecord, TradeHistory, MarginTrade
from app.utils.auth import token_required

logger = logging.getLogger(__name__)
statistics_bp = Blueprint('statistics', __name__, url_prefix='/api/statistics')

@statistics_bp.route('/fee-trend', methods=['GET'])
def get_fee_trend():
    """
    获取手续费趋势数据 - 已废弃
    """
    return jsonify({
        "success": False,
        "error": "此功能已被移除"
    }), 404

@statistics_bp.route('/fee-summary', methods=['GET'])
def get_fee_summary():
    """
    获取手续费汇总统计 - 已废弃
    """
    return jsonify({
        "success": False,
        "error": "此功能已被移除"
    }), 404

@statistics_bp.route('/summary', methods=['GET'])
@token_required
def get_summary():
    """获取交易统计摘要"""
    return jsonify({
        'success': True,
        'data': {
            'message': '统计功能正在开发中'
        }
    })

@statistics_bp.route('/fees', methods=['GET'])
@token_required
def get_fees(current_user):
    """获取手续费统计数据"""
    # 获取查询参数
    email = request.args.get('email')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    source = request.args.get('source')  # 交易类型: SPOT, MARGIN, FUTURES
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # 构建查询
    query = FeeRecord.query

    # 根据参数过滤
    if email:
        query = query.filter(FeeRecord.email == email)
    
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(FeeRecord.trade_time >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(FeeRecord.trade_time < end_dt)
    
    if source:
        query = query.filter(FeeRecord.source == source)
    
    # 获取总数
    total = query.count()
    
    # 获取分页数据
    records = query.order_by(desc(FeeRecord.trade_time)).paginate(page=page, per_page=per_page)
    
    # 转换结果
    result = {
        'success': True,
        'data': {
            'records': [record.to_dict() for record in records.items],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': records.pages
        }
    }
    
    return jsonify(result)

@statistics_bp.route('/fees/summary', methods=['GET'])
@token_required
def get_fees_summary(current_user):
    """获取手续费统计汇总"""
    # 获取查询参数
    email = request.args.get('email')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # 构建基础查询
    query = FeeRecord.query
    
    # 根据参数过滤
    if email:
        query = query.filter(FeeRecord.email == email)
    
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(FeeRecord.trade_time >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(FeeRecord.trade_time < end_dt)
    
    # 按资产类型分组统计总手续费
    fee_by_asset = query.with_entities(
        FeeRecord.fee_asset,
        func.sum(FeeRecord.fee_amount).label('total_fee')
    ).group_by(FeeRecord.fee_asset).all()
    
    # 按交易类型分组统计
    fee_by_source = query.with_entities(
        FeeRecord.source,
        func.sum(FeeRecord.fee_amount).label('total_fee'),
        FeeRecord.fee_asset
    ).group_by(FeeRecord.source, FeeRecord.fee_asset).all()
    
    # 如果有指定子账户，获取其详细统计
    account_stats = None
    if email:
        daily_fees = query.with_entities(
            func.date(FeeRecord.trade_time).label('date'),
            func.sum(FeeRecord.fee_amount).label('total_fee'),
            FeeRecord.fee_asset
        ).group_by(
            func.date(FeeRecord.trade_time),
            FeeRecord.fee_asset
        ).order_by(
            func.date(FeeRecord.trade_time)
        ).all()
        
        account_stats = {
            'email': email,
            'daily_fees': [
                {
                    'date': str(item.date),
                    'fee_amount': float(item.total_fee),
                    'fee_asset': item.fee_asset
                } for item in daily_fees
            ]
        }
    
    # 构建返回结果
    result = {
        'success': True,
        'data': {
            'fee_by_asset': [
                {
                    'asset': item.fee_asset,
                    'total_fee': float(item.total_fee)
                } for item in fee_by_asset
            ],
            'fee_by_source': [
                {
                    'source': item.source,
                    'total_fee': float(item.total_fee),
                    'asset': item.fee_asset
                } for item in fee_by_source
            ],
            'account_stats': account_stats,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    }
    
    return jsonify(result)

@statistics_bp.route('/fees/sync', methods=['POST'])
@token_required
def sync_fees():
    """同步指定账户的手续费数据"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({
            'success': False,
            'error': '请提供子账户邮箱'
        }), 400
    
    # 这里应该是调用币安API获取最新手续费数据的逻辑
    # 由于实际调用需要账户API Key等敏感信息，这里只模拟同步成功
    
    return jsonify({
        'success': True,
        'data': {
            'message': f'账户 {email} 的手续费数据同步已启动，请稍后查看结果'
        }
    })

@statistics_bp.route('/fees/accounts', methods=['GET'])
@token_required
def get_fee_accounts(current_user):
    """获取有手续费记录的所有子账户"""
    accounts = FeeRecord.query.with_entities(
        FeeRecord.email
    ).distinct().all()
    
    return jsonify({
        'success': True,
        'data': [account.email for account in accounts]
    }) 