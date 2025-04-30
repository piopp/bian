import json
import time
import hmac
import hashlib
import threading
import uuid
import logging
from urllib.parse import urlencode
from datetime import datetime
from websocket import (
    create_connection,
    WebSocketException,
    WebSocketConnectionClosedException,
    ABNF
)

# 初始化日志
logger = logging.getLogger('websocket_client')

class BinanceWebSocketClient:
    """币安WebSocket API客户端，用于直接查询数据"""
    
    def __init__(self, api_key, api_secret):
        """初始化WebSocket客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥密文
        """
        self.api_key = api_key
        self.api_secret = api_secret
        # 使用合约WebSocket API的基础URL
        self.base_url = "wss://fstream.binance.com/ws-api/v3"
        self.ws = None
        self.running = False
        self.callback = None
        self.thread = None
        self.last_ping = time.time()
        
    def _generate_signature(self, params):
        """生成API请求签名
        
        Args:
            params: 请求参数字典
            
        Returns:
            str: 签名字符串
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    def connect(self):
        """建立WebSocket连接"""
        try:
            if self.ws:
                self.ws.close()
                
            logger.info("正在建立WebSocket连接...")
            self.ws = create_connection(self.base_url)
            self.running = True
            logger.info("WebSocket连接已建立")
            return True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {str(e)}")
            return False
            
    def close(self):
        """关闭WebSocket连接"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
                logger.info("WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {str(e)}")
            self.ws = None
            
    def listen(self, callback=None):
        """开始监听WebSocket消息
        
        Args:
            callback: 消息回调函数
        """
        self.callback = callback
        
        if self.thread and self.thread.is_alive():
            logger.warning("监听线程已经在运行")
            return
            
        self.thread = threading.Thread(target=self._listen_thread)
        self.thread.daemon = True
        self.thread.start()
        logger.info("WebSocket监听线程已启动")
        
    def _listen_thread(self):
        """WebSocket监听线程"""
        while self.running:
            try:
                if not self.ws:
                    logger.warning("WebSocket连接不存在，尝试重连")
                    if not self.connect():
                        time.sleep(5)
                        continue
                
                # 接收WebSocket数据帧
                op_code, frame = self.ws.recv_data_frame(True)
                
                # 处理Ping消息
                if op_code == ABNF.OPCODE_PING:
                    self.ws.pong("")
                    logger.debug("收到Ping消息，已回复Pong")
                # 处理文本消息
                elif op_code == ABNF.OPCODE_TEXT:
                    data = frame.data.decode("utf-8")
                    logger.debug(f"收到WebSocket消息: {data[:200]}...")
                    
                    # 解析JSON数据
                    try:
                        json_data = json.loads(data)
                        # 处理回调
                        if self.callback:
                            self.callback(json_data)
                    except json.JSONDecodeError:
                        logger.error(f"解析JSON数据失败: {data[:100]}...")
                # 处理其他消息类型
                else:
                    logger.warning(f"收到未知的操作码: {op_code}")
                    
                # 检查是否需要发送心跳
                current_time = time.time()
                if current_time - self.last_ping > 30:  # 每30秒发送一次心跳
                    try:
                        self.ws.ping("")
                        self.last_ping = current_time
                        logger.debug("发送Ping心跳")
                    except Exception as e:
                        logger.error(f"发送Ping心跳失败: {str(e)}")
                        
            except WebSocketConnectionClosedException:
                logger.warning("WebSocket连接已关闭，尝试重连")
                self.connect()
                time.sleep(1)
            except WebSocketException as e:
                logger.error(f"WebSocket异常: {str(e)}")
                self.connect()
                time.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket监听线程异常: {str(e)}")
                time.sleep(5)
                
        logger.info("WebSocket监听线程已退出")
    
    def query_order(self, symbol, order_id=None, client_order_id=None):
        """查询订单状态
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            client_order_id: 客户端订单ID
            
        Returns:
            dict: 订单信息或错误信息
        """
        if not self.ws:
            if not self.connect():
                return {"success": False, "error": "WebSocket连接失败"}
                
        try:
            # 准备请求参数
            params = {
                "apiKey": self.api_key,
                "symbol": symbol,
                "timestamp": int(time.time() * 1000)
            }
            
            if order_id:
                params["orderId"] = order_id
            elif client_order_id:
                params["origClientOrderId"] = client_order_id
            else:
                return {"success": False, "error": "缺少订单ID或客户端订单ID"}
                
            # 生成签名
            signature = self._generate_signature(params)
            params["signature"] = signature
            
            # 准备WebSocket消息
            request_id = str(uuid.uuid4())
            message = {
                "id": request_id,
                "method": "order.status",
                "params": params
            }
            
            logger.debug(f"发送订单查询请求: {json.dumps(message)}")
            
            # 发送请求
            self.ws.send(json.dumps(message))
            
            # 等待响应
            start_time = time.time()
            while time.time() - start_time < 10:  # 等待最多10秒
                op_code, frame = self.ws.recv_data_frame(True)
                
                if op_code == ABNF.OPCODE_PING:
                    self.ws.pong("")
                    logger.debug("收到Ping消息，已回复Pong")
                    continue
                    
                if op_code == ABNF.OPCODE_TEXT:
                    data = frame.data.decode("utf-8")
                    json_data = json.loads(data)
                    
                    # 检查是否是我们请求的响应
                    if json_data.get("id") == request_id:
                        if "error" in json_data:
                            logger.error(f"查询订单失败: {json_data['error']}")
                            return {"success": False, "error": json_data["error"]}
                        else:
                            logger.info(f"查询订单成功: {symbol} {order_id or client_order_id}")
                            return {"success": True, "data": json_data["result"]}
                            
            return {"success": False, "error": "查询订单超时"}
            
        except Exception as e:
            logger.error(f"查询订单异常: {str(e)}")
            return {"success": False, "error": f"查询订单异常: {str(e)}"}
            
    def query_open_orders(self, symbol=None):
        """查询当前挂单
        
        Args:
            symbol: 交易对(可选)
            
        Returns:
            dict: 挂单列表或错误信息
        """
        if not self.ws:
            if not self.connect():
                return {"success": False, "error": "WebSocket连接失败"}
                
        try:
            # 准备请求参数
            params = {
                "apiKey": self.api_key,
                "timestamp": int(time.time() * 1000)
            }
            
            if symbol:
                params["symbol"] = symbol
                
            # 生成签名
            signature = self._generate_signature(params)
            params["signature"] = signature
            
            # 准备WebSocket消息
            request_id = str(uuid.uuid4())
            message = {
                "id": request_id,
                "method": "openOrders.status",
                "params": params
            }
            
            logger.debug(f"发送挂单查询请求: {json.dumps(message)}")
            
            # 发送请求
            self.ws.send(json.dumps(message))
            
            # 等待响应
            start_time = time.time()
            while time.time() - start_time < 10:  # 等待最多10秒
                op_code, frame = self.ws.recv_data_frame(True)
                
                if op_code == ABNF.OPCODE_PING:
                    self.ws.pong("")
                    logger.debug("收到Ping消息，已回复Pong")
                    continue
                    
                if op_code == ABNF.OPCODE_TEXT:
                    data = frame.data.decode("utf-8")
                    json_data = json.loads(data)
                    
                    # 检查是否是我们请求的响应
                    if json_data.get("id") == request_id:
                        if "error" in json_data:
                            logger.error(f"查询挂单失败: {json_data['error']}")
                            return {"success": False, "error": json_data["error"]}
                        else:
                            orders_count = len(json_data.get("result", []))
                            logger.info(f"查询挂单成功: {symbol or '所有交易对'} - {orders_count}个订单")
                            return {"success": True, "data": json_data["result"]}
                            
            return {"success": False, "error": "查询挂单超时"}
            
        except Exception as e:
            logger.error(f"查询挂单异常: {str(e)}")
            return {"success": False, "error": f"查询挂单异常: {str(e)}"}

# 辅助函数，根据邮箱创建WebSocket客户端
def create_websocket_client(email):
    """根据邮箱创建WebSocket客户端
    
    Args:
        email: 用户邮箱
        
    Returns:
        BinanceWebSocketClient: WebSocket客户端实例或None
    """
    from app.api.subaccounts import get_sub_account_api_credentials
    
    try:
        # 获取子账号API凭证
        api_key, api_secret = get_sub_account_api_credentials(email)
        
        if not api_key or not api_secret:
            logger.error(f"邮箱 {email} 的API密钥不完整或不存在")
            return None
            
        # 创建WebSocket客户端
        client = BinanceWebSocketClient(api_key, api_secret)
        return client
    except Exception as e:
        logger.error(f"创建WebSocket客户端异常: {str(e)}")
        return None 