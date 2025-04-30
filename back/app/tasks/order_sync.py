import logging
import time
from datetime import datetime, timedelta
import threading
import json
import websocket
from flask import current_app
from app.models import db, User, TradeHistory, OrderHistory
from app.models.account import SubAccountAPISettings
from app.models.trading_pair import TradingPair
from app.services.binance_client import get_client_by_email
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.subaccounts import get_main_account_api_credentials
from app.services.binance_client import BinanceClient
from app.tasks.websocket_client import create_websocket_client

# 初始化日志
logger = logging.getLogger('order_sync_tasks')

# 全局调度器对象
scheduler = None
lock = threading.Lock()

# WebSocket连接字典，每个子账号一个连接
ws_connections = {}

def init_scheduler(app):
    """初始化订单同步调度器"""
    global scheduler
    
    if scheduler:
        return scheduler
    
    logger.info("初始化订单同步调度器")
    scheduler = BackgroundScheduler()
    
    # 添加定时同步任务，每小时执行一次历史订单同步（降低频率，仅作为备份手段）
    scheduler.add_job(
        sync_all_orders,
        'interval',
        hours=1,
        args=[app],
        id='sync_all_orders'
    )
    
    # 添加初始化WebSocket连接的任务
    scheduler.add_job(
        init_websocket_connections,
        'date',
        run_date=datetime.now() + timedelta(seconds=5),  # 5秒后执行
        args=[app],
        id='init_websockets'
    )
    
    # 添加检查WebSocket的定时任务，每5分钟检查一次
    scheduler.add_job(
        check_websocket_connections,
        'interval',
        minutes=5,
        args=[app],
        id='check_websockets'
    )
    
    # 启动调度器
    scheduler.start()
    logger.info("订单同步调度器已启动，使用WebSocket API直接查询订单数据")
    
    return scheduler

def init_websocket_connections(app):
    """初始化所有子账号的WebSocket连接"""
    with app.app_context():
        try:
            # 查询所有有效的子账号API设置
            api_settings = SubAccountAPISettings.query.all()
            
            if not api_settings:
                logger.warning("没有找到有效的子账号API设置，WebSocket初始化跳过")
                return
                
            logger.info(f"开始为 {len(api_settings)} 个子账号初始化WebSocket连接")
            
            # 为每个子账号建立WebSocket连接
            for api_setting in api_settings:
                try:
                    email = api_setting.email
                    # 建立WebSocket连接
                    if connect_user_websocket(email, app):
                        logger.info(f"子账号 {email} 的WebSocket连接已初始化")
                    else:
                        logger.warning(f"子账号 {email} 的WebSocket连接初始化失败")
                        
                    # 避免同时建立太多连接
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"为子账号 {email} 初始化WebSocket连接时出错: {str(e)}")
                    
            logger.info("所有子账号的WebSocket连接初始化完成")
            
        except Exception as e:
            logger.error(f"初始化WebSocket连接时出错: {str(e)}")
            
def check_websocket_connections(app):
    """检查并重连断开的WebSocket连接"""
    with app.app_context():
        try:
            # 查询所有有效的子账号API设置
            api_settings = SubAccountAPISettings.query.all()
            
            if not api_settings:
                return
                
            logger.debug(f"开始检查 {len(api_settings)} 个子账号的WebSocket连接状态")
            
            # 检查每个子账号的WebSocket连接
            for api_setting in api_settings:
                try:
                    email = api_setting.email
                    
                    # 检查连接是否存在且有效
                    if email not in ws_connections or not ws_connections[email]:
                        logger.info(f"子账号 {email} 的WebSocket连接不存在，尝试重连")
                        connect_user_websocket(email, app)
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"检查子账号 {email} 的WebSocket连接时出错: {str(e)}")
                    
            logger.debug("所有子账号的WebSocket连接检查完成")
            
        except Exception as e:
            logger.error(f"检查WebSocket连接时出错: {str(e)}")

def sync_all_orders(app):
    """同步所有用户的交易订单，使用WebSocket API"""
    with lock:
        with app.app_context():
            try:
                logger.info("开始同步所有子账号的交易订单（WebSocket API）")
                
                # 直接查询所有有效的子账号API设置
                api_settings = SubAccountAPISettings.query.all()
                
                if not api_settings:
                    logger.warning("没有找到有效的子账号API设置，订单同步跳过")
                    return
                
                logger.info(f"找到 {len(api_settings)} 个子账号API设置")
                
                # 预先查询所有交易对
                trading_pairs = TradingPair.query.all()
                if not trading_pairs:
                    logger.warning("没有找到任何交易对信息，无法进行订单同步")
                    return
                    
                symbol_list = [pair.symbol for pair in trading_pairs]
                logger.debug(f"将使用以下交易对进行查询: {symbol_list[:5]}... (共{len(symbol_list)}个)")
                
                for api_setting in api_settings:
                    try:
                        email = api_setting.email
                        logger.debug(f"开始同步子账号 {email} 的交易订单（WebSocket API）")
                        
                        # 创建WebSocket客户端
                        ws_client = create_websocket_client(email)
                        if not ws_client:
                            logger.error(f"无法创建WebSocket客户端，子账号 {email} 的API密钥可能有问题")
                            continue
                            
                        # 获取活跃交易对
                        active_symbols = get_active_trading_pairs()[:10]  # 限制为前10个活跃交易对
                        
                        total_count = 0
                        for symbol in active_symbols:
                            try:
                                # 查询挂单
                                result = ws_client.query_open_orders(symbol)
                                
                                if result.get('success') and 'data' in result:
                                    orders = result.get('data', [])
                                    count = update_orders_in_db(email, orders)
                                    total_count += count
                                    logger.debug(f"WebSocket API查询：更新了 {email} 的 {symbol} {count}个订单")
                                else:
                                    logger.debug(f"WebSocket API查询：{email} 的 {symbol} 挂单查询失败 - {result.get('error', 'Unknown error')}")
                                    
                                # 限制请求频率
                                time.sleep(0.5)
                            except Exception as e:
                                logger.error(f"WebSocket API查询 {email} 的 {symbol} 挂单时出错: {str(e)}")
                                
                        # 关闭WebSocket连接
                        ws_client.close()
                        
                        if total_count > 0:
                            logger.info(f"子账号 {email} 总共更新了 {total_count} 个交易订单记录（WebSocket API）")
                        else:
                            logger.debug(f"子账号 {email} 没有新增交易订单记录")
                            
                        # 避免过于频繁请求API
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"同步子账号 {email} 的交易订单时发生错误: {str(e)}", exc_info=True)
                
                logger.info("所有子账号的交易订单同步完成（WebSocket API）")
                
            except Exception as e:
                logger.error(f"同步交易订单时发生错误: {str(e)}", exc_info=True)

def sync_user_recent_orders(email, start_time=None, end_time=None, symbol=None):
    """同步指定用户的最近订单，使用WebSocket API
    
    Args:
        email: 用户邮箱
        start_time: 开始时间戳(毫秒)
        end_time: 结束时间戳(毫秒)
        symbol: 交易对，默认为None
        
    Returns:
        int: 同步的订单数量
    """
    try:
        # 创建WebSocket客户端
        ws_client = create_websocket_client(email)
        
        if not ws_client:
            logger.error(f"无法创建WebSocket客户端，子账号 {email} 的API密钥可能有问题")
            return 0
            
        # 获取活跃交易对列表
        if symbol:
            trading_symbols = [symbol]
        else:
            # 只使用活跃交易对，减少请求数量
            trading_symbols = get_active_trading_pairs()[:5]  # 限制为前5个活跃交易对
            
        if not trading_symbols:
            logger.warning(f"没有找到可用的交易对信息，无法获取订单")
            return 0
            
        logger.info(f"将使用WebSocket API同步 {email} 的 {len(trading_symbols)} 个交易对的最近订单")
        total_count = 0
        
        # 对每个交易对分别查询订单
        for symbol in trading_symbols:
            try:
                # 查询当前挂单
                open_orders_result = ws_client.query_open_orders(symbol)
                if open_orders_result.get('success') and 'data' in open_orders_result:
                    orders = open_orders_result.get('data', [])
                    count = update_orders_in_db(email, orders)
                    total_count += count
                    logger.debug(f"通过WebSocket API更新 {email} 的 {symbol} 最近订单：{count}个")
                else:
                    logger.debug(f"通过WebSocket API查询 {email} 的 {symbol} 最近订单失败：{open_orders_result.get('error', 'Unknown error')}")
                    
                # 限制请求频率
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"同步用户 {email} 的 {symbol} 最近订单时发生错误: {str(e)}")
                continue
        
        # 关闭WebSocket连接
        ws_client.close()
        
        return total_count
        
    except Exception as e:
        logger.error(f"同步用户 {email} 的最近订单时发生错误: {str(e)}")
        return 0

def get_active_trading_pairs():
    """获取活跃交易对，用于优先同步
    
    Returns:
        list: 活跃交易对列表
    """
    try:
        # 首先获取所有交易对
        trading_pairs = TradingPair.query.all()
        if not trading_pairs:
            logger.warning("没有找到任何交易对信息")
            return []
            
        # 按照优先级过滤和排序
        
        # 1. 优先获取标记为"收藏"的交易对
        favorite_pairs = [pair for pair in trading_pairs if pair.is_favorite]
        if favorite_pairs:
            logger.info(f"找到{len(favorite_pairs)}个收藏交易对")
            return [pair.symbol for pair in favorite_pairs]
            
        # 2. 如果没有收藏交易对，则使用常见主流交易对
        common_pairs = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
            "DOGEUSDT", "XRPUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
            "AVAXUSDT", "LINKUSDT", "UNIUSDT", "ATOMUSDT", "SHIBUSDT"
        ]
        
        # 过滤出存在于数据库中的常见交易对
        active_pairs = []
        for symbol in common_pairs:
            for pair in trading_pairs:
                if pair.symbol == symbol:
                    active_pairs.append(symbol)
                    break
                    
        if active_pairs:
            logger.info(f"使用{len(active_pairs)}个常见主流交易对")
            return active_pairs
            
        # 3. 如果以上都没有，则返回所有交易对（限制数量）
        all_symbols = [pair.symbol for pair in trading_pairs]
        limited_symbols = all_symbols[:20]  # 限制为前20个
        
        logger.info(f"使用前{len(limited_symbols)}个交易对（共{len(all_symbols)}个）")
        return limited_symbols
        
    except Exception as e:
        logger.error(f"获取活跃交易对时出错: {str(e)}")
        return []

def sync_user_orders(email, start_time=None, end_time=None, symbol=None):
    """同步指定用户的交易订单，使用WebSocket API
    
    Args:
        email: 用户邮箱
        start_time: 开始时间戳(毫秒)，默认为None
        end_time: 结束时间戳(毫秒)，默认为None
        symbol: 交易对，默认为None
        
    Returns:
        int: 同步的订单数量
    """
    try:
        # 创建WebSocket客户端
        ws_client = create_websocket_client(email)
        
        if not ws_client:
            logger.error(f"无法创建WebSocket客户端，子账号 {email} 的API密钥可能有问题")
            return 0
            
        # 如果指定了单个交易对，则只处理该交易对
        if symbol:
            symbols = [symbol]
        else:
            # 获取活跃交易对并限制数量
            symbols = get_active_trading_pairs()[:10]  # 限制为前10个活跃交易对
            
        if not symbols:
            logger.warning(f"没有找到可用的交易对信息，无法获取交易记录")
            return 0
            
        logger.info(f"将使用WebSocket API同步 {email} 的 {len(symbols)} 个交易对的订单")
        total_count = 0
        
        # 对每个交易对分别获取订单
        for symbol in symbols:
            try:
                # 查询当前挂单
                open_orders_result = ws_client.query_open_orders(symbol)
                if open_orders_result.get('success') and 'data' in open_orders_result:
                    orders = open_orders_result.get('data', [])
                    count = update_orders_in_db(email, orders)
                    total_count += count
                    logger.info(f"通过WebSocket API更新 {email} 的 {symbol} 订单：{count}个")
                else:
                    logger.warning(f"通过WebSocket API查询 {email} 的 {symbol} 挂单失败：{open_orders_result.get('error', 'Unknown error')}")
                    
                # 限制请求频率
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"同步用户 {email} 的 {symbol} 订单时发生错误: {str(e)}")
                continue
        
        # 关闭WebSocket连接
        ws_client.close()
        
        return total_count
        
    except Exception as e:
        logger.error(f"同步用户 {email} 的交易订单时发生错误: {str(e)}", exc_info=True)
        return 0

def get_missing_orders(email, symbol=None, days=30):
    """检查并获取缺失的订单，使用WebSocket API
    
    Args:
        email: 用户邮箱
        symbol: 交易对，默认为None
        days: 要检查的天数，默认为30天
        
    Returns:
        int: 同步的订单数量
    """
    try:
        logger.info(f"检查用户 {email} 最近 {days} 天的缺失订单（WebSocket API）")
        
        # 创建WebSocket客户端
        ws_client = create_websocket_client(email)
        if not ws_client:
            logger.error(f"无法创建WebSocket客户端，子账号 {email} 的API密钥可能有问题")
            return 0
            
        # 如果指定了单个交易对，则只处理该交易对
        if symbol:
            symbols = [symbol]
        else:
            # 获取活跃交易对
            symbols = get_active_trading_pairs()[:10]  # 限制为前10个活跃交易对
            
        total_count = 0
        
        # 查询每个交易对的订单
        for symbol in symbols:
            try:
                # 查询当前挂单
                result = ws_client.query_open_orders(symbol)
                
                if result.get('success') and 'data' in result:
                    orders = result.get('data', [])
                    count = update_orders_in_db(email, orders)
                    total_count += count
                    
                # 限制请求频率
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"检查用户 {email} 的 {symbol} 缺失订单时出错: {str(e)}")
                
        # 关闭WebSocket连接
        ws_client.close()
        
        return total_count
        
    except Exception as e:
        logger.error(f"检查用户 {email} 的缺失订单时发生错误: {str(e)}", exc_info=True)
        return 0

def sync_orders_now(email, days=7, symbol=None):
    """立即同步指定用户的交易订单，使用WebSocket API
    
    Args:
        email: 用户邮箱
        days: 要同步的天数，默认为7天
        symbol: 交易对，默认为None
        
    Returns:
        int: 同步的订单数量
    """
    try:
        logger.info(f"立即同步用户 {email} 最近 {days} 天的交易订单（WebSocket API）")
        
        # 创建WebSocket客户端
        ws_client = create_websocket_client(email)
        if not ws_client:
            logger.error(f"无法创建WebSocket客户端，子账号 {email} 的API密钥可能有问题")
            return 0
            
        # 如果指定了单个交易对，则只处理该交易对
        if symbol:
            symbols = [symbol]
        else:
            # 获取活跃交易对
            symbols = get_active_trading_pairs()[:10]  # 限制为前10个活跃交易对
            
        total_count = 0
        
        # 查询每个交易对的订单
        for symbol in symbols:
            try:
                # 查询当前挂单
                result = ws_client.query_open_orders(symbol)
                
                if result.get('success') and 'data' in result:
                    orders = result.get('data', [])
                    count = update_orders_in_db(email, orders)
                    total_count += count
                    logger.info(f"通过WebSocket API更新 {email} 的 {symbol} 订单：{count}个")
                else:
                    logger.warning(f"通过WebSocket API查询 {email} 的 {symbol} 挂单失败：{result.get('error', 'Unknown error')}")
                    
                # 限制请求频率
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"同步用户 {email} 的 {symbol} 订单时出错: {str(e)}")
                
        # 关闭WebSocket连接
        ws_client.close()
        
        return total_count
        
    except Exception as e:
        logger.error(f"立即同步用户 {email} 的交易订单时发生错误: {str(e)}", exc_info=True)
        return 0

def check_api_permissions(email):
    """检查子账号API密钥权限
    
    Args:
        email: 子账号邮箱
        
    Returns:
        dict: 包含API权限检查结果的字典
    """
    try:
        client = get_client_by_email(email)
        if not client:
            return {
                'success': False,
                'error': '无法获取API客户端'
            }
        
        # 尝试获取账户信息，这个API相对基础，成功率高
        result = client._send_request(
            'GET',
            '/fapi/v3/account',
            signed=True
        )
        
        if not result.get('success'):
            error_msg = result.get('error', '未知错误')
            if '403' in str(error_msg):
                return {
                    'success': False,
                    'error': f'API密钥没有足够权限(403): {error_msg}',
                    'permission_issue': True
                }
            return {
                'success': False,
                'error': f'账户信息请求失败: {error_msg}'
            }
        
        # 测试其他常用端点
        endpoints = [
            # 测试获取持仓
            {
                'method': 'GET',
                'url': '/fapi/v3/positionRisk',
                'name': '持仓风险'
            },
            # 测试获取订单
            {
                'method': 'GET',
                'url': '/fapi/v1/allOrders',
                'params': {'limit': 1},
                'name': '订单历史'
            },
            # 测试获取交易历史
            {
                'method': 'GET',
                'url': '/fapi/v1/userTrades',
                'params': {'limit': 1},
                'name': '交易历史'
            }
        ]
        
        test_results = []
        
        for endpoint in endpoints:
            try:
                params = endpoint.get('params', {})
                result = client._send_request(
                    endpoint['method'],
                    endpoint['url'],
                    signed=True,
                    params=params
                )
                
                if result.get('success'):
                    test_results.append({
                        'endpoint': endpoint['name'],
                        'status': 'success'
                    })
                else:
                    error_msg = result.get('error', '未知错误')
                    test_results.append({
                        'endpoint': endpoint['name'],
                        'status': 'failed',
                        'error': error_msg
                    })
            except Exception as e:
                test_results.append({
                    'endpoint': endpoint['name'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'success': True,
            'test_results': test_results
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'API权限检查失败: {str(e)}'
        }

def diagnose_api_issues():
    """诊断所有子账号的API问题
    
    返回包含问题子账号列表的字典
    """
    try:
        from app.models.account import SubAccountAPISettings
        
        # 获取所有子账号API设置
        all_settings = SubAccountAPISettings.query.all()
        
        problem_accounts = []
        
        for setting in all_settings:
            try:
                if setting.api_key and setting.api_secret:
                    # 检查权限
                    result = check_api_permissions(setting.email)
                    
                    if not result.get('success'):
                        problem_accounts.append({
                            'email': setting.email,
                            'error': result.get('error', '未知错误'),
                            'permission_issue': result.get('permission_issue', False)
                        })
            except Exception as e:
                problem_accounts.append({
                    'email': setting.email,
                    'error': f'检查过程异常: {str(e)}'
                })
        
        logger.info(f"API诊断完成，发现{len(problem_accounts)}个问题账号，共{len(all_settings)}个账号")
        
        return {
            'success': True,
            'total_accounts': len(all_settings),
            'problem_accounts': problem_accounts
        }
    except Exception as e:
        logger.error(f"API诊断失败: {str(e)}")
        return {
            'success': False,
            'error': f'API诊断失败: {str(e)}'
        }

def test_master_api_access(email=None, symbol="BTCUSDT"):
    """测试主账号API访问子账号数据
    
    Args:
        email: 要测试的子账号邮箱（可选，默认测试所有子账号）
        symbol: 测试用的交易对
        
    Returns:
        dict: 包含测试结果的字典
    """
    try:
        # 获取主账号API客户端
        api_key, api_secret = get_main_account_api_credentials()
        
        if not api_key or not api_secret:
            logger.error("无法获取主账号API凭证，请确保有可用的主账号API密钥")
            return {
                'success': False,
                'error': '无法获取主账号API凭证'
            }
            
        # 创建主账号客户端
        client = BinanceClient(api_key, api_secret)
        
        # 如果未指定具体子账号，获取所有子账号列表
        if not email:
            # 获取子账号列表
            result = client.get_sub_accounts()
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f"获取子账号列表失败: {result.get('error', '未知错误')}"
                }
                
            if 'data' not in result or 'subaccounts' not in result['data']:
                return {
                    'success': False,
                    'error': '子账号数据格式异常'
                }
                
            # 提取子账号列表
            subaccounts = result['data']['subaccounts']
            emails = [account['email'] for account in subaccounts]
            
            if not emails:
                return {
                    'success': False,
                    'error': '未找到任何子账号'
                }
                
            logger.info(f"共找到 {len(emails)} 个子账号")
        else:
            emails = [email]
        
        # 测试结果
        results = []
        
        # 对每个子账号进行测试
        for test_email in emails:
            email_result = {
                'email': test_email,
                'tests': []
            }
            
            # 测试1: 获取合约余额
            balance_response = client.get_sub_account_futures_balance(test_email)
            email_result['tests'].append({
                'name': '合约余额',
                'success': balance_response.get('success', False),
                'error': balance_response.get('error') if not balance_response.get('success', False) else None
            })
            
            # 测试2: 获取合约持仓
            positions_response = client.get_sub_account_futures_positions(test_email, symbol)
            email_result['tests'].append({
                'name': '合约持仓',
                'success': positions_response.get('success', False),
                'error': positions_response.get('error') if not positions_response.get('success', False) else None
            })
            
            # 测试3: 获取合约订单
            orders_response = client.get_sub_account_futures_orders(test_email, symbol, 10)
            email_result['tests'].append({
                'name': '合约订单',
                'success': orders_response.get('success', False),
                'error': orders_response.get('error') if not orders_response.get('success', False) else None
            })
            
            # 计算成功率
            success_count = sum(1 for test in email_result['tests'] if test['success'])
            email_result['success_rate'] = f"{success_count}/{len(email_result['tests'])}"
            
            results.append(email_result)
        
        return {
            'success': True,
            'results': results
        }
    except Exception as e:
        logger.error(f"测试主账号API访问失败: {str(e)}")
        return {
            'success': False,
            'error': f"测试主账号API访问失败: {str(e)}"
        }

def get_listen_key(email):
    """获取WebSocket连接的listenKey，只使用合约接口
    
    Args:
        email: 子账号邮箱
        
    Returns:
        str: listenKey或None
    """
    try:
        # 获取子账号API客户端
        sub_client = get_client_by_email(email)
        if not sub_client:
            logger.error(f"无法获取子账号 {email} 的API客户端")
            return None
            
        logger.info(f"开始尝试获取子账号 {email} 的合约listenKey")
            
        # 使用USDT合约接口获取listenKey
        logger.info(f"尝试使用USDT合约接口获取子账号 {email} 的listenKey")
        result = sub_client._send_request(
            'POST',
            '/fapi/v1/listenKey',
            signed=True
        )
        
        if result.get('success'):
            listen_key = result.get('data', {}).get('listenKey')
            if listen_key:
                logger.info(f"成功获取子账号 {email} 的USDT合约listenKey: {listen_key}")
                return listen_key
            else:
                logger.warning(f"子账号 {email} 获取USDT合约listenKey成功但数据为空")
        else:
            error_msg = result.get('error', '未知错误')
            logger.warning(f"使用USDT合约接口获取子账号 {email} 的listenKey失败: {error_msg}")
            
        # 尝试使用主账号API获取子账号的listenKey
        logger.info(f"尝试使用主账号API获取子账号 {email} 的合约listenKey")
        api_key, api_secret = get_main_account_api_credentials()
        if api_key and api_secret:
            main_client = BinanceClient(api_key, api_secret)
            try:
                # 尝试通过Broker API获取子账号的listenKey（需要特殊权限）
                result = main_client._send_request(
                    'POST',
                    '/sapi/v1/broker/subAccount/futuresStream',
                    signed=True,
                    params={'email': email}
                )
                
                if result.get('success'):
                    listen_key = result.get('data', {}).get('listenKey')
                    if listen_key:
                        logger.info(f"成功通过主账号获取子账号 {email} 的合约listenKey: {listen_key}")
                        return listen_key
                    else:
                        logger.warning("通过主账号获取子账号listenKey成功但数据为空")
                else:
                    error_msg = result.get('error', '未知错误')
                    logger.warning(f"通过主账号获取子账号listenKey失败: {error_msg}")
            except Exception as e:
                logger.error(f"通过主账号获取子账号listenKey异常: {str(e)}")
            
        logger.error(f"子账号 {email} 获取合约listenKey失败，所有方法均已尝试")
        
        # 检查API权限状态并记录
        logger.info(f"尝试诊断子账号 {email} 的API权限问题")
        api_check = check_api_permissions(email)
        if not api_check.get('success'):
            logger.error(f"API权限检查失败: {api_check.get('error')}")
        else:
            test_results = api_check.get('test_results', [])
            for test in test_results:
                logger.info(f"API权限测试 - {test.get('endpoint')}: {test.get('status')}")
                if test.get('status') != 'success':
                    logger.error(f"API权限测试失败: {test.get('endpoint')} - {test.get('error')}")
        
        return None
        
    except Exception as e:
        logger.error(f"获取子账号 {email} 的listenKey异常: {str(e)}", exc_info=True)
        return None
        
def keep_listen_key_alive(email, listen_key):
    """保持合约listenKey有效
    
    Args:
        email: 子账号邮箱
        listen_key: listenKey
    """
    try:
        sub_client = get_client_by_email(email)
        if not sub_client:
            logger.error(f"无法获取子账号 {email} 的API客户端")
            return
            
        # 延长合约listenKey有效期
        result = sub_client._send_request(
            'PUT',
            '/fapi/v1/listenKey',
            signed=True
        )
        
        if result.get('success'):
            logger.debug(f"成功延长子账号 {email} 的合约listenKey有效期")
        else:
            logger.warning(f"延长子账号 {email} 的合约listenKey有效期失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"延长子账号 {email} 的合约listenKey有效期异常: {str(e)}")
        
def on_message(ws, message, email):
    """WebSocket消息处理函数
    
    Args:
        ws: WebSocket连接
        message: 接收到的消息
        email: 子账号邮箱
    """
    try:
        # 记录收到的消息
        logger.debug(f"收到WebSocket消息: {message[:500]}")
        
        # 解析JSON消息
        data = json.loads(message)
        event_type = data.get('e')
        
        # 记录事件类型
        logger.info(f"处理WebSocket事件: {event_type} 来自 {email}")
        
        # 处理订单更新事件
        if event_type == 'ORDER_TRADE_UPDATE':
            order_data = data.get('o', {})
            
            # 提取订单信息
            order_id = order_data.get('i')
            symbol = order_data.get('s')
            side = order_data.get('S')
            order_type = order_data.get('o')
            status = order_data.get('X')
            price = float(order_data.get('p', 0))
            amount = float(order_data.get('q', 0))
            executed_qty = float(order_data.get('z', 0))
            client_order_id = order_data.get('c')
            
            # 获取订单创建时间
            timestamp = data.get('E', 0)
            created_at = datetime.fromtimestamp(timestamp / 1000) if timestamp else datetime.utcnow()
            
            logger.debug(f"收到子账号 {email} 的订单更新: {symbol} {side} {status} 订单ID:{order_id}")
            
            # 更新数据库
            with lock:
                # 查询是否存在该订单记录
                order_record = OrderHistory.query.filter_by(
                    email=email,
                    order_id=str(order_id)
                ).first()
                
                # 如果订单不存在，创建新记录
                if not order_record:
                    new_order = OrderHistory(
                        email=email,
                        symbol=symbol,
                        order_type=order_type,
                        side=side,
                        amount=amount,
                        price=price,
                        status=status,
                        executed_qty=executed_qty,
                        order_id=str(order_id),
                        client_order_id=client_order_id,
                        created_at=created_at,
                        last_checked=datetime.utcnow()
                    )
                    db.session.add(new_order)
                    db.session.commit()
                    logger.info(f"通过WebSocket创建新订单记录: {email} {symbol} {order_id}")
                else:
                    # 如果订单存在，更新状态和执行数量
                    if order_record.status != status or order_record.executed_qty != executed_qty:
                        order_record.status = status
                        order_record.executed_qty = executed_qty
                        order_record.last_checked = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"通过WebSocket更新订单记录: {email} {symbol} {order_id} {status}")
                        
            # 如果订单已成交，同步交易历史记录
            if status == 'FILLED' and executed_qty > 0:
                # 检查是否已存在该订单的交易记录
                trade_exists = False
                with lock:
                    trade_record = TradeHistory.query.filter_by(
                        email=email,
                        orderId=str(order_id)
                    ).first()
                    
                    if trade_record:
                        trade_exists = True
                
                # 如果不存在交易记录，则通过API获取详细交易信息
                if not trade_exists:
                    try:
                        # 获取子账号API客户端
                        sub_client = get_client_by_email(email)
                        if sub_client:
                            # 查询该订单的交易详情
                            params = {
                                'symbol': symbol,
                                'orderId': order_id
                            }
                            
                            result = sub_client._send_request(
                                'GET',
                                "/fapi/v1/userTrades",
                                params=params,
                                signed=True
                            )
                            
                            if result.get('success') and result.get('data'):
                                trades = result.get('data')
                                # 创建交易记录
                                for trade in trades:
                                    trade_id = trade.get('id')
                                    
                                    # 检查是否已存在该交易记录
                                    with lock:
                                        existing_trade = TradeHistory.query.filter_by(
                                            email=email,
                                            id=trade_id
                                        ).first()
                                        
                                        if not existing_trade:
                                            # 创建新交易记录
                                            new_trade = TradeHistory(
                                                id=trade_id,
                                                email=email,
                                                symbol=symbol,
                                                side=side,
                                                price=float(trade.get('price', 0)),
                                                qty=float(trade.get('qty', 0)),
                                                quote_qty=float(trade.get('quoteQty', 0)),
                                                commission=float(trade.get('commission', 0)),
                                                commission_asset=trade.get('commissionAsset', ''),
                                                is_maker=trade.get('isMaker', False),
                                                orderId=str(order_id),
                                                trade_time=datetime.fromtimestamp(int(trade.get('time', 0)) / 1000),
                                                created_at=datetime.utcnow(),
                                                updated_at=datetime.utcnow()
                                            )
                                            db.session.add(new_trade)
                                            
                                    # 提交交易记录
                                    db.session.commit()
                                    logger.info(f"通过WebSocket创建新交易记录: {email} {symbol} {trade_id}")
                                    
                    except Exception as e:
                        logger.error(f"同步子账号 {email} 的交易记录时出错: {str(e)}")
                
        # 账户更新事件
        elif event_type == 'ACCOUNT_UPDATE':
            # 处理账户余额和持仓更新
            logger.info(f"收到账户更新事件: {email}")
            # 记录详细的事件内容以供调试
            logger.debug(f"账户更新数据: {json.dumps(data, ensure_ascii=False)}")
            pass
        
        # 标记价格更新    
        elif event_type == 'markPriceUpdate':
            logger.debug(f"收到标记价格更新: {email} {data.get('s')} {data.get('p')}")
            pass
            
        # 其他事件类型
        else:
            logger.info(f"收到未处理的WebSocket事件类型: {event_type} 来自 {email}")
            logger.debug(f"事件数据: {json.dumps(data, ensure_ascii=False)}")
                
    except Exception as e:
        logger.error(f"处理WebSocket消息异常: {str(e)}", exc_info=True)
        
def on_error(ws, error, email):
    """WebSocket错误处理函数
    
    Args:
        ws: WebSocket连接
        error: 错误信息
        email: 子账号邮箱
    """
    logger.error(f"子账号 {email} 的WebSocket连接错误: {str(error)}")
    # 记录详细错误信息
    if hasattr(error, 'status_code'):
        logger.error(f"WebSocket错误状态码: {error.status_code}")
    if hasattr(error, 'message'):
        logger.error(f"WebSocket错误消息: {error.message}")
        
    # 尝试重连
    if email in ws_connections:
        del ws_connections[email]
    
def on_close(ws, close_status_code, close_msg, email):
    """WebSocket关闭处理函数
    
    Args:
        ws: WebSocket连接
        close_status_code: 关闭状态码
        close_msg: 关闭消息
        email: 子账号邮箱
    """
    logger.warning(f"子账号 {email} 的WebSocket连接关闭: 状态码={close_status_code} 消息={close_msg}")
    
    # 从连接字典中移除
    if email in ws_connections:
        del ws_connections[email]
        
    # 尝试重连（如果是非正常关闭）
    if close_status_code != 1000:  # 1000是正常关闭
        logger.info(f"尝试为子账号 {email} 重新建立WebSocket连接")
        try:
            # 使用线程重新连接，避免阻塞当前线程
            reconnect_thread = threading.Thread(
                target=lambda: time.sleep(5) or connect_user_websocket(email, current_app._get_current_object())
            )
            reconnect_thread.daemon = True
            reconnect_thread.start()
        except Exception as e:
            logger.error(f"为子账号 {email} 重建WebSocket连接时出错: {str(e)}")
    
def on_open(ws, email):
    """WebSocket打开处理函数
    
    Args:
        ws: WebSocket连接
        email: 子账号邮箱
    """
    logger.info(f"子账号 {email} 的WebSocket连接已打开")
    # 发送一个ping消息测试连接
    try:
        ws.send('ping')
        logger.debug(f"发送WebSocket ping消息到 {email}")
    except Exception as e:
        logger.error(f"发送WebSocket ping消息失败: {str(e)}")
        
def on_ping(ws, message, email):
    """WebSocket ping处理函数
    
    Args:
        ws: WebSocket连接
        message: ping消息
        email: 子账号邮箱
    """
    logger.debug(f"收到WebSocket ping: {email} {message}")
    
def on_pong(ws, message, email):
    """WebSocket pong处理函数
    
    Args:
        ws: WebSocket连接
        message: pong消息
        email: 子账号邮箱
    """
    logger.debug(f"收到WebSocket pong: {email} {message}")

def connect_user_websocket(email, app):
    """为用户建立合约WebSocket连接
    
    Args:
        email: 子账号邮箱
        app: Flask应用实例
        
    Returns:
        bool: 连接是否成功
    """
    # 如果已经有连接，先关闭
    if email in ws_connections and ws_connections[email]:
        try:
            ws_connections[email].close()
            logger.info(f"关闭子账号 {email} 的现有WebSocket连接")
        except Exception as e:
            logger.error(f"关闭现有WebSocket连接出错: {str(e)}")
        
    # 获取listenKey
    listen_key = get_listen_key(email)
    if not listen_key:
        logger.error(f"无法为子账号 {email} 建立WebSocket连接：获取合约listenKey失败")
        return False
        
    # 构建合约WebSocket URL
    ws_url = f"wss://fstream.binance.com/ws/{listen_key}"
    logger.info(f"准备连接合约WebSocket URL: {ws_url}")
    
    # 创建WebSocket连接
    websocket.enableTrace(True)  # 启用详细的WebSocket跟踪日志
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=lambda ws, message: on_message(ws, message, email),
        on_error=lambda ws, error: on_error(ws, error, email),
        on_close=lambda ws, close_status_code, close_msg: on_close(ws, close_status_code, close_msg, email),
        on_open=lambda ws: on_open(ws, email),
        on_ping=lambda ws, message: on_ping(ws, message, email),
        on_pong=lambda ws, message: on_pong(ws, message, email)
    )
    
    # 保存连接
    ws_connections[email] = ws
    
    # 启动WebSocket连接（非阻塞）
    wst = threading.Thread(target=lambda: ws.run_forever(
        ping_interval=30,
        ping_timeout=10,
        ping_payload='ping'
    ))
    wst.daemon = True
    wst.start()
    
    logger.info(f"子账号 {email} 的合约WebSocket连接线程已启动")
    
    # 添加listenKey续期任务
    if scheduler:
        job_id = f"keep_listen_key_{email}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            
        scheduler.add_job(
            keep_listen_key_alive,
            'interval',
            minutes=30,  # 每30分钟续期一次
            id=job_id,
            args=[email, listen_key]
        )
        logger.info(f"已添加子账号 {email} 的合约listenKey续期任务")
    
    # 启动时同步一次历史订单，确保数据完整性
    with app.app_context():
        try:
            # 使用WebSocket客户端获取数据
            ws_client = create_websocket_client(email)
            if ws_client:
                # 获取活跃交易对
                symbol_list = get_active_trading_pairs()[:5]  # 限制为前5个活跃交易对
                
                total_count = 0
                for symbol in symbol_list:
                    try:
                        # 查询当前挂单
                        open_orders_result = ws_client.query_open_orders(symbol)
                        if open_orders_result.get('success') and 'data' in open_orders_result:
                            orders = open_orders_result.get('data', [])
                            count = update_orders_in_db(email, orders)
                            total_count += count
                    except Exception as e:
                        logger.error(f"WebSocket初始化查询子账号 {email} 的 {symbol} 挂单时出错: {str(e)}")
                
                # 关闭WebSocket连接
                ws_client.close()
                
                if total_count > 0:
                    logger.info(f"合约WebSocket连接初始化时同步了 {total_count} 个当前订单")
        except Exception as e:
            logger.error(f"合约WebSocket连接初始化时同步当前订单出错: {str(e)}")
    
    return True

def enable_rest_api_fallback(email, app):
    """当WebSocket连接无法建立时，启用备用的REST API轮询
    
    Args:
        email: 子账号邮箱
        app: Flask应用实例
    """
    # WebSocket直接连接失败时的处理，不再使用轮询
    logger.warning(f"子账号 {email} 的WebSocket连接无法建立，请检查API密钥权限")
    # 不再添加轮询任务

def sync_orders_rest_fallback(email, app):
    """已弃用：REST API轮询备用方案（现在直接使用WebSocket API）
    
    Args:
        email: 子账号邮箱
        app: Flask应用实例
    """
    # 此函数已被弃用，保留函数签名以防其他地方调用
    logger.debug(f"REST API轮询已弃用，现在直接使用WebSocket API: {email}")
    pass

def get_websocket_status(email=None):
    """获取WebSocket连接状态
    
    Args:
        email: 子账号邮箱，如果不指定，则返回所有连接状态
        
    Returns:
        dict: WebSocket连接状态信息
    """
    try:
        if email:
            # 返回指定子账号的连接状态
            if email in ws_connections and ws_connections[email]:
                return {
                    'success': True,
                    'status': 'connected',
                    'email': email
                }
            else:
                return {
                    'success': True,
                    'status': 'disconnected',
                    'email': email
                }
        else:
            # 返回所有连接的状态
            status_list = []
            for email, ws in ws_connections.items():
                status_list.append({
                    'email': email,
                    'status': 'connected' if ws else 'disconnected'
                })
                
            return {
                'success': True,
                'connections': status_list,
                'total': len(status_list),
                'connected': sum(1 for item in status_list if item['status'] == 'connected')
            }
            
    except Exception as e:
        logger.error(f"获取WebSocket连接状态时出错: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
def restart_websocket(email, app=None):
    """重启指定子账号的WebSocket连接
    
    Args:
        email: 子账号邮箱
        app: Flask应用实例，如果不指定则使用current_app
        
    Returns:
        dict: 重启结果
    """
    try:
        if not app:
            app = current_app._get_current_object()
            
        # 关闭现有连接
        if email in ws_connections and ws_connections[email]:
            try:
                ws_connections[email].close()
            except:
                pass
                
        # 从连接字典中移除
        if email in ws_connections:
            del ws_connections[email]
            
        # 重新建立连接
        if connect_user_websocket(email, app):
            return {
                'success': True,
                'message': f"子账号 {email} 的WebSocket连接已重启"
            }
        else:
            return {
                'success': False,
                'error': f"子账号 {email} 的WebSocket连接重启失败"
            }
            
    except Exception as e:
        logger.error(f"重启WebSocket连接时出错: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
def restart_all_websockets(app=None):
    """重启所有WebSocket连接
    
    Args:
        app: Flask应用实例，如果不指定则使用current_app
        
    Returns:
        dict: 重启结果
    """
    try:
        if not app:
            app = current_app._get_current_object()
            
        # 查询所有有效的子账号API设置
        api_settings = SubAccountAPISettings.query.all()
        if not api_settings:
            return {
                'success': False,
                'error': "没有找到有效的子账号API设置"
            }
            
        # 关闭所有现有连接
        for email in list(ws_connections.keys()):
            try:
                if ws_connections[email]:
                    ws_connections[email].close()
                del ws_connections[email]
            except:
                pass
                
        # 重新建立所有连接
        results = []
        with app.app_context():
            for api_setting in api_settings:
                email = api_setting.email
                if connect_user_websocket(email, app):
                    results.append({
                        'email': email,
                        'status': 'success'
                    })
                else:
                    results.append({
                        'email': email,
                        'status': 'failed'
                    })
                    
                # 避免同时建立太多连接
                time.sleep(1)
                
        return {
            'success': True,
            'results': results,
            'total': len(results),
            'success_count': sum(1 for r in results if r['status'] == 'success')
        }
        
    except Exception as e:
        logger.error(f"重启所有WebSocket连接时出错: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 