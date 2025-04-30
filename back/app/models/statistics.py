from datetime import datetime
from app.models import db

class FeeStatistics(db.Model):
    """
    手续费统计模型
    """
    __tablename__ = 'fee_statistics'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    order_id = db.Column(db.String(100), nullable=False, unique=True)
    client_order_id = db.Column(db.String(100), nullable=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    order_type = db.Column(db.String(20), nullable=False)  # LIMIT / MARKET
    side = db.Column(db.String(10), nullable=False)  # BUY / SELL
    executed_qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, nullable=False)
    fee_currency = db.Column(db.String(20), nullable=False)
    fee_usdt = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order_created_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<FeeStatistics {self.order_id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'executed_qty': self.executed_qty,
            'price': self.price,
            'fee': self.fee,
            'fee_currency': self.fee_currency,
            'fee_usdt': self.fee_usdt,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'order_created_at': self.order_created_at.isoformat() if self.order_created_at else None
        } 