import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useSubaccountsStore } from '@/stores/subaccounts'
import { getCurrentUser } from '@/services/auth'

export default {
  name: 'AutoArbitrageDialog',
  props: {
    visible: {
      type: Boolean,
      required: true
    }
  },
  setup(props, { emit }) {
    const subaccountsStore = useSubaccountsStore()
    
    // 使用 store 中的状态
    const subaccounts = computed(() => subaccountsStore.subaccounts)
    const subaccountsWithApi = computed(() => subaccountsStore.getSubaccountsWithApi())
    
    // 修改 loadSubaccounts 函数
    const loadSubaccounts = async () => {
      try {
        const user = getCurrentUser()
        if (!user || !user.token) {
          throw new Error('未登录或登录已过期')
        }
        
        await subaccountsStore.fetchSubaccounts()
      } catch (error) {
        console.error('加载子账户出错:', error)
        ElMessage.error('加载子账户失败: ' + error.message)
      }
    }
    
    // 监听对话框显示状态
    watch(() => props.visible, (newVal) => {
      if (newVal) {
        loadSubaccounts()
      }
    })
    
    return {
      subaccounts,
      subaccountsWithApi,
      loadSubaccounts,
    }
  }
} 