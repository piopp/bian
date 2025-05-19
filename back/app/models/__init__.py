from flask_sqlalchemy import SQLAlchemy

# 全局SQLAlchemy实例
db = SQLAlchemy()

# 导出所有模型，方便从app.models直接导入
from app.models.user import User, APIKey
from app.models.account import SubAccount, OperationLog, Setting
from app.models.trading import GridTrading, OrderHistory, TradeHistory, MarginOrder, MarginTrade, FeeRecord
from app.models.trading_pair import TradingPair 