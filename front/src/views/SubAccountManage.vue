<template>
  <div class="sub-account-page">
    <h1 class="page-title">子账户管理</h1>
    
    <div class="action-bar">
      <el-button type="primary" @click="openCreateDialog">创建子账户</el-button>
      <el-button type="primary" @click="openBatchCreateDialog">批量创建</el-button>
      <el-button type="danger" @click="openDeleteDialog(selectedAccounts)" :disabled="selectedAccounts.length === 0">删除所选</el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索子账户"
        prefix-icon="el-icon-search"
        class="search-input"
        clearable
      />
    </div>
    
    <el-table
      v-loading="loading"
      :data="filteredAccounts"
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="name" label="子账户名称" />
      <el-table-column prop="type" label="账户类型">
        <template #default="scope">
          <el-tag :type="scope.row.type === 'spot' ? 'success' : 'warning'">
            {{ scope.row.type === 'spot' ? '现货账户' : '期货账户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间">
        <template #default="scope">
          {{ formatDate(scope.row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.status === 'active' ? 'success' : 'danger'">
            {{ scope.row.status === 'active' ? '活跃' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button 
            size="small" 
            type="primary" 
            @click="viewAccount(scope.row)"
          >详情</el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="openDeleteDialog([scope.row])"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-if="totalAccounts > 0"
      class="pagination"
      :current-page="currentPage"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pageSize"
      layout="total, sizes, prev, pager, next, jumper"
      :total="totalAccounts"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
    />
    
    <!-- 创建子账户对话框 -->
    <create-account-dialog
      v-model="createDialogVisible"
      @account-created="fetchAccounts"
    />
    
    <!-- 批量创建子账户对话框 -->
    <batch-create-dialog
      v-model="batchCreateDialogVisible"
      @accounts-created="fetchAccounts"
    />
    
    <!-- 删除子账户对话框 -->
    <delete-account-dialog
      v-model="deleteDialogVisible"
      :accounts="accountsToDelete"
      @accounts-deleted="handleAccountsDeleted"
    />
    
    <!-- 账户详情对话框 -->
    <account-details-dialog
      v-model="detailsDialogVisible"
      :account-id="selectedAccountId"
      @delete-account="openDeleteDialog"
      @transfer="handleTransferRequest"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import CreateAccountDialog from '@/components/dialogs/CreateAccountDialog.vue'
import BatchCreateDialog from '@/components/dialogs/BatchCreateDialog.vue'
import DeleteAccountDialog from '@/components/dialogs/DeleteAccountDialog.vue'
import AccountDetailsDialog from '@/components/dialogs/AccountDetailsDialog.vue'

export default {
  name: 'SubAccountManage',
  components: {
    CreateAccountDialog,
    BatchCreateDialog,
    DeleteAccountDialog,
    AccountDetailsDialog
  },
  setup() {
    const accounts = ref([])
    const loading = ref(false)
    const selectedAccounts = ref([])
    const searchQuery = ref('')
    const createDialogVisible = ref(false)
    const batchCreateDialogVisible = ref(false)
    const deleteDialogVisible = ref(false)
    const detailsDialogVisible = ref(false)
    const accountsToDelete = ref([])
    const selectedAccountId = ref(null)
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalAccounts = ref(0)

    // 模拟数据 - 实际项目中应从API获取
    const fetchAccounts = async () => {
      loading.value = true
      try {
        // 模拟API调用
        setTimeout(() => {
          accounts.value = [
            {
              id: 1,
              name: 'sub_account_001',
              type: 'spot',
              createdAt: new Date('2023-01-15'),
              status: 'active'
            },
            {
              id: 2,
              name: 'futures_001',
              type: 'futures',
              createdAt: new Date('2023-02-20'),
              status: 'active'
            },
            {
              id: 3,
              name: 'test_account',
              type: 'spot',
              createdAt: new Date('2023-03-10'),
              status: 'disabled'
            }
          ]
          totalAccounts.value = accounts.value.length
          loading.value = false
        }, 500)
      } catch (error) {
        console.error('获取子账户列表失败:', error)
        ElMessage.error('获取子账户列表失败')
        loading.value = false
      }
    }

    const filteredAccounts = computed(() => {
      if (!searchQuery.value) return accounts.value
      const query = searchQuery.value.toLowerCase()
      return accounts.value.filter(account => 
        account.name.toLowerCase().includes(query) || 
        account.type.toLowerCase().includes(query)
      )
    })

    const handleSelectionChange = (selection) => {
      selectedAccounts.value = selection
    }

    const openCreateDialog = () => {
      createDialogVisible.value = true
    }

    const openBatchCreateDialog = () => {
      batchCreateDialogVisible.value = true
    }

    const openDeleteDialog = (accountsList) => {
      if (accountsList.length === 0) return
      
      accountsToDelete.value = accountsList
      deleteDialogVisible.value = true
    }

    const handleAccountsDeleted = (deletedIds) => {
      // 删除成功后从列表中移除这些账户
      accounts.value = accounts.value.filter(a => !deletedIds.includes(a.id))
      totalAccounts.value = accounts.value.length
      
      // 如果删除的是当前选中的账户，则清空选中列表
      if (selectedAccounts.value.some(a => deletedIds.includes(a.id))) {
        selectedAccounts.value = []
      }
    }

    const viewAccount = (account) => {
      selectedAccountId.value = account.id
      detailsDialogVisible.value = true
    }
    
    const handleTransferRequest = (account) => {
      ElMessage.info(`转账功能待实现 - 账户: ${account.name}`)
      // 实际项目中可打开转账对话框
    }

    const formatDate = (date) => {
      return new Date(date).toLocaleDateString('zh-CN')
    }

    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
    }

    const handleCurrentChange = (page) => {
      currentPage.value = page
    }

    onMounted(() => {
      fetchAccounts()
    })

    return {
      accounts,
      loading,
      selectedAccounts,
      searchQuery,
      createDialogVisible,
      batchCreateDialogVisible,
      deleteDialogVisible,
      detailsDialogVisible,
      accountsToDelete,
      selectedAccountId,
      currentPage,
      pageSize,
      totalAccounts,
      filteredAccounts,
      handleSelectionChange,
      openCreateDialog,
      openBatchCreateDialog,
      openDeleteDialog,
      handleAccountsDeleted,
      viewAccount,
      handleTransferRequest,
      formatDate,
      fetchAccounts,
      handleSizeChange,
      handleCurrentChange
    }
  }
}
</script>

<style scoped>
.sub-account-page {
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
  color: #303133;
}

.action-bar {
  display: flex;
  margin-bottom: 20px;
  align-items: center;
}

.action-bar .el-button {
  margin-right: 15px;
}

.search-input {
  width: 250px;
  margin-left: auto;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style> 