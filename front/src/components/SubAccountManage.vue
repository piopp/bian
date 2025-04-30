<template>
  <div class="subaccount-manage-container">
    <h1 class="page-title">子账号管理中心</h1>

    <!-- 操作卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><Plus /></el-icon>
            <h3>创建子账号</h3>
            <p class="text-muted">创建新的虚拟子账号</p>
            <el-button type="primary" @click="showCreateAccountDialog">创建子账号</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><User /></el-icon>
            <h3>批量创建</h3>
            <p class="text-muted">批量创建多个子账号</p>
            <el-button type="success" @click="showBatchCreateDialog">批量创建</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 子账号列表卡片 -->
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <div>
            <h3>子账号列表</h3>
            <small class="text-muted">共有 {{ subaccountCount }} 个子账号</small>
          </div>
          <div>
            <el-button type="primary" plain size="small" @click="refreshSubaccounts">
              <el-icon><Refresh /></el-icon> 刷新列表
            </el-button>
            <el-button type="success" plain size="small" @click="exportData">
              <el-icon><Download /></el-icon> 导出数据
            </el-button>
          </div>
        </div>
      </template>

      <!-- 批量操作按钮组 -->
      <div class="batch-action-group">
        <el-button
          type="primary"
          @click="batchEnableFutures"
          :disabled="!hasSelectedAccounts"
          :loading="loading"
        >
          <el-icon><CircleCheck /></el-icon>
          批量开通期货
        </el-button>
        <el-button
          type="primary"
          @click="batchEnableMargin"
          :disabled="!hasSelectedAccounts"
          :loading="loading"
        >
          <el-icon><CircleCheck /></el-icon>
          批量开通杠杆
        </el-button>
        <el-button
          type="primary"
          @click="batchQueryDetails"
          :disabled="!hasSelectedAccounts"
          :loading="loading"
        >
          <el-icon><InfoFilled /></el-icon>
          批量查询详情
        </el-button>
        <el-button
          type="primary"
          @click="batchQueryBalance"
          :disabled="!hasSelectedAccounts"
          :loading="loading"
        >
          <el-icon><Money /></el-icon>
          批量查询余额
        </el-button>
        <el-button
          type="warning"
          @click="showBatchTransferDialog"
          :disabled="!hasSelectedAccounts"
        >
          <el-icon><RefreshRight /></el-icon>
          批量转账
        </el-button>
      </div>

      <!-- 子账号列表表格 -->
      <el-table
        v-loading="loading"
        :data="subaccounts"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="email" label="邮箱" min-width="180"/>
        <el-table-column prop="createTime" label="创建时间" :formatter="formatDate" min-width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tooltip
              :content="getStatusDescription(scope.row.status)"
              placement="top"
              effect="light"
            >
              <el-tag :type="getStatusType(scope.row.status)" effect="light">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="accountType" label="账号类型" width="120">
          <template #default="scope">
            <el-tag 
              :type="getAccountTypeTag(scope.row.accountType)"
              effect="plain"
              size="small"
              class="account-type-tag"
            >
              {{ getAccountTypeText(scope.row.accountType) }}
            </el-tag>
            <div class="account-features" v-if="scope.row.features && scope.row.features.length">
              <el-tag 
                v-for="feature in scope.row.features" 
                :key="feature"
                size="small" 
                class="feature-tag"
                :type="getFeatureTag(feature)"
              >
                {{ getFeatureText(feature) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="scope">
            <el-button size="small" @click="viewAccountDetails(scope.row)">详情</el-button>
            <el-button size="small" type="success" @click="showTransferDialog(scope.row)">转账</el-button>
            <el-dropdown>
              <el-button size="small" type="primary">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="enableFutures(scope.row)">开通期货</el-dropdown-item>
                  <el-dropdown-item @click="enableMargin(scope.row)">开通杠杆</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          @update:current-page="currentPage = $event"
          :page-size="pageSize"
          :total="totalSubaccounts"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 各种对话框组件 -->
    <create-account-dialog 
      :visible="createAccountDialogVisible"
      @update:visible="createAccountDialogVisible = $event"
      @success="handleAccountCreated"
    />
    
    <batch-create-dialog
      :visible="batchCreateDialogVisible"
      @update:visible="batchCreateDialogVisible = $event"
      @success="handleBatchAccountCreated"
    />
    
    <transfer-dialog
      :visible="transferDialogVisible"
      @update:visible="transferDialogVisible = $event"
      :account="selectedAccount"
      @success="handleTransferSuccess"
    />
    
    <batch-transfer-dialog
      :visible="batchTransferDialogVisible"
      @update:visible="batchTransferDialogVisible = $event"
      :selected-accounts="selectedAccounts"
      @success="handleBatchTransferSuccess"
    />
    
    <account-details-dialog
      :visible="accountDetailsDialogVisible"
      @update:visible="accountDetailsDialogVisible = $event"
      :account="selectedAccount"
    />
    
    <batch-result-dialog
      :visible="batchResultDialogVisible"
      @update:visible="batchResultDialogVisible = $event"
      :results="batchResults"
      :title="batchResultTitle"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, User, Refresh, Download, 
  ArrowDown, InfoFilled, Money, CircleCheck, RefreshRight
} from '@element-plus/icons-vue'
import { getCurrentUser } from '../services/auth.js'
import CreateAccountDialog from './dialogs/CreateAccountDialog.vue'
import BatchCreateDialog from './dialogs/BatchCreateDialog.vue'
import TransferDialog from './dialogs/TransferDialog.vue'
import BatchTransferDialog from './dialogs/BatchTransferDialog.vue'
import AccountDetailsDialog from './dialogs/AccountDetailsDialog.vue'
import BatchResultDialog from './dialogs/BatchResultDialog.vue'

export default {
  name: 'SubAccountManagePage',
  components: {
    CreateAccountDialog,
    BatchCreateDialog, 
    TransferDialog,
    BatchTransferDialog,
    AccountDetailsDialog,
    BatchResultDialog,
    Plus, User, Refresh, Download,
    ArrowDown, InfoFilled, Money, CircleCheck, RefreshRight
  },
  setup() {
    // 表格数据相关
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalSubaccounts = ref(0)
    const subaccounts = ref([])
    
    // 选中的账号数据
    const selectedAccounts = ref([])
    const selectedAccount = ref(null)
    
    // 对话框控制
    const createAccountDialogVisible = ref(false)
    const batchCreateDialogVisible = ref(false)
    const transferDialogVisible = ref(false)
    const batchTransferDialogVisible = ref(false)
    
    // 批量操作结果
    const batchResults = ref([])
    const batchResultTitle = ref('操作结果')
    
    // 各种对话框显示状态
    const accountDetailsDialogVisible = ref(false)
    const batchResultDialogVisible = ref(false)
    
    // 计算属性
    const subaccountCount = computed(() => subaccounts.value.length)
    const hasSelectedAccounts = computed(() => selectedAccounts.value.length > 0)
    
    // 获取当前用户ID
    const currentUser = ref(getCurrentUser())
    const userIdValue = currentUser.value?.id
    
    // 服务器时间偏移量（服务器时间与本地时间的差值）
    const serverTimeOffset = ref(0)
    
    // 获取服务器时间
    const getServerTime = async () => {
      try {
        const user = getCurrentUser()
        const response = await fetch('/api/server/time', {
          headers: {
            'Authorization': `Bearer ${user?.token}`
          }
        })
        if (response.ok) {
          const data = await response.json()
          if (data.success && data.data && data.data.timestamp) {
            // 计算服务器时间与本地时间的偏移量
            const serverTime = data.data.timestamp
            const localTime = Date.now()
            serverTimeOffset.value = serverTime - localTime
            console.log(`服务器时间偏移量: ${serverTimeOffset.value}ms，时区: ${data.data.timezone || 'UTC'}`)
          }
        }
      } catch (error) {
        console.error('获取服务器时间出错:', error)
      }
    }
    
    // 获取当前服务器时间
    const getCurrentServerTime = () => {
      return new Date(Date.now() + serverTimeOffset.value)
    }
    
    // 分页改变处理
    const handlePageChange = (page) => {
      currentPage.value = page
      fetchSubaccounts()
    }
    
    // 选择改变处理
    const handleSelectionChange = (selection) => {
      selectedAccounts.value = selection
    }
    
    // 格式化日期（使用服务器时间）
    const formatDate = (row, column, cellValue) => {
      if (!cellValue) return '-'
      
      // 如果是数字时间戳，转换为Date对象
      const date = typeof cellValue === 'number' ? new Date(cellValue) : new Date(cellValue)
      
      // 使用 toLocaleString 格式化日期时间
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    }
    
    // 获取状态样式和文字
    const getStatusType = (status) => {
      // 如果状态为空，默认为ACTIVE(正常)
      if (!status) status = 'ACTIVE';
      
      const statusMap = {
        'ACTIVE': 'success',
        'ENABLED': 'success',
        'DISABLED': 'danger',
        'PENDING': 'warning',
        'SUSPENDED': 'info',
        'LOCKED': 'danger',
        'EXPIRED': 'info',
        'INACTIVE': 'warning'
      }
      return statusMap[status] || 'info'
    }
    
    const getStatusText = (status) => {
      // 如果状态为空，默认为ACTIVE(正常)
      if (!status) status = 'ACTIVE';
      
      const statusMap = {
        'ACTIVE': '活跃',
        'ENABLED': '已启用',
        'DISABLED': '已禁用',
        'PENDING': '待激活',
        'SUSPENDED': '已暂停',
        'LOCKED': '已锁定',
        'EXPIRED': '已过期',
        'INACTIVE': '未激活'
      }
      return statusMap[status] || status
    }
    
    // 获取状态描述
    const getStatusDescription = (status) => {
      // 如果状态为空，默认为ACTIVE(正常)
      if (!status) status = 'ACTIVE';
      
      const descriptionMap = {
        'ACTIVE': '账号正常可用，可以进行所有操作',
        'ENABLED': '账号已启用，功能正常',
        'DISABLED': '账号已被禁用，暂时无法使用',
        'PENDING': '账号等待激活，请完成设置',
        'SUSPENDED': '账号已被暂时挂起',
        'LOCKED': '账号因安全原因被锁定',
        'EXPIRED': '账号已过期，请联系管理员',
        'INACTIVE': '账号尚未激活，无法使用'
      }
      return descriptionMap[status] || '未知状态'
    }
    
    // 获取账号类型标签样式
    const getAccountTypeTag = (type) => {
      // 如果类型为空，默认为VIRTUAL(虚拟子账号)
      if (!type) type = 'VIRTUAL';
      
      const typeMap = {
        'VIRTUAL': 'info',
        'PHYSICAL': 'success',
        'MAIN': 'danger',
        'SPOT': 'primary',
        'FUTURES': 'warning',
        'MARGIN': 'danger',
        'DELIVERY': 'warning'
      }
      return typeMap[type] || 'info'
    }
    
    // 获取账号类型文本
    const getAccountTypeText = (type) => {
      // 如果类型为空，默认为VIRTUAL(虚拟子账号)
      if (!type) type = 'VIRTUAL';
      
      const typeMap = {
        'VIRTUAL': '虚拟账号',
        'PHYSICAL': '实体账号',
        'MAIN': '主账号',
        'SPOT': '现货账号',
        'FUTURES': '期货账号',
        'MARGIN': '杠杆账号',
        'DELIVERY': '交割账号'
      }
      return typeMap[type] || type || '未知类型'
    }
    
    // 获取功能标签样式
    const getFeatureTag = (feature) => {
      const featureMap = {
        'FUTURES': 'warning',
        'MARGIN': 'danger',
        'OPTIONS': 'success',
        'SPOT': 'primary',
        'VANILLA': 'info'
      }
      return featureMap[feature] || 'info'
    }
    
    // 获取功能描述文本
    const getFeatureText = (feature) => {
      const featureMap = {
        'FUTURES': '期货',
        'MARGIN': '杠杆',
        'OPTIONS': '期权',
        'SPOT': '现货',
        'VANILLA': '普通'
      }
      return featureMap[feature] || feature
    }
    
    // 获取子账号列表
    const fetchSubaccounts = async () => {
      loading.value = true
      try {
        const user = getCurrentUser()
        const userIdValue = user?.id
        const response = await fetch(`/api/subaccounts?page=${currentPage.value}&limit=${pageSize.value}&user_id=${userIdValue}`, {
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        })
        
        const result = await response.json()
        
        if (result.success) {
          if (result.data && result.data.subaccounts) {
            // 确保每个子账号都有状态和类型字段，如果没有则添加默认值
            subaccounts.value = result.data.subaccounts.map(account => {
              const features = [];
              if (account.is_futures_enabled) features.push('FUTURES');
              if (account.is_margin_enabled) features.push('MARGIN');
              if (account.is_options_enabled) features.push('OPTIONS');
              
              return {
                ...account,
                status: account.status || 'ACTIVE',
                accountType: account.account_type || 'VIRTUAL',
                features: features
              }
            })
            totalSubaccounts.value = result.data.total || result.data.subaccounts.length
          } else {
            subaccounts.value = []
            totalSubaccounts.value = 0
            console.error('API返回数据结构有误:', result.data)
          }
        } else {
          ElMessage.error(result.error || '获取子账号列表失败')
        }
      } catch (error) {
        console.error('加载子账号列表出错:', error)
        ElMessage.error('加载子账号列表失败')
      } finally {
        loading.value = false
      }
    }

    // 刷新子账号列表
    const refreshSubaccounts = () => {
      fetchSubaccounts()
    }
    
    // 导出全部数据
    const exportData = async () => {
      try {
        const response = await fetch(`/api/subaccounts/api-download?user_id=${userIdValue || ''}`)
        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'subaccount_api.json'
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          a.remove()
          ElMessage.success('数据导出成功')
        } else {
          ElMessage.error('导出数据失败')
        }
      } catch (error) {
        console.error('导出数据出错:', error)
        ElMessage.error('导出数据失败')
      }
    }
    
    // 导出选中账号
    const exportSelected = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择要导出的账号')
        return
      }
      
      try {
        const dataStr = JSON.stringify(selectedAccounts.value)
        const blob = new Blob([dataStr], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'selected_subaccounts.json'
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        a.remove()
        ElMessage.success(`已导出${selectedAccounts.value.length}个选中账号`)
      } catch (error) {
        console.error('导出选中账号出错:', error)
        ElMessage.error('导出选中账号失败')
      }
    }
    
    // 查看账户详情
    const viewAccountDetails = (account) => {
      selectedAccount.value = account
      accountDetailsDialogVisible.value = true
    }
    
    // 显示转账对话框
    const showTransferDialog = (account) => {
      selectedAccount.value = account
      transferDialogVisible.value = true
    }
    
    // 开通期货
    const enableFutures = async (account) => {
      try {
        await ElMessageBox.confirm(`确定要为子账号 ${account.email} 开通期货吗？`, '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/futures/enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            email: account.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          ElMessage.success(`已成功为子账号 ${account.email} 开通期货功能`)
          // 刷新子账号列表
          refreshSubaccounts()
        } else {
          ElMessage.error(result.error || '开通期货失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('开通期货出错:', error)
          ElMessage.error('开通期货失败')
        }
      }
    }
    
    // 开通杠杆
    const enableMargin = async (account) => {
      try {
        await ElMessageBox.confirm(`确定要为子账号 ${account.email} 开通杠杆吗？`, '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/margin/enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            email: account.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          ElMessage.success(`已成功为子账号 ${account.email} 开通杠杆功能`)
          // 刷新子账号列表
          refreshSubaccounts()
        } else {
          ElMessage.error(result.error || '开通杠杆失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('开通杠杆出错:', error)
          ElMessage.error('开通杠杆失败')
        }
      }
    }
    
    // 批量操作函数
    const batchEnableFutures = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号')
        return
      }
      
      try {
        await ElMessageBox.confirm(`确定要为选中的${selectedAccounts.value.length}个子账号开通期货吗？`, '批量开通期货', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const emails = selectedAccounts.value.map(account => account.email)
        const user = getCurrentUser()
        
        const response = await fetch('/api/subaccounts/batch-enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails: emails,
            feature: 'futures'
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          batchResults.value = result.results
          batchResultTitle.value = '批量开通期货结果'
          batchResultDialogVisible.value = true
          ElMessage.success(`成功为${result.success_count}/${result.total}个子账号开通期货`)
          // 刷新子账号列表
          refreshSubaccounts()
        } else {
          ElMessage.error(result.error || '批量开通期货失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量开通期货出错:', error)
          ElMessage.error('批量开通期货失败')
        }
      }
    }
    
    const batchEnableMargin = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号')
        return
      }
      
      try {
        await ElMessageBox.confirm(`确定要为选中的${selectedAccounts.value.length}个子账号开通杠杆吗？`, '批量开通杠杆', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const emails = selectedAccounts.value.map(account => account.email)
        const user = getCurrentUser()
        
        const response = await fetch('/api/subaccounts/batch-enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails: emails,
            feature: 'margin'
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          batchResults.value = result.results
          batchResultTitle.value = '批量开通杠杆结果'
          batchResultDialogVisible.value = true
          ElMessage.success(`成功为${result.success_count}/${result.total}个子账号开通杠杆`)
          // 刷新子账号列表
          refreshSubaccounts()
        } else {
          ElMessage.error(result.error || '批量开通杠杆失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量开通杠杆出错:', error)
          ElMessage.error('批量开通杠杆失败')
        }
      }
    }
    
    // 批量查询详情
    const batchQueryDetails = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请至少选择一个子账号')
        return
      }

      loading.value = true
      try {
        const emails = selectedAccounts.value.map(acc => acc.email)
        const user = getCurrentUser()
        const userIdValue = user?.username || user?.id || user?.userId

        const response = await fetch('/api/subaccounts/batch-details', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails,
            userId: userIdValue
          })
        })

        if (response.ok) {
          const result = await response.json()
          
          if (result.success) {
            batchResults.value = result.results.map(result => ({
              email: result.email,
              success: result.success,
              message: result.success ? '查询详情成功' : result.message || '查询详情失败'
            }))
            batchResultTitle.value = '批量查询详情结果'
            batchResultDialogVisible.value = true
            
            // 更新成功查询的账号信息
            if (result.accounts && result.accounts.length > 0) {
              const updatedAccounts = result.accounts
              updatedAccounts.forEach(updatedAcc => {
                const index = subaccounts.value.findIndex(acc => acc.email === updatedAcc.email)
                if (index !== -1) {
                  subaccounts.value[index] = { ...subaccounts.value[index], ...updatedAcc }
                }
              })
            }
            
            ElMessage.success('批量查询详情操作完成')
          } else {
            ElMessage.error(result.message || '批量查询详情失败')
          }
        } else {
          ElMessage.error('批量查询详情失败')
        }
      } catch (error) {
        console.error('批量查询详情错误:', error)
        ElMessage.error('批量查询详情发生错误: ' + (error.message || '未知错误'))
      } finally {
        loading.value = false
      }
    }
    
    // 批量查询余额
    const batchQueryBalance = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请至少选择一个子账号')
        return
      }

      loading.value = true
      try {
        const emails = selectedAccounts.value.map(acc => acc.email)
        const user = getCurrentUser()
        const userIdValue = user?.username || user?.id || user?.userId

        const response = await fetch('/api/subaccounts/batch-balance', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails,
            userId: userIdValue
          })
        })

        if (response.ok) {
          const result = await response.json()
          
          if (result.success) {
            batchResults.value = result.results.map(result => ({
              email: result.email,
              success: result.success,
              message: result.success 
                ? `查询成功: BTC=${result.btcVal || '0'}, USDT=${result.usdtVal || '0'}` 
                : result.message || '查询余额失败'
            }))
            batchResultTitle.value = '批量查询余额结果'
            batchResultDialogVisible.value = true
            
            // 更新余额信息
            if (result.balances && result.balances.length > 0) {
              const balances = result.balances
              balances.forEach(balance => {
                const index = subaccounts.value.findIndex(acc => acc.email === balance.email)
                if (index !== -1) {
                  subaccounts.value[index].balance = balance
                }
              })
            }
            
            ElMessage.success('批量查询余额操作完成')
          } else {
            ElMessage.error(result.message || '批量查询余额失败')
          }
        } else {
          ElMessage.error('批量查询余额失败')
        }
      } catch (error) {
        console.error('批量查询余额错误:', error)
        ElMessage.error('批量查询余额发生错误: ' + (error.message || '未知错误'))
      } finally {
        loading.value = false
      }
    }
    
    // 显示批量转账对话框
    const showBatchTransferDialog = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择子账号')
        return
      }
      batchTransferDialogVisible.value = true
    }
    
    // 显示创建账号对话框
    const showCreateAccountDialog = () => {
      createAccountDialogVisible.value = true
    }
    
    // 显示批量创建对话框
    const showBatchCreateDialog = () => {
      batchCreateDialogVisible.value = true
    }
    
    // 账号创建成功处理
    const handleAccountCreated = (newAccount) => {
      ElMessage.success('子账号创建成功')
      
      // 如果传入了新创建的账号信息，可以直接添加到列表中，避免重新请求API
      if (newAccount) {
        // 确保新账号有默认值
        const accountWithDefaults = {
          ...newAccount,
          status: newAccount.status || 'ACTIVE', 
          accountType: newAccount.accountType || 'VIRTUAL',
          features: newAccount.features || []
        }
        
        // 添加到列表顶部
        subaccounts.value.unshift(accountWithDefaults)
        totalSubaccounts.value++
      } else {
        // 否则重新获取列表
        fetchSubaccounts()
      }
    }
    
    // 批量账号创建成功处理
    const handleBatchAccountCreated = (result) => {
      const count = typeof result === 'number' ? result : (result?.success_count || 0)
      ElMessage.success(`成功创建${count}个子账号`)
      
      // 如果传入了新创建的账号列表，可以直接添加到现有列表中
      if (result && Array.isArray(result.accounts)) {
        // 确保每个新账号都有默认值
        const accountsWithDefaults = result.accounts.map(account => ({
          ...account,
          status: account.status || 'ACTIVE',
          accountType: account.accountType || 'VIRTUAL',
          features: account.features || []
        }))
        
        // 添加到列表顶部
        subaccounts.value = [...accountsWithDefaults, ...subaccounts.value]
        totalSubaccounts.value += accountsWithDefaults.length
      } else {
        // 否则重新获取列表
        fetchSubaccounts()
      }
    }
    
    // 转账成功处理
    const handleTransferSuccess = () => {
      ElMessage.success('转账操作成功')
    }
    
    // 批量转账成功处理
    const handleBatchTransferSuccess = () => {
      ElMessage.success('批量转账操作成功')
    }
    
    // 生命周期钩子
    onMounted(() => {
      getServerTime() // 在组件挂载时获取服务器时间
      fetchSubaccounts()
    })
    
    return {
      loading,
      currentPage,
      pageSize,
      totalSubaccounts,
      subaccounts,
      selectedAccounts,
      selectedAccount,
      createAccountDialogVisible,
      batchCreateDialogVisible,
      transferDialogVisible,
      batchTransferDialogVisible,
      batchResults,
      batchResultTitle,
      accountDetailsDialogVisible,
      batchResultDialogVisible,
      subaccountCount,
      hasSelectedAccounts,
      handlePageChange,
      handleSelectionChange,
      formatDate,
      getStatusType,
      getStatusText,
      getStatusDescription,
      getAccountTypeTag,
      getAccountTypeText,
      getFeatureTag,
      getFeatureText,
      refreshSubaccounts,
      exportData,
      exportSelected,
      viewAccountDetails,
      showTransferDialog,
      enableFutures,
      enableMargin,
      batchEnableFutures,
      batchEnableMargin,
      showBatchTransferDialog,
      showCreateAccountDialog,
      showBatchCreateDialog,
      handleAccountCreated,
      handleBatchAccountCreated,
      handleTransferSuccess,
      handleBatchTransferSuccess,
      getCurrentServerTime,
      batchQueryDetails,
      batchQueryBalance
    }
  }
}
</script>

<style scoped>
.subaccount-manage-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
  font-size: 1.8rem;
  color: #2c3e50;
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
}

.action-card {
  height: 100%;
  text-align: center;
}

.action-icon {
  font-size: 32px;
  margin-bottom: 15px;
  color: #409EFF;
}

.text-center {
  text-align: center;
}

.text-muted {
  color: #909399;
  font-size: 14px;
}

.batch-actions {
  border-bottom: 1px solid #EBEEF5;
  padding-bottom: 15px;
  margin-bottom: 15px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.hint-text {
  color: #909399;
  font-size: 12px;
}

.pagination-container {
  text-align: center;
  margin-top: 20px;
}

.navbar-container {
  width: 100%;
}

.flex-grow {
  flex-grow: 1;
}

.el-menu {
  display: flex;
}

/* 添加账号类型和功能标签的样式 */
.account-type-tag {
  margin-bottom: 5px;
  font-weight: 500;
}

.account-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.feature-tag {
  font-size: 10px !important;
  height: 20px !important;
  line-height: 18px !important;
  padding: 0 6px !important;
  border-radius: 10px !important;
}

/* 状态标签样式 */
.el-table .el-tag {
  border-radius: 12px;
  padding: 0 8px;
  font-weight: normal;
}

/* 调整表格样式 */
.el-table {
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 20px;
}

/* 批量操作按钮组样式 */
.batch-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  background-color: #f9f9f9;
  padding: 12px;
  border-radius: 6px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style> 