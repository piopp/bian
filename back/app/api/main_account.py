import logging
import json
from flask import Blueprint, request, jsonify, current_app
from app.utils.auth import token_required
from app.services.binance_client import BinanceClient
from app.models.user import User, APIKey
from app.models.account import SubAccountAPISettings

logger = logging.getLogger(__name__)
main_account_bp = Blueprint('main_account', __name__, url_prefix='/api/main-account')

@main_account_bp.route('/assets', methods=['GET'])
@token_required
def get_master_account_assets(current_user):
    """
    获取主账号的资产信息
    
    返回:
    {
        "success": true,
        "data": {
            "assets": [
                {
                    "asset": "BTC",
                    "free": "0.01",
                    "locked": "0",
                    "usdtValue": 500.0,
                    "btcValue": 0.01
                },
                ...
            ],
            "totalValue": 1000.0,
            "btcValue": 0.02
        }
    }
    """
    try:
        # 获取用户ID
        user_id = current_user.id
        
        # 获取用户对象
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在"
            }), 404
        
        # 从APIKey表中获取主账号API密钥
        api_key_obj = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
        
        if not api_key_obj:
            return jsonify({
                "success": False,
                "error": "未设置主账号API密钥"
            }), 400
            
        api_key = api_key_obj.api_key
        api_secret = api_key_obj.api_secret
        
        if not api_key or not api_secret:
            return jsonify({
                "success": False,
                "error": "未设置主账号API密钥"
            }), 400
        
        # 创建币安客户端
        client = BinanceClient(api_key, api_secret)
        
        # 获取主账号资产信息
        account_response = client._send_request('GET', '/api/v3/account', signed=True)
        
        if not account_response.get('success'):
            return jsonify({
                "success": False,
                "error": account_response.get('error', '获取主账号资产信息失败')
            }), 400
        
        # 获取账户资产
        account_data = account_response.get('data', {})
        balances = account_data.get('balances', [])
        
        # 获取所有交易对的价格以计算USDT价值
        price_response = client._send_request('GET', '/api/v3/ticker/price')
        
        if not price_response.get('success'):
            logger.warning(f"获取价格信息失败: {price_response.get('error')}")
            prices = {}
        else:
            price_data = price_response.get('data', [])
            prices = {item['symbol']: float(item['price']) for item in price_data}
        
        # 获取BTC/USDT价格
        btc_usdt_price = prices.get('BTCUSDT', 0)
        
        # 处理资产数据
        processed_assets = []
        total_usdt_value = 0
        total_btc_value = 0
        
        for balance in balances:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            
            # 如果资产数量为0则跳过
            if free == 0 and locked == 0:
                continue
            
            # 计算USDT价值
            usdt_value = 0
            btc_value = 0
            
            # 如果是USDT，直接使用数量作为价值
            if asset == 'USDT':
                usdt_value = free + locked
                btc_value = usdt_value / btc_usdt_price if btc_usdt_price > 0 else 0
            
            # 如果是BTC，使用BTC/USDT价格计算
            elif asset == 'BTC':
                usdt_value = (free + locked) * btc_usdt_price
                btc_value = free + locked
            
            # 其他资产，尝试使用资产/USDT交易对计算
            else:
                asset_usdt_pair = f"{asset}USDT"
                asset_btc_pair = f"{asset}BTC"
                
                # 尝试使用资产/USDT价格
                if asset_usdt_pair in prices:
                    usdt_value = (free + locked) * prices[asset_usdt_pair]
                    btc_value = usdt_value / btc_usdt_price if btc_usdt_price > 0 else 0
                
                # 如果没有资产/USDT价格，尝试使用资产/BTC价格
                elif asset_btc_pair in prices:
                    btc_value = (free + locked) * prices[asset_btc_pair]
                    usdt_value = btc_value * btc_usdt_price
            
            # 添加到处理后的资产列表
            processed_assets.append({
                'asset': asset,
                'free': balance['free'],
                'locked': balance['locked'],
                'usdtValue': usdt_value,
                'btcValue': btc_value
            })
            
            # 累加总价值
            total_usdt_value += usdt_value
            total_btc_value += btc_value
        
        # 按USDT价值排序
        processed_assets.sort(key=lambda x: x['usdtValue'], reverse=True)
        
        return jsonify({
            "success": True,
            "data": {
                "assets": processed_assets,
                "totalValue": total_usdt_value,
                "btcValue": total_btc_value
            }
        })
        
    except Exception as e:
        logger.exception(f"获取主账号资产信息时出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取主账号资产信息时出错: {str(e)}"
        }), 500 