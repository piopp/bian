from flask import Blueprint, jsonify, request, session, current_app
from app.models import APIKey, db
import random
import logging
from app.services.binance_client import BinanceClient

logger = logging.getLogger(__name__)
misc_bp = Blueprint('misc', __name__, url_prefix='/api/misc')

@misc_bp.route('/balance', methods=['GET'])
def get_balance():
    """
    获取指定币种的可用余额
    
    查询参数:
    - asset: 币种名称 (如BTC, USDT)
    - direction: 转账方向 (toSubAccount或fromSubAccount)
    - user_id: 用户ID
    
    返回:
    {"success": true, "data": {"available": "金额"}}
    """
    # 获取查询参数
    asset = request.args.get('asset', 'USDT')
    direction = request.args.get('direction', 'toSubAccount')
    
    # 记录请求参数
    logger.info(f"余额请求 - 币种: {asset}, 方向: {direction}, 参数: {request.args}")
    
    # 获取用户ID (从会话或查询参数)
    user_id = session.get('user_id')
    if not user_id:
        # 尝试从不同的参数名获取用户ID
        user_id = request.args.get('user_id') or request.args.get('id')
    
    logger.info(f"余额请求 - 使用用户ID: {user_id}")
    
    # 尝试从数据库获取API密钥
    api_key = None
    api_secret = None
    
    if user_id:
        api_key_record = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
        if api_key_record:
            api_key = api_key_record.api_key
            api_secret = api_key_record.api_secret
            # 安全地记录API密钥的一部分，用于调试
            masked_key = api_key[:4] + '****' + api_key[-4:] if len(api_key) > 8 else '****'
            logger.info(f"余额请求 - 找到用户 {user_id} 的API密钥: {masked_key}")
        else:
            logger.warning(f"余额请求 - 用户 {user_id} 没有设置API密钥")
    
    # 如果未找到API密钥或未指定用户ID，则使用模拟数据
    if not api_key or not api_secret:
        logger.info("余额请求 - 使用模拟数据")
        
        # 返回模拟数据
        mock_balances = {
            "BTC": "0.0",
            "ETH": "0.0",
            "USDT": "0.0",
            "BNB": "0.0",
            "SOL": "0.0",
            "ADA": "0.0",
            "XRP": "0.0",
            "DOGE": "0.0"
        }
        
        # 如果请求的币种不在模拟列表中，生成随机数据
        if asset not in mock_balances:
            mock_balance = str(round(random.uniform(0.1, 100.0), 4))
        else:
            mock_balance = mock_balances[asset]
        
        return jsonify({
            "success": True,
            "data": {
                "available": mock_balance
            }
        })
    
    # 使用API密钥初始化币安客户端
    client = BinanceClient(api_key, api_secret)
    
    # 调用API获取余额
    logger.info(f"余额请求 - 调用币安API获取 {asset} 的余额")
    result = client.get_account_balance(asset)
    
    if result.get('success'):
        logger.info(f"余额请求 - 成功获取 {asset} 的余额: {result.get('data', {}).get('available', '0')}")
    else:
        logger.error(f"余额请求 - 获取 {asset} 的余额失败: {result.get('error', '未知错误')}")
    
    return jsonify(result)

@misc_bp.route('/assets', methods=['GET'])
def get_assets():
    """获取所有资产信息"""
    try:
        # 获取用户ID
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "未提供用户ID"
            }), 400
            
        # 从数据库获取API密钥
        api_key_record = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
        
        if not api_key_record:
            return jsonify({
                "success": False,
                "error": "未找到有效的API密钥"
            }), 404
            
        # 初始化币安客户端
        client = BinanceClient(api_key_record.api_key, api_key_record.api_secret)
        
        # 获取资产信息
        result = client.get_all_assets()
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"获取资产信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取资产信息失败: {str(e)}"
        }), 500

@misc_bp.route('/markets', methods=['GET'])
def get_markets():
    """获取市场行情"""
    try:
        # 获取查询参数
        symbol = request.args.get('symbol')
        
        # 初始化币安客户端 (市场行情不需要API密钥)
        client = BinanceClient('', '')
        
        if symbol:
            # 获取指定交易对的行情
            result = client.get_ticker(symbol)
        else:
            # 获取所有交易对的行情
            result = client.get_all_tickers()
            
        return jsonify(result)
    except Exception as e:
        logger.exception(f"获取市场行情失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取市场行情失败: {str(e)}"
        }), 500

@misc_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        # 初始化币安客户端 (系统状态不需要API密钥)
        client = BinanceClient('', '')
        
        # 获取系统状态
        result = client.get_system_status()
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"获取系统状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取系统状态失败: {str(e)}"
        }), 500 