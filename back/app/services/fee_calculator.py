"""
手续费计算工具
根据交易类型和订单类型计算手续费
"""

# 手续费率常量
FEE_RATES = {
    # 现货及杠杆
    "SPOT": {
        "TAKER": 0.001,  # 0.10%
        "MAKER": 0.001,  # 0.10%
    },
    # U本位合约(USDT)
    "USDT_FUTURE": {
        "TAKER": 0.0005,  # 0.05%
        "MAKER": 0.0002,  # 0.02%
    },
    # U本位合约(USDC)
    "USDC_FUTURE": {
        "TAKER": 0.0004,  # 0.04%
        "MAKER": 0.0,  # 0%
    },
    # 币本位合约
    "COIN_FUTURE": {
        "TAKER": 0.0005,  # 0.05%
        "MAKER": 0.0002,  # 0.02%
    }
}

def calculate_order_fee(order):
    """
    计算订单手续费
    
    参数:
    order - 订单信息
        symbol - 交易对
        order_type - 订单类型 (LIMIT, MARKET 等)
        product_type - 产品类型 (SPOT, USDT_FUTURE, USDC_FUTURE, COIN_FUTURE)
        amount - 交易数量
        price - 交易价格
        status - 订单状态 (FILLED, PARTIALLY_FILLED, CANCELED 等)
        is_maker - 是否是做市商订单 (可选，如果不提供将基于订单类型判断)
    
    返回:
    dict - 手续费信息
        fee - 手续费金额
        fee_rate - 手续费率
        fee_type - 手续费类型 (MAKER/TAKER)
        fee_usdt - 手续费的USDT估值
    """
    # 只有成交的订单才计算手续费
    if order.get('status') not in ['FILLED', 'PARTIALLY_FILLED']:
        return {
            'fee': 0,
            'fee_rate': 0,
            'fee_type': 'NONE',
            'fee_usdt': 0
        }
    
    # 确定产品类型
    product_type = order.get('product_type', 'SPOT')
    
    # 确定是Taker还是Maker
    fee_type = 'MAKER'
    
    # 如果明确指定了is_maker，则使用它
    if 'is_maker' in order:
        fee_type = 'MAKER' if order.get('is_maker') else 'TAKER'
    else:
        # 否则根据订单类型判断
        # 市价单一般是Taker
        if order.get('order_type') == 'MARKET':
            fee_type = 'TAKER'
        # 限价单可能是Maker也可能是Taker，但默认按Maker计算
        elif order.get('order_type') == 'LIMIT':
            fee_type = 'MAKER'
        # 其他特殊订单类型如STOP_MARKET等都当作Taker处理
        else:
            fee_type = 'TAKER'
    
    # 获取费率
    fee_rate = FEE_RATES.get(product_type, {}).get(fee_type, 0)
    
    # 计算交易金额
    trade_amount = float(order.get('amount', 0)) * float(order.get('price', 0))
    
    # 计算手续费
    fee = trade_amount * fee_rate
    
    # 如果是USDT或USDC交易对，手续费就是USDT计价
    # 否则需要根据交易对的报价币种转换为USDT
    fee_usdt = fee
    if order.get('fee_currency') and order.get('fee_currency') != 'USDT' and order.get('fee_usdt_rate'):
        fee_usdt = fee * float(order.get('fee_usdt_rate'))
    
    return {
        'fee': fee,
        'fee_rate': fee_rate,
        'fee_type': fee_type,
        'fee_usdt': fee_usdt
    }

def calculate_total_fees(orders):
    """
    批量计算多个订单的总手续费
    
    参数:
    orders - 订单列表
    
    返回:
    dict - 总手续费信息
    """
    total_fee = 0
    total_fee_usdt = 0
    
    for order in orders:
        result = calculate_order_fee(order)
        total_fee += result['fee']
        total_fee_usdt += result['fee_usdt']
    
    return {
        'total_fee': total_fee,
        'total_fee_usdt': total_fee_usdt,
        'order_count': len(orders)
    }

def get_fee_rate(product_type, is_maker):
    """
    获取特定交易类型的手续费率
    
    参数:
    product_type - 产品类型
    is_maker - 是否是做市商
    
    返回:
    float - 手续费率
    """
    fee_type = 'MAKER' if is_maker else 'TAKER'
    return FEE_RATES.get(product_type, {}).get(fee_type, 0)

def estimate_fee(product_type, amount):
    """
    按照简化方式计算手续费（使用固定费率）
    
    参数:
    product_type - 产品类型 (SPOT, FUTURE)
    amount - 交易金额
    
    返回:
    float - 估算的手续费
    """
    # 使用简化费率
    fee_rate = 0.001  # 默认现货0.1%
    
    if product_type == 'FUTURE':
        fee_rate = 0.0005  # 合约使用0.05%
    
    return amount * fee_rate 