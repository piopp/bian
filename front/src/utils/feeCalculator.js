/**
 * 手续费计算工具
 * 根据交易类型和订单类型计算手续费
 */

// 手续费率常量
export const FEE_RATES = {
  // 现货及杠杆
  SPOT: {
    TAKER: 0.001, // 0.10%
    MAKER: 0.001, // 0.10%
  },
  // U本位合约(USDT)
  USDT_FUTURE: {
    TAKER: 0.0005, // 0.05%
    MAKER: 0.0002, // 0.02%
  },
  // U本位合约(USDC)
  USDC_FUTURE: {
    TAKER: 0.0004, // 0.04%
    MAKER: 0, // 0%
  },
  // 币本位合约
  COIN_FUTURE: {
    TAKER: 0.0005, // 0.05%
    MAKER: 0.0002, // 0.02%
  }
};

/**
 * 计算订单手续费
 * @param {Object} order - 订单信息
 * @param {string} order.symbol - 交易对
 * @param {string} order.orderType - 订单类型 (LIMIT, MARKET 等)
 * @param {string} order.productType - 产品类型 (SPOT, USDT_FUTURE, USDC_FUTURE, COIN_FUTURE)
 * @param {number} order.amount - 交易数量
 * @param {number} order.price - 交易价格
 * @param {string} order.status - 订单状态 (FILLED, PARTIALLY_FILLED, CANCELED 等)
 * @param {boolean} order.isMaker - 是否是做市商订单 (可选，如果不提供将基于订单类型判断)
 * @returns {Object} - 手续费信息
 */
export function calculateOrderFee(order) {
  // 只有成交的订单才计算手续费
  if (order.status !== 'FILLED' && order.status !== 'PARTIALLY_FILLED') {
    return {
      fee: 0,
      feeRate: 0,
      feeType: 'NONE',
      feeUSDT: 0
    };
  }

  // 确定产品类型
  const productType = order.productType || 'SPOT';
  
  // 确定是Taker还是Maker
  let feeType = 'MAKER';
  
  // 如果明确指定了isMaker，则使用它
  if (order.isMaker !== undefined) {
    feeType = order.isMaker ? 'MAKER' : 'TAKER';
  } else {
    // 否则根据订单类型判断
    // 市价单一般是Taker
    if (order.orderType === 'MARKET') {
      feeType = 'TAKER';
    } 
    // 限价单可能是Maker也可能是Taker，但默认按Maker计算
    else if (order.orderType === 'LIMIT') {
      feeType = 'MAKER';
    }
    // 其他特殊订单类型如STOP_MARKET等都当作Taker处理
    else {
      feeType = 'TAKER';
    }
  }
  
  // 获取费率
  const feeRate = FEE_RATES[productType]?.[feeType] || 0;
  
  // 计算交易金额
  const tradeAmount = order.amount * order.price;
  
  // 计算手续费
  const fee = tradeAmount * feeRate;
  
  // 如果是USDT或USDC交易对，手续费就是USDT计价
  // 否则需要根据交易对的报价币种转换为USDT
  let feeUSDT = fee;
  if (order.feeCurrency && order.feeCurrency !== 'USDT' && order.feeUSDTRate) {
    feeUSDT = fee * order.feeUSDTRate;
  }
  
  return {
    fee,
    feeRate,
    feeType,
    feeUSDT
  };
}

/**
 * 批量计算多个订单的总手续费
 * @param {Array} orders - 订单列表
 * @returns {Object} - 包含总手续费信息
 */
export function calculateTotalFees(orders) {
  let totalFee = 0;
  let totalFeeUSDT = 0;
  
  orders.forEach(order => {
    const { fee, feeUSDT } = calculateOrderFee(order);
    totalFee += fee;
    totalFeeUSDT += feeUSDT;
  });
  
  return {
    totalFee,
    totalFeeUSDT,
    orderCount: orders.length
  };
}

/**
 * 获取特定交易类型的手续费率
 * @param {string} productType - 产品类型
 * @param {boolean} isMaker - 是否是做市商
 * @returns {number} - 手续费率
 */
export function getFeeRate(productType, isMaker) {
  const type = isMaker ? 'MAKER' : 'TAKER';
  return FEE_RATES[productType]?.[type] || 0;
}

/**
 * 按照简化方式计算手续费（使用固定费率）
 * @param {string} productType - 产品类型 (SPOT, FUTURE)
 * @param {number} amount - 交易金额
 * @returns {number} - 估算的手续费
 */
export function estimateFee(productType, amount) {
  // 使用简化费率
  let feeRate = 0.001; // 默认现货0.1%
  
  if (productType === 'FUTURE') {
    feeRate = 0.0005; // 合约使用0.05%
  }
  
  return amount * feeRate;
} 