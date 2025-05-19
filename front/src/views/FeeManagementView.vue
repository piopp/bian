<template>
  <div class="fee-management-container">
    <div class="page-header">
      <h2>手续费管理</h2>
      <div class="operation-buttons">
        <el-button type="primary" @click="syncFees" :loading="syncLoading">
          同步手续费数据
        </el-button>
        <el-button type="success" @click="exportData">
          导出数据
        </el-button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-section">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="子账户">
          <el-select v-model="filterForm.email" placeholder="请选择子账户" clearable @change="loadFees">
            <el-option
              v-for="account in accounts"
              :key="account"
              :label="account"
              :value="account"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="交易类型">
          <el-select v-model="filterForm.source" placeholder="交易类型" clearable @change="loadFees">
            <el-option label="杠杆交易" value="MARGIN" />
            <el-option label="合约交易" value="FUTURES" />
            <el-option label="现货交易" value="SPOT" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadFees">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 手续费汇总卡片 -->
    <div class="summary-section" v-loading="summaryLoading">
      <div class="summary-title">
        <h3>手续费汇总</h3>
        <span class="period-label" v-if="filterForm.startDate && filterForm.endDate">
          {{ filterForm.startDate }} 至 {{ filterForm.endDate }}
        </span>
      </div>
      <div class="summary-cards">
        <div class="summary-card" v-for="(item, index) in feeSummary.fee_by_asset" :key="index">
          <div class="card-title">{{ item.asset }} 手续费</div>
          <div class="card-value">{{ item.total_fee.toFixed(8) }}</div>
          <div class="card-footer">总计</div>
        </div>
        <div class="summary-card" v-if="!feeSummary.fee_by_asset || feeSummary.fee_by_asset.length === 0">
          <div class="card-title">暂无数据</div>
          <div class="card-value">-</div>
          <div class="card-footer">请选择账户查询</div>
        </div>
      </div>

      <!-- 交易类型统计 -->
      <div class="source-stats" v-if="feeSummary.fee_by_source && feeSummary.fee_by_source.length > 0">
        <h4>交易类型统计</h4>
        <el-table :data="feeSummary.fee_by_source" stripe border>
          <el-table-column prop="source" label="交易类型" min-width="120">
            <template #default="scope">
              <span>{{ getSourceLabel(scope.row.source) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="total_fee" label="手续费总额" min-width="120">
            <template #default="scope">
              <span>{{ scope.row.total_fee.toFixed(8) }} {{ scope.row.asset }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 单账户每日统计 -->
      <div class="daily-stats" v-if="feeSummary.account_stats && feeSummary.account_stats.daily_fees.length > 0">
        <h4>每日手续费统计 - {{ feeSummary.account_stats.email }}</h4>
        <div class="chart-container">
          <!-- 这里可以添加图表组件，如ECharts -->
          <el-table :data="feeSummary.account_stats.daily_fees" stripe border>
            <el-table-column prop="date" label="日期" min-width="120" />
            <el-table-column prop="fee_amount" label="手续费" min-width="150">
              <template #default="scope">
                <span>{{ scope.row.fee_amount.toFixed(8) }} {{ scope.row.fee_asset }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 手续费明细表格 -->
    <div class="fee-table-section">
      <div class="section-header">
        <h3>手续费明细</h3>
      </div>
      <el-table
        :data="feeRecords"
        stripe
        border
        style="width: 100%"
        v-loading="tableLoading"
      >
        <el-table-column prop="email" label="子账户" min-width="180" />
        <el-table-column prop="fee_amount" label="手续费金额" min-width="120">
          <template #default="scope">
            <span>{{ scope.row.fee_amount.toFixed(8) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="fee_asset" label="手续费资产" min-width="100" />
        <el-table-column prop="source" label="交易类型" min-width="120">
          <template #default="scope">
            <el-tag :type="getSourceTagType(scope.row.source)">
              {{ getSourceLabel(scope.row.source) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="交易对" min-width="120" />
        <el-table-column prop="trade_time" label="交易时间" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="200" />
      </el-table>

      <!-- 分页器 -->
      <div class="pagination-container">
        <el-pagination
          background
          layout="prev, pager, next, sizes"
          :total="total"
          :page-size="pageSize"
          :current-page="currentPage"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
          :page-sizes="[10, 20, 50, 100]"
        />
      </div>
    </div>

    <!-- 同步手续费对话框 -->
    <el-dialog
      v-model="syncDialogVisible"
      title="同步手续费数据"
      width="500px"
    >
      <div class="sync-dialog-content">
        <p>选择要同步手续费数据的子账户：</p>
        <el-select v-model="syncAccount" placeholder="请选择子账户" style="width: 100%;">
          <el-option
            v-for="account in allAccounts"
            :key="account.email"
            :label="account.email"
            :value="account.email"
          />
        </el-select>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="syncDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmSync" :loading="syncLoading">
            确认同步
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'FeeManagementView',
  setup() {
    // 数据加载状态
    const tableLoading = ref(false)
    const summaryLoading = ref(false)
    const syncLoading = ref(false)

    // 同步对话框
    const syncDialogVisible = ref(false)
    const syncAccount = ref('')
    const allAccounts = ref([])

    // 过滤表单
    const filterForm = reactive({
      email: '',
      source: '',
      startDate: '',
      endDate: ''
    })
    const dateRange = ref([])

    // 分页相关
    const currentPage = ref(1)
    const pageSize = ref(20)
    const total = ref(0)

    // 手续费数据
    const feeRecords = ref([])
    const accounts = ref([])
    const feeSummary = reactive({
      fee_by_asset: [],
      fee_by_source: [],
      account_stats: null
    })

    // 处理日期变更
    const handleDateChange = (dates) => {
      if (dates && dates.length === 2) {
        filterForm.startDate = formatDate(dates[0])
        filterForm.endDate = formatDate(dates[1])
      } else {
        filterForm.startDate = ''
        filterForm.endDate = ''
      }
    }

    // 格式化日期
    const formatDate = (date) => {
      if (!date) return ''
      const d = new Date(date)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    // 重置过滤器
    const resetFilter = () => {
      filterForm.email = ''
      filterForm.source = ''
      filterForm.startDate = ''
      filterForm.endDate = ''
      dateRange.value = []
      loadFees()
    }

    // 加载子账户列表
    const loadAccounts = async () => {
      try {
        // 获取有手续费记录的账户
        const response = await axios.get('/api/statistics/fees/accounts')
        if (response.data.success) {
          accounts.value = response.data.data || []
        } else {
          ElMessage.error('获取子账户列表失败')
        }

        // 获取所有子账户（用于同步功能）
        const subaccountsResponse = await axios.get('/api/subaccounts/')
        if (subaccountsResponse.data.success) {
          allAccounts.value = subaccountsResponse.data.data.subaccounts || []
        }
      } catch (error) {
        console.error('加载子账户列表失败:', error)
        ElMessage.error('加载子账户列表失败')
      }
    }

    // 加载手续费数据
    const loadFees = async () => {
      tableLoading.value = true
      try {
        const params = {
          page: currentPage.value,
          per_page: pageSize.value,
          email: filterForm.email || undefined,
          source: filterForm.source || undefined,
          start_date: filterForm.startDate || undefined,
          end_date: filterForm.endDate || undefined
        }

        const response = await axios.get('/api/statistics/fees', { params })
        if (response.data.success) {
          feeRecords.value = response.data.data.records
          total.value = response.data.data.total
        } else {
          ElMessage.error('加载手续费数据失败')
        }
      } catch (error) {
        console.error('加载手续费数据失败:', error)
        ElMessage.error('加载手续费数据失败')
      } finally {
        tableLoading.value = false
      }

      // 加载手续费汇总
      loadFeeSummary()
    }

    // 加载手续费汇总
    const loadFeeSummary = async () => {
      summaryLoading.value = true
      try {
        const params = {
          email: filterForm.email || undefined,
          start_date: filterForm.startDate || undefined,
          end_date: filterForm.endDate || undefined
        }

        const response = await axios.get('/api/statistics/fees/summary', { params })
        if (response.data.success) {
          feeSummary.fee_by_asset = response.data.data.fee_by_asset || []
          feeSummary.fee_by_source = response.data.data.fee_by_source || []
          feeSummary.account_stats = response.data.data.account_stats
        } else {
          ElMessage.error('加载手续费汇总失败')
        }
      } catch (error) {
        console.error('加载手续费汇总失败:', error)
        ElMessage.error('加载手续费汇总失败')
      } finally {
        summaryLoading.value = false
      }
    }

    // 同步手续费数据
    const syncFees = () => {
      syncDialogVisible.value = true
    }

    // 确认同步
    const confirmSync = async () => {
      if (!syncAccount.value) {
        ElMessage.warning('请选择子账户')
        return
      }

      syncLoading.value = true
      try {
        const response = await axios.post('/api/statistics/fees/sync', {
          email: syncAccount.value
        })

        if (response.data.success) {
          ElMessage.success(response.data.data.message)
          syncDialogVisible.value = false
          // 延迟后刷新数据
          setTimeout(() => {
            loadFees()
          }, 2000)
        } else {
          ElMessage.error(response.data.error || '同步失败')
        }
      } catch (error) {
        console.error('同步手续费数据失败:', error)
        ElMessage.error('同步手续费数据失败')
      } finally {
        syncLoading.value = false
      }
    }

    // 处理分页变化
    const handlePageChange = (page) => {
      currentPage.value = page
      loadFees()
    }

    // 处理每页数量变化
    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
      loadFees()
    }

    // 导出数据
    const exportData = () => {
      const params = new URLSearchParams()
      if (filterForm.email) params.append('email', filterForm.email)
      if (filterForm.source) params.append('source', filterForm.source)
      if (filterForm.startDate) params.append('start_date', filterForm.startDate)
      if (filterForm.endDate) params.append('end_date', filterForm.endDate)

      // const queryString = params.toString()
      // const url = `/api/statistics/fees/export${queryString ? `?${queryString}` : ''}`
      
      ElMessage.info('导出功能正在开发中...')
      // window.open(url, '_blank')
    }

    // 获取交易类型标签
    const getSourceLabel = (source) => {
      const labels = {
        'SPOT': '现货交易',
        'MARGIN': '杠杆交易',
        'FUTURES': '合约交易',
        'MINING': '挖矿',
        'STAKING': '质押收益'
      }
      return labels[source] || source
    }

    // 获取交易类型标签样式
    const getSourceTagType = (source) => {
      const types = {
        'SPOT': 'primary',
        'MARGIN': 'warning',
        'FUTURES': 'danger',
        'MINING': 'success',
        'STAKING': 'info'
      }
      return types[source] || 'info'
    }

    // 初始化
    onMounted(async () => {
      await loadAccounts()
      loadFees()
    })

    return {
      tableLoading,
      summaryLoading,
      syncLoading,
      syncDialogVisible,
      syncAccount,
      allAccounts,
      filterForm,
      dateRange,
      currentPage,
      pageSize,
      total,
      feeRecords,
      accounts,
      feeSummary,
      handleDateChange,
      resetFilter,
      loadFees,
      syncFees,
      confirmSync,
      handlePageChange,
      handleSizeChange,
      exportData,
      getSourceLabel,
      getSourceTagType
    }
  }
}
</script>

<style scoped>
.fee-management-container {
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
  margin-bottom: 20px;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.summary-section {
  margin-bottom: 30px;
  background-color: white;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.summary-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.period-label {
  font-size: 14px;
  color: #909399;
}

.summary-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
}

.summary-card {
  flex: 1;
  min-width: 180px;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  border-left: 4px solid #409EFF;
}

.card-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.card-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 10px;
}

.card-footer {
  font-size: 12px;
  color: #909399;
}

.source-stats,
.daily-stats {
  margin-top: 30px;
}

.chart-container {
  margin-top: 15px;
  height: 300px;
}

.fee-table-section {
  background-color: white;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.section-header {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.sync-dialog-content {
  margin-bottom: 20px;
}
</style> 