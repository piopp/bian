<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title || '操作结果'"
    width="800px"
    :close-on-click-modal="false"
  >
    <div v-if="results && results.length > 0" class="results-container">
      <el-table :data="results" style="width: 100%">
        <el-table-column prop="email" label="子账号" min-width="180" />
        <el-table-column prop="success" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.success ? 'success' : 'danger'">
              {{ scope.row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="信息" min-width="180" />
        <el-table-column label="操作" width="120" v-if="hasDetailsButton">
          <template #default="scope">
            <el-button 
              v-if="scope.row.showDetailsButton || scope.row.details" 
              type="primary" 
              size="small"
              @click="viewDetails(scope.row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="summary">
        <div class="summary-item">
          <span class="label">总数:</span>
          <span class="value">{{ results.length }}</span>
        </div>
        <div class="summary-item">
          <span class="label">成功:</span>
          <span class="value success">{{ successCount }}</span>
        </div>
        <div class="summary-item">
          <span class="label">失败:</span>
          <span class="value error">{{ failCount }}</span>
        </div>
      </div>
    </div>
    <div v-else class="empty-results">
      <el-empty description="暂无结果数据" />
    </div>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="closeDialog">关闭</el-button>
        <el-button v-if="hasSuccessResults" type="primary" @click="exportResults">
          导出结果
        </el-button>
      </span>
    </template>
    
    <!-- 子账户详情对话框 -->
    <account-details-dialog
      v-model="accountDetailsDialogVisible"
      :account-email="selectedAccountEmail"
    />
  </el-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AccountDetailsDialog from './AccountDetailsDialog.vue'

export default {
  name: 'BatchResultDialog',
  components: {
    AccountDetailsDialog
  },
  props: {
    // 控制对话框显示
    visible: {
      type: Boolean,
      default: false
    },
    // 结果数据数组
    results: {
      type: Array,
      default: () => []
    },
    // 对话框标题
    title: {
      type: String,
      default: '操作结果'
    }
  },
  emits: ['update:visible', 'view-details'],
  setup(props, { emit }) {
    // 子账户详情对话框控制
    const accountDetailsDialogVisible = ref(false)
    const selectedAccountEmail = ref('')
    
    // 控制对话框显示
    const dialogVisible = computed({
      get: () => props.visible,
      set: (value) => emit('update:visible', value)
    })
    
    // 计算成功和失败的数量
    const successCount = computed(() => {
      return props.results.filter(item => item.success).length
    })
    
    const failCount = computed(() => {
      return props.results.filter(item => !item.success).length
    })
    
    // 判断是否有成功的结果
    const hasSuccessResults = computed(() => {
      return successCount.value > 0
    })
    
    // 判断是否有任何行显示详情按钮
    const hasDetailsButton = computed(() => {
      return props.results.some(item => item.showDetailsButton || item.details)
    })
    
    // 关闭对话框
    const closeDialog = () => {
      dialogVisible.value = false
    }
    
    // 查看子账户详情
    const viewDetails = (row) => {
      if (row && row.email) {
        // 发送view-details事件到父组件
        emit('view-details', row)
        
        // 同时在本组件内也处理
        selectedAccountEmail.value = row.email
        accountDetailsDialogVisible.value = true
      } else {
        ElMessage.warning('无法查看详情：缺少账户邮箱')
      }
    }
    
    // 导出结果
    const exportResults = () => {
      try {
        const successResults = props.results.filter(item => item.success)
        if (successResults.length === 0) {
          ElMessage.warning('没有可导出的成功结果')
          return
        }
        
        // 格式化要导出的数据
        const exportData = successResults.map(item => {
          // 如果有详情数据，包含详情，否则只包含基本信息
          if (item.details) {
            return {
              email: item.email,
              ...item.details
            }
          }
          return {
            email: item.email,
            success: item.success,
            message: item.message
          }
        })
        
        // 导出为JSON文件
        const dataStr = JSON.stringify(exportData, null, 2)
        const blob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        
        const a = document.createElement('a')
        a.href = url
        a.download = `batch_result_${new Date().getTime()}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        ElMessage.success(`成功导出${exportData.length}条结果数据`)
      } catch (error) {
        console.error('导出结果失败:', error)
        ElMessage.error('导出结果失败: ' + error.message)
      }
    }
    
    // 监听对话框打开，重置状态
    watch(() => props.visible, (newValue) => {
      if (newValue) {
        // 对话框打开时，重置子账户详情对话框状态
        accountDetailsDialogVisible.value = false
        selectedAccountEmail.value = ''
      }
    })
    
    return {
      dialogVisible,
      successCount,
      failCount,
      hasSuccessResults,
      hasDetailsButton,
      closeDialog,
      exportResults,
      viewDetails,
      accountDetailsDialogVisible,
      selectedAccountEmail
    }
  }
}
</script>

<style scoped>
.results-container {
  margin-bottom: 20px;
}

.summary {
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
  align-items: center;
}

.label {
  font-size: 12px;
  color: #909399;
}

.value {
  font-size: 16px;
  font-weight: bold;
}

.value.success {
  color: #67c23a;
}

.value.error {
  color: #f56c6c;
}

.empty-results {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  gap: 10px;
}
</style> 