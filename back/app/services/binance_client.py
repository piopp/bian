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
        """
        初始化币安客户端
        
        参数:
        - api_key: 币安API密钥
        - api_secret: 币安API密钥
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        # 设置固定的API基础URL，根据用户要求只使用单一URL
        self.base_url = "https://api.binance.com"
        self.fapi_url = "https://fapi.binance.com"  # U本位合约API - 使用固定URL
        self.sapi_url = "https://api.binance.com/sapi"
        
        # 获取代理设置
        self.proxy = current_app.config.get('BINANCE_PROXY', None)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"初始化币安客户端 - API Key: {'*****' if api_key else 'None'}, 代理: {self.proxy or '未使用'}, 合约API URL: {self.fapi_url}")
    
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
        
        # 准备请求头
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 对于需要签名的请求，添加时间戳和签名
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        # 设置请求超时和重试参数
        timeout = 10  # 10秒超时
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒
        
        # 构建URL - 简化逻辑，确保正确构建
        # 移除endpoint开头的斜杠（如果有）
        if endpoint.startswith('/'):
            endpoint = endpoint[1:] 
            
        # 合约API
        if endpoint.startswith('fapi/') or endpoint == 'fapi':
            url = f"{self.fapi_url}/{endpoint}"
        # SAPI接口
        elif endpoint.startswith('sapi/'):
            url = f"{self.base_url}/{endpoint}"
        # 现货API
        else:
            if not endpoint.startswith('api/') and not endpoint.startswith('v'):
                endpoint = f"api/v3/{endpoint}"
            url = f"{self.base_url}/{endpoint}"
        
        # 确保URL格式正确
        # 修复协议部分
        if not url.startswith('http'):
            url = f"https://{url}"
            
        # 记录构建的URL（用于调试）
        self.logger.debug(f"构建的URL: {url}")
        
        # 验证URL格式
        if not url.startswith('http://') and not url.startswith('https://'):
            self.logger.error(f"检测到无效URL: {url}")
            return {"success": False, "error": f"无效的URL格式: {url}"}
        
        # 设置代理
        proxies = None
        if self.proxy:
            proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
            self.logger.info(f"使用代理: {self.proxy}")
        
        # 打印简化的请求信息（隐藏API密钥和详细参数）
        request_summary = {
            'method': method,
            'url': url,
            'params_count': len(params) if params else 0
        }
        
        # 使用更简洁的日志输出
        if method in ['POST', 'PUT', 'DELETE']:
            self.logger.info(f"API请求: {method} {url} (参数数量: {request_summary['params_count']})")
        else:
            # GET请求通常不需要详细日志
            self.logger.debug(f"API请求: {method} {url}")
        
        # 实现重试机制
        last_error = None
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
                elif method == 'PUT':
                    response = requests.put(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
                else:
                    error_msg = f"不支持的请求方法: {method}"
                    self.logger.error(error_msg)
                    return {
                        "success": False, 
                        "error": error_msg
                    }
                
                # 记录简化的响应信息
                if response.status_code != 200:
                    # 只有非成功状态码才记录详细信息
                    response_summary = {
                        'status_code': response.status_code,
                        'text': response.text[:200] if len(response.text) > 200 else response.text
                    }
                    self.logger.warning(f"非成功响应: {response.status_code}")
                    if response.status_code >= 400:
                        self.logger.error(f"API错误响应: {response_summary}")
                else:
                    # 成功响应只记录状态码
                    self.logger.debug(f"API响应成功: {response.status_code}")
                
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
                        last_error = error_msg
                        # JSON解析错误，尝试重试
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                            continue
                        return {
                            "success": False, 
                            "error": error_msg,
                            "raw_response": response.text
                        }
                # 处理API速率限制
                elif response.status_code == 429:
                    # 从响应头获取重试时间
                    retry_after = int(response.headers.get('Retry-After', 1))
                    self.logger.warning(f"API速率限制，将在 {retry_after} 秒后重试")
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        error_msg = "API速率限制，已达最大重试次数"
                        self.logger.error(error_msg)
                        last_error = error_msg
                        break
                # 处理服务器错误
                elif 500 <= response.status_code < 600:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"服务器错误 {response.status_code}，将在 {retry_delay} 秒后重试")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        error_msg = f"服务器错误: {response.status_code}"
                        self.logger.error(error_msg)
                        last_error = error_msg
                        break
                # 处理 403 Forbidden，通常是CloudFront拦截
                elif response.status_code == 403:
                    error_msg = f"访问被拒绝(403)，可能是CloudFront拦截。尝试使用代理。"
                    self.logger.error(error_msg)
                    last_error = error_msg
                    # 403错误，尝试重试
                    if attempt < max_retries - 1 and self.proxy:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    break
                # 其他错误
                else:
                    try:
                        error_data = response.json()
                        error_msg = f"API错误: {error_data.get('msg', str(error_data))}"
                        self.logger.error(f"{error_msg}, 状态码: {response.status_code}")
                        last_error = error_msg
                        return {
                            "success": False, 
                            "error": error_msg,
                            "status_code": response.status_code,
                            "error_data": error_data
                        }
                    except Exception:
                        error_msg = f"请求失败: {response.status_code} {response.text}"
                        self.logger.error(error_msg)
                        last_error = error_msg
                        return {
                            "success": False, 
                            "error": error_msg
                        }
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    self.logger.warning(f"请求超时，将在 {retry_delay} 秒后重试 ({attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                else:
                    error_msg = "请求超时，已达最大重试次数"
                    self.logger.error(error_msg)
                    last_error = error_msg
                    break
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    self.logger.warning(f"连接错误，将在 {retry_delay} 秒后重试 ({attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                else:
                    error_msg = "连接错误，已达最大重试次数"
                    self.logger.error(error_msg)
                    last_error = error_msg
                    break
            except Exception as e:
                error_msg = f"发送请求到币安API异常: {str(e)}"
                self.logger.exception(error_msg)
                last_error = error_msg
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                break
        
        # 如果所有重试都失败
        return {
            "success": False, 
            "error": last_error or "请求失败，已达最大重试次数",
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
        
    def get_sub_account_futures_orders(self, email, symbol=None, limit=50):
        """
        通过子账户API密钥获取子账户的合约订单
        
        根据币安官方文档，只能使用子账户自己的API密钥查询订单信息，
        母账户API密钥无法查询子账户订单
        
        参数:
        - email: 子账号邮箱
        - symbol: 交易对(可选)，不提供时查询所有交易对
        - limit: 返回记录的数量限制，默认50条
        
        返回:
        - dict: 包含API响应的字典
        """
        try:
            logger.info(f"使用子账号 {email} 的API密钥查询合约订单")
            
            # 调用API获取订单历史 - 根据币安官方文档设置参数
            params = {
                'limit': limit,
                'recvWindow': 5000  # 增加接收窗口时间，提高请求成功率
            }
            
            # 重要优化：如果不指定symbol，可以一次性获取所有交易对的订单
            # 这样做效率更高，但权重会更高(40而非5)
            if symbol:
                params['symbol'] = symbol
                logger.info(f"查询子账号 {email} 单一交易对 {symbol} 的订单，权重:5")
            else:
                logger.info(f"查询子账号 {email} 所有交易对的订单，权重:40")
            
            # 使用 U本位合约API 查询订单 - 使用完整路径
            endpoint = "fapi/v1/allOrders"  # 移除前导斜杠，确保URL正确构建
            logger.info(f"请求合约API: {endpoint}")
            
            # 直接使用当前实例发送请求
            response = self._send_request('GET', endpoint, signed=True, params=params)
            
            # 检查响应是否有效
            if response.get('success'):
                orders_count = len(response.get('data', []))
                logger.info(f"成功获取子账号 {email} 的订单列表: {orders_count}个订单")
                
                # 如果订单为空但没有出错，返回空列表而非错误
                if orders_count == 0:
                    logger.info(f"子账号 {email} 没有符合条件的订单记录")
                
                return response
            else:
                error_msg = response.get('error', 'Unknown error')
                
                # 分析错误类型，提供更具体的错误信息
                if 'Invalid API-key' in str(error_msg):
                    logger.error(f"子账号 {email} 的API密钥无效，请更新API设置")
                    return {
                        'success': False,
                        'error': f"API密钥无效，请在设置中更新API密钥"
                    }
                elif 'permission' in str(error_msg).lower():
                    logger.error(f"子账号 {email} 的API密钥权限不足，需要启用读取权限")
                    return {
                        'success': False,
                        'error': f"API密钥权限不足，请确保启用了读取权限"
                    }
                elif '403' in str(error_msg) or 'Forbidden' in str(error_msg):
                    logger.error(f"子账号 {email} 访问被拒绝，可能是IP限制或API被禁用")
                    return {
                        'success': False,
                        'error': f"访问被拒绝(403)，可能是API被限制或IP被禁止，请尝试使用代理或更新API密钥"
                    }
                elif 'signature' in str(error_msg).lower():
                    logger.error(f"子账号 {email} 签名验证失败，API密钥可能不正确")
                    return {
                        'success': False,
                        'error': f"API签名验证失败，请检查API密钥设置是否正确"
                    }
                
                logger.error(f"获取子账号 {email} 订单失败: {error_msg}")
                return response
        
        except Exception as e:
            logger.error(f"获取子账号 {email} 订单处理过程异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取子账户订单处理异常: {str(e)}"
            }
    
    def get_sub_account_futures_open_orders(self, email, symbol=None):
        """
        通过子账户API密钥获取子账户的当前挂单
        
        参数:
        - email: 子账号邮箱
        - symbol: 交易对(可选)，不提供时获取所有交易对的挂单
        
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
                logger.error(f"未找到邮箱 {email} 的有效API设置")
                return {
                    'success': False,
                    'error': f"未找到邮箱 {email} 的有效API设置"
                }
            
            max_retries = 3
            retry_delay = 1  # 初始延迟1秒
            
            for attempt in range(max_retries):
                try:
                    # 创建子账户客户端
                    sub_client = BinanceClient(api_setting.api_key, api_setting.api_secret)
                    
                    # 调用API获取当前挂单
                    params = {}
                    if symbol:
                        params['symbol'] = symbol
                    
                    endpoint = "fapi/v1/openOrders"  # 移除前导斜杠，确保URL正确构建
                    response = sub_client._send_request('GET', endpoint, signed=True, params=params)
                    
                    # 检查响应是否有效
                    if response.get('success'):
                        logger.info(f"成功获取子账号 {email} 的挂单列表: {len(response.get('data', []))}个")
                        return response
                    else:
                        error_msg = response.get('error', 'Unknown error')
                        
                        # 检查是否需要重试的错误
                        if 'timeout' in str(error_msg).lower() or 'connection' in str(error_msg).lower() or '5xx' in str(error_msg):
                            if attempt < max_retries - 1:
                                logger.warning(f"获取子账号 {email} 挂单失败，将重试 ({attempt+1}/{max_retries}): {error_msg}")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # 指数退避
                                continue
                        
                        logger.error(f"获取子账号 {email} 挂单失败: {error_msg}")
                        return response
                
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"获取子账号 {email} 挂单异常，将重试 ({attempt+1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        logger.error(f"获取子账号 {email} 挂单异常，已达最大重试次数: {str(e)}")
                        return {
                            'success': False,
                            'error': f"获取子账户挂单异常: {str(e)}"
                        }
            
            # 如果所有重试都失败
            return {
                'success': False,
                'error': f"获取子账户挂单失败，已尝试 {max_retries} 次"
            }
            
        except Exception as e:
            logger.error(f"获取子账号 {email} 挂单处理过程异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取子账户挂单处理异常: {str(e)}"
            }
            
    def sub_account_transfer(self, from_email, to_email, asset, amount):
        """
        在主账号和子账号之间转账
        
        参数:
        - from_email: 源账号邮箱
        - to_email: 目标账号邮箱
        - asset: 资产类型
        - amount: 转账金额
        
        返回:
        - dict: 包含API响应的字典
        """
        try:
            # 构建API请求参数
            params = {
                'fromEmail': from_email,
                'toEmail': to_email,
                'asset': asset,
                'amount': amount,
                'timestamp': int(time.time() * 1000)
            }
            
            # 发送API请求
            endpoint = "/sapi/v1/sub-account/transfer/subToSub"
            
            # 如果是主账号转子账号
            if from_email == '':
                endpoint = "/sapi/v1/sub-account/transfer/subToMaster"
                params.pop('fromEmail', None)
            # 如果是子账号转主账号
            elif to_email == '':
                endpoint = "/sapi/v1/sub-account/transfer/subToMaster"
                params.pop('toEmail', None)
            
            logger.info(f"转账请求: {endpoint}, 参数: {params}")
            
            # 发送请求
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            return response
            
        except Exception as e:
            logger.error(f"执行转账操作异常: {str(e)}")
            return {
                'success': False,
                'error': f"执行转账操作异常: {str(e)}"
            }
    
    def get_account_balance(self, asset=None):
        """
        获取账户可用余额
        
        参数:
        - asset: 币种名称，如果不提供则返回所有币种余额
        
        返回:
        - dict: 包含余额信息的字典，格式为 {'success': True, 'data': {'available': '100'}}
        """
        try:
            # 获取账户信息
            endpoint = "/api/v3/account"
            response = self._send_request('GET', endpoint, signed=True)
            
            if not response.get('success'):
                return response
            
            account_data = response.get('data', {})
            balances = account_data.get('balances', [])
            
            # 如果指定了币种，只返回该币种的余额
            if asset:
                for balance in balances:
                    if balance.get('asset') == asset:
                        available = balance.get('free', '0')
                        return {
                            'success': True,
                            'data': {
                                'available': available,
                                'locked': balance.get('locked', '0'),
                                'total': str(float(available) + float(balance.get('locked', '0')))
                            }
                        }
                
                # 如果未找到指定币种，尝试通过合约账户获取
                futures_response = self._send_request('GET', '/fapi/v2/balance', signed=True)
                
                if futures_response.get('success'):
                    futures_balances = futures_response.get('data', [])
                    
                    for balance in futures_balances:
                        if balance.get('asset') == asset:
                            available = balance.get('availableBalance', '0')
                            return {
                                'success': True,
                                'data': {
                                    'available': available,
                                    'locked': balance.get('withdrawAvailable', '0'),
                                    'total': balance.get('balance', '0')
                                }
                            }
                
                # 如果两个API都未找到，返回0
                return {
                    'success': True,
                    'data': {
                        'available': '0',
                        'locked': '0',
                        'total': '0'
                    }
                }
            
            # 如果未指定币种，返回所有币种的余额
            result = {}
            for balance in balances:
                asset_name = balance.get('asset')
                available = balance.get('free', '0')
                
                # 只包含余额大于0的币种
                if float(available) > 0 or float(balance.get('locked', '0')) > 0:
                    result[asset_name] = {
                        'available': available,
                        'locked': balance.get('locked', '0'),
                        'total': str(float(available) + float(balance.get('locked', '0')))
                    }
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            logger.error(f"获取账户余额异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取账户余额异常: {str(e)}"
            }
    
    def get_all_assets(self):
        """
        获取所有资产信息
        
        返回:
        - dict: 包含所有资产信息的字典
        """
        try:
            # 尝试获取现货账户资产
            spot_response = self._send_request('GET', "/api/v3/account", signed=True)
            
            # 尝试获取合约账户资产
            futures_response = self._send_request('GET', "/fapi/v2/balance", signed=True)
            
            result = {
                'success': True,
                'data': {
                    'spot': spot_response.get('data', {}).get('balances', []) if spot_response.get('success') else [],
                    'futures': futures_response.get('data', []) if futures_response.get('success') else []
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取所有资产信息异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取所有资产信息异常: {str(e)}"
            }
    
    def get_ticker(self, symbol):
        """
        获取指定交易对的行情
        
        参数:
        - symbol: 交易对名称，如BTCUSDT
        
        返回:
        - dict: 包含行情信息的字典
        """
        try:
            endpoint = "/api/v3/ticker/24hr"
            params = {'symbol': symbol}
            
            response = self._send_request('GET', endpoint, params=params)
            return response
            
        except Exception as e:
            logger.error(f"获取行情信息异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取行情信息异常: {str(e)}"
            }
    
    def get_all_tickers(self):
        """
        获取所有交易对的行情
        
        返回:
        - dict: 包含所有交易对行情的字典
        """
        try:
            endpoint = "/api/v3/ticker/24hr"
            
            response = self._send_request('GET', endpoint)
            return response
            
        except Exception as e:
            logger.error(f"获取所有行情信息异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取所有行情信息异常: {str(e)}"
            }
    
    def get_system_status(self):
        """
        获取系统状态
        
        返回:
        - dict: 包含系统状态的字典
        """
        try:
            endpoint = "/sapi/v1/system/status"
            
            response = self._send_request('GET', endpoint)
            return response
            
        except Exception as e:
            logger.error(f"获取系统状态异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取系统状态异常: {str(e)}"
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
    from app.models.account import SubAccountAPISettings
    
    try:
        # 从数据库中查询该邮箱的API设置
        api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        # 如果找不到设置或API密钥不完整，返回错误
        if not api_setting or not api_setting.api_key or not api_setting.api_secret:
            logger.error(f"未找到邮箱 {email} 的有效API设置，无法创建客户端")
            return None
            
        # 创建并返回BinanceClient实例
        logger.info(f"为子账号 {email} 创建API客户端，API Key: {api_setting.api_key[:5]}*****")
        return BinanceClient(api_setting.api_key, api_setting.api_secret)
            
    except Exception as e:
        logger.exception(f"获取币安客户端异常: {str(e)}")
        return None 