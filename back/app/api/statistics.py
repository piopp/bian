from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app.models import db
import logging

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