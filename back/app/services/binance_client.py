# -*- coding: utf-8 -*-
"""
币安API客户端模块

重要说明:
1. 本模块包含与币安API通信的核心功能
2. 所有子账号操作应该使用子账号自己的API密钥，而不是主账号的token
3. 主账号和子账号API的使用有明确区分

修改历史:
- 2023-XX-XX: 初始版本
- 2023-XX-XX: 增加了对DOGE交易对的支持
- 2023-XX-XX: 修复了API密钥格式验证和请求日志记录
- 2023-XX-XX: 重要修改 - 明确区分主账号和子账号API使用，确保子账号操作使用其自己的API密钥
"""

import requests
import hmac
import hashlib
import time
import logging
import os
import json
import urllib.parse
from flask import current_app
from app.models.account import SubAccountAPISettings
from app.models.user import APIKey

logger = logging.getLogger(__name__)

# 添加工具函数，限制字符串长度
def truncate_message(message, max_length=500):
    """
    截断消息，确保不超过最大长度
    """
    if not message:
        return ""
    
    if len(message) <= max_length:
        return message
    
    # 超过长度则截断并添加省略号
    return message[:max_length-3] + "..."

# 添加日志辅助函数
def log_info(message):
    """安全记录信息日志，确保不超过字符限制"""
    # 大幅减少日志输出，只在特定环境记录
    if current_app and current_app.config.get('ENV') != 'development':
        return
    logger.info(truncate_message(message))
    
def log_error(message):
    """安全记录错误日志，确保不超过字符限制"""
    logger.error(truncate_message(message))
    
def log_debug(message):
    """安全记录调试日志，确保不超过字符限制"""
    # 完全禁用调试日志
    return
    
def log_warning(message):
    """安全记录警告日志，确保不超过字符限制"""
    logger.warning(truncate_message(message))
    
def log_exception(message):
    """安全记录异常日志，确保不超过字符限制"""
    logger.exception(truncate_message(message))

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
        
        # 标记是否为子账号API客户端
        self.is_subaccount = False
        self.subaccount_email = None
        
        # 初始化logger
        self.logger = logging.getLogger(__name__)
        
        # 设置固定的API基础URL
        self.base_url = "https://api.binance.com"
        self.fapi_url = "https://fapi.binance.com/fapi"  # U本位合约API - 使用固定URL
        self.sapi_url = "https://api.binance.com/sapi"
        self.papi_url = "https://papi.binance.com/papi"  # 统一账户API
        
        # 获取代理设置
        self.proxy = current_app.config.get('BINANCE_PROXY', None)
        
        # 初始化时间偏移量
        self.time_offset = 0
        
        # 记录API密钥前缀（安全显示）
        key_info = '未提供'
        if api_key:
            key_info = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "格式异常"
        
        log_info(f"初始化币安客户端 - API Key: {key_info}, 代理: {self.proxy or '未使用'}, 合约API URL: {self.fapi_url}, 统一账户API URL: {self.papi_url}")
    
    def _generate_signature(self, params):
        """
        生成签名
        
        参数:
        - params: 要签名的参数字典
        
        返回:
        - 签名字符串
        """
        # 确保secret key可用
        if not self.api_secret:
            log_error("无法生成签名：API Secret Key不可用")
            return ""
            
        # 清理API密钥，移除可能的空格和换行符
        api_secret = self.api_secret.strip()
        
        # 按照币安API要求将参数转换为查询字符串
        query_string = urllib.parse.urlencode(params)
        log_debug(f"【签名前】查询字符串: {query_string}")
        
        try:
            # 使用HMAC SHA256算法生成签名
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            log_debug(f"【签名结果】 {signature}")
            return signature
        except Exception as e:
            log_error(f"生成签名时出错: {str(e)}")
            return ""
    
    def _send_request(self, method, url, payload=None, signed=False, params=None):
        """
        发送API请求到币安
        
        参数:
        - method: 请求方法 (GET, POST, DELETE等)
        - url: 请求URL或API端点
        - payload: 请求参数 (新格式)
        - signed: 是否需要签名 (旧格式)
        - params: 请求参数 (旧格式)
        
        返回:
        - dict: 包含响应数据和结果状态的字典
        """
        log_debug(f"_send_request调用方式: method={method}, url={url}, 有payload={payload is not None}, 有params={params is not None}, signed={signed}")
        
        # 处理兼容性: 如果使用旧格式调用(签名和params)，转换为新格式
        if params is not None:
            payload = params
            
        # 处理兼容性: 检查url是否为API端点(不含http)，如果是则构建完整URL
        if not url.startswith('http'):
            # 判断API端点类型
            if url.startswith('/'):
                url = url[1:]
                
            # 不同API类型的基础URL
            if url.startswith('fapi/') or url == 'fapi':
                # U本位合约
                url = f"{self.fapi_url}/{url.replace('fapi/', '')}"
                log_debug(f"构建U本位合约URL: {url}")
            elif url.startswith('dapi/'):
                # 币本位合约
                url = f"https://dapi.binance.com/{url}"
                log_debug(f"构建币本位合约URL: {url}")
            elif url.startswith('sapi/'):
                # SAPI接口
                url = f"{self.sapi_url}/{url.replace('sapi/', '')}"
                log_debug(f"构建SAPI接口URL: {url}")
            elif url.startswith('papi/'):
                # 统一账户API
                url = f"{self.papi_url}/{url.replace('papi/', '')}"
                log_debug(f"构建统一账户API URL: {url}")
            else:
                # 现货API
                if not url.startswith('api/') and not url.startswith('v'):
                    url = f"{self.base_url}/api/v3/{url}"
                else:
                    url = f"{self.base_url}/{url}"
                log_debug(f"构建现货API URL: {url}")
        
        # 初始化参数字典
        if payload is None:
            payload = {}
            
        # 如果需要签名，添加时间戳和生成签名
        if signed:
            # 确保API密钥存在
            if not self.api_key or not self.api_secret:
                log_error("无法发送签名请求：API密钥不完整")
                return {'success': False, 'error': "API密钥不完整，无法签名请求"}
                
            # 添加时间戳参数
            if 'timestamp' not in payload:
                payload['timestamp'] = self.get_timestamp()
                
            # 添加recvWindow参数（可选）
            if 'recvWindow' not in payload:
                payload['recvWindow'] = 60000  # 60秒，根据需要调整
                
            # 生成签名
            try:
                payload['signature'] = self._generate_signature(payload)
                
                if not payload['signature']:
                    log_error("生成签名失败")
                    return {'success': False, 'error': "生成签名失败"}
            except Exception as e:
                log_error(f"生成签名异常: {str(e)}")
                return {'success': False, 'error': f"生成签名异常: {str(e)}"}
            
        # 为安全起见，不记录完整的API密钥，只记录前6位和后4位
        masked_key = "未提供API密钥"
        if self.api_key:
            masked_key = self.api_key[:6] + "..." + self.api_key[-4:] if len(self.api_key) > 10 else "密钥格式异常"
        log_debug(f"准备请求 {url}, 方法: {method}, 使用API密钥: {masked_key}")
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 只有在API密钥存在时才添加到头部
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        # 设置代理
        proxies = None
        if self.proxy:
            proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
            log_debug(f"使用代理: {self.proxy}")
            
        # 设置超时
        timeout = 15  # 15秒超时
        
        # 打印完整的请求信息 (不包含敏感信息)
        safe_payload = payload.copy()
        if 'signature' in safe_payload:
            safe_payload['signature'] = safe_payload['signature'][:10] + '...'
        
        if method == 'GET':
            full_url = f"{url}?{urllib.parse.urlencode(payload)}" if payload else url
        else:
            full_url = url
            
        # 简化日志输出，只记录基本请求信息
        log_info(f"{method} {url.split('?')[0]}")
        
        try:
            # 使用请求会话保持连接复用
            session = requests.Session()
            
            try:
                # 发送HTTP请求
                if method == 'GET':
                    response = session.get(url, headers=headers, params=payload, proxies=proxies, timeout=timeout)
                elif method == 'POST':
                    response = session.post(url, headers=headers, params=payload, proxies=proxies, timeout=timeout)
                elif method == 'DELETE':
                    response = session.delete(url, headers=headers, params=payload, proxies=proxies, timeout=timeout)
                else:
                    log_error(f"不支持的请求方法: {method}")
                    return {'success': False, 'error': f"不支持的请求方法: {method}"}
            except requests.exceptions.ProxyError as proxy_error:
                # 代理连接失败，尝试直接连接
                log_warning(f"代理连接失败，尝试直接连接: {str(proxy_error)}")
                
                if method == 'GET':
                    response = session.get(url, headers=headers, params=payload, timeout=timeout)
                elif method == 'POST':
                    response = session.post(url, headers=headers, params=payload, timeout=timeout)
                elif method == 'DELETE':
                    response = session.delete(url, headers=headers, params=payload, timeout=timeout)
            
            # 简化响应日志记录
            if response.status_code != 200:
                log_error(f"响应状态码: {response.status_code}")
            
            # 解析JSON响应
            try:
                result = response.json()
                
                # 打印截取的响应内容
                if isinstance(result, dict):
                    # 如果是错误响应，只记录错误信息
                    if 'code' in result and result['code'] != 200 and result['code'] != 0:
                        error_msg = result.get('msg', '未知错误')
                        log_error(f"API错误: 代码={result['code']}, 消息={error_msg}")
                        
                        # 检查是否为API-key错误
                        if result.get('code') in [-2015, -2014]:
                            log_error("API密钥无效或权限不足")
                            return {'success': False, 'error': f"API密钥错误: {error_msg}"}
                        
                        return {'success': False, 'error': f"API错误: {error_msg}"}
                elif isinstance(result, list) and len(result) > 0:
                    # 列表结果只记录长度
                    log_info(f"列表响应，共{len(result)}项")
                
                if response.status_code != 200:
                    return {'success': False, 'error': f"请求失败: HTTP {response.status_code}"}
                
                return {'success': True, 'data': result}
            except json.JSONDecodeError as e:
                log_error(f"JSON解析错误: {str(e)}, 响应内容: {response.text[:200]}")
                return {'success': False, 'error': f"响应格式错误: {str(e)}"}
            
        except requests.exceptions.RequestException as e:
            log_error(f"请求异常: {str(e)}")
            return {'success': False, 'error': f"网络请求异常: {str(e)}"}
        except Exception as e:
            log_error(f"未知错误: {str(e)}")
            return {'success': False, 'error': f"未知错误: {str(e)}"}
    
    def get_timestamp(self):
        """获取校正后的时间戳"""
        return int(time.time() * 1000 + self.time_offset)
    
    def sync_time(self):
        """
        同步本地时间与币安服务器时间
        
        返回:
            - 成功时: {'success': True, 'data': {'local_time': 本地时间, 'server_time': 服务器时间, 'offset': 时间偏移}}
            - 失败时: {'success': False, 'error': '错误信息'}
        """
        try:
            log_info("开始同步本地时间与币安服务器时间")
            local_time = int(time.time() * 1000)
            
            # 直接构建URL，不使用_send_request方法，避免循环依赖
            url = f"{self.base_url}/api/v3/time"
            
            try:
                # 简单的GET请求获取服务器时间
                log_info(f"发送请求到币安时间API: {url}")
                # 设置超时为5秒，避免长时间等待
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        server_time = data.get('serverTime')
                        
                        if server_time:
                            # 计算时间偏移量
                            now = int(time.time() * 1000)
                            self.time_offset = server_time - now
                            
                            log_info(f"时间同步成功 - 本地时间: {now}, 服务器时间: {server_time}, 偏移量: {self.time_offset}毫秒")
                            
                            return {
                                'success': True,
                                'data': {
                                    'local_time': now,
                                    'server_time': server_time,
                                    'offset': self.time_offset,
                                    'synchronized': True
                                }
                            }
                        else:
                            log_error("币安返回的响应中不包含serverTime字段")
                            return {
                                'success': False,
                                'error': '币安返回的响应中不包含serverTime字段'
                            }
                    except ValueError as json_error:
                        log_error(f"解析币安时间API响应JSON失败: {str(json_error)}")
                        return {
                            'success': False,
                            'error': f"解析币安时间API响应失败: {str(json_error)}"
                        }
                else:
                    log_error(f"币安时间API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                    return {
                        'success': False,
                        'error': f"币安时间API请求失败，状态码: {response.status_code}"
                    }
            except requests.RequestException as req_error:
                log_error(f"请求币安时间API异常: {str(req_error)}")
                return {
                    'success': False,
                    'error': f"请求币安时间API异常: {str(req_error)}"
                }
        except Exception as e:
            error_msg = str(e)
            log_error(f"同步时间异常: {error_msg}")
            return {
                'success': False,
                'error': f"同步时间异常: {error_msg}"
            }
    
    def get_account_info(self):
        """
        获取账户信息，可用于验证API密钥
        
        返回:
        - 成功时返回{'success': True, 'data': {...}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            # 现货账户信息端点
            endpoint = '/api/v3/account'
            
            # 发送请求，需要签名
            response = self._send_request('GET', endpoint, signed=True)
            
            return response
        except Exception as e:
            logger.exception(f"获取账户信息异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取账户信息异常: {str(e)}"
            }
    
    def get_account_balance(self):
        """
        获取账户余额信息
        
        返回:
        - 成功时返回{'success': True, 'data': [...]}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            # 获取账户信息，包含余额
            account_info = self.get_account_info()
            
            if not account_info.get('success'):
                return account_info
            
            # 从账户信息中提取余额
            balances = account_info.get('data', {}).get('balances', [])
            
            # 筛选出有余额的资产
            non_zero_balances = [
                balance for balance in balances
                if float(balance.get('free', 0)) > 0 or float(balance.get('locked', 0)) > 0
            ]
            
            return {
                'success': True,
                'data': non_zero_balances
            }
        except Exception as e:
            logger.exception(f"获取账户余额异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取账户余额异常: {str(e)}"
            }
            
    def check_trade_permission(self):
        """
        检查是否有交易权限
        
        返回:
        - 成功时返回{'success': True, 'data': {'canTrade': True/False, ...}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            # 获取账户信息
            account_info = self.get_account_info()
            
            if not account_info.get('success'):
                return account_info
            
            # 检查交易权限
            data = account_info.get('data', {})
            permissions = {
                'canTrade': data.get('canTrade', False),
                'canDeposit': data.get('canDeposit', False),
                'canWithdraw': data.get('canWithdraw', False)
            }
            
            return {
                'success': True,
                'data': permissions
            }
        except Exception as e:
            logger.exception(f"检查交易权限异常: {str(e)}")
            return {
                'success': False,
                'error': f"检查交易权限异常: {str(e)}"
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
        
        response = self._send_request('GET', endpoint, signed=True, params=params)
        
        # 处理响应以确保返回统一的数据结构
        if isinstance(response, dict) and response.get('success') and 'data' in response:
            data = response['data']
            # 检查数据结构，确保正确返回子账号列表
            if isinstance(data, list):
                # 如果直接返回列表，保持原样
                return response
            elif isinstance(data, dict):
                # 如果返回字典，检查关键字段
                if 'subAccountList' in data:
                    subaccounts = data['subAccountList']
                    # 更新数据结构
                    response['data'] = subaccounts
                    return response
        
        # 如果无法处理，返回原始响应
        return response
    
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
    
    def create_virtual_sub_account(self, username_prefix):
        """
        创建虚拟子账号
        
        参数:
        - username_prefix: 子账号用户名前缀，后面会自动添加随机字符串
        
        返回:
        - 成功时返回{'success': True, 'data': {'email': '子账号邮箱'}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            logger.info(f"开始创建虚拟子账号，前缀: {username_prefix}")
            
            # 确保用户名合法（只允许字母、数字和下划线）
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', username_prefix):
                logger.error(f"用户名前缀 {username_prefix} 包含非法字符")
                return {
                    'success': False,
                    'error': '用户名只能包含字母、数字和下划线'
                }
            
            # 用户名长度检查 - 币安API限制
            if len(username_prefix) > 20:
                logger.error(f"用户名前缀 {username_prefix} 太长")
                return {
                    'success': False,
                    'error': '用户名前缀不能超过20个字符'
                }
            
            # 币安创建虚拟子账号的API端点
            endpoint = "/sapi/v1/sub-account/virtualSubAccount"
            
            # 确定子账号用户名 - 不再添加_virtual后缀
            final_username = username_prefix
            
            # 如果用户名长度小于6，自动添加随机字符
            import random
            import string
            if len(username_prefix) < 6:
                # 添加随机字符，确保用户名长度至少为6
                random_suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6 - len(username_prefix)))
                final_username = f"{username_prefix}{random_suffix}"
                logger.info(f"自动添加随机后缀，最终用户名: {final_username}")
            
            # 移除_virtual后缀如果存在
            if final_username.endswith('_virtual'):
                final_username = final_username[:-8]  # 移除_virtual
                logger.info(f"移除_virtual后缀，最终用户名: {final_username}")
                
            # 再次检查长度限制（确保添加随机字符后仍然符合要求）
            if len(final_username) > 20:
                final_username = final_username[:20]
                logger.warning(f"用户名超长，已截断为: {final_username}")
            
            # 所需参数 - 标准币安API规定
            params = {
                'subAccountString': final_username  # 唯一必要的参数
            }
            
            # 发送请求
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            # 处理返回结果
            if isinstance(response, dict):
                # 如果已经是我们格式化的响应
                if 'success' in response:
                    if response['success']:
                        logger.info(f"创建虚拟子账号 {final_username} 成功: {response.get('data', {})}")
                    else:
                        error_msg = response.get('error', '未知错误')
                        logger.error(f"创建虚拟子账号 {final_username} 失败: {error_msg}")
                        
                        # 检查常见错误并提供更详细的错误信息
                        if "parameter is invalid" in error_msg.lower():
                            logger.error("可能是参数格式错误或用户名不符合币安要求，请检查用户名是否合法")
                            response['error'] = f"{error_msg} - 可能是用户名格式不符合币安要求，请使用只包含字母、数字、下划线的用户名"
                        
                    return response
                
                # 币安API成功返回的格式可能是 {"email": "xxx@xxx.com"}
                if 'email' in response:
                    email = response['email']
                    logger.info(f"创建虚拟子账号成功，邮箱: {email}")
                    return {
                        'success': True,
                        'data': response,
                        'message': '成功创建虚拟子账号'
                    }
                
                # 检查是否有错误信息
                if 'msg' in response or 'message' in response or 'errorMessage' in response or 'code' in response:
                    error_msg = response.get('msg', response.get('message', response.get('errorMessage', '未知错误')))
                    error_code = response.get('code', 'UNKNOWN')
                    logger.error(f"创建虚拟子账号 {final_username} 失败: 错误码={error_code}, 错误信息={error_msg}")
                    
                    return {
                        'success': False,
                        'error': f"错误码: {error_code}, 错误信息: {error_msg}",
                        'code': error_code
                    }
                
                # 其他格式的成功响应
                logger.info(f"创建虚拟子账号 {final_username} API调用成功，但返回格式未知: {response}")
                return {
                    'success': True,
                    'data': response,
                    'message': '虚拟子账号创建请求已提交'
                }
            else:
                # 处理非字典响应
                logger.error(f"创建虚拟子账号 {final_username} 返回格式异常: {response}")
                return {
                    'success': False,
                    'error': f'返回格式异常: {response}'
                }
                
        except Exception as e:
            # 捕获并记录异常
            error_msg = str(e)
            logger.error(f"创建虚拟子账号 {username_prefix} 异常: {error_msg}")
            return {
                'success': False,
                'error': f"创建虚拟子账号异常: {error_msg}"
            }
    
    def enable_subaccount_futures(self, email):
        """
        为子账号开通期货功能
        
        参数:
        - email: 子账号邮箱
        
        返回值：
        - 成功时返回{'success': True, 'data': {...}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            logger.info(f"开始为子账号{email} 开通期货交易")
            
            # 正确的子账号开通期货的API端点
            endpoint = "/sapi/v1/sub-account/futures/enable"
            
            # 所需参数
            params = {
                'email': email,
                'recvWindow': 10000  # 增加接收窗口，提高成功率
            }
            
            # 发送请求
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            # 处理返回结果
            if isinstance(response, dict):
                # 如果返回正常的字典响应
                if 'success' in response:
                    # API调用可能已经返回了格式化的结果
                    return response
                
                # 币安API成功时会返回包含子账号信息的对象，无success字段
                if 'email' in response:
                    # 检查是否包含期货账户状态字段
                    futures_enabled = response.get('enableFutures', False) or response.get('isFuturesEnabled', False)
                    if futures_enabled:
                        logger.info(f"为子账号 {email} 开通期货交易成功")
                        return {
                            'success': True,
                            'data': response,
                            'message': '成功开通期货交易'
                        }
                    else:
                        logger.warning(f"调用API成功但期货可能未开通 {response}")
                        return {
                            'success': False,
                            'data': response,
                            'error': '调用API成功但期货状态未改变'
                        }
                
                # 其他情况，API调用成功但无法确认结果
                logger.info(f"子账号{email} 期货交易API调用成功，返回 {response}")
                return {
                    'success': True,
                    'data': response,
                    'message': '期货交易开通请求已提交'
                }
            else:
                # 如果返回不是字典，可能是API调用异常
                logger.error(f"为子账号 {email} 开通期货交易返回格式异常 {response}")
                return {
                    'success': False,
                    'error': f'返回格式异常: {response}'
                }
                
        except Exception as e:
            # 捕获并记录异常
            error_msg = str(e)
            logger.error(f"为子账号 {email} 开通期货交易异常 {error_msg}")
            return {
                'success': False,
                'error': f"开通期货交易异常 {error_msg}"
            }
    
    # 添加兼容性方法
    def enable_futures(self, email):
        return self.enable_subaccount_futures(email)

    def enable_subaccount_margin(self, email):
        """
        为子账号开通杠杆交易
        
        参数:
        - email: 子账号邮箱
        
        返回:
        - 成功时返回{'success': True, 'data': {...}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            logger.info(f"开始为子账号{email} 开通杠杆交易")
            
            # 正确的子账号开通杠杆的API端点
            endpoint = "/sapi/v1/sub-account/margin/enable"
            
            # 所需参数
            params = {
                'email': email,
                'recvWindow': 10000  # 增加接收窗口，提高成功率
            }
            
            # 发送请求
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            # 处理返回结果
            if isinstance(response, dict):
                # 如果返回正常的字典响应
                if 'success' in response:
                    # API调用可能已经返回了格式化的结果
                    return response
                
                # 币安API成功时会返回包含子账号信息的对象，无success字段
                if 'email' in response:
                    # 检查是否包含杠杆账户状态字段
                    margin_enabled = response.get('enableMargin', False)
                    if margin_enabled:
                        logger.info(f"为子账号 {email} 开通杠杆交易成功")
                        return {
                            'success': True,
                            'data': response,
                            'message': '成功开通杠杆交易'
                        }
                    else:
                        logger.warning(f"调用API成功但杠杆可能未开通 {response}")
                        return {
                            'success': False,
                            'data': response,
                            'error': '调用API成功但杠杆状态未改变'
                        }
                
                # 其他情况，API调用成功但无法确认结果
                logger.info(f"子账号{email} 杠杆交易API调用成功，返回 {response}")
                return {
                    'success': True,
                    'data': response,
                    'message': '杠杆交易开通请求已提交'
                }
            else:
                # 如果返回不是字典，可能是API调用异常
                logger.error(f"为子账号 {email} 开通杠杆交易返回格式异常 {response}")
                return {
                    'success': False,
                    'error': f'返回格式异常: {response}'
                }
                
        except Exception as e:
            # 捕获并记录异常
            error_msg = str(e)
            logger.error(f"为子账号 {email} 开通杠杆交易异常 {error_msg}")
            return {
                'success': False,
                'error': f"开通杠杆交易异常 {error_msg}"
            }
    
    # 添加兼容性方法
    def enable_margin(self, email):
        return self.enable_subaccount_margin(email)
    
    def place_portfolio_margin_order(self, symbol, side, order_type, quantity=None, price=None, time_in_force=None, quoteOrderQty=None, **kwargs):
        """
        在统一账户下现货/杠杆市场下单
        
        参数:
        - symbol: 交易对名称
        - side: 交易方向 (BUY, SELL)
        - order_type: 订单类型 (LIMIT, MARKET)
        - quantity: 交易数量
        - quoteOrderQty: 交易金额（以计价币种计算，例如USDT）
        - price: 交易价格 (LIMIT订单必填)
        - time_in_force: 订单有效期 (GTC, IOC, FOK)
        - **kwargs: 其他可选参数
        
        返回:
        - dict: 包含订单信息的字典
        """
        try:
            # 强化记录API使用情况
            if hasattr(self, 'is_subaccount') and self.is_subaccount and hasattr(self, 'subaccount_email'):
                logger.info(f"✅ 确认使用子账号 {self.subaccount_email} 的API密钥执行统一账户下单")
            else:
                # 更严格的警告，这种情况下很可能会失败
                error_msg = "⚠️ 警告: 此次统一账户下单未使用子账号API，将很可能导致操作失败"
                logger.warning(error_msg)
                
                # 遇到这种情况时，返回明确的错误信息
                if side == 'SELL' and order_type == 'MARKET':
                    # 市价卖单必须使用子账号API
                    return {
                        'success': False, 
                        'error': '市价卖单必须使用子账号API，当前未检测到有效的子账号API配置。请确保在交易前设置useSubAccountApi=true。'
                    }
            
            # 验证并格式化交易对
            if symbol:
                # 检查是否交易对格式正确
                common_quote_assets = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB', 'USDC']
                common_base_assets = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LTC']
                has_quote_asset = False
                
                for quote in common_quote_assets:
                    if symbol.endswith(quote):
                        has_quote_asset = True
                        break
                
                if not has_quote_asset:
                    # 如果只提供了基础资产名称，自动添加USDT作为计价资产
                    if symbol.upper() in common_base_assets:
                        logger.info(f"自动为基础资产 {symbol} 添加USDT计价币")
                        symbol = f"{symbol.upper()}USDT"
                    else:
                        # 检查是否为常见基础资产，不支持则保持原样
                        # 注意：这里不会自动修复错误的交易对
                        logger.warning(f"交易对 {symbol} 不符合标准格式，不进行自动修正")
            
            # 验证参数合法性
            if not quantity and not quoteOrderQty:
                return {'success': False, 'error': '必须提供交易数量(quantity)或交易金额(quoteOrderQty)参数中的至少一个'}
            
            # 获取交易对精度规则
            filters = self._get_symbol_filters(symbol)
            
            # 处理数量和价格的精度
            quantity_precision = 8  # 默认精度
            price_precision = 8     # 默认精度
            
            if filters:
                # 获取数量精度
                if 'LOT_SIZE' in filters:
                    step_size = filters['LOT_SIZE'].get('stepSize', '0.00000001')
                    # 计算小数位数
                    decimals = 0
                    if '.' in step_size:
                        decimals = len(step_size.split('.')[1].rstrip('0'))
                    quantity_precision = decimals
                    logger.info(f"交易对{symbol}的数量精度为{quantity_precision}位小数")
                
                # 获取价格精度
                if 'PRICE_FILTER' in filters:
                    tick_size = filters['PRICE_FILTER'].get('tickSize', '0.00000001')
                    # 计算小数位数
                    decimals = 0
                    if '.' in tick_size:
                        decimals = len(tick_size.split('.')[1].rstrip('0'))
                    price_precision = decimals
                    logger.info(f"交易对{symbol}的价格精度为{price_precision}位小数")
            
            # 调整数量和价格精度
            if quantity is not None:
                original_quantity = quantity
                quantity = self._format_number_precision(quantity, quantity_precision)
                if original_quantity != quantity:
                    logger.info(f"调整数量精度: {original_quantity} -> {quantity}")
            
            if price is not None:
                original_price = price
                price = self._format_number_precision(price, price_precision)
                if original_price != price:
                    logger.info(f"调整价格精度: {original_price} -> {price}")
            
            if quoteOrderQty is not None:
                # 计价币种金额一般精度为8位
                original_quote_qty = quoteOrderQty
                quoteOrderQty = self._format_number_precision(quoteOrderQty, 8)
                if original_quote_qty != quoteOrderQty:
                    logger.info(f"调整金额精度: {original_quote_qty} -> {quoteOrderQty}")
            
            # 记录参数信息
            logger.debug(f"统一账户下单参数: symbol={symbol}, side={side}, type={order_type}, quantity={quantity}, quoteOrderQty={quoteOrderQty}, price={price}")
            
            # 发送请求到API端点 - 使用正确的统一账户API端点
            endpoint = "https://papi.binance.com/papi/v1/margin/order" 
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type
            }
            
            # 添加数量参数 - 优先使用quantity，其次使用quoteOrderQty
            if quantity:
                params['quantity'] = str(quantity)
            elif quoteOrderQty:
                params['quoteOrderQty'] = str(quoteOrderQty)
                
            # LIMIT订单必须包含价格和有效期
            if order_type == 'LIMIT':
                if not price:
                    return {'success': False, 'error': 'LIMIT订单必须提供价格'}
                params['price'] = str(price)
                params['timeInForce'] = time_in_force or 'GTC'
            
            # 市价卖单SELL MARKET必须使用quantity参数，不能使用quoteOrderQty
            if order_type == 'MARKET' and side == 'SELL' and 'quantity' not in params and 'quoteOrderQty' in params:
                return {'success': False, 'error': '市价卖单(SELL MARKET)必须使用quantity参数指定卖出数量，不能使用quoteOrderQty参数'}
            
            # 添加其他可选参数
            for key, value in kwargs.items():
                if value is not None:
                    params[key] = value
            
            # 发送请求并处理响应
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            if response.get('success'):
                logger.info(f"统一账户下单成功: {symbol}, {side}, {order_type}, 订单ID: {response.get('data', {}).get('orderId')}")
                return response
            else:
                logger.error(f"统一账户下单失败: {response.get('error')}")
                return response
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"统一账户下单异常: {error_msg}")
            return {
                'success': False,
                'error': f"统一账户下单异常: {error_msg}"
            }
    
    def place_portfolio_margin_order_um(self, symbol, side, order_type, quantity=None, price=None, time_in_force=None, quoteOrderQty=None, position_side=None, **kwargs):
        """
        在统一账户下U本位合约市场下单
        
        参数:
        - symbol: 交易对名称
        - side: 交易方向 (BUY, SELL)
        - order_type: 订单类型 (LIMIT, MARKET)
        - quantity: 交易数量
        - quoteOrderQty: 交易金额（以计价币种计算，例如USDT）
        - price: 交易价格 (LIMIT订单必填)
        - time_in_force: 订单有效期 (GTC, IOC, FOK)
        - position_side: 持仓方向 (LONG, SHORT, 用于双向持仓模式)
        - **kwargs: 其他可选参数
        
        返回:
        - dict: 包含订单信息的字典
        """
        try:
            # 强化记录API使用情况
            if hasattr(self, 'is_subaccount') and self.is_subaccount and hasattr(self, 'subaccount_email'):
                logger.info(f"✅ 确认使用子账号 {self.subaccount_email} 的API密钥执行U本位合约下单")
            else:
                # 更严格的警告，这种情况下很可能会失败
                error_msg = "⚠️ 警告: 此次U本位合约下单未使用子账号API，将很可能导致操作失败"
                logger.warning(error_msg)
                
                # 遇到这种情况时，返回明确的错误信息
                if side == 'SELL' and order_type == 'MARKET':
                    # 市价卖单必须使用子账号API
                    return {
                        'success': False, 
                        'error': '市价卖单必须使用子账号API，当前未检测到有效的子账号API配置。请确保在交易前设置useSubAccountApi=true。'
                    }
            
            # 验证并格式化交易对
            if symbol:
                # 检查是否交易对格式正确
                # U本位合约的计价币必须是USDT/BUSD
                common_quote_assets = ['USDT', 'BUSD']
                common_base_assets = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LTC']
                has_quote_asset = False
                
                for quote in common_quote_assets:
                    if symbol.endswith(quote):
                        has_quote_asset = True
                        break
                
                if not has_quote_asset:
                    # 如果只提供了基础资产名称，自动添加USDT作为计价资产
                    if symbol.upper() in common_base_assets:
                        logger.info(f"自动为U本位合约 {symbol} 添加USDT计价币")
                        symbol = f"{symbol.upper()}USDT"
                    else:
                        # 不进行自动修正
                        logger.warning(f"U本位合约交易对 {symbol} 不符合标准格式，不进行自动修正")
            
            # 验证参数合法性
            if not quantity and not quoteOrderQty:
                return {'success': False, 'error': '必须提供交易数量(quantity)或交易金额(quoteOrderQty)参数中的至少一个'}
            
            # 获取U本位合约交易对精度规则
            # 由于无法通过普通的exchangeInfo获取PAPI的精度，这里使用一个硬编码的常见精度表
            # 一般来说，主要币种合约的数量精度为3位，价格精度在1-4位
            quantity_precision = 3  # 默认精度
            price_precision = 2     # 默认精度
            
            # 根据常见交易对调整精度
            if symbol.startswith('BTC'):
                quantity_precision = 3
                price_precision = 1
            elif symbol.startswith('ETH'):
                quantity_precision = 3
                price_precision = 2
            elif symbol.startswith('BNB'):
                quantity_precision = 2
                price_precision = 2
            elif symbol.startswith('DOGE'):
                quantity_precision = 0
                price_precision = 6
            
            logger.info(f"使用U本位合约交易对{symbol}的数量精度为{quantity_precision}位小数，价格精度为{price_precision}位小数")
            
            # 调整数量和价格精度
            if quantity is not None:
                original_quantity = quantity
                quantity = self._format_number_precision(quantity, quantity_precision)
                if original_quantity != quantity:
                    logger.info(f"调整数量精度: {original_quantity} -> {quantity}")
            
            if price is not None:
                original_price = price
                price = self._format_number_precision(price, price_precision)
                if original_price != price:
                    logger.info(f"调整价格精度: {original_price} -> {price}")
            
            if quoteOrderQty is not None:
                # 计价币种金额一般精度为2位
                original_quote_qty = quoteOrderQty
                quoteOrderQty = self._format_number_precision(quoteOrderQty, 2)
                if original_quote_qty != quoteOrderQty:
                    logger.info(f"调整金额精度: {original_quote_qty} -> {quoteOrderQty}")
            
            # 记录参数信息
            logger.debug(f"U本位合约下单参数: symbol={symbol}, side={side}, type={order_type}, quantity={quantity}, quoteOrderQty={quoteOrderQty}, price={price}, position_side={position_side}")
            
            # 发送请求到API端点 - 使用正确的统一账户U本位合约端点
            endpoint = "https://papi.binance.com/papi/v1/um/order"
            
            # 构建基本参数
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type
            }
            
            # 添加持仓方向参数 - 始终使用双向持仓模式
            if position_side:
                # 使用用户指定的持仓方向
                params['positionSide'] = position_side
                logger.info(f"使用指定的持仓方向: {position_side}")
            else:
                # 根据交易方向自动设置默认持仓方向
                params['positionSide'] = 'LONG' if side == 'BUY' else 'SHORT'
                logger.info(f"根据交易方向自动设置持仓方向: {params['positionSide']}")
            
            # 添加数量参数 - 优先使用quantity，其次使用quoteOrderQty
            if quantity is not None:
                # 确保quantity是字符串格式
                params['quantity'] = str(quantity)
                logger.debug(f"使用quantity参数: {params['quantity']}")
            elif quoteOrderQty is not None:
                # 确保quoteOrderQty是字符串格式
                params['quoteOrderQty'] = str(quoteOrderQty)
                logger.debug(f"使用quoteOrderQty参数: {params['quoteOrderQty']}")
            else:
                logger.error("下单错误: 必须提供quantity或quoteOrderQty参数")
                return {'success': False, 'error': '必须提供交易数量(quantity)或交易金额(quoteOrderQty)参数中的至少一个'}
            
            # LIMIT订单必须包含价格和有效期
            if order_type == 'LIMIT':
                if not price:
                    return {'success': False, 'error': 'LIMIT订单必须提供价格'}
                params['price'] = str(price)
                params['timeInForce'] = time_in_force or 'GTC'
            
            # 市价卖单SELL MARKET必须使用quantity参数，不能使用quoteOrderQty
            if order_type == 'MARKET' and side == 'SELL' and 'quantity' not in params and 'quoteOrderQty' in params:
                return {'success': False, 'error': '市价卖单(SELL MARKET)必须使用quantity参数指定卖出数量，不能使用quoteOrderQty参数'}
            
            # 添加其他可选参数
            for key, value in kwargs.items():
                if value is not None:
                    params[key] = value
                    
            # 打印关键参数摘要
            param_info = {
                '交易对': symbol,
                '方向': side,
                '类型': order_type
            }
            
            if 'quantity' in params:
                param_info['数量'] = params['quantity']
            if 'quoteOrderQty' in params:
                param_info['金额'] = params['quoteOrderQty']
            if 'price' in params:
                param_info['价格'] = params['price']
            if 'positionSide' in params:
                param_info['持仓方向'] = params['positionSide']
                
            logger.info(f"统一账户合约下单: {json.dumps(param_info, ensure_ascii=False)}")
            
            # 发送请求并处理响应
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            if response.get('success', False):
                # 获取订单ID和状态等关键信息
                order_id = response.get('data', {}).get('orderId')
                status = response.get('data', {}).get('status', 'UNKNOWN')
                logger.info(f"下单成功: {symbol}, {side}, {order_type}, 订单ID: {order_id}, 状态: {status}")
                return response
            else:
                error_msg = response.get('error', '未知错误')
                logger.error(f"下单失败: {error_msg}")
                
                # 如果错误与quantity相关，给出更具体的建议
                if 'quantity' in error_msg.lower():
                    logger.error(f"数量参数错误: 请检查是否达到币安最小交易量要求，当前quantity值: {params.get('quantity', 'N/A')}")
                elif 'Portfolio Margin' in error_msg:
                    logger.error("统一账户错误: 请确保使用正确的子账号API密钥，并确保账户为统一账户模式")
                elif 'position side' in error_msg.lower():
                    if 'positionSide' in params:
                        logger.error(f"持仓方向错误: 当前使用的positionSide={params['positionSide']}，可能与账户的持仓模式不匹配")
                    else:
                        logger.error("持仓方向错误: 缺少positionSide参数，但账户可能设置为双向持仓模式")
                
                return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"下单异常: {error_msg}")
            return {
                'success': False,
                'error': f"下单异常: {error_msg}"
            }
    
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
        
    def sub_account_transfer(self, from_email, to_email, asset, amount, transfer_type=None):
        """
        在主账号和子账号之间或子账号之间转账
        
        参数:
        - from_email: 源账号邮箱 (为空字符串时表示主账号)
        - to_email: 目标账号邮箱 (为空字符串时表示主账号)
        - asset: 转账资产名称
        - amount: 转账金额
        - transfer_type: 转账类型 ('MASTER_TO_SUB'/'SUB_TO_MASTER'/'SUB_TO_SUB')
        
        返回:
        - 成功时返回{'success': True, 'data': {...}}
        - 失败时返回{'success': False, 'error': '错误信息'}
        """
        try:
            logger.info(f"开始执行转账: 从 {from_email or '主账号'} 到 {to_email or '主账号'}, 资产: {asset}, 金额: {amount}")
            
            # 确保金额是字符串格式
            if not isinstance(amount, str):
                amount = str(amount)
            
            # 根据from_email和to_email确定转账类型
            if not transfer_type:
                if not from_email and to_email:
                    transfer_type = 'MASTER_TO_SUB'
                elif from_email and not to_email:
                    transfer_type = 'SUB_TO_MASTER'
                elif from_email and to_email:
                    transfer_type = 'SUB_TO_SUB'
                else:
                    return {
                        'success': False,
                        'error': '无效的转账请求：源账号和目标账号不能同时为空'
                    }
            
            logger.info(f"转账类型: {transfer_type}")
            
            # 根据转账类型选择不同的API端点和参数
            if transfer_type == 'MASTER_TO_SUB':
                # 使用universalTransfer API
                endpoint = "/sapi/v1/sub-account/universalTransfer"
                params = {
                    'toEmail': to_email,
                    'fromAccountType': 'SPOT',
                    'toAccountType': 'SPOT',
                    'asset': asset,
                    'amount': amount
                }
            elif transfer_type == 'SUB_TO_SUB':
                # 使用universalTransfer API
                endpoint = "/sapi/v1/sub-account/universalTransfer"
                params = {
                    'fromEmail': from_email,
                    'toEmail': to_email,
                    'fromAccountType': 'SPOT',
                    'toAccountType': 'SPOT',
                    'asset': asset,
                    'amount': amount
                }
            elif transfer_type == 'SUB_TO_MASTER':
                # 这种情况下应该使用子账号的API密钥，而不是主账号的
                # 子账号到主账号转账应该使用子账号API发起
                return {
                    'success': False,
                    'error': '子账号向主账号转账需要使用子账号API密钥，请使用子账号API客户端'
                }
            else:
                return {
                    'success': False,
                    'error': f'不支持的转账类型: {transfer_type}'
                }
            
            # 发送请求
            response = self._send_request('POST', endpoint, signed=True, params=params)
            
            if response.get('success'):
                logger.info(f"转账成功: 从 {from_email or '主账号'} 到 {to_email or '主账号'}, 资产: {asset}, 金额: {amount}")
                return response
            else:
                error_msg = response.get('error', '未知错误')
                logger.error(f"转账失败: {error_msg}")
                return response
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"转账异常: {error_msg}")
            return {
                'success': False,
                'error': f"转账异常: {error_msg}"
            }

    def get_portfolio_margin_positions_um(self, symbol=None):
        """
        获取统一账户下U本位合约持仓信息
        
        参数:
        - symbol: 交易对名称（可选）
        
        返回:
        - dict: 包含持仓信息的字典
        """
        try:
            # 记录API使用情况
            if hasattr(self, 'is_subaccount') and self.is_subaccount:
                logger.info(f"使用子账号 {self.subaccount_email} 的API密钥获取统一账户合约持仓")
            else:
                logger.warning("注意: 此次获取统一账户合约持仓未使用子账号API，可能会导致操作失败")
            
            # 构建参数
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            # 使用统一账户papi端点
            endpoint = "https://papi.binance.com/papi/v1/um/account"
            
            # 发送请求并获取响应
            response = self._send_request('GET', endpoint, signed=True, params=params)
            
            if response.get('success'):
                account_data = response.get('data', {})
                positions = account_data.get('positions', [])
                
                # 过滤零仓位
                non_zero_positions = []
                for position in positions:
                    position_amt = float(position.get('positionAmt', '0'))
                    # 只保留有仓位的交易对
                    if position_amt != 0:
                        non_zero_positions.append(position)
                
                logger.info(f"成功获取统一账户合约持仓信息，共 {len(non_zero_positions)} 个持仓")
                return {
                    'success': True,
                    'data': non_zero_positions
                }
            else:
                logger.error(f"获取统一账户合约持仓信息失败: {response.get('error')}")
                return response
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取统一账户合约持仓信息异常: {error_msg}")
            return {
                'success': False,
                'error': f"获取统一账户合约持仓信息异常: {error_msg}"
            }

    def _print_error_response(self, result, request_params=None):
        """
        打印API错误响应的详细信息
        
        参数:
        - result: API响应结果
        - request_params: 请求参数（可选）
        """
        if not isinstance(result, dict):
            log_error(f"非字典格式的错误响应: {result}")
            return
            
        # 获取错误代码和消息
        error_code = result.get('code', 'UNKNOWN')
        error_msg = result.get('msg', result.get('message', '未知错误'))
        
        # 打印错误信息框
        log_error("==================== API错误详情 ====================")
        log_error(f"错误代码: {error_code}")
        log_error(f"错误消息: {error_msg}")
        
        # 打印其他响应信息
        for key, value in result.items():
            if key not in ['code', 'msg', 'message']:
                log_error(f"{key}: {value}")
                
        # 如果提供了请求参数，也打印出来
        if request_params:
            log_error("----- 请求参数 -----")
            if isinstance(request_params, dict):
                for key, value in request_params.items():
                    if key != 'signature':  # 不打印签名
                        log_error(f"{key}: {value}")
            else:
                log_error(f"{request_params}")
        
        # 根据错误类型提供具体建议
        if 'quantity' in error_msg.lower():
            log_error("----- 可能的解决方案 -----")
            log_error("1. 确保quantity参数已正确传递并且是字符串格式")
            log_error("2. 检查quantity值是否符合该交易对的最小交易量要求")
            log_error("3. 尝试增加交易数量，币安对一些交易对有最小交易量限制")
        elif 'price' in error_msg.lower():
            log_error("----- 可能的解决方案 -----")
            log_error("1. 检查价格是否符合交易对的价格精度要求")
            log_error("2. 确认价格是否在当前交易区间内")
        
        log_error("======================================================")

    def _format_number_precision(self, number, precision):
        """格式化数字到指定精度"""
        try:
            precision = int(precision)
            format_string = f"{{:.{precision}f}}"
            formatted = format_string.format(float(number))
            # 去除尾部的0
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
            return formatted
        except Exception as e:
            log_error(f"格式化数字精度异常: {str(e)}")
            return str(number)
    
    def get_unified_account_trades(self, symbol=None, start_time=None, end_time=None, from_id=None, limit=None, recvWindow=None, **kwargs):
        """
        获取统一账户交易历史
        
        参数:
        - symbol: 交易对
        - start_time: 开始时间(毫秒时间戳)
        - end_time: 结束时间(毫秒时间戳)
        - from_id: 从哪个ID开始获取
        - limit: 返回的记录数量
        - recvWindow: 接收窗口时间(毫秒)
        - **kwargs: 其他参数，兼容驼峰命名的参数
        
        返回:
        - 交易历史记录列表
        """
        try:
            # 同步服务器时间
            self.sync_time()
            
            # 构建请求参数
            params = {}
            
            # 参数兼容处理，支持蛇形命名和驼峰命名
            if symbol or kwargs.get('symbol'):
                params['symbol'] = symbol or kwargs.get('symbol')
                
            if start_time or kwargs.get('startTime'):
                params['startTime'] = int(start_time or kwargs.get('startTime'))
                
            if end_time or kwargs.get('endTime'):
                params['endTime'] = int(end_time or kwargs.get('endTime'))
            else:
                # 如果没有提供end_time，使用当前时间
                params['endTime'] = int(time.time() * 1000)
                
            if from_id or kwargs.get('fromId'):
                params['fromId'] = int(from_id or kwargs.get('fromId'))
                
            if limit or kwargs.get('limit'):
                params['limit'] = int(limit or kwargs.get('limit'))
                
            # 设置接收窗口时间
            if recvWindow or kwargs.get('recvWindow'):
                params['recvWindow'] = recvWindow or kwargs.get('recvWindow')
            else:
                params['recvWindow'] = 60000  # 默认值
            
            # 调用统一账户API - 使用papi前缀的正确端点，去掉多余的斜杠
            endpoint = 'papi/v1/margin/myTrades'
            logger.info(f"请求统一账户交易历史: {endpoint}, 参数: {params}")
            
            # 发送请求
            response = self._send_request('GET', endpoint, signed=True, params=params)
            
            # 处理响应
            if isinstance(response, list):
                # 直接返回列表数据
                return {
                    'success': True,
                    'data': response
                }
            elif response.get('success'):
                return response
            else:
                error_msg = response.get('error', '获取统一账户交易历史失败') if isinstance(response, dict) else str(response)
                logger.error(f"获取统一账户交易历史失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            logger.exception(f"获取统一账户交易历史异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取统一账户交易历史异常: {str(e)}"
            }
    
    def get_um_trades(self, symbol=None, start_time=None, end_time=None, from_id=None, limit=None, recvWindow=None, **kwargs):
        """
        获取统一账户UM合约交易历史
        
        参数:
        - symbol: 交易对
        - start_time: 开始时间(毫秒时间戳)
        - end_time: 结束时间(毫秒时间戳)
        - from_id: 从哪个ID开始获取
        - limit: 返回的记录数量
        - recvWindow: 接收窗口时间(毫秒)
        - **kwargs: 其他参数，兼容驼峰命名的参数
        
        返回:
        - 交易历史记录列表
        """
        try:
            # 同步服务器时间
            self.sync_time()
            
            # 构建请求参数
            params = {}
            
            # 参数兼容处理，支持蛇形命名和驼峰命名
            if symbol or kwargs.get('symbol'):
                params['symbol'] = symbol or kwargs.get('symbol')
                
            if start_time or kwargs.get('startTime'):
                params['startTime'] = int(start_time or kwargs.get('startTime'))
                
            if end_time or kwargs.get('endTime'):
                params['endTime'] = int(end_time or kwargs.get('endTime'))
            else:
                # 如果没有提供end_time，使用当前时间
                params['endTime'] = int(time.time() * 1000)
                
            if from_id or kwargs.get('fromId'):
                params['fromId'] = int(from_id or kwargs.get('fromId'))
                
            if limit or kwargs.get('limit'):
                params['limit'] = int(limit or kwargs.get('limit'))
                
            # 设置接收窗口时间
            if recvWindow or kwargs.get('recvWindow'):
                params['recvWindow'] = recvWindow or kwargs.get('recvWindow')
            else:
                params['recvWindow'] = 60000  # 默认值
            
            # 调用统一账户API - 使用papi前缀的正确端点，去掉多余的斜杠
            endpoint = 'papi/v1/um/userTrades'
            logger.info(f"请求统一账户UM合约交易历史: {endpoint}, 参数: {params}")
            
            # 发送请求
            response = self._send_request('GET', endpoint, signed=True, params=params)
            
            # 处理响应
            if isinstance(response, list):
                # 直接返回列表数据
                return {
                    'success': True,
                    'data': response
                }
            elif response.get('success'):
                return response
            else:
                error_msg = response.get('error', '获取统一账户UM合约交易历史失败') if isinstance(response, dict) else str(response)
                logger.error(f"获取统一账户UM合约交易历史失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            logger.exception(f"获取统一账户UM合约交易历史异常: {str(e)}")
            return {
                'success': False,
                'error': f"获取统一账户UM合约交易历史异常: {str(e)}"
            }

    def get_exchange_info(self, symbol=None):
        """
        获取交易规则和交易对信息
        
        参数:
        - symbol: 交易对(可选)
        
        返回:
        - 交易所规则和交易对信息
        """
        try:
            endpoint = "/api/v3/exchangeInfo"
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            response = self._send_request('GET', endpoint, params=params)
            return response
        except Exception as e:
            logger.error(f"获取交易对信息异常: {str(e)}")
            return {'success': False, 'error': f"获取交易对信息异常: {str(e)}"}
            
    def _get_symbol_filters(self, symbol):
        """
        获取交易对的过滤器规则（精度、最小数量等）
        
        参数:
        - symbol: 交易对名称
        
        返回:
        - dict: 过滤器规则
        """
        try:
            exchange_info = self.get_exchange_info(symbol)
            if not exchange_info.get('success', False):
                logger.warning(f"获取交易对{symbol}信息失败: {exchange_info.get('error')}")
                return None
                
            symbols_info = exchange_info.get('data', {}).get('symbols', [])
            
            for sym_info in symbols_info:
                if sym_info.get('symbol') == symbol:
                    filters = {}
                    for filter_item in sym_info.get('filters', []):
                        filter_type = filter_item.get('filterType')
                        filters[filter_type] = filter_item
                    
                    logger.info(f"获取到交易对{symbol}的过滤器规则: {json.dumps(filters, indent=2)}")
                    return filters
                    
            logger.warning(f"未找到交易对{symbol}的信息")
            return None
        except Exception as e:
            logger.error(f"获取交易对过滤器规则异常: {str(e)}")
            return None

    def cm_new_order(self, symbol, side, type, quantity, price=None, timeInForce=None, **kwargs):
        """
        统一账户API下的币本位合约下单
        
        参数:
        - symbol: 交易对
        - side: 订单方向，BUY（买入）或SELL（卖出）
        - type: 订单类型，如LIMIT（限价单）、MARKET（市价单）等
        - quantity: 订单数量
        - price: 订单价格（限价单必需）
        - timeInForce: 订单有效方式，GTC（成交为止）、IOC（无法立即成交的部分就撤销）、FOK（无法全部立即成交就撤销）
        - **kwargs: 其他可选参数
        
        返回:
        - dict: 订单信息
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'quantity': quantity
        }
        
        # 限价单必需传入价格
        if type == 'LIMIT':
            if price is None:
                raise ValueError("限价单必须指定价格")
            params['price'] = price
            
            # 限价单必需传入timeInForce
            if timeInForce is None:
                params['timeInForce'] = 'GTC'  # 默认为GTC
            else:
                params['timeInForce'] = timeInForce
        
        # 添加其他可选参数
        params.update(kwargs)
        
        # 使用统一账户API下单
        try:
            endpoint = '/papi/v1/cm/order'
            result = self._send_request('POST', endpoint, payload=params, signed=True)
            logger.info(f"币本位合约下单结果: {result}")
            return result
        except Exception as e:
            logger.error(f"币本位合约下单失败: {str(e)}")
            raise e

    def set_coin_futures_leverage(self, symbol, leverage):
        """
        设置币本位合约杠杆倍数
        
        参数:
        - symbol: 交易对，例如 BTCUSD
        - leverage: 杠杆倍数，范围1-125
        
        返回:
        - dict: 设置结果
        """
        try:
            endpoint = '/papi/v1/cm/leverage'
            params = {
                'symbol': symbol,
                'leverage': leverage
            }
            
            result = self._send_request('POST', endpoint, params=params, signed=True)
            logger.info(f"设置币本位合约杠杆倍数结果: {result}")
            return result
        except Exception as e:
            logger.error(f"设置币本位合约杠杆倍数失败: {str(e)}")
            raise e

    def set_um_leverage(self, symbol, leverage):
        """
        设置U本位合约杠杆倍数
        
        参数:
        - symbol: 交易对，例如 BTCUSDT
        - leverage: 杠杆倍数，范围1-125
        
        返回:
        - dict: 设置结果
        """
        try:
            endpoint = '/papi/v1/um/leverage'
            params = {
                'symbol': symbol,
                'leverage': leverage
            }
            
            result = self._send_request('POST', endpoint, params=params, signed=True)
            logger.info(f"设置U本位合约杠杆倍数结果: {result}")
            return result
        except Exception as e:
            logger.error(f"设置U本位合约杠杆倍数失败: {str(e)}")
            raise e

    def auto_collection(self, recvWindow=5000):
        """
        统一账户资金归集
        """
        try:
            params = {
                'recvWindow': recvWindow,
                'timestamp': self.get_timestamp()
            }
            
            # 调用API
            return self._send_request('POST', 'papi/v1/auto-collection', params=params, signed=True)
        
        except Exception as e:
            log_error(f"资金归集异常: {str(e)}")
            return {
                'success': False,
                'error': f"资金归集异常: {str(e)}"
            }
            
    def _request_margin_api(self, method, endpoint, signed=False, data=None):
        """
        调用币安保证金/统一账户API
        
        参数:
        - method: 请求方法 (GET, POST, DELETE等)
        - endpoint: API端点，如 'papi/v1/repay-futures-switch'
        - signed: 是否需要签名
        - data: 请求参数
        
        返回:
        - API响应数据
        """
        try:
            log_info(f"调用保证金API: {method} {endpoint}, 签名: {signed}")
            
            # 构建完整URL
            url = endpoint
            if not url.startswith('http'):
                if url.startswith('papi/'):
                    # 统一账户API
                    url = f"{self.papi_url}/{url.replace('papi/', '')}"
                elif url.startswith('sapi/'):
                    # SAPI接口
                    url = f"{self.sapi_url}/{url.replace('sapi/', '')}"
                else:
                    url = f"{self.sapi_url}/{url}"  # 默认使用SAPI基础URL
            
            # 发送请求并获取响应
            response = self._send_request(method, url, payload=data, signed=signed)
            
            # 处理响应
            if not response.get('success'):
                log_error(f"保证金API请求失败: {response.get('error')}")
                return response.get('data', {})
                
            return response.get('data', {})
            
        except Exception as e:
            log_error(f"保证金API请求异常: {str(e)}")
            raise Exception(f"保证金API请求异常: {str(e)}")
            
# 辅助函数，从email获取币安客户端实例
def get_client_by_email(email, user_id=None):
    """
    通过子账号邮箱获取币安客户端
    
    参数:
    - email: 子账号邮箱
    - user_id: 用户ID (可选，但不使用此参数进行查询，保留参数是为了兼容性)
    
    返回:
    - BinanceClient 实例或 None
    """
    if not email:
        log_warning("未提供子账号邮箱，无法获取API客户端")
        return None
    
    # 使用子账号邮箱查询API设置，不使用user_id字段
    api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
    if api_setting and api_setting.api_key and api_setting.api_secret:
        # 清理API密钥，移除可能的空格、换行符和其他不可见字符
        api_key = api_setting.api_key.strip()
        api_secret = api_setting.api_secret.strip()
        
        # 验证API密钥格式
        if not api_key or len(api_key) < 10:
            log_error(f"子账号 {email} 的API密钥格式无效（长度不足）")
            return None
            
        if not api_secret or len(api_secret) < 10:
            log_error(f"子账号 {email} 的API密钥Secret格式无效（长度不足）")
            return None
            
        # 验证仅包含字母和数字
        import re
        if not re.match(r'^[A-Za-z0-9]+$', api_key):
            log_error(f"子账号 {email} 的API密钥格式无效（包含非法字符）")
            return None
            
        if not re.match(r'^[A-Za-z0-9]+$', api_secret):
            log_error(f"子账号 {email} 的API密钥Secret格式无效（包含非法字符）")
            return None
            
        log_info(f"找到子账号 {email} 的API设置，使用子账号自己的API密钥初始化客户端")
        # 返回初始化的客户端
        client = BinanceClient(api_key, api_secret)
        client.is_subaccount = True  # 标记这是子账号API客户端
        client.subaccount_email = email  # 记录子账号邮箱
        return client
    else:
        log_error(f"未找到子账号 {email} 的API设置或API设置不完整，无法使用子账号API")
        return None

def get_binance_client(user_id=None):
    """
    获取币安客户端
    
    参数:
    - user_id: 用户ID (可选)
    
    返回:
    - BinanceClient 实例或 None
    """
    try:
        # 如果提供了用户ID，则查询该用户的API密钥
        if user_id:
            log_info(f"尝试从数据库获取用户 {user_id} 的API密钥")
            # 查询数据库
            api_key_record = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
            
            if api_key_record:
                log_info(f"找到用户 {user_id} 的API密钥")
                return BinanceClient(api_key_record.api_key, api_key_record.api_secret)
            else:
                log_warning(f"未找到用户 {user_id} 的API密钥")
        
        # 使用环境变量API密钥
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if api_key and api_secret:
            log_info("使用环境变量中的API密钥")
            return BinanceClient(api_key, api_secret)
        else:
            log_warning("环境变量中未设置API密钥")
            
        # 尝试从配置中获取
        try:
            api_key = current_app.config.get('BINANCE_API_KEY')
            api_secret = current_app.config.get('BINANCE_API_SECRET')
            
            if api_key and api_secret:
                log_info("使用配置中的API密钥")
                return BinanceClient(api_key, api_secret)
            else:
                log_warning("配置中未设置API密钥")
        except Exception as e:
            log_warning(f"尝试从应用配置获取API密钥时出错: {str(e)}")
        
        # 如果都没有找到，返回None
        log_warning("未找到有效的API密钥")
        return None
    except Exception as e:
        log_exception(f"获取币安客户端异常: {str(e)}")
        return None

def get_main_account_api_credentials(user_id=None):
    """
    获取主账号API凭证
    
    参数:
    - user_id: 用户ID (可选)
    
    返回:
    - (api_key, api_secret) 元组
    """
    try:
        # 如果提供了用户ID，则查询该用户的API密钥
        if user_id:
            # 查询数据库
            api_key_record = APIKey.query.filter_by(user_id=user_id, is_active=True).first()
            
            if api_key_record:
                log_info(f"找到用户 {user_id} 的API密钥")
                return api_key_record.api_key, api_key_record.api_secret
            else:
                log_warning(f"未找到用户 {user_id} 的API密钥")
        
        # 使用环境变量API密钥
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if api_key and api_secret:
            log_info("使用环境变量中的API密钥")
            return api_key, api_secret
        else:
            log_warning("环境变量中未设置API密钥")
            
        # 尝试从配置中获取
        try:
            api_key = current_app.config.get('BINANCE_API_KEY')
            api_secret = current_app.config.get('BINANCE_API_SECRET')
            
            if api_key and api_secret:
                log_info("使用配置中的API密钥")
                return api_key, api_secret
        except Exception as e:
            log_warning(f"尝试从应用配置获取API密钥时出错: {str(e)}")
        
        # 如果都没有找到，返回空字符串
        log_warning("未找到有效的API密钥")
        return '', ''
    except Exception as e:
        log_exception(f"获取主账号API凭证异常: {str(e)}")
        return '', '' 

def get_sub_account_api_credentials(email):
    """
    通过子账号邮箱获取其API凭证
    
    参数:
    - email: 子账号邮箱地址
    
    返回:
    - (api_key, api_secret) 元组
    """
    try:
        if not email:
            log_warning("未提供子账号邮箱，无法获取API凭证")
            return None, None
        
        # 查询子账号API设置
        api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
        
        if api_setting and api_setting.api_key and api_setting.api_secret:
            log_info(f"找到子账号 {email} 的API凭证")
            return api_setting.api_key, api_setting.api_secret
        else:
            log_warning(f"未找到子账号 {email} 的API凭证")
            return None, None
            
    except Exception as e:
        log_exception(f"获取子账号 {email} API凭证异常: {str(e)}")
        return None, None 
    