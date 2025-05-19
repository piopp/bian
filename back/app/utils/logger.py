import logging
import os
import datetime
import json
from functools import wraps
import time
import traceback
from flask import current_app

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/app_{datetime.datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('binance_app')

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
    # 只在开发环境记录信息日志
    if current_app and current_app.config.get('ENV') != 'development':
        return
    logger.info(truncate_message(message))
    
def log_error(message):
    """安全记录错误日志，确保不超过字符限制"""
    logger.error(truncate_message(message))
    
def log_exception(message):
    """安全记录异常日志，确保不超过字符限制"""
    logger.exception(truncate_message(message))

def log_debug(message):
    """安全记录调试日志，确保不超过字符限制"""
    logger.debug(truncate_message(message))

def log_warning(message):
    """安全记录警告日志，确保不超过字符限制"""
    logger.warning(truncate_message(message))

def log_parallel_execution(operation_type, start_time, end_time, buy_result, sell_result):
    """记录并行执行买卖单的日志
    
    Args:
        operation_type: 操作类型，例如'UM'或'CM'
        start_time: 开始时间戳
        end_time: 结束时间戳
        buy_result: 买单执行结果
        sell_result: 卖单执行结果
    """
    duration_ms = int((end_time - start_time) * 1000)
    
    # 提取结果状态
    buy_success = buy_result.get('success', False) if buy_result else False
    sell_success = sell_result.get('success', False) if sell_result else False
    
    # 构建日志详情
    log_details = {
        'operation_type': operation_type,
        'duration_ms': duration_ms,
        'buy_order': {
            'success': buy_success,
            'order_id': buy_result.get('data', {}).get('orderId') if buy_success else None,
            'error': buy_result.get('error') if not buy_success and buy_result else None
        },
        'sell_order': {
            'success': sell_success,
            'order_id': sell_result.get('data', {}).get('orderId') if sell_success else None,
            'error': sell_result.get('error') if not sell_success and sell_result else None
        }
    }
    
    # 记录为JSON格式
    logger.info(f"并行执行{operation_type}买卖单: 耗时{duration_ms}ms | {json.dumps(log_details, ensure_ascii=False)}")

def log_function_call(func):
    """函数调用日志装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.info(f"开始调用函数: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 毫秒
            logger.info(f"函数 {func_name} 调用成功，耗时: {duration:.2f}ms")
            return result
        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 毫秒
            logger.error(f"函数 {func_name} 调用失败，耗时: {duration:.2f}ms, 错误: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            raise
    
    return wrapper 