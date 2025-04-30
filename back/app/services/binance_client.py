import requests
import hmac
import hashlib
import time
import logging
import os
import json
from urllib.parse import urlencode
from flask import current_app
from app.models.account import SubAccountAPISettings

logger = logging.getLogger(__name__)

class BinanceClient:
    """
    币安API客户端，处理与币安API的通信
    """
    
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"
        self.sapi_url = "https://api.binance.com/sapi"
        self.fapi_url = "https://fapi.binance.com"  # U本位合约API基础URL
        self.logger = logging.getLogger(__name__)
    
    def _generate_signature(self, params):
        """
        生成签名
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _send_request(self, method, endpoint, signed=False, params=None):
        """
        发送请求到币安API
        
        参数:
        - method: 请求方法 (GET, POST, DELETE)
        - endpoint: API端点
        - signed: 是否需要签名
        - params: 请求参数
        
        返回:
        - dict: 包含响应数据和请求结果状态的字典
        """
        if params is None:
            params = {}
        
        # 确定基础URL
        if endpoint.startswith('/sapi'):
            url = f"{self.sapi_url}{endpoint[5:]}"
        elif endpoint.startswith('/fapi'):
            url = f"{self.fapi_url}{endpoint[5:]}"
        else:
            url = f"{self.base_url}{endpoint}"
        
        # 准备请求头
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        # 对于需要签名的请求，添加时间戳和签名
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        # 打印完整请求信息（隐藏API密钥）
        debug_params = params.copy()
        
        request_details = {
            'method': method,
            'url': url,
            'headers': {'X-MBX-APIKEY': '***'},  # 隐藏API密钥
            'params': debug_params
        }
        
        self.logger.info(f"发送请求: {json.dumps(request_details, indent=2, ensure_ascii=False)}")
        
        # 发送请求
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            else:
                error_msg = f"不支持的请求方法: {method}"
                self.logger.error(error_msg)
                return {
                    "success": False, 
                    "error": error_msg,
                    "url": url
                }
            
            # 记录响应信息
            response_log = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text[:1000]  # 限制长度以避免日志过大
            }
            if len(response.text) > 1000:
                response_log['text'] += '... (已截断)'
                
            self.logger.info(f"收到响应: {json.dumps(response_log, indent=2, ensure_ascii=False)}")
            
            # 检查响应状态
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        "success": True, 
                        "data": data,
                        "url": url
                    }
                except Exception as e:
                    error_msg = f"解析响应JSON失败: {str(e)}"
                    self.logger.error(f"{error_msg}, 原始响应: {response.text}")
                    return {
                        "success": False, 
                        "error": error_msg,
                        "url": url,
                        "raw_response": response.text
                    }
            else:
                try:
                    error_data = response.json()
                    error_msg = f"API错误: {error_data.get('msg', str(error_data))}"
                    self.logger.error(f"{error_msg}, 状态码: {response.status_code}")
                    return {
                        "success": False, 
                        "error": error_msg,
                        "status_code": response.status_code,
                        "url": url,
                        "error_data": error_data
                    }
                except Exception:
                    error_msg = f"请求失败: {response.status_code} {response.text}"
                    self.logger.error(error_msg)
                    return {
                        "success": False, 
                        "error": error_msg,
                        "url": url
                    }
                
        except Exception as e:
            error_msg = f"发送请求到币安API异常: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False, 
                "error": error_msg,
                "url": url
            }
    
    def get_sub_accounts(self, page=1, size=10):
        """
        获取所有子账号列表
        """
        endpoint = "/sapi/v1/sub-account/list"
        params = {
            'page': page,
            'limit': size
        }
        
        return self._send_request('GET', endpoint, signed=True, params=params)
    
    def get_subaccount_status(self, email=None):
        """
        获取子账号状态
        
        参数:
        - email: 子账号邮箱，如果不提供则获取所有子账号状态
        """
        endpoint = "/sapi/v1/sub-account/status"
        params = {}
        
        if email:
            params['email'] = email
        
        return self._send_request('GET', endpoint, signed=True, params=params)
    
    def enable_subaccount_futures(self, email):
        """
        为子账号开通期货
        
        参数:
        - email: 子账号邮箱
        """
        endpoint = "/sapi/v1/sub-account/futures/enable"
        params = {
            'email': email
        }
        
        return self._send_request('POST', endpoint, signed=True, params=params)
    
    # 添加兼容性方法
    def enable_futures(self, email):
        """兼容性方法，调用enable_subaccount_futures"""
        return self.enable_subaccount_futures(email)
    
    def enable_subaccount_margin(self, email):
        """
        为子账号开通杠杆
        
        参数:
        - email: 子账号邮箱
        """
        endpoint = "/sapi/v1/sub-account/margin/enable"
        params = {
            'email': email
        }
        
        return self._send_request('POST', endpoint, signed=True, params=params)
    
    # 添加兼容性方法
    def enable_margin(self, email):
        """兼容性方法，调用enable_subaccount_margin"""
        return self.enable_subaccount_margin(email)
    
    def enable_subaccount_options(self, email):
        """
        为子账号开通期权
        
        参数:
        - email: 子账号邮箱
        """
        endpoint = "/sapi/v2/sub-account/options/enable"
        params = {
            'email': email
        }
        
        return self._send_request('POST', endpoint, signed=True, params=params)
        
    def get_sub_account_futures_balance(self, email):
        """
        通过主账户获取子账户的合约余额
        
        参数:
        - email: 子账号邮箱
        
        返回:
        - dict: 包含API响应的字典
        """
        endpoint = "/sapi/v1/sub-account/futures/account"
        params = {'email': email}
        
        return self._send_request('GET', endpoint, signed=True, params=params)
    
    def get_sub_account_futures_summary(self):
        """
        获取所有子账户的合约资金汇总
        
        返回:
        - dict: 包含API响应的字典
        """
        endpoint = "/sapi/v1/sub-account/futures/accountSummary"
        
        return self._send_request('GET', endpoint, signed=True)
    
    def get_sub_account_snapshot(self, email, account_type='FUTURES', limit=7):
        """
        获取子账户的账户快照
        
        参数:
        - email: 子账号邮箱
        - account_type: 账户类型，可选值: SPOT, MARGIN, FUTURES
        - limit: 返回记录的数量限制
        
        返回:
        - dict: 包含API响应的字典
        """
        endpoint = "/sapi/v1/sub-account/accountSnapshot"
        params = {
            'email': email,
            'type': account_type,
            'limit': limit
        }
        
        return self._send_request('GET', endpoint, signed=True, params=params)
        
    def get_sub_account_futures_positions(self, email, symbol=None):
        """
        通过主账户获取子账户的合约持仓信息
        
        参数:
        - email: 子账号邮箱
        - symbol: 交易对(可选)
        
        返回:
        - dict: 包含API响应的字典
        """
        # 首先获取子账户资产
        account_response = self.get_sub_account_futures_balance(email)
        
        if not account_response.get('success'):
            return account_response
            
        # 尝试通过其他方式获取持仓
        
        # 方法1: 使用账户获取持仓详情
        futures_data = account_response.get('data', {})
        positions = []
        
        # 查找持仓信息
        if 'positions' in futures_data:
            positions = futures_data.get('positions', [])
        elif 'futureAccountResp' in futures_data and 'positions' in futures_data.get('futureAccountResp', {}):
            positions = futures_data.get('futureAccountResp', {}).get('positions', [])
        
        # 如果找到持仓，返回结果
        if positions:
            # 如果指定了symbol，过滤持仓
            if symbol:
                positions = [p for p in positions if p.get('symbol') == symbol]
                
            return {
                'success': True,
                'data': positions
            }
            
        # 方法2: 尝试通过账户快照获取持仓
        snapshot_response = self.get_sub_account_snapshot(email, 'FUTURES', 1)
        
        if snapshot_response.get('success'):
            snapshot_data = snapshot_response.get('data', {})
            snapshots = snapshot_data.get('snapshotVos', [])
            
            if snapshots and len(snapshots) > 0:
                # 获取最新的快照
                latest_snapshot = snapshots[0]
                snapshot_data = latest_snapshot.get('data', {})
                
                # 从快照中提取持仓信息
                if 'positions' in snapshot_data:
                    positions = snapshot_data.get('positions', [])
                    
                    # 如果指定了symbol，过滤持仓
                    if symbol:
                        positions = [p for p in positions if p.get('symbol') == symbol]
                        
                    return {
                        'success': True,
                        'data': positions
                    }
        
        # 如果以上方法都未找到持仓数据，返回空列表
        return {
            'success': True,
            'data': []
        }
        
    def get_sub_account_futures_orders(self, email, symbol=None, limit=20):
        """
        通过子账户API密钥获取子账户的合约订单
        
        参数:
        - email: 子账号邮箱
        - symbol: 交易对(可选)
        - limit: 返回记录的数量限制
        
        返回:
        - dict: 包含API响应的字典
        """
        # 由于需要子账户的API密钥才能查询订单历史，我们通过数据库获取子账户API密钥
        from app.models.account import SubAccountAPISettings
        
        try:
            # 从数据库中查询该邮箱的API设置
            api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
            
            # 如果找不到设置，返回错误
            if not api_setting or not api_setting.api_key or not api_setting.api_secret:
                return {
                    'success': False,
                    'error': f"未找到邮箱 {email} 的有效API设置"
                }
                
            # 创建子账户客户端
            sub_client = BinanceClient(api_setting.api_key, api_setting.api_secret)
            
            # 调用API获取订单历史
            params = {'limit': limit}
            if symbol:
                params['symbol'] = symbol
                
            endpoint = "/fapi/v1/allOrders"
            response = sub_client._send_request('GET', endpoint, signed=True, params=params)
            
            return response
        except Exception as e:
            return {
                'success': False,
                'error': f"获取子账户订单异常: {str(e)}"
            }
    
    def get_sub_account_futures_open_orders(self, email, symbol=None):
        """
        通过子账户API密钥获取子账户的当前挂单
        
        参数:
        - email: 子账号邮箱
        - symbol: 交易对(可选)
        
        返回:
        - dict: 包含API响应的字典
        """
        # 由于需要子账户的API密钥才能查询当前挂单，我们通过数据库获取子账户API密钥
        from app.models.account import SubAccountAPISettings
        
        try:
            # 从数据库中查询该邮箱的API设置
            api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
            
            # 如果找不到设置，返回错误
            if not api_setting or not api_setting.api_key or not api_setting.api_secret:
                return {
                    'success': False,
                    'error': f"未找到邮箱 {email} 的有效API设置"
                }
                
            # 创建子账户客户端
            sub_client = BinanceClient(api_setting.api_key, api_setting.api_secret)
            
            # 调用API获取当前挂单
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            endpoint = "/fapi/v1/openOrders"
            response = sub_client._send_request('GET', endpoint, signed=True, params=params)
            
            return response
        except Exception as e:
            return {
                'success': False,
                'error': f"获取子账户挂单异常: {str(e)}"
            }

# 辅助函数，从email获取币安客户端实例
def get_client_by_email(email):
    """
    根据邮箱获取币安API客户端实例
    
    参数:
    - email: 子账号邮箱
    
    返回:
    - BinanceClient实例或None
    """
    from app.api.subaccounts import get_sub_account_api_credentials
    
    try:
        # 使用专门的子账号API获取函数
        api_key, api_secret = get_sub_account_api_credentials(email)
        
        # 验证API密钥
        if not api_key or not api_secret:
            logger.error(f"邮箱 {email} 的API密钥不完整或不存在")
            return None
            
        # 创建并返回BinanceClient实例
        return BinanceClient(api_key, api_secret)
            
    except Exception as e:
        logger.exception(f"获取币安客户端异常: {str(e)}")
        return None 