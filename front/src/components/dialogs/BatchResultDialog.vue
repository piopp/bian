<template>
  <el-dialog
    :title="title || '操作结果'"
    v-model="dialogVisible"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="result-summary">
      <div class="summary-item">
        <span class="summary-label">总操作数:</span>
        <span class="summary-value">{{ results.length }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">成功:</span>
        <span class="summary-value success">{{ successCount }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">失败:</span>
        <span class="summary-value error">{{ failureCount }}</span>
      </div>
    </div>

    <el-table
      :data="results"
      border
      style="width: 100%"
      max-height="400px"
    >
      <el-table-column prop="email" label="子账号" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.success ? 'success' : 'danger'">
            {{ scope.row.success ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="结果信息" />
    </el-table>

    <div class="action-buttons">
      <el-button type="primary" @click="exportResults">导出结果</el-button>
      <el-button 
        type="warning" 
        @click="retryFailedItems"
        :disabled="failureCount === 0"
      >
        重试失败项
      </el-button>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'BatchResultDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    results: {
      type: Array,
      default: () => []
    },
    title: {
      type: String,
      default: ''
    }
  },
  emits: ['update:visible', 'retry'],
  setup(props, { emit }) {
    // 计算属性: 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 成功数量
    const successCount = computed(() => {
      return props.results.filter(item => item.success).length
    })
    
    // 失败数量
    const failureCount = computed(() => {
      return props.results.filter(item => !item.success).length
    })
    
    // 导出结果
    const exportResults = () => {
      // 创建CSV内容
      const headers = ['子账号', '状态', '结果信息']
      const csvContent = [
        headers.join(','),
        ...props.results.map(item => [
          item.email,
          item.success ? '成功' : '失败',
          item.message || '-'
        ].join(','))
      ].join('\n')
      
      // 创建Blob对象
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      
      // 创建下载链接
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      
      // 设置下载属性
      link.setAttribute('href', url)
      link.setAttribute('download', `批量操作结果_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.display = 'none'
      
      // 添加到DOM，触发下载，然后移除
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      ElMessage.success('结果已导出为CSV文件')
    }
    
    // 重试失败项
    const retryFailedItems = () => {
      const failedItems = props.results.filter(item => !item.success)
      
      if (failedItems.length === 0) {
        ElMessage.warning('没有失败项可重试')
        return
      }
      
      // 触发重试事件，将失败项传递给父组件处理
      emit('retry', failedItems)
      
      // 关闭对话框
      dialogVisible.value = false
      
      ElMessage.success(`正在重试 ${failedItems.length} 个失败项`)
    }
    
    return {
      dialogVisible,
      successCount,
      failureCount,
      exportResults,
      retryFailedItems
    }
  }
}
</script>

<style scoped>
.result-summary {
  display: flex;
  justify-content: space-between;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.summary-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.summary-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.summary-value.success {
  color: #67c23a;
}

.summary-value.error {
  color: #f56c6c;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 