import axios from 'axios';
import { getCurrentUser } from './auth';

// 缓存对象
const cache = {
  orders: new Map(), // 按唯一键存储订单数据
  lastUpdate: null,  // 最后更新时间
  isLoading: false,  // 是否正在加载
  pendingCallbacks: [], // 等待数据的回调函数列表
  activeRequests: new Map(), // 当前活跃的请求，用于合并相同请求
  requestCount: 0,    // 请求计数器，用于调试
  cacheHits: 0        // 缓存命中计数，用于调试
};

// 生成缓存键
function generateCacheKey(params) {
  const { emails, symbol, contractType, limit } = params;
  // 确保emails排序，保证不同顺序的相同emails集合生成相同的键
  const emailsKey = emails ? [...emails].sort().join(',') : '';
  return `${emailsKey}|${symbol || ''}|${contractType || 'UM'}|${limit || '50'}`;
}

// 检查缓存是否有效
function isCacheValid(key, maxAge = 3000) { // 默认3秒有效期
  const entry = cache.orders.get(key);
  if (!entry) return false;
  
  const now = Date.now();
  return (now - entry.timestamp) < maxAge;
}

// 从API获取订单数据
async function fetchOrdersFromAPI(params) {
  const user = getCurrentUser();
  if (!user || !user.token) {
    throw new Error('用户未登录或token无效');
  }
  
  // 确保contractType参数被传递
  const apiParams = {...params};
  if (!apiParams.contractType) {
    apiParams.contractType = 'UM'; // 默认设置为UM类型
  }
  
  // 增加请求计数器
  cache.requestCount++;
  console.log(`订单缓存: 发送API请求 #${cache.requestCount}`, apiParams);
  
  const response = await axios.post('/api/subaccounts/futures-orders', apiParams, {
    headers: {
      'Authorization': `Bearer ${user.token}`
    }
  });
  
  return response;
}

// 获取订单数据(带缓存)
export async function getOrdersData(params, forceRefresh = false, maxAge = 3000) {
  const cacheKey = generateCacheKey(params);
  
  // 如果缓存有效且不强制刷新，直接返回缓存的数据
  if (!forceRefresh && isCacheValid(cacheKey, maxAge)) {
    cache.cacheHits++;
    console.log(`订单缓存: 命中缓存 #${cache.cacheHits}`, { key: cacheKey, maxAge });
    return cache.orders.get(cacheKey).data;
  }
  
  // 如果已经有一个相同cacheKey的请求正在进行，复用它
  if (cache.activeRequests.has(cacheKey)) {
    console.log(`订单缓存: 复用现有请求`, { key: cacheKey });
    return cache.activeRequests.get(cacheKey);
  }
  
  // 如果已经有正在进行的其他请求，等待该请求完成
  if (cache.isLoading) {
    return new Promise((resolve) => {
      console.log(`订单缓存: 等待其他请求完成`, { key: cacheKey });
      cache.pendingCallbacks.push(() => {
        // 请求完成后，再次检查缓存
        if (isCacheValid(cacheKey, maxAge)) {
          resolve(cache.orders.get(cacheKey).data);
        } else {
          // 如果新请求的参数与刚完成的不同，需要重新请求
          getOrdersData(params, true, maxAge).then(resolve);
        }
      });
    });
  }
  
  // 开始新的请求
  cache.isLoading = true;
  
  // 创建一个Promise用于跟踪请求
  const requestPromise = (async () => {
  try {
    const response = await fetchOrdersFromAPI(params);
    
    // 处理响应
    if (response && response.data) {
      // 更新缓存
      cache.orders.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });
      cache.lastUpdate = Date.now();
      
      // 处理等待的回调
      cache.pendingCallbacks.forEach(callback => callback());
      cache.pendingCallbacks = [];
      
      return response.data;
    } else {
      throw new Error(response?.data?.error || '获取订单数据失败');
    }
  } catch (error) {
    console.error('获取订单数据错误:', error);
    throw error;
  } finally {
    cache.isLoading = false;
      // 请求完成后从活跃请求列表中移除
      cache.activeRequests.delete(cacheKey);
    }
  })();
  
  // 将请求添加到活跃请求集合中
  cache.activeRequests.set(cacheKey, requestPromise);
  
  return requestPromise;
}

// 清除缓存
export function clearCache() {
  cache.orders.clear();
  cache.lastUpdate = null;
  cache.requestCount = 0;
  cache.cacheHits = 0;
  console.log('订单缓存: 已清除所有缓存');
}

// 获取缓存状态
export function getCacheStatus() {
  return {
    hasCache: cache.orders.size > 0,
    lastUpdate: cache.lastUpdate,
    cacheSize: cache.orders.size,
    requestCount: cache.requestCount,
    cacheHits: cache.cacheHits,
    hitRate: cache.requestCount > 0 ? (cache.cacheHits / cache.requestCount * 100).toFixed(2) + '%' : '0%'
  };
} 