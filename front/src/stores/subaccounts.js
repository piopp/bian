import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { getCurrentUser } from '@/services/auth'
import { ElMessage } from 'element-plus'

// 添加立即执行的日志，确认文件被加载
console.log('子账号Store被加载')

// 添加一个基础的全局错误处理函数
window.onerror = function(message, source, lineno, colno, error) {
  console.error('全局JS错误:', message, 'at', source, lineno, colno, error);
  return false;
};

// 安全地设置拦截器
console.log('设置Axios拦截器')
try {
  axios.interceptors.response.use(
    response => {
      if (response.config.url.includes('/api/subaccounts')) {
        console.log(`API响应 (${response.config.url}):`, response.data)
      }
      return response
    },
    error => {
      console.error('API请求失败:', error.message)
      return Promise.reject(error)
    }
  )
  console.log('Axios拦截器设置完成')
} catch (e) {
  console.error('设置拦截器失败:', e)
}

// 导出Store定义
export const useSubaccountsStore = defineStore('subaccounts', () => {
  console.log('子账号Store初始化中')
  
  // 初始化状态
  const subaccounts = ref([])
  const isLoading = ref(false)
  const lastFetchTime = ref(null)
  const CACHE_DURATION = 5 * 60 * 1000 // 5分钟缓存
  const apiError = ref(null) // 记录API错误
  console.log('子账号Store状态初始化完成')

  // 标准化子账号数据格式
  const standardizeAccountData = (account) => {
    if (!account) return null;
    
    // 打印完整的原始数据，用于调试
    console.log('原始账号数据:', account);
    
    // 创建一个标准化的账号对象
    return {
      email: account.email,
      // API字段可能是api_key或apiKey
      apiKey: account.api_key || account.apiKey || '',
      apiSecret: account.api_secret || account.apiSecret || '',
      // 使用email作为名称，如果没有其他名称字段
      name: account.name || account.email,
      // 状态字段标准化
      status: account.status || 'ACTIVE',
      // 账号类型字段标准化
      accountType: account.accountType || account.account_type || 'VIRTUAL',
      // 功能列表
      features: account.features || [],
      // hasApiKey判断逻辑：
      // 1. 直接使用has_api_key字段（如果存在）
      // 2. 如果api_key存在且非空，则为true
      // 3. 如果api_secret_masked存在且非空，则为true
      hasApiKey: account.has_api_key === true || 
                 !!(account.api_key) || 
                 !!(account.api_secret_masked) ||
                 !!(account.apiKey),
      // 杠杆相关字段
      is_margin_enabled: account.is_margin_enabled || false,
      // 时间字段标准化，API可能返回createTime或create_time
      create_time: account.createTime || account.create_time || Date.now(),
      // 其他详情字段
      margin_details: account.margin_details || null,
      // 保留原始数据
      raw: { ...account }
    };
  };

  // 获取子账号列表函数
  const fetchSubaccounts = async (forceRefresh = false) => {
    console.log('fetchSubaccounts被调用, forceRefresh =', forceRefresh)
    
    // 检查是否使用缓存
    const now = Date.now()
    if (!forceRefresh && lastFetchTime.value && (now - lastFetchTime.value < CACHE_DURATION)) {
      console.log('使用缓存数据，不发起新请求')
      return subaccounts.value
    }

    // 显示加载状态
    console.log('开始加载子账号数据')
    isLoading.value = true
    apiError.value = null // 重置错误状态
    
    try {
      // 获取用户信息
      const user = getCurrentUser()
      console.log('当前用户状态:', user ? '已登录' : '未登录')
      
      if (!user || !user.token) {
        console.error('未登录或登录已过期')
        throw new Error('未登录或登录已过期')
      }

      const userId = user.id
      console.log('当前用户ID:', userId)

      // API获取子账号流程开始
      console.log('=== 子账号数据获取流程开始 ===')
      
      // 1. 尝试获取API设置
      console.log('1. 尝试从/api/subaccounts/api-export获取数据')
      let hasApiAccounts = false
      
      try {
        const apiSettingsResponse = await axios.get('/api/subaccounts/api-export', {
          params: { user_id: userId }, // 添加用户ID
          headers: { 'Authorization': `Bearer ${user.token}` }
        })
        
        console.log('API设置响应成功:', apiSettingsResponse.data.success)
        
        if (apiSettingsResponse.data.success) {
          const apiSettings = apiSettingsResponse.data.data || {}
          let apiSettingsArray = []
          
          // 添加日志输出查看原始数据
          console.log('API设置响应类型:', typeof apiSettings)
          console.log('API设置是否为数组:', Array.isArray(apiSettings))
          console.log('原始API设置数据:', JSON.stringify(apiSettings).substring(0, 500) + '...')
          
          // 处理不同格式的API设置返回
          if (Array.isArray(apiSettings)) {
            // 后端直接返回了数组
            apiSettingsArray = apiSettings
            console.log('API设置数组长度:', apiSettings.length)
            if (apiSettings.length > 0) {
              console.log('API设置第一个元素:', apiSettings[0])
            }
          } else if (typeof apiSettings === 'object') {
            // 如果是对象格式 {email: {apiKey: xxx, ...}}
            apiSettingsArray = Object.entries(apiSettings).map(([email, settings]) => ({
              email,
              api_key: settings.api_key || settings.apiKey || '',
              ...settings
            }))
          }
          
          console.log('API设置条目数量:', apiSettingsArray.length)
          
          if (apiSettingsArray.length > 0) {
            // 转换数据结构
            subaccounts.value = apiSettingsArray.map(api => standardizeAccountData(api));
            
            hasApiAccounts = true;
            lastFetchTime.value = now;
            console.log('成功从API设置构建子账号列表, 数量:', subaccounts.value.length);
          }
        }
      } catch (apiError) {
        console.error('获取API设置失败:', apiError.message)
      }

      // 2. 如果API设置没有数据，尝试子账号列表API
      if (!hasApiAccounts) {
        console.log('2. 从API设置没有获取到数据，尝试/api/subaccounts')
        
        try {
          const response = await axios.get('/api/subaccounts', {
            params: { user_id: userId }, // 使用用户ID
            headers: { 'Authorization': `Bearer ${user.token}` }
          })
          
          console.log('子账号API响应成功:', response.data.success)
          
          if (response.data.success) {
            const data = response.data.data || {}
            // 后端API可能直接返回子账号数组，或者包含在subaccounts字段中
            let subaccountsData = data.subaccounts || data || []
            
            // 如果后端直接返回了数组
            if (Array.isArray(response.data.data)) {
              subaccountsData = response.data.data
            }
            
            // 添加日志输出查看原始数据
            console.log('原始子账号数据类型:', Array.isArray(subaccountsData) ? 'Array' : typeof subaccountsData)
            console.log('原始子账号数据长度:', Array.isArray(subaccountsData) ? subaccountsData.length : 'N/A')
            console.log('原始子账号数据示例:', JSON.stringify(subaccountsData.slice(0, 2)).substring(0, 500) + '...')
            
            if (Array.isArray(subaccountsData)) {
              subaccounts.value = subaccountsData.map(account => standardizeAccountData(account))
              
              lastFetchTime.value = now
              console.log('成功从子账号API构建列表, 数量:', subaccounts.value.length)
            } else {
              console.error('子账号API返回的数据不是数组:', typeof subaccountsData)
            }
          }
        } catch (listError) {
          console.error('获取子账号列表失败:', listError.message)
          if (!hasApiAccounts) {
            throw listError
          }
        }
      }

      // 3. 尝试丰富子账号API信息
      if (subaccounts.value.length > 0) {
        console.log('3. 尝试丰富子账号API信息')
        
        try {
          const apiSettingsResponse = await axios.get('/api/subaccounts/api-export', {
            params: { user_id: userId }, // 添加用户ID
            headers: { 'Authorization': `Bearer ${user.token}` }
          })
          
          if (apiSettingsResponse.data.success) {
            const apiSettings = apiSettingsResponse.data.data || {}
            let apiSettingsArray = []
            
            // 处理不同格式的API设置返回
            if (Array.isArray(apiSettings)) {
              apiSettingsArray = apiSettings
            } else if (typeof apiSettings === 'object') {
              apiSettingsArray = Object.entries(apiSettings).map(([email, settings]) => ({
                email,
                api_key: settings.api_key || settings.apiKey || '',
                ...settings
              }))
            }
            
            console.log('丰富API信息, 收到API设置数量:', apiSettingsArray.length)
            
            subaccounts.value = subaccounts.value.map(account => {
              const apiInfo = apiSettingsArray.find(api => api.email === account.email) || {};
              // 合并现有账号信息和API信息
              const mergedData = {
                ...account,
                apiKey: apiInfo.api_key || apiInfo.apiKey || account.apiKey || '',
                hasApiKey: apiInfo.has_api_key === true || !!(apiInfo.api_key || apiInfo.apiKey || account.apiKey)
              };
              // 重新标准化确保所有字段格式一致
              return standardizeAccountData(mergedData);
            });
          }
        } catch (apiError) {
          console.error('丰富API信息失败:', apiError.message)
        }
      }
      
      // 4. 尝试获取杠杆信息，但不阻塞整个流程
      if (subaccounts.value.length > 0) {
        console.log('4. 尝试获取每个子账号的杠杆状态')
        
        // 首先检查主账号API是否可用
        let isMainApiAvailable = true
        try {
          // 尝试查询一个常规API接口来测试主账号API状态
          const testResponse = await axios.get('/api/account/status', {
            params: { user_id: userId }, // 添加用户ID
            headers: { 'Authorization': `Bearer ${user.token}` }
          })
          
          if (!testResponse.data.success && testResponse.data.error && 
              testResponse.data.error.includes('主账号API未配置')) {
            isMainApiAvailable = false
            console.warn('主账号API未配置，将跳过杠杆状态查询')
            apiError.value = '主账号API未配置，某些功能可能无法使用'
          }
        } catch (error) {
          // 如果出现明确的API未配置错误，设置标志
          if (error.response && error.response.data && 
              error.response.data.error && error.response.data.error.includes('主账号API未配置')) {
            isMainApiAvailable = false
            console.warn('主账号API未配置，将跳过杠杆状态查询')
            apiError.value = '主账号API未配置，某些功能可能无法使用'
          }
        }
        
        // 只有在主账号API可用的情况下才查询杠杆状态
        if (isMainApiAvailable) {
          // 并行处理所有账号的查询以提高效率
          const promises = subaccounts.value.map(async (account) => {
            try {
              // 查询杠杆账户详情
              const marginResponse = await axios.post('/api/subaccounts/margin-account', {
                email: account.email,
                user_id: userId // 添加用户ID
              }, {
                headers: { 'Authorization': `Bearer ${user.token}` }
              })
              
              if (marginResponse.data.success) {
                account.is_margin_enabled = marginResponse.data.data.marginEnabled || false
                account.margin_details = marginResponse.data.data
              }
              
              // 查询子账号状态
              const statusResponse = await axios.post('/api/subaccounts/status', {
                email: account.email,
                user_id: userId // 添加用户ID
              }, {
                headers: { 'Authorization': `Bearer ${user.token}` }
              })
              
              if (statusResponse.data.success && statusResponse.data.data) {
                const statusData = statusResponse.data.data
                if (statusData.status) {
                  account.status = statusData.status
                } else if (statusData.isActive === false) {
                  account.status = 'INACTIVE'
                } else if (statusData.isFreeze === true) {
                  account.status = 'FREEZE'
                }
              }
            } catch (error) {
              console.error(`查询账号 ${account.email} 状态失败:`, error)
              
              // 如果是API未配置错误，保存错误信息并停止后续查询
              if (error.response && error.response.data && 
                  error.response.data.error && error.response.data.error.includes('主账号API未配置')) {
                apiError.value = '主账号API未配置，某些功能可能无法使用'
                throw new Error('API_NOT_CONFIGURED') // 这将中断Promise.all
              }
            }
            return account
          })
          
          try {
            await Promise.allSettled(promises) // 使用Promise.allSettled确保即使有错误也会处理所有promise
          } catch (error) {
            if (error.message === 'API_NOT_CONFIGURED') {
              console.warn('由于API未配置，停止杠杆状态查询')
            } else {
              console.error('批量查询杠杆状态时发生错误:', error)
            }
          }
        } else {
          // 如果主账号API不可用，设置所有账号为默认状态
          subaccounts.value.forEach(account => {
            account.is_margin_enabled = false
            account.margin_details = null
          })
        }
      }
      
      console.log('=== 子账号数据获取流程结束, 最终子账号数量:', subaccounts.value.length, ' ===')
      
      return subaccounts.value
    } catch (error) {
      console.error('获取子账号列表失败:', error.message)
      ElMessage.error('获取子账号列表失败: ' + error.message)
      subaccounts.value = []
      return []
    } finally {
      isLoading.value = false
      console.log('加载状态设置为false')
    }
  }

  // 获取带API的子账号
  const getSubaccountsWithApi = () => {
    console.log('获取带有API的子账号, 当前总数:', 
                Array.isArray(subaccounts.value) ? subaccounts.value.length : '非数组')
    
    if (!Array.isArray(subaccounts.value)) {
      console.warn('子账号列表不是数组')
      return []
    }
    
    const filtered = subaccounts.value.filter(account => 
      account && account.apiKey && account.apiKey.trim() !== ''
    )
    
    console.log('带API子账号数量:', filtered.length)
    return filtered
  }

  // 获取没有API的子账号
  const getSubaccountsWithoutApi = () => {
    if (!Array.isArray(subaccounts.value)) return []
    
    return subaccounts.value.filter(account => 
      !account || !account.apiKey || account.apiKey.trim() === ''
    )
  }

  // 获取API错误信息
  const getApiError = () => {
    return apiError.value
  }

  // 返回Store对象
  console.log('子账号Store初始化完成')
  return {
    subaccounts,
    isLoading,
    apiError,
    fetchSubaccounts,
    getSubaccountsWithApi,
    getSubaccountsWithoutApi,
    getApiError
  }
})

console.log('子账号Store模块加载完成') 