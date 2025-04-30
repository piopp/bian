from datetime import datetime
from app.models import db

class TradingPair(db.Model):
    """
    交易对模型，用于存储常用交易对信息
    """
    __tablename__ = 'trading_pairs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)  # 交易对符号，如BTCUSDT
    base_asset = db.Column(db.String(10), nullable=False)  # 基础资产，如BTC
    quote_asset = db.Column(db.String(10), nullable=False)  # 计价资产，如USDT
    description = db.Column(db.String(100), nullable=True)  # 描述，如"比特币/USDT"
    is_favorite = db.Column(db.Boolean, default=False)  # 是否标记为常用
    order = db.Column(db.Integer, default=0)  # 显示顺序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradingPair {self.symbol}>"
    
    def to_dict(self):
        """
        转换为字典对象，方便JSON序列化
        """
        return {
            'id': self.id,
            'symbol': self.symbol,
            'base_asset': self.base_asset,
            'quote_asset': self.quote_asset,
            'description': self.description,
            'is_favorite': self.is_favorite,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 