/**
 * 认证服务
 */

// 使用相对路径代替硬编码URL，这样请求会被vue.config.js中的代理配置处理
const API_URL = '/api';

// 登录函数，连接到后端API
export const login = async (username, password) => {
  try {
    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || '登录失败');
    }

    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.error || '登录失败');
    }
    
    // 从返回数据中获取用户信息
    const userData = {
      username: result.data.username,
      id: result.data.id,
      userId: result.data.id,
      // 添加令牌，如果后端返回了令牌则使用，否则使用用户ID作为简单令牌
      token: result.data.token || `user_${result.data.id}`,
      // 添加过期时间（默认30天）
      exp: Date.now() + 2592000000
    };
    
    // 存储用户信息到localStorage
    localStorage.setItem('user', JSON.stringify(userData));
    
    return userData;
  } catch (error) {
    throw new Error(error.message || '登录请求失败，请检查网络连接');
  }
};

// 登出函数
export const logout = () => {
  localStorage.removeItem('user');
};

// 获取当前用户
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  if (!userStr) return null;
  
  try {
    const user = JSON.parse(userStr);
    
    // 检查令牌是否已过期
    if (user.exp && user.exp < Date.now()) {
      localStorage.removeItem('user');
      return null;
    }
    
    // 确保用户ID存在
    if (!user.id && user.userId) {
      user.id = user.userId;
    } else if (!user.id && !user.userId) {
      // 添加默认ID
      user.id = 1; 
    }
    
    return user;
  } catch (error) {
    return null;
  }
};

// 检查用户是否已登录
export const isAuthenticated = () => {
  return getCurrentUser() !== null;
};

// 获取认证头信息，用于API请求
export const getAuthHeader = () => {
  const user = getCurrentUser();
  if (user && user.token) {
    return { 'Authorization': `Bearer ${user.token}` };
  }
  return {};
}; 