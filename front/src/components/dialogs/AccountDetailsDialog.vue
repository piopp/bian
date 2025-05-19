<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`子账户详情: ${account ? account.email : ''}`"
    width="800px"
    :close-on-click-modal="false"
    :before-close="handleClose"
    v-optimize-layout
  >
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>
    
    <div v-else-if="account" class="account-details" v-optimize-layout>
      <!-- 基本信息卡片 -->
      <el-card class="detail-card" v-optimize-layout>
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-tag 
              :type="getAccountStatus(account).type"
              effect="dark"
            >
              {{ getAccountStatus(account).text }}
            </el-tag>
          </div>
        </template>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">子账户ID:</span>
            <span class="value">{{ account.id || account.subAccountId || account.subaccountId || '无ID信息' }}</span>
          </div>
          <div class="info-item">
            <span class="label">邮箱:</span>
            <span class="value">{{ account.email }}</span>
          </div>
          <div class="info-item">
            <span class="label">账户状态:</span>
            <el-tag :type="getAccountStatus(account).statusType" size="small">
              {{ getAccountStatus(account).statusText }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatDate(account.createTime) }}</span>
          </div>
          <div class="info-item">
            <span class="label">API配置:</span>
            <el-tag :type="account.hasApiKey ? 'success' : 'info'" size="small">
              {{ account.hasApiKey ? '已配置' : '未配置' }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">已启用功能:</span>
            <div class="features-list">
              <el-tag 
                v-if="hasFeature(account, 'margin')"
                size="small"
                class="feature-tag"
                type="success"
              >
                保证金交易
              </el-tag>
              <el-tag 
                v-if="hasFeature(account, 'futures')"
                size="small"
                class="feature-tag"
                type="warning"
              >
                期货交易
              </el-tag>
              <span v-if="!hasFeature(account, 'margin') && !hasFeature(account, 'futures')" class="no-features">
                无特殊功能
              </span>
            </div>
          </div>
        </div>
      </el-card>
      
      <!-- 资产信息卡片 -->
      <el-card class="detail-card" v-optimize-layout>
        <template #header>
          <div class="card-header">
            <span>资产信息</span>
            <el-button type="primary" size="small" @click="refreshAssets">
              <el-icon><refresh /></el-icon> 刷新
            </el-button>
          </div>
        </template>
        <div v-loading="assetsLoading" class="assets-section">
          <div v-if="assets.length > 0" class="assets-table">
            <el-table :data="assets" style="width: 100%" border v-optimize-layout>
              <el-table-column prop="asset" label="币种" width="80" />
              <el-table-column prop="free" label="可用余额" />
              <el-table-column prop="locked" label="锁定金额" />
              <el-table-column label="总计">
                <template #default="scope">
                  {{ (Number(scope.row.free) + Number(scope.row.locked)).toFixed(8) }}
                </template>
              </el-table-column>
            </el-table>
            
            <div class="summary-section">
              <div class="summary-item">
                <span class="label">总BTC价值:</span>
                <span class="value">{{ totalBtcValue }}</span>
              </div>
              <div class="summary-item">
                <span class="label">总USDT价值:</span>
                <span class="value">{{ totalUsdtValue }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="无资产数据" />
        </div>
      </el-card>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button 
          type="success" 
          @click="openUnifiedAccount"
          :disabled="!account"
        >
          统一账户管理
        </el-button>
        <el-button 
          type="danger" 
          @click="openDeleteDialog"
          :disabled="!account"
        >
          删除账户
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from 'axios'
import { debounce } from '../../utils/performance'

export default {
  name: 'AccountDetailsDialog',
  components: {
    Refresh
  },
  props: {
    // 对话框可见性
    modelValue: {
      type: Boolean,
      required: true
    },
    // 账户邮箱
    accountEmail: {
      type: String,
      default: null
    }
  },
  emits: ['update:modelValue', 'delete-account', 'open-unified-account'],
  setup(props, { emit }) {
    const loading = ref(false)
    const account = ref(null)
    const assets = ref([])
    const assetsLoading = ref(false)
    
    // 计算总BTC价值
    const totalBtcValue = computed(() => {
      if (account.value && account.value.btcVal) {
        return account.value.btcVal
      }
      return '0.00000000'
    })
    
    // 计算总USDT价值
    const totalUsdtValue = computed(() => {
      if (account.value && account.value.usdtVal) {
        return account.value.usdtVal
      }
      return '0.00'
    })
    
    // 计算对话框的可见性
    const dialogVisible = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })
    
    // 使用防抖处理数据加载
    const debouncedFetchAccountDetails = debounce(async (email) => {
      if (!email) return
      
      loading.value = true
      try {
        // 使用batch-details API获取子账户详情
        const response = await axios.post('/api/subaccounts/batch-details', {
          emails: [email],
          recvWindow: 10000
        })
        
        if (response.data.success) {
          // 首先尝试从accounts数组获取数据
          if (response.data.accounts && response.data.accounts.length > 0) {
            account.value = response.data.accounts[0]
          } 
          // 如果accounts数组不存在或为空，尝试从results数组获取
          else if (response.data.results && response.data.results.length > 0) {
            const result = response.data.results[0]
            if (result.success && result.details) {
              // 如果结果中包含details字段，使用它
              account.value = result.details
            } else if (result.success) {
              // 如果没有details但有其他字段，尝试构建账户对象
              account.value = {
                email: email,
                ...result
              }
            } else {
              ElMessage.error(`获取子账户详情失败: ${result.message || result.error || '未知错误'}`)
              account.value = null
            }
          } 
          // 如果data字段存在，尝试从中获取数据
          else if (response.data.data && response.data.data.length > 0) {
            const resultData = response.data.data[0]
            if (resultData.details) {
              account.value = resultData.details
            } else if (resultData.success) {
              account.value = {
                email: email,
                ...resultData
              }
            } else {
              ElMessage.error(`获取子账户详情失败: ${resultData.message || resultData.error || '未知错误'}`)
              account.value = null
            }
          } else {
            ElMessage.error('获取子账户详情失败: 返回数据格式异常')
            account.value = null
          }
        } else {
          ElMessage.error(`获取子账户详情失败: ${response.data.message || '未知错误'}`)
          account.value = null
        }
      } catch (error) {
        console.error('获取子账户详情出错:', error)
        ElMessage.error(`获取子账户详情失败: ${error.message || '未知错误'}`)
        account.value = null
      } finally {
        loading.value = false
      }
    }, 300)
    
    // 当accountEmail变化时，加载账户详情
    watch(() => props.accountEmail, (newEmail) => {
      if (newEmail) {
        debouncedFetchAccountDetails(newEmail)
      }
    })
    
    // 当对话框打开时，加载账户详情
    watch(() => props.modelValue, (newValue) => {
      if (newValue && props.accountEmail) {
        debouncedFetchAccountDetails(props.accountEmail)
      }
    })
    
    // 获取账户详情
    const fetchAccountDetails = async (email) => {
      await debouncedFetchAccountDetails(email)
    }
    
    // 刷新资产信息
    const refreshAssets = async () => {
      if (!account.value || !account.value.email) return
      
      assetsLoading.value = true
      try {
        const response = await axios.get(`/api/subaccounts/balance?email=${account.value.email}`)
        
        if (response.data.success) {
          assets.value = response.data.data || []
        } else {
          ElMessage.error(`获取资产信息失败: ${response.data.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取资产信息出错:', error)
        ElMessage.error(`获取资产信息失败: ${error.message || '未知错误'}`)
      } finally {
        assetsLoading.value = false
      }
    }
    
    // 关闭对话框
    const handleClose = () => {
      dialogVisible.value = false
    }
    
    // 打开删除对话框
    const openDeleteDialog = () => {
      if (!account.value || !account.value.email) {
        ElMessage.warning('账户信息不完整，无法删除')
        return
      }
      
      ElMessageBox.confirm(
        `确定要删除子账户 ${account.value.email} 吗？此操作不可恢复!`,
        '删除确认',
        {
          confirmButtonText: '确定删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
        .then(() => {
          emit('delete-account', account.value.email)
          dialogVisible.value = false
        })
        .catch(() => {
          // 用户取消删除，不执行任何操作
        })
    }
    
    // 打开统一账户管理
    const openUnifiedAccount = () => {
      if (!account.value || !account.value.email) {
        ElMessage.warning('账户信息不完整，无法打开统一账户管理')
        return
      }
      
      emit('open-unified-account', account.value)
      dialogVisible.value = false
    }
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '未知'
      
      try {
        const date = new Date(dateString)
        return date.toLocaleString()
      } catch (e) {
        return dateString
      }
    }
    
    // 获取账户状态
    const getAccountStatus = (account) => {
      if (!account) return { type: 'info', text: '未知', statusType: 'info', statusText: '未知' }
      
      // 检查账户状态
      const status = account.status || 'UNKNOWN'
      
      // 状态映射
      const statusMap = {
        'ENABLED': { type: 'success', text: '已启用', statusType: 'success', statusText: '已启用' },
        'DISABLED': { type: 'danger', text: '已禁用', statusType: 'danger', statusText: '已禁用' },
        'PENDING': { type: 'warning', text: '待处理', statusType: 'warning', statusText: '待处理' },
        'UNKNOWN': { type: 'info', text: '未知', statusType: 'info', statusText: '未知' }
      }
      
      return statusMap[status] || statusMap['UNKNOWN']
    }
    
    // 检查账户是否具有特定功能
    const hasFeature = (account, feature) => {
      if (!account) return false
      
      // 检查features数组
      if (account.features && Array.isArray(account.features)) {
        return account.features.includes(feature)
      }
      
      // 检查特定字段
      if (feature === 'margin' && account.isMarginEnabled) return true
      if (feature === 'futures' && account.isFuturesEnabled) return true
      
      return false
    }
    
    // 组件挂载时
    onMounted(() => {
      // 如果初始有账户邮箱，加载详情
      if (props.accountEmail) {
        debouncedFetchAccountDetails(props.accountEmail)
      }
    })
    
    return {
      loading,
      account,
      assets,
      assetsLoading,
      totalBtcValue,
      totalUsdtValue,
      dialogVisible,
      fetchAccountDetails,
      refreshAssets,
      handleClose,
      openDeleteDialog,
      openUnifiedAccount,
      formatDate,
      getAccountStatus,
      hasFeature
    }
  }
}
</script>

<style scoped>
.account-details {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-card {
  margin-bottom: 0;
  /* 减少布局抖动 */
  contain: content;
  will-change: transform;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 14px;
  color: #606266;
}

.value {
  font-size: 14px;
  color: #303133;
  word-break: break-all;
}

.features-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  margin-right: 4px;
}

.no-features {
  color: #909399;
  font-size: 14px;
}

.assets-section {
  min-height: 200px;
}

.assets-table {
  margin-bottom: 16px;
}

.summary-section {
  display: flex;
  justify-content: flex-end;
  gap: 24px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #EBEEF5;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-item .label {
  font-weight: 500;
}

.summary-item .value {
  font-weight: 600;
  color: #409EFF;
}

.loading-container {
  padding: 20px;
}

/* 添加过渡效果 */
.account-details {
  transition: opacity 0.3s ease;
}

/* 优化表格渲染 */
.el-table {
  transform: translateZ(0);
  backface-visibility: hidden;
}
</style> 