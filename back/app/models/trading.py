from datetime import datetime
from app.models import db

class GridTrading(db.Model):
    """
    网格交易模型
    """
    __tablename__ = 'grid_trading'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grid_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    total_investment = db.Column(db.Float, nullable=False)
    grid_levels = db.Column(db.Integer, nullable=False)
    upper_price = db.Column(db.Float, nullable=False)
    lower_price = db.Column(db.Float, nullable=False)
    grid_prices = db.Column(db.Text, nullable=False)  # JSON 格式的价格数组
    is_bilateral = db.Column(db.Boolean, default=True)  # 是否双向交易
    leverage = db.Column(db.Float, default=1.0)
    status = db.Column(db.String(20), default="PENDING")  # PENDING/RUNNING/CLOSED
    stop_loss_price = db.Column(db.Float, nullable=True)
    stop_profit_price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    close_reason = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f"<GridTrading {self.grid_id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'grid_id': self.grid_id,
            'email': self.email,
            'symbol': self.symbol,
            'total_investment': self.total_investment,
            'grid_levels': self.grid_levels,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price,
            'grid_prices': self.grid_prices,
            'is_bilateral': self.is_bilateral,
            'leverage': self.leverage,
            'status': self.status,
            'stop_loss_price': self.stop_loss_price,
            'stop_profit_price': self.stop_profit_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'close_reason': self.close_reason
        }

class OrderHistory(db.Model):
    """
    订单历史模型
    """
    __tablename__ = 'order_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # LIMIT / MARKET
    side = db.Column(db.String(10), nullable=False)  # BUY / SELL
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # NEW/FILLED/PARTIALLY_FILLED/CANCELED
    executed_qty = db.Column(db.Float, default=0)
    order_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    client_order_id = db.Column(db.String(100), nullable=True)
    leverage = db.Column(db.Float, default=1.0)
    grid_id = db.Column(db.String(64), nullable=True, index=True)
    remarks = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<OrderHistory {self.order_id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'amount': self.amount,
            'price': self.price,
            'status': self.status,
            'executed_qty': self.executed_qty,
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'leverage': self.leverage,
            'grid_id': self.grid_id,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None
        }

class TradeHistory(db.Model):
    """
    交易历史模型
    """
    __tablename__ = 'trade_history'
    
    id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    side = db.Column(db.String(10), nullable=False)  # BUY或SELL
    price = db.Column(db.Float, nullable=False)
    qty = db.Column(db.Float, nullable=False)
    quote_qty = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    commission_asset = db.Column(db.String(20), nullable=False)
    is_maker = db.Column(db.Boolean, default=False)
    trade_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradeHistory {self.id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'qty': self.qty,
            'quote_qty': self.quote_qty,
            'commission': self.commission,
            'commission_asset': self.commission_asset,
            'is_maker': self.is_maker,
            'trade_time': self.trade_time.isoformat() if self.trade_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MarginOrder(db.Model):
    """
    杠杆交易订单模型
    """
    __tablename__ = 'margin_orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # BUY / SELL
    order_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    client_order_id = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=False)
    orig_qty = db.Column(db.Float, nullable=False)
    executed_qty = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), nullable=False)  # NEW/FILLED/PARTIALLY_FILLED/CANCELED
    type = db.Column(db.String(20), nullable=False)  # LIMIT / MARKET
    time = db.Column(db.DateTime, nullable=False)
    fee_amount = db.Column(db.Float, nullable=True)
    fee_asset = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MarginOrder {self.order_id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'symbol': self.symbol,
            'side': self.side,
            'order_id': self.order_id,
            'client_order_id': self.client_order_id,
            'price': self.price,
            'orig_qty': self.orig_qty,
            'executed_qty': self.executed_qty,
            'status': self.status,
            'type': self.type,
            'time': self.time.isoformat() if self.time else None,
            'fee_amount': self.fee_amount,
            'fee_asset': self.fee_asset,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MarginTrade(db.Model):
    """
    杠杆交易历史记录模型
    """
    __tablename__ = 'margin_trades'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trade_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    order_id = db.Column(db.String(100), nullable=False, index=True)
    side = db.Column(db.String(10), nullable=False)  # BUY / SELL
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    commission_asset = db.Column(db.String(20), nullable=False)
    is_buyer = db.Column(db.Boolean, default=False)
    is_maker = db.Column(db.Boolean, default=False)
    trade_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MarginTrade {self.trade_id}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'email': self.email,
            'symbol': self.symbol,
            'order_id': self.order_id,
            'side': self.side,
            'price': self.price,
            'quantity': self.quantity,
            'commission': self.commission,
            'commission_asset': self.commission_asset,
            'is_buyer': self.is_buyer,
            'is_maker': self.is_maker,
            'trade_time': self.trade_time.isoformat() if self.trade_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class FeeRecord(db.Model):
    """
    交易手续费记录模型
    """
    __tablename__ = 'fee_records'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False, index=True)  # 子账号邮箱
    symbol = db.Column(db.String(20), nullable=False, index=True)  # 交易对
    order_id = db.Column(db.String(100), nullable=True, index=True)  # 相关订单ID
    fee_amount = db.Column(db.Float, nullable=False)  # 手续费金额
    fee_asset = db.Column(db.String(20), nullable=False)  # 手续费资产
    source = db.Column(db.String(50), nullable=False)  # 手续费来源，例如: 'SPOT', 'MARGIN', 'FUTURES'
    description = db.Column(db.String(255), nullable=True)  # 描述信息
    trade_time = db.Column(db.DateTime, nullable=False)  # 交易时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 记录创建时间
    
    def __repr__(self):
        return f"<FeeRecord {self.id}: {self.email} - {self.fee_amount} {self.fee_asset}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'symbol': self.symbol,
            'order_id': self.order_id,
            'fee_amount': self.fee_amount,
            'fee_asset': self.fee_asset,
            'source': self.source,
            'description': self.description,
            'trade_time': self.trade_time.isoformat() if self.trade_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 