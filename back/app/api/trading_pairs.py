from flask import Blueprint, jsonify, request, session
from app.models import db, TradingPair
import logging

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

@trading_pairs_bp.route('/toggle_favorite/<int:pair_id>', methods=['POST'])
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