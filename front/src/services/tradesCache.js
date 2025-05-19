import axios from 'axios';
import { getCurrentUser } from './auth';

// 缓存对象
const cache = {
  trades: new Map(), // 按唯一键存储交易数据
  lastUpdate: null,  // 最后更新时间
  isLoading: false,  // 是否正在加载
  pendingCallbacks: [] // 等待数据的回调函数列表
};

// 生成缓存键
function generateCacheKey(params) {
  const { emails, symbol, contractType, startTime, limit } = params;
  const emailsKey = emails ? emails.sort().join(',') : '';
  return `${emailsKey}|${symbol || ''}|${contractType || 'UM'}|${startTime || ''}|${limit || '500'}`;
}

// 检查缓存是否有效
function isCacheValid(key, maxAge = 30000) { // 默认30秒有效期
  const entry = cache.trades.get(key);
  if (!entry) return false;
  
  const now = Date.now();
  return (now - entry.timestamp) < maxAge;
}

// 从API获取交易数据
async function fetchTradesFromAPI(params) {
  const user = getCurrentUser();
  if (!user || !user.token) {
    throw new Error('用户未登录或token无效');
  }
  
  const response = await axios.post('/api/subaccounts/futures-trades', params, {
    headers: {
      'Authorization': `Bearer ${user.token}`
    }
  });
  
  return response;
}

// 获取交易历史数据(带缓存)
export async function getTradesData(params, forceRefresh = false, maxAge = 30000) {
  const cacheKey = generateCacheKey(params);
  
  // 如果缓存有效且不强制刷新，直接返回缓存的数据
  if (!forceRefresh && isCacheValid(cacheKey, maxAge)) {
    return cache.trades.get(cacheKey).data;
  }
  
  // 如果已经有正在进行的请求，等待该请求完成
  if (cache.isLoading) {
    return new Promise((resolve) => {
      cache.pendingCallbacks.push(() => {
        // 请求完成后，再次检查缓存
        if (isCacheValid(cacheKey, maxAge)) {
          resolve(cache.trades.get(cacheKey).data);
        } else {
          // 如果新请求的参数与刚完成的不同，需要重新请求
          getTradesData(params, true, maxAge).then(resolve);
        }
      });
    });
  }
  
  // 开始新的请求
  cache.isLoading = true;
  
  try {
    const response = await fetchTradesFromAPI(params);
    
    // 处理响应
    if (response && response.data && response.data.success) {
      // 更新缓存
      cache.trades.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });
      cache.lastUpdate = Date.now();
      
      // 处理等待的回调
      cache.pendingCallbacks.forEach(callback => callback());
      cache.pendingCallbacks = [];
      
      return response.data;
    } else {
      throw new Error(response?.data?.error || '获取交易数据失败');
    }
  } catch (error) {
    console.error('获取交易数据错误:', error);
    throw error;
  } finally {
    cache.isLoading = false;
  }
}

// 清除缓存
export function clearCache() {
  cache.trades.clear();
  cache.lastUpdate = null;
}

// 获取缓存状态
export function getCacheStatus() {
  return {
    hasCache: cache.trades.size > 0,
    lastUpdate: cache.lastUpdate,
    cacheSize: cache.trades.size
  };
} 