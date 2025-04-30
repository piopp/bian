<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`子账户详情: ${account ? account.name : ''}`"
    width="800px"
    :close-on-click-modal="false"
    :before-close="handleClose"
  >
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>
    
    <div v-else-if="account" class="account-details">
      <!-- 基本信息卡片 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-tag 
              :type="account.status === 'active' ? 'success' : 'danger'"
              effect="dark"
            >
              {{ account.status === 'active' ? '活跃' : '禁用' }}
            </el-tag>
          </div>
        </template>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">子账户ID:</span>
            <span class="value">{{ account.id }}</span>
          </div>
          <div class="info-item">
            <span class="label">名称:</span>
            <span class="value">{{ account.name }}</span>
          </div>
          <div class="info-item">
            <span class="label">账户类型:</span>
            <el-tag :type="account.type === 'spot' ? 'success' : 'warning'" size="small">
              {{ account.type === 'spot' ? '现货账户' : '期货账户' }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatDate(account.createdAt) }}</span>
          </div>
          <div class="info-item">
            <span class="label">最后活动:</span>
            <span class="value">{{ formatDate(account.lastActive || account.createdAt) }}</span>
          </div>
          <div class="info-item">
            <span class="label">启用的功能:</span>
            <div class="features-list">
              <el-tag 
                v-for="feature in account.features || []" 
                :key="feature"
                size="small"
                class="feature-tag"
              >
                {{ featureLabels[feature] || feature }}
              </el-tag>
              <span v-if="!account.features || account.features.length === 0" class="no-features">
                无特殊功能
              </span>
            </div>
          </div>
        </div>
      </el-card>
      
      <!-- 资产信息卡片 -->
      <el-card class="detail-card">
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
            <el-table :data="assets" style="width: 100%" border>
              <el-table-column prop="asset" label="币种" width="80" />
              <el-table-column prop="free" label="可用余额" />
              <el-table-column prop="locked" label="锁定金额" />
              <el-table-column prop="total" label="总计">
                <template #default="scope">
                  {{ (Number(scope.row.free) + Number(scope.row.locked)).toFixed(8) }}
                </template>
              </el-table-column>
              <el-table-column prop="btcValue" label="BTC价值" />
              <el-table-column prop="usdtValue" label="USDT价值" />
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
      
      <!-- 操作记录卡片 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>最近操作记录</span>
            <el-button type="primary" size="small" @click="loadMoreLogs">
              加载更多
            </el-button>
          </div>
        </template>
        <div v-loading="logsLoading" class="logs-section">
          <div v-if="activityLogs.length > 0" class="logs-list">
            <el-timeline>
              <el-timeline-item
                v-for="log in activityLogs"
                :key="log.id"
                :timestamp="formatDateTime(log.timestamp)"
                :type="logTypeMap[log.type] || 'primary'"
              >
                <h4>{{ log.title }}</h4>
                <p>{{ log.description }}</p>
                <el-tag v-if="log.status" size="small" :type="log.status === 'success' ? 'success' : 'danger'">
                  {{ log.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </el-timeline-item>
            </el-timeline>
          </div>
          <el-empty v-else description="无操作记录" />
        </div>
      </el-card>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button type="primary" @click="openTransferDialog">转账</el-button>
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
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

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
    // 账户ID
    accountId: {
      type: [Number, String],
      default: null
    }
  },
  emits: ['update:modelValue', 'delete-account', 'transfer'],
  setup(props, { emit }) {
    const loading = ref(false)
    const account = ref(null)
    const assets = ref([])
    const assetsLoading = ref(false)
    const activityLogs = ref([])
    const logsLoading = ref(false)
    const logsPage = ref(1)
    
    // 特性标签映射
    const featureLabels = {
      margin: '保证金交易',
      futures: '期货交易',
      options: '期权交易',
      otc: '场外交易',
      transfer: '内部转账',
      api: 'API访问'
    }
    
    // 日志类型映射到Element UI的类型
    const logTypeMap = {
      transfer: 'primary',
      trade: 'success',
      deposit: 'success',
      withdraw: 'warning',
      api: 'info',
      system: 'info',
      error: 'danger'
    }
    
    // 计算总BTC价值
    const totalBtcValue = computed(() => {
      const total = assets.value.reduce((sum, asset) => sum + Number(asset.btcValue || 0), 0)
      return total.toFixed(8)
    })
    
    // 计算总USDT价值
    const totalUsdtValue = computed(() => {
      const total = assets.value.reduce((sum, asset) => sum + Number(asset.usdtValue || 0), 0)
      return total.toFixed(2)
    })
    
    // 计算对话框的可见性
    const dialogVisible = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })
    
    // 当accountId变化时，加载账户详情
    watch(() => props.accountId, async (newId, oldId) => {
      if (newId && newId !== oldId) {
        await fetchAccountDetails(newId)
      }
    })
    
    // 当对话框打开时，加载账户详情
    watch(() => props.modelValue, async (newValue) => {
      if (newValue && props.accountId) {
        await fetchAccountDetails(props.accountId)
      }
    })
    
    // 获取账户详情
    const fetchAccountDetails = async (id) => {
      loading.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 800))
        
        // 模拟数据
        account.value = {
          id: id,
          name: `sub_account_${id}`,
          type: Math.random() > 0.5 ? 'spot' : 'futures',
          createdAt: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
          lastActive: new Date(Date.now() - Math.floor(Math.random() * 1000000000)),
          status: Math.random() > 0.2 ? 'active' : 'disabled',
          features: sampleFeatures()
        }
        
        // 加载资产和日志
        await Promise.all([
          fetchAssets(),
          fetchActivityLogs()
        ])
      } catch (error) {
        console.error('获取账户详情失败:', error)
        ElMessage.error('获取账户详情失败，请重试')
      } finally {
        loading.value = false
      }
    }
    
    // 获取资产数据
    const fetchAssets = async () => {
      if (!account.value) return
      
      assetsLoading.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 600))
        
        // 模拟数据
        assets.value = [
          {
            asset: 'BTC',
            free: (Math.random() * 0.5).toFixed(8),
            locked: (Math.random() * 0.05).toFixed(8),
            btcValue: (Math.random() * 0.5).toFixed(8),
            usdtValue: (Math.random() * 15000).toFixed(2)
          },
          {
            asset: 'ETH',
            free: (Math.random() * 10).toFixed(8),
            locked: (Math.random() * 1).toFixed(8),
            btcValue: (Math.random() * 0.2).toFixed(8),
            usdtValue: (Math.random() * 6000).toFixed(2)
          },
          {
            asset: 'USDT',
            free: (Math.random() * 10000).toFixed(2),
            locked: (Math.random() * 1000).toFixed(2),
            btcValue: (Math.random() * 0.1).toFixed(8),
            usdtValue: (Math.random() * 3000).toFixed(2)
          }
        ]
      } catch (error) {
        console.error('获取资产数据失败:', error)
        ElMessage.error('获取资产数据失败')
      } finally {
        assetsLoading.value = false
      }
    }
    
    // 刷新资产数据
    const refreshAssets = async () => {
      await fetchAssets()
      ElMessage.success('资产数据已刷新')
    }
    
    // 获取活动日志
    const fetchActivityLogs = async (reset = true) => {
      if (!account.value) return
      
      logsLoading.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // 如果是重置，则清空现有日志
        if (reset) {
          activityLogs.value = []
          logsPage.value = 1
        }
        
        // 模拟数据
        const newLogs = [
          {
            id: Date.now() + 1,
            title: '内部转账',
            description: `从主账户转入 0.5 BTC`,
            type: 'transfer',
            status: 'success',
            timestamp: new Date(Date.now() - Math.floor(Math.random() * 86400000))
          },
          {
            id: Date.now() + 2,
            title: 'API密钥创建',
            description: '创建了新的API密钥用于交易',
            type: 'api',
            status: 'success',
            timestamp: new Date(Date.now() - Math.floor(Math.random() * 86400000 * 2))
          },
          {
            id: Date.now() + 3,
            title: '提现请求',
            description: '尝试提现 0.1 BTC 到外部钱包',
            type: 'withdraw',
            status: Math.random() > 0.5 ? 'success' : 'failed',
            timestamp: new Date(Date.now() - Math.floor(Math.random() * 86400000 * 3))
          }
        ]
        
        // 添加新日志到现有日志列表
        activityLogs.value = [...activityLogs.value, ...newLogs]
        logsPage.value++
      } catch (error) {
        console.error('获取活动日志失败:', error)
        ElMessage.error('获取活动日志失败')
      } finally {
        logsLoading.value = false
      }
    }
    
    // 加载更多日志
    const loadMoreLogs = () => {
      fetchActivityLogs(false)
    }
    
    // 打开删除对话框
    const openDeleteDialog = () => {
      if (!account.value) return
      emit('delete-account', account.value)
    }
    
    // 打开转账对话框
    const openTransferDialog = () => {
      if (!account.value) return
      emit('transfer', account.value)
    }
    
    // 关闭对话框
    const handleClose = () => {
      dialogVisible.value = false
      // 等待对话框关闭动画后清空数据
      setTimeout(() => {
        account.value = null
        assets.value = []
        activityLogs.value = []
      }, 300)
    }
    
    // 格式化日期
    const formatDate = (date) => {
      if (!date) return '-'
      return new Date(date).toLocaleDateString('zh-CN')
    }
    
    // 格式化日期和时间
    const formatDateTime = (date) => {
      if (!date) return '-'
      return new Date(date).toLocaleString('zh-CN')
    }
    
    // 随机选择特性
    const sampleFeatures = () => {
      const allFeatures = Object.keys(featureLabels)
      const count = Math.floor(Math.random() * 4) // 0-3个特性
      const selected = []
      
      for (let i = 0; i < count; i++) {
        const feature = allFeatures[Math.floor(Math.random() * allFeatures.length)]
        if (!selected.includes(feature)) {
          selected.push(feature)
        }
      }
      
      return selected
    }
    
    return {
      dialogVisible,
      loading,
      account,
      assets,
      assetsLoading,
      activityLogs,
      logsLoading,
      featureLabels,
      logTypeMap,
      totalBtcValue,
      totalUsdtValue,
      handleClose,
      fetchAccountDetails,
      fetchAssets,
      refreshAssets,
      fetchActivityLogs,
      loadMoreLogs,
      openDeleteDialog,
      openTransferDialog,
      formatDate,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.loading-container {
  padding: 20px;
  min-height: 300px;
}

.account-details {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.label {
  font-size: 12px;
  color: #909399;
}

.value {
  font-size: 14px;
  color: #303133;
}

.features-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.feature-tag {
  margin-right: 5px;
}

.no-features {
  font-size: 12px;
  color: #909399;
  font-style: italic;
}

.assets-section, .logs-section {
  min-height: 200px;
}

.summary-section {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
  margin-top: 15px;
  padding: 10px;
  background-color: #f7f7f7;
  border-radius: 4px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.summary-item .value {
  font-weight: bold;
  color: #409eff;
}

.logs-list {
  margin-top: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 