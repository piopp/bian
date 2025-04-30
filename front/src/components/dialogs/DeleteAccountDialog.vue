<template>
  <el-dialog
    v-model="dialogVisible"
    title="删除子账户"
    width="500px"
    :close-on-click-modal="false"
    :before-close="handleClose"
  >
    <div class="delete-dialog-content">
      <el-alert
        v-if="accounts.length > 0"
        type="warning"
        :title="accounts.length > 1 ? '批量删除确认' : '删除确认'"
        :description="warningMessage"
        show-icon
        :closable="false"
        class="delete-warning"
      />
      
      <div v-if="accounts.length > 1" class="account-list">
        <p class="list-title">将删除以下子账户：</p>
        <el-scrollbar height="150px">
          <ul class="account-items">
            <li v-for="account in accounts" :key="account.id" class="account-item">
              <span class="account-name">{{ account.name }}</span>
              <el-tag size="small" :type="account.type === 'spot' ? 'success' : 'warning'">
                {{ account.type === 'spot' ? '现货账户' : '期货账户' }}
              </el-tag>
            </li>
          </ul>
        </el-scrollbar>
      </div>
      
      <div class="confirmation-section">
        <p class="confirmation-text">此操作将<span class="highlight">永久删除</span>选定的子账户，无法恢复。</p>
        <el-checkbox v-model="confirmDelete">我确认要删除这些子账户</el-checkbox>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="danger"
          :disabled="!confirmDelete"
          :loading="loading"
          @click="confirmDeletion"
        >
          确认删除
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'DeleteAccountDialog',
  props: {
    // 对话框可见性
    modelValue: {
      type: Boolean,
      required: true
    },
    // 要删除的账户列表
    accounts: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue', 'accounts-deleted'],
  setup(props, { emit }) {
    const loading = ref(false)
    const confirmDelete = ref(false)

    // 计算对话框的可见性
    const dialogVisible = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    // 警告消息
    const warningMessage = computed(() => {
      if (props.accounts.length === 0) return ''
      
      if (props.accounts.length === 1) {
        return `您即将删除子账户 "${props.accounts[0].name}"。该操作不可逆，请确认。`
      } else {
        return `您即将删除 ${props.accounts.length} 个子账户。该操作不可逆，请确认。`
      }
    })

    // 关闭对话框
    const handleClose = () => {
      confirmDelete.value = false
      dialogVisible.value = false
    }

    // 确认删除
    const confirmDeletion = async () => {
      if (!confirmDelete.value) return
      
      loading.value = true
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // 假设删除成功
        ElMessage.success(`成功删除 ${props.accounts.length} 个子账户`)
        
        // 通知父组件删除成功
        emit('accounts-deleted', props.accounts.map(a => a.id))
        
        // 重置并关闭对话框
        confirmDelete.value = false
        dialogVisible.value = false
      } catch (error) {
        console.error('删除子账户失败:', error)
        ElMessage.error('删除子账户失败，请重试')
      } finally {
        loading.value = false
      }
    }

    return {
      dialogVisible,
      loading,
      confirmDelete,
      warningMessage,
      handleClose,
      confirmDeletion
    }
  }
}
</script>

<style scoped>
.delete-dialog-content {
  padding: 10px 0;
}

.delete-warning {
  margin-bottom: 20px;
}

.account-list {
  margin: 15px 0;
}

.list-title {
  font-weight: bold;
  margin-bottom: 10px;
}

.account-items {
  list-style: none;
  padding: 0;
  margin: 0;
}

.account-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 5px;
  border-radius: 4px;
  background-color: #f7f7f7;
}

.account-name {
  font-family: monospace;
  font-weight: 500;
}

.confirmation-section {
  margin-top: 20px;
  border-top: 1px solid #ebeef5;
  padding-top: 15px;
}

.confirmation-text {
  margin-bottom: 15px;
}

.highlight {
  color: #f56c6c;
  font-weight: bold;
  margin: 0 5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 