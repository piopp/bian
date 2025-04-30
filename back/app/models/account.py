from datetime import datetime
from app.models import db

class SubAccount(db.Model):
    """
    子账号模型
    """
    __tablename__ = 'subaccounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    subaccount_id = db.Column(db.String(64), unique=True, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='ACTIVE')
    account_type = db.Column(db.String(20), default='standard')
    
    # 功能开通状态
    is_futures_enabled = db.Column(db.Boolean, default=False)
    is_margin_enabled = db.Column(db.Boolean, default=False)
    is_options_enabled = db.Column(db.Boolean, default=False)
    
    # 关联主账号
    master_account = db.Column(db.String(100), nullable=True)
    
    # 额外信息 (JSON格式)
    extra_info = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<SubAccount {self.email}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'subaccount_id': self.subaccount_id,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'status': self.status,
            'account_type': self.account_type,
            'is_futures_enabled': self.is_futures_enabled,
            'is_margin_enabled': self.is_margin_enabled,
            'is_options_enabled': self.is_options_enabled,
            'master_account': self.master_account
        }

class OperationLog(db.Model):
    """
    操作日志模型，记录子账号相关的操作
    """
    __tablename__ = 'operation_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operation_type = db.Column(db.String(50), nullable=False)  # 操作类型：create, delete, transfer, enable_feature, etc.
    subaccount_email = db.Column(db.String(100), nullable=True, index=True)  # 关联子账号
    operator = db.Column(db.String(100), nullable=True)  # 操作者
    operation_time = db.Column(db.DateTime, default=datetime.utcnow)
    operation_details = db.Column(db.Text, nullable=True)  # 操作详情（JSON格式）
    is_success = db.Column(db.Integer, default=1)  # 操作是否成功，1=成功，0=失败
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    
    def __repr__(self):
        return f"<OperationLog {self.operation_type}:{self.subaccount_email}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'subaccount_email': self.subaccount_email,
            'operator': self.operator,
            'operation_time': self.operation_time.isoformat() if self.operation_time else None,
            'operation_details': self.operation_details,
            'is_success': self.is_success,
            'error_message': self.error_message
        }

class Setting(db.Model):
    """
    系统设置模型
    """
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Setting {self.key}>'

class SubAccountAPISettings(db.Model):
    """
    子账号API设置模型，存储子账号的API密钥信息
    """
    __tablename__ = 'subaccount_api_settings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(128), nullable=False)
    api_secret = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SubAccountAPISettings {self.email}>"
    
    def to_dict(self):
        """
        转换为字典对象
        """
        return {
            'id': self.id,
            'email': self.email,
            'api_key': self.api_key,
            'has_api_secret': bool(self.api_secret),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict_with_secret(self):
        """
        转换为包含密钥的字典对象（谨慎使用）
        """
        data = self.to_dict()
        data['api_secret'] = self.api_secret
        return data 