<template>
  <div class="leverage-market-container">
    <div class="page-header">
      <h2>统一账户杠杆交易</h2>
      <div class="operation-buttons">
        <el-button type="warning" @click="openAutoArbitrageDialog" :disabled="selectedAccounts.length === 0">
          自动化套利交易
        </el-button>
        <el-button type="primary" @click="openBatchTradeDialog" :disabled="selectedAccounts.length === 0">
          批量交易
        </el-button>
        <el-button type="success" @click="queryMarginStatus" :disabled="selectedAccounts.length === 0">
          账户详情
        </el-button>
      </div>
    </div>
    
    <!-- 统一账户提示 -->
    <el-alert
      title="重要提示：系统已升级为仅支持统一账户交易"
      type="info"
      description="本系统现在专门支持币安统一账户(Portfolio Margin)功能，提供更高效的资金利用和风险管理。普通子账号功能已停用。"
      show-icon
      :closable="true"
      style="margin-bottom: 15px;"
    />

    <!-- API错误提示 -->
    <el-alert
      v-if="apiError"
      :title="apiError"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 15px;"
    />

    <!-- 账户选择和筛选区域 -->
    <div class="filter-section">
      <el-input v-model="searchKeyword" placeholder="搜索统一账户" class="search-input" clearable />
      <el-select v-model="filterStatus" placeholder="状态筛选" class="filter-select" clearable>
        <el-option label="全部" value="" />
        <el-option label="账户已激活" value="ENABLED" />
        <el-option label="账户未激活" value="DISABLED" />
      </el-select>
      <div class="selection-summary" v-if="selectedAccounts.length > 0">
        已选择: {{ selectedAccounts.length }} 个账户
        <el-button type="text" @click="clearSelection">清除</el-button>
      </div>
    </div>

    <!-- 账户列表 -->
    <el-table
      ref="accountTable"
      :data="filteredAccounts"
      style="width: 100%"
      @selection-change="handleSelectionChange"
      v-loading="loading"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="email" label="统一账户" min-width="240">
        <template #default="scope">
          <div class="account-info">
            <span class="account-email">{{ scope.row.email }}</span>
            <el-tag size="small" :type="scope.row.is_margin_enabled ? 'success' : 'info'">
              {{ scope.row.is_margin_enabled ? '账户已激活' : '账户未激活' }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.create_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : 'danger'">
            {{ scope.row.status === 'ACTIVE' ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button type="primary" size="small" @click="openSingleTradeDialog(scope.row)">
            交易
          </el-button>
          <el-button type="info" size="small" @click="querySingleMarginStatus(scope.row)">
            账户详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页器 -->
    <div class="pagination-container">
      <el-pagination
        background
        layout="prev, pager, next, sizes"
        :total="totalAccounts"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
        :page-sizes="[10, 20, 50, 100]"
      />
    </div>

    <!-- 市场交易对话框 -->
    <market-trade-dialog
      v-model="tradeDialogVisible"
      :account="currentAccount"
      :selected-accounts="selectedAccounts"
      @success="handleTradeSuccess"
      @open-arbitrage="handleOpenArbitrage"
    />

    <!-- 杠杆账户详情对话框 -->
    <margin-account-dialog
      v-model="marginDialogVisible"
      :account="currentAccount"
      :selected-accounts="selectedAccounts"
    />

    <!-- 自动化套利对话框 -->
    <auto-arbitrage-dialog
      v-model="autoArbitrageDialogVisible"
      :account="arbitrageAccount"
      :selectedAccounts="arbitrageSelectedAccounts"
      @success="handleArbitrageSuccess"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { formatDate } from '../utils/format'
import MarketTradeDialog from '../components/dialogs/MarketTradeDialog.vue'
import MarginAccountDialog from '../components/dialogs/MarginAccountDialog.vue'
import AutoArbitrageDialog from '../components/dialogs/AutoArbitrageDialog.vue'
import eventBus from '../services/eventBus.js'
import { useSubaccountsStore } from '../stores/subaccounts' // 导入子账号Store

export default {
  name: 'LeverageMarketView',
  components: {
    MarketTradeDialog,
    MarginAccountDialog,
    AutoArbitrageDialog
  },
  setup() {
    // 数据加载状态
    const loading = ref(false)

    // 获取子账号Store
    const subaccountsStore = useSubaccountsStore()

    // 子账号列表数据
    const accounts = ref([])
    const totalAccounts = ref(0)
    const currentPage = ref(1)
    const pageSize = ref(20)
    const apiError = ref(null)

    // 选择和筛选
    const selectedAccounts = ref([])
    const searchKeyword = ref('')
    const filterStatus = ref('')

    // 对话框控制
    const tradeDialogVisible = ref(false)
    const marginDialogVisible = ref(false)
    const currentAccount = ref(null)

    // 表格引用
    const accountTable = ref(null)

    // 自动化套利对话框控制
    const autoArbitrageDialogVisible = ref(false)
    const arbitrageAccount = ref(null)
    const arbitrageSelectedAccounts = ref([])

    // 计算分页后的账号
    const paginatedAccounts = computed(() => {
      const allAccounts = subaccountsStore.subaccounts || []
      const start = (currentPage.value - 1) * pageSize.value
      const end = start + pageSize.value
      return allAccounts.slice(start, end)
    })

    // 过滤后的账号列表
    const filteredAccounts = computed(() => {
      return paginatedAccounts.value.filter(account => {
        const matchKeyword = !searchKeyword.value ||
          account.email.toLowerCase().includes(searchKeyword.value.toLowerCase())
        
        const matchStatus = !filterStatus.value ||
          (filterStatus.value === 'ENABLED' && account.is_margin_enabled) ||
          (filterStatus.value === 'DISABLED' && !account.is_margin_enabled)
        
        return matchKeyword && matchStatus
      })
    })

    // 监听Store中的子账号数据变化
    watch(() => subaccountsStore.subaccounts, (newAccounts) => {
      accounts.value = newAccounts
      totalAccounts.value = newAccounts.length
      // 检查API错误
      apiError.value = subaccountsStore.getApiError()
    }, { immediate: true })

    // 加载子账号列表
    const loadAccounts = async () => {
      loading.value = true
      try {
        await subaccountsStore.fetchSubaccounts(true) // 强制刷新数据
        apiError.value = subaccountsStore.getApiError()
      } catch (error) {
        ElMessage.error(`加载子账号列表异常: ${error.message}`)
      } finally {
        loading.value = false
      }
    }

    // 处理选择变化
    const handleSelectionChange = (selection) => {
      selectedAccounts.value = selection
    }

    // 清除选择
    const clearSelection = () => {
      accountTable.value?.clearSelection()
      selectedAccounts.value = []
    }

    // 处理分页变化
    const handlePageChange = (page) => {
      currentPage.value = page
    }

    // 处理每页数量变化
    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
    }

    // 打开单个账户交易对话框
    const openSingleTradeDialog = (account) => {
      currentAccount.value = account
      tradeDialogVisible.value = true
    }

    // 打开批量交易对话框
    const openBatchTradeDialog = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择要交易的子账号')
        return
      }
      currentAccount.value = null
      tradeDialogVisible.value = true
    }

    // 查询单个账户杠杆状态
    const querySingleMarginStatus = (account) => {
      currentAccount.value = account
      marginDialogVisible.value = true
    }

    // 批量查询杠杆状态
    const queryMarginStatus = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择要查询的子账号')
        return
      }
      currentAccount.value = null
      marginDialogVisible.value = true
    }

    // 处理交易成功
    const handleTradeSuccess = () => {
      ElMessage.success('交易请求已成功提交')
      // 重新加载账户信息
      loadAccounts()
    }

    // 处理自动化套利
    const handleOpenArbitrage = (params) => {
      arbitrageAccount.value = params.account || null
      arbitrageSelectedAccounts.value = params.selectedAccounts || []
      
      // 两种方式: 本地显示对话框或通过事件总线全局处理
      
      // 方式1: 本地显示对话框
      autoArbitrageDialogVisible.value = true
      
      // 方式2: 通过事件总线让App全局处理
      eventBus.emit('open-arbitrage', {
        account: arbitrageAccount.value,
        selectedAccounts: arbitrageSelectedAccounts.value
      })
    }

    // 打开自动化套利对话框
    const openAutoArbitrageDialog = () => {
      arbitrageSelectedAccounts.value = [...selectedAccounts.value]
      autoArbitrageDialogVisible.value = true
    }

    // 处理自动化套利成功
    const handleArbitrageSuccess = () => {
      autoArbitrageDialogVisible.value = false
      loadAccounts()
    }

    // 初始化
    onMounted(() => {
      loadAccounts()
    })

    return {
      loading,
      accounts,
      filteredAccounts,
      totalAccounts,
      currentPage,
      pageSize,
      selectedAccounts,
      searchKeyword,
      filterStatus,
      tradeDialogVisible,
      marginDialogVisible,
      currentAccount,
      accountTable,
      apiError,
      formatDate,
      loadAccounts,
      handleSelectionChange,
      clearSelection,
      handlePageChange,
      handleSizeChange,
      openSingleTradeDialog,
      openBatchTradeDialog,
      querySingleMarginStatus,
      queryMarginStatus,
      handleTradeSuccess,
      autoArbitrageDialogVisible,
      arbitrageAccount,
      arbitrageSelectedAccounts,
      handleOpenArbitrage,
      openAutoArbitrageDialog,
      handleArbitrageSuccess
    }
  }
}
</script>

<style scoped>
.leverage-market-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.operation-buttons {
  display: flex;
  gap: 10px;
}

.filter-section {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.search-input {
  width: 250px;
}

.filter-select {
  width: 150px;
}

.selection-summary {
  margin-left: auto;
  font-size: 14px;
  color: #606266;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.account-email {
  font-weight: bold;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style> 