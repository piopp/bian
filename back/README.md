# 币安API子账号管理系统 - 后端服务

## 系统简介
本系统提供币安子账号管理功能，主要包括：
- 批量创建和管理子账号
- 查询子账号资产和持仓
- 批量开仓、平仓操作
- 子账号间资金转账
- 合约订单查询和统计

## 安装依赖
```bash
pip install -r requirements.txt
```

## 配置说明

### 环境变量
系统支持通过环境变量配置关键参数:
- `BINANCE_PROXY`: 币安API代理服务器，解决403/连接问题
- `DEFAULT_API_KEY`: 默认主账号API Key
- `DEFAULT_API_SECRET`: 默认主账号API Secret

### 解决合约订单查询403问题
如果遇到合约订单查询(`/api/subaccounts/futures-orders`)返回403错误，这通常是由CloudFront拦截导致的，有以下解决方法：

1. **配置代理服务器**:
   在环境变量中设置`BINANCE_PROXY`变量，支持HTTP和SOCKS5代理:
   ```
   # HTTP代理
   export BINANCE_PROXY=http://proxy-server:port
   
   # SOCKS5代理
   export BINANCE_PROXY=socks5://proxy-server:port
   ```

2. **直接在配置文件中设置代理**:
   编辑`config.py`文件，修改`BINANCE_PROXY`设置:
   ```python
   BINANCE_PROXY = 'http://proxy-server:port'  # 或 'socks5://proxy-server:port'
   ```

3. **使用多URL自动切换**:
   系统已优化为自动在多个币安API URL间切换:
   - api.binance.com
   - api1.binance.com
   - api2.binance.com
   - api3.binance.com
   
   同样支持合约API域名自动切换。

### 优化合约订单查询性能
1. **不指定symbol参数**:
   当不需要查询特定交易对时，不传入symbol参数可以一次性获取所有交易对的订单数据。

2. **增加limit参数**:
   默认查询最近50条订单，可根据需要调整limit参数，但过大的值可能导致响应时间增加。

## 启动服务
```bash
python run.py
```

## API文档
系统主要API端点:
- `GET /api/subaccounts`: 获取子账号列表
- `POST /api/subaccounts/futures-orders`: 获取子账号合约订单
- `POST /api/subaccounts/futures-positions`: 获取子账号持仓
- `POST /api/subaccounts/futures-balance`: 获取子账号余额
- `POST /api/subaccounts/batch-close`: 批量平仓子账号持仓

更详细的API文档请参考系统内部接口注释。

# 币安API子账号管理系统 - 订单查询说明

## 合约订单查询重要说明

根据币安官方文档，查询子账户订单时必须遵循以下规则：

> 如果您想要查看子账户的订单信息，您需要通过子账户的API密钥进行操作，母账户的API密钥无法查询子账户订单。

这意味着每个子账户必须有自己的API密钥才能查询其订单。主账户API无法直接获取子账户的订单信息。

## 使用的币安API基础URL

本系统使用以下固定URL访问币安API：

- 合约API: `https://fapi.binance.com`
- 现货API: `https://api.binance.com`
- SAPI接口: `https://api.binance.com/sapi`

## 设置子账户API密钥

请确保每个需要查询订单的子账户都已设置API密钥：

1. 登录币安子账户
2. 创建API密钥（必须启用读取权限）
3. 在系统中导入子账户API密钥（通过`/api/subaccounts/api-import`接口）

## 订单查询最佳实践

### 1. 使用正确的API端点

对于U本位合约订单查询，使用`/fapi/v1/allOrders`端点：
```
GET /fapi/v1/allOrders
```

完整API文档：https://developers.binance.com/docs/zh-CN/derivatives/usds-margined-futures/trade/rest-api/All-Orders

### 2. 参数优化

- **不指定symbol参数** - 不传入symbol时可以一次性获取所有交易对的订单，减少API请求次数
- **增加recvWindow参数** - 设置为5000增加请求成功率：`recvWindow=5000`
- **使用时间筛选** - 对于大量订单，使用startTime和endTime参数限制查询范围

### 3. 处理请求限制

币安API对请求频率有严格限制，尤其是订单查询：

- 查询单交易对：权重5
- 不指定交易对：权重40

请确保不要频繁请求，建议：
- 实现缓存机制，短时间内不重复查询
- 仅在需要时查询，避免周期性轮询
- 增加请求间隔，每秒不超过5个请求

## 常见问题解决

### 403 Forbidden 错误

此错误通常表示API访问被币安拒绝，可能原因：

1. **API密钥问题**
   - 确保API密钥有效且拥有读取权限
   - 检查API密钥是否已过期或被撤销

2. **IP限制**
   - 系统配置了IP限制，确保服务器IP已添加到币安API白名单
   - 使用代理服务器绕过IP限制（通过修改`config.py`中的`BINANCE_PROXY`配置）

3. **请求频率过高**
   - 减少请求频率，增加间隔时间
   - 实现指数退避重试机制

### 无法获取子账户订单

1. **检查子账户API设置**
   - 确认SubAccountAPISettings表中存在该子账户的记录
   - 验证API密钥是否正确保存

2. **验证API权限**
   - 子账户API密钥必须至少启用"读取"权限
   - 主账户无法查询子账户订单，必须使用子账户自身API密钥

3. **查询缓慢或超时**
   - 增加`recvWindow`参数值（默认5000毫秒）
   - 缩小查询范围，使用时间或交易对过滤
   - 检查网络连接稳定性，确保服务器可以访问币安API

## API错误码参考

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| -1022  | 签名无效 | 检查API密钥和密钥是否匹配 |
| -1021  | 时间戳过期 | 服务器时间与币安不同步，校准服务器时间 |
| -2015  | 无效的API密钥 | 更新或重新生成API密钥 |
| -2014  | API权限不足 | 确保API密钥拥有读取权限 |
| 403    | 请求被拒绝 | 使用代理服务器 |
| 429    | 请求频率过高 | 减少请求频率，增加间隔 |

# 币安API子账户合约订单查询功能修复说明

## 主要问题

币安API子账户合约订单查询功能(`/api/subaccounts/futures-orders`)存在以下问题:

1. **子账户API权限问题**：
   - 根据币安官方文档，只能使用子账户自己的API密钥查询其订单
   - 母账户API密钥无法查询子账户订单

2. **API URL构建问题**：
   - 当前URL构建逻辑在某些情况下可能导致错误
   - 需固定使用`https://fapi.binance.com/fapi/v1/allOrders`端点

3. **错误处理和用户提示**：
   - 需要更友好的错误提示，帮助用户快速定位问题
   - 增强对常见API错误的分类和处理

## 修复方案

### 1. 修复URL构建逻辑

在`BinanceClient`类中，确保合约API URL正确构建：

```python
def __init__(self, api_key=None, api_secret=None):
    # ...
    # 设置固定的API基础URL，根据用户要求只使用单一URL
    self.base_url = "https://api.binance.com"
    self.fapi_url = "https://fapi.binance.com"  # U本位合约API
    self.sapi_url = "https://api.binance.com/sapi"
    # ...

def _send_request(self, method, endpoint, signed=False, params=None):
    # ...
    # 正确构建URL，保留完整路径
    if endpoint.startswith('/fapi'):
        # 合约API - 使用完整路径，不删除/fapi前缀
        url = f"{self.fapi_url}{endpoint}"
    # ...
```

### 2. 子账户API密钥使用

确保每个子账户使用自己的API密钥：

```python
def get_sub_account_futures_orders(self, email, symbol=None, limit=50):
    # ...
    # 从数据库中查询该邮箱的API设置
    api_setting = SubAccountAPISettings.query.filter_by(email=email).first()
    
    # 如果找不到设置，返回错误
    if not api_setting or not api_setting.api_key or not api_setting.api_secret:
        logger.error(f"未找到邮箱 {email} 的有效API设置，无法查询订单")
        return {
            'success': False,
            'error': f"未找到邮箱 {email} 的有效API设置，请先配置API密钥"
        }
    
    # 创建子账户客户端
    sub_client = BinanceClient(api_setting.api_key, api_setting.api_secret)
    # ...
```

### 3. 优化请求参数

增加`recvWindow`参数提高请求成功率：

```python
# 调用API获取订单历史 - 根据币安官方文档设置参数
params = {
    'limit': limit,
    'recvWindow': 5000  # 增加接收窗口时间，提高请求成功率
}

# 重要优化：如果不指定symbol，可以一次性获取所有交易对的订单
if symbol:
    params['symbol'] = symbol
```

### 4. 增强错误处理和重试机制

```python
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
```

## 常见问题解决

1. **"API密钥无效"错误**：
   - 检查子账户API密钥是否正确配置
   - 确认API密钥未过期或被禁用

2. **"API权限不足"错误**：
   - 确保API密钥启用了读取权限
   - 如使用IP白名单，确保当前服务器IP已添加

3. **请求超时错误**：
   - 增加`recvWindow`参数值（默认已设为5000ms）
   - 检查网络连接和服务器代理设置

4. **返回空订单列表**：
   - 如查询指定交易对，确认子账户在该交易对有订单记录
   - 考虑调整时间范围参数`startTime`和`endTime`

## 参考资料

- [币安官方API文档 - U本位合约查询所有订单](https://binance-docs.github.io/apidocs/futures/cn/#trade-3)
- [币安API错误码](https://binance-docs.github.io/apidocs/futures/cn/#error-codes-2) 