import logging
from flask import Blueprint, request, jsonify, current_app
from app.utils.auth import token_required
from app.services.binance_client import get_binance_client

logger = logging.getLogger(__name__)
account_bp = Blueprint('account', __name__, url_prefix='/api/account')

@account_bp.route('/status', methods=['GET'])
@token_required
def account_status(current_user):
    """
    获取主账号状态信息
    
    参数:
    - user_id: 用户ID (查询参数)
    
    返回:
    {
        "success": true,
        "data": {
            "apiConfigured": true,
            "status": "ACTIVE"
        }
    }
    """
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "缺少用户ID参数"
        }), 400
    
    # 获取主账号币安客户端
    client = get_binance_client(user_id)
    if not client:
        return jsonify({
            "success": False,
            "error": "主账号API未配置或不可用"
        }), 400
    
    try:
        # 获取账号状态 - 可以简单调用一个API来检查账号可用性
        test_result = client.test_connectivity()
        
        if test_result.get('success'):
            # 如果连接测试成功，说明API可用，返回状态正常
            return jsonify({
                "success": True,
                "data": {
                    "apiConfigured": True,
                    "status": "ACTIVE"
                }
            })
        else:
            error_msg = test_result.get('error', '未知错误')
            logger.error(f"获取账号状态失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取账号状态异常: {error_msg}")
        return jsonify({
            "success": False,
            "error": f"获取账号状态异常: {error_msg}"
        }) 