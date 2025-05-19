import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCurrentUser } from '@/services/auth'

/**
 * 主账号信息存储
 * 用于全局存储主账号ID和邮箱信息
 */
export const useUserStore = defineStore('user', () => {
  // 状态
  const mainAccountId = ref(null)
  const mainAccountEmail = ref('')
  const isLoading = ref(false)
  const lastUpdateTime = ref(null)
  const errorMessage = ref('')

  // 计算属性
  const hasMainAccount = computed(() => !!mainAccountId.value && !!mainAccountEmail.value)

  // 初始化函数 - 从localStorage加载数据
  const initialize = () => {
    try {
      // 从localStorage加载数据
      const storedData = localStorage.getItem('mainAccount')
      if (storedData) {
        const parsedData = JSON.parse(storedData)
        mainAccountId.value = parsedData.id || null
        mainAccountEmail.value = parsedData.email || ''
        lastUpdateTime.value = parsedData.lastUpdateTime || null
        console.log('从本地存储加载主账号信息:', parsedData)
      } else {
        console.log('本地存储中无主账号信息')
      }

      // 如果没有数据或数据已过期，尝试从当前用户信息获取
      const currentUser = getCurrentUser()
      if (currentUser && currentUser.id && (!mainAccountId.value || !lastUpdateTime.value)) {
        mainAccountId.value = currentUser.id
        mainAccountEmail.value = currentUser.email || currentUser.username || ''
        lastUpdateTime.value = Date.now()
        saveToLocalStorage()
        console.log('从当前用户信息更新主账号:', { id: mainAccountId.value, email: mainAccountEmail.value })
      }
    } catch (error) {
      console.error('初始化主账号信息失败:', error)
      errorMessage.value = '加载主账号信息失败'
    }
  }

  // 保存到localStorage
  const saveToLocalStorage = () => {
    try {
      localStorage.setItem('mainAccount', JSON.stringify({
        id: mainAccountId.value,
        email: mainAccountEmail.value,
        lastUpdateTime: lastUpdateTime.value
      }))
    } catch (error) {
      console.error('保存主账号信息到本地存储失败:', error)
    }
  }

  // 从API获取主账号信息
  const fetchMainAccountInfo = async () => {
    if (isLoading.value) return

    isLoading.value = true
    errorMessage.value = ''

    try {
      const currentUser = getCurrentUser()
      if (!currentUser || !currentUser.token) {
        throw new Error('未登录或登录已过期')
      }

      const response = await fetch('/api/main-account/info', {
        headers: {
          'Authorization': `Bearer ${currentUser.token}`
        }
      })

      if (!response.ok) {
        throw new Error(`获取主账号信息失败: ${response.status}`)
      }

      const result = await response.json()

      if (result.success && result.data) {
        mainAccountId.value = result.data.id || currentUser.id
        mainAccountEmail.value = result.data.email || result.data.username || currentUser.email || ''
        lastUpdateTime.value = Date.now()
        saveToLocalStorage()
        console.log('成功获取主账号信息:', result.data)
      } else {
        throw new Error(result.error || '无法获取主账号数据')
      }
    } catch (error) {
      console.error('获取主账号信息失败:', error)
      errorMessage.value = error.message || '获取主账号信息失败'
      
      // 如果API失败但有当前用户信息，使用当前用户信息
      const currentUser = getCurrentUser()
      if (currentUser && currentUser.id && (!mainAccountId.value || !mainAccountEmail.value)) {
        mainAccountId.value = currentUser.id
        mainAccountEmail.value = currentUser.email || currentUser.username || ''
        lastUpdateTime.value = Date.now()
        saveToLocalStorage()
        console.log('从当前用户信息更新主账号:', { id: mainAccountId.value, email: mainAccountEmail.value })
      }
    } finally {
      isLoading.value = false
    }
  }

  // 手动设置主账号信息
  const setMainAccount = (id, email) => {
    if (id) mainAccountId.value = id
    if (email) mainAccountEmail.value = email
    lastUpdateTime.value = Date.now()
    saveToLocalStorage()
    console.log('手动设置主账号信息:', { id: mainAccountId.value, email: mainAccountEmail.value })
  }

  // 清除主账号信息
  const clearMainAccount = () => {
    mainAccountId.value = null
    mainAccountEmail.value = ''
    lastUpdateTime.value = null
    localStorage.removeItem('mainAccount')
    console.log('已清除主账号信息')
  }

  // 初始化时加载数据
  initialize()

  return {
    // 状态
    mainAccountId,
    mainAccountEmail,
    isLoading,
    lastUpdateTime,
    errorMessage,
    
    // 计算属性
    hasMainAccount,
    
    // 方法
    fetchMainAccountInfo,
    setMainAccount,
    clearMainAccount
  }
}) 