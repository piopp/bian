from flask import Blueprint, jsonify, request, session
from app.models import db, TradingPair
import logging
from app.services.binance_client import BinanceClient

logger = logging.getLogger(__name__)
trading_pairs_bp = Blueprint('trading_pairs', __name__, url_prefix='/api/trading-pairs')

@trading_pairs_bp.route('/', methods=['GET'])
def get_trading_pairs():
    """
    获取交易对列表
    可选参数: 
    - favorite (Boolean): 只获取标记为收藏的交易对
    - quote_asset (String): 按报价资产筛选，例如 USDT, BTC
    """
    try:
        # 获取查询参数
        favorite = request.args.get('favorite', 'false').lower() == 'true'
        quote_asset = request.args.get('quote_asset')
        
        # 构建查询
        query = TradingPair.query
        
        # 应用过滤条件
        if favorite:
            query = query.filter_by(is_favorite=True)
        if quote_asset:
            query = query.filter_by(quote_asset=quote_asset)
        
        # 按顺序获取交易对
        trading_pairs = query.order_by(TradingPair.order.desc(), TradingPair.symbol).all()
        
        # 将结果转为字典列表
        result = [tp.to_dict() for tp in trading_pairs]
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.exception(f"获取交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/add', methods=['POST'])
def add_trading_pair():
    """添加交易对"""
    try:
        data = request.json
        
        # 验证必要字段
        if not data.get('symbol') or not data.get('base_asset') or not data.get('quote_asset'):
            return jsonify({
                "success": False,
                "error": "缺少必要字段: symbol, base_asset, quote_asset"
            }), 400
        
        # 检查交易对是否已存在
        existing = TradingPair.query.filter_by(symbol=data['symbol']).first()
        if existing:
            return jsonify({
                "success": False,
                "error": f"交易对 {data['symbol']} 已存在"
            }), 400
        
        # 创建新交易对
        new_pair = TradingPair(
            symbol=data['symbol'],
            base_asset=data['base_asset'],
            quote_asset=data['quote_asset'],
            description=data.get('description', f"{data['base_asset']}/{data['quote_asset']}"),
            is_favorite=data.get('is_favorite', False),
            order=data.get('order', 0)
        )
        
        db.session.add(new_pair)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": new_pair.to_dict(),
            "message": f"交易对 {data['symbol']} 添加成功"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"添加交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"添加交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/update/<int:pair_id>', methods=['PUT'])
def update_trading_pair(pair_id):
    """更新交易对"""
    try:
        data = request.json
        
        # 查找交易对
        pair = TradingPair.query.get(pair_id)
        if not pair:
            return jsonify({
                "success": False,
                "error": f"交易对 ID {pair_id} 不存在"
            }), 404
        
        # 更新字段
        if 'description' in data:
            pair.description = data['description']
        if 'is_favorite' in data:
            pair.is_favorite = data['is_favorite']
        if 'order' in data:
            pair.order = data['order']
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": pair.to_dict(),
            "message": f"交易对 {pair.symbol} 更新成功"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"更新交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"更新交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/delete/<int:pair_id>', methods=['DELETE'])
def delete_trading_pair(pair_id):
    """删除交易对"""
    try:
        # 查找交易对
        pair = TradingPair.query.get(pair_id)
        if not pair:
            return jsonify({
                "success": False,
                "error": f"交易对 ID {pair_id} 不存在"
            }), 404
        
        symbol = pair.symbol
        db.session.delete(pair)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"交易对 {symbol} 删除成功"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"删除交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"删除交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/favorite/<int:pair_id>', methods=['POST'])
def toggle_favorite(pair_id):
    """切换交易对收藏状态"""
    try:
        # 查找交易对
        pair = TradingPair.query.get(pair_id)
        if not pair:
            return jsonify({
                "success": False,
                "error": f"交易对 ID {pair_id} 不存在"
            }), 404
        
        # 切换收藏状态
        pair.is_favorite = not pair.is_favorite
        db.session.commit()
        
        status = "已添加到收藏" if pair.is_favorite else "已从收藏中移除"
        
        return jsonify({
            "success": True,
            "data": pair.to_dict(),
            "message": f"交易对 {pair.symbol} {status}"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"切换收藏状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"切换收藏状态失败: {str(e)}"
        }), 500 

@trading_pairs_bp.route('/initialize-common', methods=['POST'])
def initialize_common_trading_pairs():
    """初始化常见的交易对"""
    try:
        # 定义常见的交易对
        common_pairs = [
            # 主流币种 USDT 交易对
            {"symbol": "BTCUSDT", "base_asset": "BTC", "quote_asset": "USDT", "description": "比特币/USDT", "is_favorite": True, "order": 100},
            {"symbol": "ETHUSDT", "base_asset": "ETH", "quote_asset": "USDT", "description": "以太坊/USDT", "is_favorite": True, "order": 95},
            {"symbol": "BNBUSDT", "base_asset": "BNB", "quote_asset": "USDT", "description": "币安币/USDT", "is_favorite": True, "order": 90},
            {"symbol": "SOLUSDT", "base_asset": "SOL", "quote_asset": "USDT", "description": "索拉纳/USDT", "is_favorite": True, "order": 85},
            {"symbol": "XRPUSDT", "base_asset": "XRP", "quote_asset": "USDT", "description": "瑞波币/USDT", "is_favorite": True, "order": 80},
            
            # 热门山寨币
            {"symbol": "ADAUSDT", "base_asset": "ADA", "quote_asset": "USDT", "description": "艾达币/USDT", "is_favorite": True, "order": 75},
            {"symbol": "DOGEUSDT", "base_asset": "DOGE", "quote_asset": "USDT", "description": "狗狗币/USDT", "is_favorite": True, "order": 70},
            {"symbol": "DOTUSDT", "base_asset": "DOT", "quote_asset": "USDT", "description": "波卡/USDT", "is_favorite": True, "order": 65},
            {"symbol": "MATICUSDT", "base_asset": "MATIC", "quote_asset": "USDT", "description": "Polygon/USDT", "is_favorite": True, "order": 60},
            {"symbol": "LTCUSDT", "base_asset": "LTC", "quote_asset": "USDT", "description": "莱特币/USDT", "is_favorite": True, "order": 55},
            
            # 其他常见交易对
            {"symbol": "AVAXUSDT", "base_asset": "AVAX", "quote_asset": "USDT", "description": "雪崩/USDT", "is_favorite": True, "order": 50},
            {"symbol": "LINKUSDT", "base_asset": "LINK", "quote_asset": "USDT", "description": "ChainLink/USDT", "is_favorite": True, "order": 45},
            {"symbol": "UNIUSDT", "base_asset": "UNI", "quote_asset": "USDT", "description": "Uniswap/USDT", "is_favorite": False, "order": 40},
            {"symbol": "SHIBUSDT", "base_asset": "SHIB", "quote_asset": "USDT", "description": "柴犬币/USDT", "is_favorite": False, "order": 35},
            {"symbol": "APTUSDT", "base_asset": "APT", "quote_asset": "USDT", "description": "Aptos/USDT", "is_favorite": False, "order": 30},
            
            # BTC 交易对
            {"symbol": "ETHBTC", "base_asset": "ETH", "quote_asset": "BTC", "description": "以太坊/比特币", "is_favorite": False, "order": 25},
            {"symbol": "BNBBTC", "base_asset": "BNB", "quote_asset": "BTC", "description": "币安币/比特币", "is_favorite": False, "order": 20},
            {"symbol": "XRPBTC", "base_asset": "XRP", "quote_asset": "BTC", "description": "瑞波币/比特币", "is_favorite": False, "order": 15},
            
            # 稳定币交易对
            {"symbol": "BUSDUSDT", "base_asset": "BUSD", "quote_asset": "USDT", "description": "BUSD/USDT", "is_favorite": False, "order": 10},
            {"symbol": "USDCUSDT", "base_asset": "USDC", "quote_asset": "USDT", "description": "USDC/USDT", "is_favorite": False, "order": 5}
        ]
        
        # 统计信息
        stats = {
            "total": len(common_pairs),
            "added": 0,
            "skipped": 0
        }
        
        # 批量添加交易对
        for pair_data in common_pairs:
            # 检查交易对是否已存在
            existing = TradingPair.query.filter_by(symbol=pair_data['symbol']).first()
            if existing:
                # 如果已存在，可选择更新或跳过
                logger.info(f"交易对 {pair_data['symbol']} 已存在，跳过")
                stats["skipped"] += 1
                continue
            
            # 创建新交易对
            new_pair = TradingPair(
                symbol=pair_data['symbol'],
                base_asset=pair_data['base_asset'],
                quote_asset=pair_data['quote_asset'],
                description=pair_data['description'],
                is_favorite=pair_data['is_favorite'],
                order=pair_data['order']
            )
            
            db.session.add(new_pair)
            stats["added"] += 1
        
        # 提交所有更改
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"成功初始化常见交易对: {stats['added']} 个添加, {stats['skipped']} 个已存在",
            "stats": stats
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"初始化常见交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"初始化常见交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/clear-all', methods=['DELETE'])
def clear_all_trading_pairs():
    """清空所有交易对"""
    try:
        # 删除所有交易对记录
        count = db.session.query(TradingPair).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"成功清空所有交易对，共删除 {count} 个",
            "count": count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"清空交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"清空交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/batch-import', methods=['POST'])
def batch_import_trading_pairs():
    """批量导入交易对"""
    try:
        data = request.json
        if not data or not isinstance(data.get('pairs'), list):
            return jsonify({
                "success": False,
                "error": "无效的数据格式，请提供交易对列表"
            }), 400
            
        pairs = data['pairs']
        results = []
        stats = {
            "successCount": 0,
            "existingCount": 0,
            "failCount": 0
        }
        
        for pair_data in pairs:
            # 检查必要字段
            if not pair_data.get('symbol'):
                results.append({
                    "symbol": "未知",
                    "success": False,
                    "error": "缺少必要字段: symbol"
                })
                stats["failCount"] += 1
                continue
                
            symbol = pair_data['symbol']
            
            try:
                # 检查交易对是否已存在
                existing = TradingPair.query.filter_by(symbol=symbol).first()
                if existing:
                    results.append({
                        "symbol": symbol,
                        "success": False,
                        "message": f"交易对已存在",
                        "error": "交易对已存在"
                    })
                    stats["existingCount"] += 1
                    continue
                
                # 解析基础资产和计价资产（如果未提供）
                base_asset = pair_data.get('base_asset')
                quote_asset = pair_data.get('quote_asset')
                
                if not base_asset or not quote_asset:
                    # 常见的计价资产列表
                    quote_assets = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB']
                    found = False
                    
                    # 检查symbol是否以已知计价资产结尾
                    for quote in quote_assets:
                        if symbol.endswith(quote):
                            base = symbol[:-len(quote)]
                            if base:
                                if not base_asset:
                                    base_asset = base
                                if not quote_asset:
                                    quote_asset = quote
                                found = True
                                break
                    
                    # 如果没有匹配到任何已知计价资产，使用一个基本的规则
                    if not found:
                        # 假设后4个字符是计价资产，前面的是基础资产
                        if len(symbol) > 4:
                            if not base_asset:
                                base_asset = symbol[:-4]
                            if not quote_asset:
                                quote_asset = symbol[-4:]
                
                description = pair_data.get('description') or f"{base_asset}/{quote_asset}"
                is_favorite = bool(pair_data.get('is_favorite', False))
                order = int(pair_data.get('order', 0))
                
                # 创建新交易对
                new_pair = TradingPair(
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    description=description,
                    is_favorite=is_favorite,
                    order=order
                )
                
                db.session.add(new_pair)
                
                results.append({
                    "symbol": symbol,
                    "success": True,
                    "message": "添加成功"
                })
                stats["successCount"] += 1
                
            except Exception as e:
                logger.exception(f"导入交易对 {symbol} 失败: {str(e)}")
                results.append({
                    "symbol": symbol,
                    "success": False,
                    "error": f"导入失败: {str(e)}"
                })
                stats["failCount"] += 1
        
        # 提交所有更改
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"批量导入结果: {stats['successCount']}个成功, {stats['existingCount']}个已存在, {stats['failCount']}个失败",
            "results": results,
            "successCount": stats["successCount"],
            "existingCount": stats["existingCount"],
            "failCount": stats["failCount"]
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"批量导入交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量导入交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/with-price', methods=['GET'])
def get_trading_pairs_with_price():
    """
    获取交易对列表并附带最新价格信息
    
    可选参数: 
    - market_type: 市场类型 (spot, futures, coin_futures等)
    - favorite: 是否只获取收藏的交易对
    - quote_asset: 按报价资产筛选
    - base_asset: 按基础资产筛选
    
    返回:
    - success: 是否成功
    - data: 交易对列表，每个交易对包含价格信息
    """
    try:
        # 获取查询参数
        market_type = request.args.get('market_type', 'spot').lower()
        favorite = request.args.get('favorite', 'false').lower() == 'true'
        quote_asset = request.args.get('quote_asset')
        base_asset = request.args.get('base_asset')
        
        # 构建查询
        query = TradingPair.query
        
        # 应用过滤条件
        if favorite:
            query = query.filter_by(is_favorite=True)
        if quote_asset:
            query = query.filter_by(quote_asset=quote_asset)
        if base_asset:
            query = query.filter_by(base_asset=base_asset)
        
        # 按顺序获取交易对
        trading_pairs = query.order_by(TradingPair.order.desc(), TradingPair.symbol).all()
        
        # 将结果转为字典列表
        result = [tp.to_dict() for tp in trading_pairs]
        
        # 如果获取了交易对，则尝试获取价格信息
        if result:
            # 创建无API密钥的客户端用于获取公开市场数据
            client = BinanceClient('', '')
            
            # 获取所有交易对的价格信息
            price_info = {}
            
            # 根据市场类型选择不同的API端点
            if market_type in ['futures', 'usdt_futures', 'portfolio_margin_um']:
                # U本位合约
                endpoint = '/fapi/v1/ticker/price'
                res = client._send_request('GET', endpoint)
            elif market_type in ['coin_futures', 'delivery']:
                # 币本位合约
                endpoint = 'dapi/v1/ticker/price'
                res = client._send_request('GET', endpoint)
            else:
                # 默认使用现货
                endpoint = '/api/v3/ticker/price'
                res = client._send_request('GET', endpoint)
                
            if res.get('success') and res.get('data'):
                # 处理返回的价格数据
                prices = res['data'] if isinstance(res['data'], list) else [res['data']]
                for price_item in prices:
                    symbol = price_item.get('symbol')
                    if symbol:
                        price_info[symbol] = {
                            'price': price_item.get('price'),
                            'timestamp': price_item.get('time', None)
                        }
            
            # 为每个交易对添加价格信息
            for pair in result:
                symbol = pair['symbol']
                # 添加价格信息
                if symbol in price_info:
                    pair['price_info'] = price_info[symbol]
                    # 计算建议的交易数量
                    try:
                        if pair['price_info'].get('price'):
                            price = float(pair['price_info']['price'])
                            # 价值标准化 - 基于不同价格范围推荐不同的合约数量/交易金额
                            pair['suggested_quantity'] = calculate_suggested_quantity(pair['base_asset'], price)
                            pair['suggested_amount'] = calculate_suggested_amount(pair['base_asset'], price)
                    except Exception as price_error:
                        logger.warning(f"计算建议交易数量出错: {str(price_error)}")
                else:
                    pair['price_info'] = {'price': None, 'timestamp': None}
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.exception(f"获取带价格的交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取带价格的交易对失败: {str(e)}"
        }), 500

def calculate_suggested_quantity(base_asset, price):
    """计算建议的交易数量（适用于币本位合约）"""
    if not price or price <= 0:
        return 1
        
    # 根据资产和价格计算合适的合约张数
    # 目标价值范围: 2000-5000 USDT
    target_value = 3000  # 目标价值
    
    if base_asset == 'BTC':
        # BTC价格通常较高，适合小数量
        if price > 50000:
            return 1  # 非常高价格
        elif price > 20000:
            return 2  # 高价格
        else:
            return max(1, round(target_value / price))  # 标准范围
            
    elif base_asset == 'ETH':
        # ETH价格中等，适合中等数量
        if price > 3000:
            return 5
        elif price > 1500:
            return 10
        else:
            return max(1, round(target_value / price / 2)) * 2  # 偶数张数
            
    else:
        # 其他资产，基于价格动态计算
        if price > 1000:
            return max(1, round(target_value / price / 5) * 5)  # 调整为5的倍数
        elif price > 100:
            return max(5, round(target_value / price / 10) * 10)  # 调整为10的倍数
        elif price > 10:
            return max(10, round(target_value / price / 25) * 25)  # 调整为25的倍数
        elif price > 1:
            return max(50, round(target_value / price / 50) * 50)  # 调整为50的倍数
        elif price > 0.1:
            return max(100, round(target_value / price / 100) * 100)  # 调整为100的倍数
        else:
            return max(500, round(target_value / price / 500) * 500)  # 调整为500的倍数

def calculate_suggested_amount(base_asset, price):
    """计算建议的交易金额（适用于U本位合约，以USDT计价）"""
    if not price or price <= 0:
        return 3000  # 默认金额
        
    # 基础金额范围
    base_amount = 3000
    
    # 根据资产和价格调整金额
    if base_asset == 'BTC':
        # BTC价格高，建议较大金额
        if price > 50000:
            return 5000
        else:
            return 3000
            
    elif base_asset == 'ETH':
        # ETH价格中等
        if price > 3000:
            return 4000
        else:
            return 3000
            
    else:
        # 其他资产，提供标准金额
        if price > 100:
            return 3000
        elif price > 10:
            return 2000
        elif price > 1:
            return 1500
        else:
            return 1000

@trading_pairs_bp.route('/add-doge', methods=['POST'])
def add_doge_trading_pairs():
    """添加DOGE相关的交易对"""
    try:
        # 定义要添加的DOGE交易对
        doge_pairs = [
            {"symbol": "DOGEUSDT", "base_asset": "DOGE", "quote_asset": "USDT", "description": "狗狗币/USDT", "is_favorite": True, "order": 69},
            {"symbol": "DOGEUSDC", "base_asset": "DOGE", "quote_asset": "USDC", "description": "狗狗币/USDC", "is_favorite": False, "order": 68}
        ]
        
        # 统计信息
        stats = {
            "total": len(doge_pairs),
            "added": 0,
            "skipped": 0
        }
        
        # 批量添加交易对
        for pair_data in doge_pairs:
            # 检查交易对是否已存在
            existing = TradingPair.query.filter_by(symbol=pair_data['symbol']).first()
            if existing:
                logger.info(f"交易对 {pair_data['symbol']} 已存在，跳过")
                stats["skipped"] += 1
                continue
            
            # 创建新交易对
            new_pair = TradingPair(
                symbol=pair_data['symbol'],
                base_asset=pair_data['base_asset'],
                quote_asset=pair_data['quote_asset'],
                description=pair_data['description'],
                is_favorite=pair_data['is_favorite'],
                order=pair_data['order']
            )
            
            db.session.add(new_pair)
            stats["added"] += 1
        
        # 提交所有更改
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"成功添加DOGE交易对: {stats['added']} 个添加, {stats['skipped']} 个已存在",
            "stats": stats
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"添加DOGE交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"添加DOGE交易对失败: {str(e)}"
        }), 500

@trading_pairs_bp.route('/global-pair', methods=['GET'])
def get_global_trading_pair():
    """
    获取全局交易对（用于交易中心默认选择）
    
    参数:
    - contract_type: 合约类型，可选值为 UM（U本位合约）或 CM（币本位合约），默认为 UM
    
    返回:
    - 全局交易对信息，包含适合对应合约类型的格式
    """
    try:
        # 获取合约类型参数
        contract_type = request.args.get('contract_type', 'UM').upper()
        
        # 查询收藏的交易对，按顺序获取第一个
        global_pair = TradingPair.query.filter_by(is_favorite=True).order_by(TradingPair.order.desc()).first()
        
        if not global_pair:
            # 如果没有收藏的交易对，获取任意一个交易对
            global_pair = TradingPair.query.order_by(TradingPair.order.desc()).first()
        
        if not global_pair:
            # 如果数据库中没有交易对，返回默认交易对
            default_pair = {
                "symbol": "BTCUSDT" if contract_type == "UM" else "BTCUSD_PERP",
                "base_asset": "BTC",
                "quote_asset": "USDT" if contract_type == "UM" else "USD",
                "description": "比特币/USDT" if contract_type == "UM" else "比特币/USD永续",
                "is_favorite": True
            }
            return jsonify({
                "success": True,
                "data": default_pair,
                "message": "使用默认全局交易对"
            })
        
        # 将交易对转换为字典
        pair_dict = global_pair.to_dict()
        
        # 根据合约类型调整交易对格式
        if contract_type == "CM" and pair_dict["symbol"].endswith("USDT"):
            # 将U本位合约格式转换为币本位合约格式
            original_symbol = pair_dict["symbol"]
            pair_dict["symbol"] = original_symbol.replace("USDT", "USD_PERP")
            pair_dict["quote_asset"] = "USD"
            pair_dict["description"] = pair_dict["description"].replace("USDT", "USD永续")
        elif contract_type == "UM" and pair_dict["symbol"].endswith("USD_PERP"):
            # 将币本位合约格式转换为U本位合约格式
            original_symbol = pair_dict["symbol"]
            pair_dict["symbol"] = original_symbol.replace("USD_PERP", "USDT")
            pair_dict["quote_asset"] = "USDT"
            pair_dict["description"] = pair_dict["description"].replace("USD永续", "USDT")
        
        return jsonify({
            "success": True,
            "data": pair_dict,
            "message": "获取全局交易对成功"
        })
        
    except Exception as e:
        logger.exception(f"获取全局交易对失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取全局交易对失败: {str(e)}"
        }), 500