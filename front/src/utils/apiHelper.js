/**
 * API 结果解析工具
 * 用于统一处理后端 API 返回的结果格式
 */

/**
 * 解析 API 返回结果
 * @param {Object} response - Axios 响应对象
 * @returns {Object} 标准化的结果对象，包含 success, data 和 error 字段
 */
export function parseApiResult(response) {
  try {
    // 检查 response 及其 data 是否存在
    if (!response || !response.data) {
      return { success: false, error: '接口返回数据格式错误', data: null };
    }

    const data = response.data;
    
    // 处理标准化的结果格式
    if (data.success !== undefined) {
      return {
        success: data.success,
        data: data.data || data.result,
        error: data.error || data.message
      };
    }
    
    // 处理可能的其他格式
    if (data.code !== undefined) {
      // 一些 API 可能使用 code=0 表示成功
      const isSuccess = data.code === 0 || data.code === 200;
      return {
        success: isSuccess,
        data: data.data || data.result,
        error: isSuccess ? null : (data.message || data.error || `错误码: ${data.code}`)
      };
    }
    
    // 默认情况，视为成功
    return {
      success: true,
      data: data,
      error: null
    };
  } catch (err) {
    console.error('解析 API 结果时出错:', err);
    return {
      success: false,
      data: null,
      error: '处理接口返回数据失败: ' + err.message
    };
  }
}

/**
 * 处理 API 请求异常
 * @param {Error} error - Axios 捕获的错误
 * @returns {Object} 标准化的错误信息
 */
export function handleApiError(error) {
  let errorMessage = '未知错误';
  
  if (error.response) {
    // 服务器响应了，但状态码不在 2xx 范围
    const status = error.response.status;
    const responseData = error.response.data || {};
    
    if (status === 401) {
      errorMessage = '未授权，请重新登录';
    } else if (status === 403) {
      errorMessage = '权限不足，禁止访问';
    } else if (status === 404) {
      errorMessage = '请求的资源不存在';
    } else if (status === 500) {
      errorMessage = '服务器内部错误';
    } else {
      errorMessage = responseData.message || responseData.error || `请求错误 (${status})`;
    }
  } else if (error.request) {
    // 请求已发送但未收到响应
    errorMessage = '服务器无响应，请检查网络连接';
  } else {
    // 请求设置时发生了错误
    errorMessage = error.message || '请求设置错误';
  }
  
  return {
    success: false,
    error: errorMessage,
    data: null
  };
} 