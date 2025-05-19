/**
 * 时间同步服务
 * 提供与币安服务器的时间同步功能
 */

import { getCurrentUser } from './auth';

// 时间偏移量(毫秒)
let timeOffset = 0;
// 上次同步时间
let lastSyncTime = null;
// 同步状态
let syncStatus = {
  success: false,
  message: '未同步'
};

// API基础URL
const API_URL = '/api';

/**
 * 与币安服务器同步时间
 * @returns {Promise<Object>} 同步结果
 */
export const syncWithServer = async () => {
  try {
    const startTime = Date.now();
    
    // 获取当前用户信息
    const user = getCurrentUser();
    if (!user) {
      throw new Error('请先登录');
    }
    
    // 调用后端时间同步接口
    const response = await fetch(`${API_URL}/server/sync_time`, {
      headers: {
        'Authorization': `Bearer ${user.token}`
      }
    });
    const data = await response.json();
    
    // 计算网络延迟
    const endTime = Date.now();
    const networkLatency = Math.round((endTime - startTime) / 2);
    
    if (!data.success) {
      // 如果币安同步失败，尝试使用普通服务器时间
      const fallbackResponse = await fetch(`${API_URL}/server/time`, {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });
      const fallbackData = await fallbackResponse.json();
      
      if (fallbackData.success) {
        // 使用服务器时间
        const serverTime = fallbackData.data.timestamp;
        timeOffset = serverTime - Date.now();
        lastSyncTime = new Date();
        
        syncStatus = {
          success: true, 
          source: 'server',
          offset: timeOffset,
          latency: 0,
          message: '与服务器时间同步成功(后备)',
          timestamp: lastSyncTime
        };
        
        return syncStatus;
      } else {
        throw new Error(data.error || '同步币安服务器时间失败');
      }
    }
    
    // 获取同步结果
    const syncData = data.data;
    timeOffset = syncData.offset;
    
    // 更新同步状态
    lastSyncTime = new Date();
    syncStatus = {
      success: true,
      source: 'binance',
      offset: timeOffset,
      latency: networkLatency,
      message: '与币安服务器时间同步成功',
      timestamp: lastSyncTime
    };
    
    return syncStatus;
  } catch (error) {
    console.error('时间同步失败:', error);
    
    syncStatus = {
      success: false,
      message: `同步失败: ${error.message || '未知错误'}`,
      timestamp: new Date()
    };
    
    return syncStatus;
  }
};

/**
 * 获取校正后的当前时间戳(毫秒)
 * @returns {number} 校正后的时间戳
 */
export const getCorrectedTime = () => {
  return Date.now() + timeOffset;
};

/**
 * 获取校正后的当前Date对象
 * @returns {Date} 校正后的Date对象
 */
export const getCorrectedDate = () => {
  return new Date(getCorrectedTime());
};

/**
 * 获取上次同步时间
 * @returns {Date|null} 上次同步时间
 */
export const getLastSyncTime = () => {
  return lastSyncTime;
};

/**
 * 获取同步状态
 * @returns {Object} 同步状态
 */
export const getSyncStatus = () => {
  return {...syncStatus};
};

/**
 * 检查是否需要同步(超过30分钟未同步)
 * @returns {boolean} 是否需要同步
 */
export const needsSync = () => {
  if (!lastSyncTime) return true;
  
  const thirtyMinutes = 30 * 60 * 1000;
  return Date.now() - lastSyncTime.getTime() > thirtyMinutes;
};

/**
 * 初始化时间同步(在应用启动时调用)
 * @returns {Promise<void>}
 */
export const initTimeSync = async () => {
  try {
    await syncWithServer();
    
    // 每30分钟自动同步一次
    setInterval(async () => {
      console.log('自动执行时间同步...');
      await syncWithServer();
    }, 30 * 60 * 1000);
  } catch (error) {
    console.error('初始化时间同步失败:', error);
  }
}; 