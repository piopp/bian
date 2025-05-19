import logging
from flask import Blueprint, request, jsonify, current_app
from app.utils.auth import token_required
from app.services.binance_client import get_binance_client, get_client_by_email, BinanceClient

logger = logging.getLogger(__name__)
binance_bp = Blueprint('binance', __name__, url_prefix='/api/binance')

@binance_bp.route('/query', methods=['POST'])
@token_required
def binance_query(current_user):
    """
    通用的币安API查询接口，支持直接调用任何币安API端点
    
    请求体:
    {
        "endpoint": "API端点，例如 '/fapi/v1/premiumIndex'",
        "method": "请求方法，例如 'GET'",
        "params": {"参数名": "参数值"},
        "email": "可选，指定子账号邮箱"
    }
    
    返回:
    - success: True/False
    - data: API返回的数据
    - error: 如果出错，返回错误信息
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        endpoint = data.get('endpoint')
        method = data.get('method', 'GET')
        params = data.get('params', {})
        email = data.get('email')
        
        if not endpoint:
            return jsonify({
                "success": False,
                "error": "必须提供endpoint参数"
            }), 400
        
        # 判断是否需要签名
        signed = 'timestamp' in params or endpoint.startswith('/sapi/') or 'api-key' in params
        
        # 获取客户端
        client = None
        if email:
            client = get_client_by_email(email)
        
        # 如果未指定子账号或获取子账号客户端失败，使用主账号
        if not client:
            client = get_binance_client(current_user.id)
        
        # 如果主账号也不可用，则使用无API密钥的公共客户端
        if not client:
            # 对于需要签名的请求，必须有API密钥
            if signed:
                return jsonify({
                    "success": False,
                    "error": "此API请求需要签名，但未配置有效的API密钥"
                }), 400
            
            logger.warning(f"使用无API密钥的客户端访问公共端点: {endpoint}")
            client = BinanceClient('', '')
        
        logger.info(f"调用币安API: {method} {endpoint}, 参数: {params}")
        
        # 发送请求
        result = client._send_request(method, endpoint, signed=signed, params=params)
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"调用币安API失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"调用币安API失败: {str(e)}"
        }), 500 