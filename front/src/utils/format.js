/**
 * 格式化日期时间
 * @param {string|number|Date} date - 要格式化的日期
 * @param {string} format - 格式模板, 默认: 'YYYY-MM-DD HH:mm:ss'
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) {
    return '--';
  }
  
  // 处理时间戳（毫秒或秒）
  let timestamp = date;
  if (typeof date === 'number') {
    // 如果是秒级时间戳，转换为毫秒
    if (date < 10000000000) {
      timestamp = date * 1000;
    }
  }
  
  const d = new Date(timestamp);
  
  if (isNaN(d.getTime())) {
    return '--';
  }
  
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}

/**
 * 格式化数字
 * @param {number} num - 要格式化的数字
 * @param {number} precision - 小数位数
 * @returns {string} 格式化后的数字字符串
 */
export function formatNumber(num, precision = 2) {
  if (num === null || num === undefined || isNaN(Number(num))) {
    return '--';
  }
  
  return Number(num).toFixed(precision);
}

/**
 * 格式化价格
 * @param {number} price - 价格
 * @param {number} precision - 小数位数
 * @returns {string} 格式化后的价格字符串
 */
export function formatPrice(price, precision = 8) {
  return formatNumber(price, precision);
}

/**
 * 格式化数量
 * @param {number} quantity - 数量
 * @param {number} precision - 小数位数
 * @returns {string} 格式化后的数量字符串
 */
export function formatQuantity(quantity, precision = 6) {
  return formatNumber(quantity, precision);
} 