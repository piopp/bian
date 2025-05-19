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
      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><RefreshRight /></el-icon>
            <h3>账户激活</h3>
            <p class="text-muted">通过转账激活子账号</p>
            <el-button type="warning" @click="showBatchSelectDialog">激活账户</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主账户操作卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><Money /></el-icon>
            <h3>主账号资产</h3>
            <p class="text-muted">查询主账号的资产余额</p>
            <el-button type="primary" @click="showMasterAccountDialog">查看资产</el-button>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><Connection /></el-icon>
            <h3>统一账户</h3>
            <p class="text-muted">管理Portfolio Margin统一账户</p>
            <el-button type="success" @click="showUnifiedAccountDialog">统一账户管理</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="action-card">
          <div class="text-center">
            <el-icon class="action-icon"><Upload /></el-icon>
            <h3>导入API设置</h3>
            <p class="text-muted">导入API密钥到主账号或子账号</p>
            <div class="action-buttons">
              <el-button type="primary" @click="importApiSettings">导入API设置</el-button>
              <el-button type="info" @click="exportApiSettings">导出API设置</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 子账户划转卡片 -->
    <div class="action-card-container">
      <el-card class="action-card">
        <template #header>
          <div class="action-header">
            <span>子账户划转</span>
          </div>
        </template>
        <p>在子母账户之间或子账户之间进行资产划转</p>
        <el-button type="primary" @click="showUniversalTransferDialog">万能划转</el-button>
      </el-card>
    </div>

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
        <el-button
          type="success"
          @click="showBatchActivateDialog"
          :disabled="!hasSelectedAccounts"
        >
          <el-icon><CircleCheck /></el-icon>
          批量激活账户
        </el-button>
        <el-button
          type="primary"
          @click="showPositionModeDialog"
          :disabled="!hasSelectedAccounts"
        >
          <el-icon><Setting /></el-icon>
          批量设置持仓模式
        </el-button>
        <el-button
          type="warning"
          @click="showBatchLeverageDialog"
          :disabled="!hasSelectedAccounts"
        >
          <el-icon><Setting /></el-icon>
          批量设置杠杆
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
                  <el-dropdown-item @click="updateApiSettings(scope.row)">修改API</el-dropdown-item>
                  <el-dropdown-item @click="showLeverageSettingDialog(scope.row)">杠杆倍数设置</el-dropdown-item>
                  <el-dropdown-item divided @click="showActivateDialog(scope.row)">激活账户</el-dropdown-item>
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
      :activate-mode="batchActivateMode"
      @success="handleBatchTransferSuccess"
    />
    
    <account-details-dialog
      :visible="accountDetailsDialogVisible"
      @update:visible="accountDetailsDialogVisible = $event"
      :account="selectedAccount"
      @open-unified-account="handleOpenUnifiedAccount"
    />
    
    <batch-result-dialog
      :visible="batchResultDialogVisible"
      @update:visible="batchResultDialogVisible = $event"
      @view-details="handleViewDetailFromBatchResult"
      :results="batchResults"
      :title="batchResultTitle"
    />
    
    <account-activate-dialog
      :visible="accountActivateDialogVisible"
      @update:visible="accountActivateDialogVisible = $event"
      :account="selectedAccount"
      @success="handleActivateSuccess"
    />
    
    <!-- 万能划转对话框 -->
    <universal-transfer-dialog 
      :visible="universalTransferDialogVisible"
      @update:visible="universalTransferDialogVisible = $event"
      @success="handleTransferSuccess"
    />
    
    <!-- 杠杆账户查询对话框 -->
    <margin-account-dialog
      :visible="marginAccountDialogVisible"
      @update:visible="marginAccountDialogVisible = $event"
      :account="selectedAccount"
      :selected-accounts="selectedAccounts"
    />
    
    <!-- 市场交易对话框 -->
    <market-trade-dialog
      :visible="marketTradeDialogVisible"
      @update:visible="marketTradeDialogVisible = $event"
      :account="selectedAccount"
      :selected-accounts="selectedAccounts"
      @success="handleTradeSuccess"
      @open-arbitrage="handleOpenArbitrage"
    />

    <!-- 自动化套利对话框 -->
    <auto-arbitrage-dialog
      v-model="autoArbitrageDialogVisible"
      :account="arbitrageAccount"
      :selectedAccounts="arbitrageSelectedAccounts"
    />

    <!-- 主账号资产对话框 -->
    <master-account-dialog
      :visible="masterAccountDialogVisible"
      @update:visible="masterAccountDialogVisible = $event"
    />

    <!-- 更新子账号API对话框 -->
    <update-sub-account-api
      :visible="updateSubAccountApiVisible"
      @update:visible="updateSubAccountApiVisible = $event"
      :account-data="selectedAccount"
      @success="handleUpdateApiSuccess"
    />

    <!-- 统一账户管理对话框 -->
    <unified-account-dialog
      :visible="unifiedAccountDialogVisible"
      @update:visible="unifiedAccountDialogVisible = $event"
      :account="selectedAccount"
      :selected-accounts="selectedAccounts"
      @success="handleUnifiedAccountSuccess"
    />

    <!-- 持仓模式设置对话框 -->
    <el-dialog
      v-model="positionModeDialogVisible"
      title="设置持仓模式"
      width="500px"
    >
      <div>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="mb-3"
        >
          <p>为选中的 {{ selectedAccounts.length }} 个子账号设置持仓模式。</p>
          <p>请选择想要设置的持仓模式：</p>
        </el-alert>
        
        <el-form
          ref="positionModeFormRef"
          :model="positionModeForm"
          label-width="120px"
          label-position="right"
          class="mt-3"
        >
          <el-form-item label="持仓模式" prop="dualSidePosition">
            <el-radio-group v-model="positionModeForm.dualSidePosition">
              <el-radio :label="false">单向持仓</el-radio>
              <el-radio :label="true">双向持仓</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="positionModeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="setBatchPositionMode" :loading="positionModeLoading">
            确认设置
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 批量杠杆设置对话框 -->
    <el-dialog
      v-model="batchLeverageDialogVisible"
      title="批量设置杠杆倍数"
      width="500px"
    >
      <div>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="mb-3"
        >
          <p>为选中的 {{ selectedAccounts.length }} 个子账号设置杠杆倍数。</p>
          <p>杠杆倍数范围为1-125</p>
        </el-alert>
        
        <el-form
          ref="batchLeverageFormRef"
          :model="batchLeverageForm"
          label-width="120px"
          label-position="right"
          class="mt-3"
        >
          <el-form-item label="合约类型" prop="contractType">
            <el-radio-group v-model="batchLeverageForm.contractType">
              <el-radio label="UM">U本位合约</el-radio>
              <el-radio label="CM">币本位合约</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="交易对" prop="symbol">
            <el-select v-model="batchLeverageForm.symbol" placeholder="请选择交易对" style="width: 100%">
              <el-option label="BTCUSDT" value="BTCUSDT" />
              <el-option label="ETHUSDT" value="ETHUSDT" />
              <el-option label="BNBUSDT" value="BNBUSDT" />
              <el-option label="SOLUSDT" value="SOLUSDT" />
              <el-option label="DOGEUSDT" value="DOGEUSDT" />
              <el-option label="ADAUSDT" value="ADAUSDT" />
              <el-option label="XRPUSDT" value="XRPUSDT" />
              <el-option label="DOTUSDT" value="DOTUSDT" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="杠杆倍数" prop="leverage">
            <el-slider
              v-model="batchLeverageForm.leverage"
              :min="1"
              :max="125"
              :step="1"
              show-input
              show-stops
              :marks="{
                1: '1x',
                25: '25x',
                50: '50x',
                75: '75x',
                100: '100x',
                125: '125x'
              }"
            ></el-slider>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="batchLeverageDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="setBatchLeverage" :loading="batchLeverageLoading">
            确认设置
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 导入API设置对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入API设置" width="50%">
      <div class="mb-3">
        <label class="form-label">选择JSON文件</label>
        <el-upload
          class="upload-demo"
          action=""
          :auto-upload="false"
          :on-change="handleFileUpload"
          :limit="1"
          accept=".json"
        >
          <el-button type="primary">选择文件</el-button>
          <template #tip>
            <div class="el-upload__tip">只能上传JSON文件</div>
          </template>
        </el-upload>
      </div>
      <div class="mb-3">
        <label class="form-label">或直接粘贴JSON内容</label>
        <el-input
          v-model="apiJsonContent"
          type="textarea"
          :rows="10"
          placeholder='{"apiKey":"KdjFLprXQLbLzUnSqyU5uwMGOHIMlF87tEp6fDzpcEGwSVW4V2cuXdpZukL0p2bM","secretKey":"QEZRDcOOyNqlcPuISXBEQQmTlm5kMJcGuKwMmB6bpJ1EE0PNpS0P4XQUFxS0drq2","comment":"1"}'
        ></el-input>
      </div>
      <div class="mb-3">
        <el-radio-group v-model="importToMasterAccount">
          <el-radio :label="true">导入到主账号</el-radio>
          <el-radio :label="false">导入到子账号</el-radio>
        </el-radio-group>
      </div>
      <div class="mb-3" v-if="!importToMasterAccount">
        <label class="form-label">选择要应用设置的子账号</label>
        <el-select v-model="selectedImportAccount" class="w-100" placeholder="选择子账号">
          <el-option
            v-for="account in subaccounts"
            :key="account.email"
            :label="account.email"
            :value="account.email"
          ></el-option>
        </el-select>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmImport" :disabled="!canImport">
            导入
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { 
  Plus, User, Refresh, Download, 
  ArrowDown, InfoFilled, Money, CircleCheck, RefreshRight, Connection, Upload, Setting
} from '@element-plus/icons-vue'
import { getCurrentUser } from '../services/auth.js'
import CreateAccountDialog from './dialogs/CreateAccountDialog.vue'
import BatchCreateDialog from './dialogs/BatchCreateDialog.vue'
import TransferDialog from './dialogs/TransferDialog.vue'
import BatchTransferDialog from './dialogs/BatchTransferDialog.vue'
import AccountDetailsDialog from './dialogs/AccountDetailsDialog.vue'
import BatchResultDialog from './dialogs/BatchResultDialog.vue'
import AccountActivateDialog from './dialogs/AccountActivateDialog.vue'
import UniversalTransferDialog from './dialogs/UniversalTransferDialog.vue'
import MarginAccountDialog from './dialogs/MarginAccountDialog.vue'
import MarketTradeDialog from './dialogs/MarketTradeDialog.vue'
import AutoArbitrageDialog from './dialogs/AutoArbitrageDialog.vue'
import MasterAccountDialog from './dialogs/MasterAccountDialog.vue'
import UpdateSubAccountApi from './dialogs/UpdateSubAccountApi.vue'
import UnifiedAccountDialog from './dialogs/UnifiedAccountDialog.vue'

export default {
  name: 'SubAccountManagePage',
  components: {
    CreateAccountDialog,
    BatchCreateDialog, 
    TransferDialog,
    BatchTransferDialog,
    AccountDetailsDialog,
    BatchResultDialog,
    AccountActivateDialog,
    UniversalTransferDialog,
    MarginAccountDialog,
    MarketTradeDialog,
    AutoArbitrageDialog,
    MasterAccountDialog,
    UpdateSubAccountApi,
    UnifiedAccountDialog,
    Plus, User, Refresh, Download,
    ArrowDown, InfoFilled, Money, CircleCheck, RefreshRight, Connection, Upload, Setting
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
    const accountDetailsDialogVisible = ref(false)
    const batchResultDialogVisible = ref(false)
    const accountActivateDialogVisible = ref(false)
    const batchActivateMode = ref(false)
    const universalTransferDialogVisible = ref(false)
    const marginAccountDialogVisible = ref(false)
    const marketTradeDialogVisible = ref(false)
    const masterAccountDialogVisible = ref(false)
    const updateSubAccountApiVisible = ref(false)
    const unifiedAccountDialogVisible = ref(false)
    const importDialogVisible = ref(false)
    const leverageSettingDialogVisible = ref(false)
    const leverageLoading = ref(false)
    const positionModeDialogVisible = ref(false)
    const positionModeLoading = ref(false)
    const batchLeverageDialogVisible = ref(false)
    const batchLeverageLoading = ref(false)
    
    // 杠杆设置表单
    const leverageFormRef = ref(null)
    const leverageForm = ref({
      symbol: 'BTCUSDT',
      leverage: 20
    })
    
    // 持仓模式设置表单
    const positionModeFormRef = ref(null)
    const positionModeForm = ref({
      dualSidePosition: false // 默认单向持仓
    })
    
    // 批量杠杆设置表单
    const batchLeverageFormRef = ref(null)
    const batchLeverageForm = ref({
      contractType: 'UM',
      symbol: 'BTCUSDT',
      leverage: 20
    })
    
    // API导入相关变量
    const apiFile = ref(null)
    const apiJsonContent = ref('')
    const selectedImportAccount = ref('')
    const importToMasterAccount = ref(false)
    
    // 批量操作结果
    const batchResults = ref([])
    const batchResultTitle = ref('')
    
    // 自动化套利相关
    const autoArbitrageDialogVisible = ref(false)
    const arbitrageAccount = ref(null)
    const arbitrageSelectedAccounts = ref([])
    
    // 计算属性
    const subaccountCount = computed(() => subaccounts.value.length)
    const hasSelectedAccounts = computed(() => selectedAccounts.value.length > 0)
    
    // API导入相关计算属性
    const canImport = computed(() => {
      return (apiFile.value || (apiJsonContent.value.trim() !== '' && (importToMasterAccount.value || selectedImportAccount.value)))
    })
    
    // 获取当前用户ID
    const currentUser = ref(getCurrentUser())
    const userIdValue = currentUser.value?.id  // 只使用ID
    
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
          // 处理各种可能的数据结构
          let subaccountData = [];
          
          // 打印原始数据结构用于调试
          console.log('子账号API返回数据:', result);
          
          if (Array.isArray(result.data)) {
            // 直接是数组的情况
            subaccountData = result.data;
            console.log('API返回数据是直接数组, 长度:', subaccountData.length);
          } else if (result.data && result.data.subaccounts) {
            // 包含在subaccounts字段中的情况
            subaccountData = result.data.subaccounts;
            console.log('API返回数据包含在subaccounts字段中, 长度:', subaccountData.length);
          } else if (result.data) {
            // 其他可能的数据结构
            console.log('API返回数据结构不明确，尝试处理');
            if (typeof result.data === 'object' && !Array.isArray(result.data)) {
              // 可能是单个对象
              const keys = Object.keys(result.data);
              if (keys.length > 0 && Array.isArray(result.data[keys[0]])) {
                // 可能结构是 {someKey: [...]}
                subaccountData = result.data[keys[0]];
                console.log(`API返回数据包含在 ${keys[0]} 字段中, 长度:`, subaccountData.length);
              } else {
                // 作为单个对象处理
                subaccountData = [result.data];
                console.log('API返回数据作为单个对象处理');
              }
            }
          }
          
          if (Array.isArray(subaccountData) && subaccountData.length > 0) {
            // 确保每个子账号都有状态和类型字段，如果没有则添加默认值
            subaccounts.value = subaccountData.map(account => {
              const features = [];
              if (account.is_futures_enabled) features.push('FUTURES');
              if (account.is_margin_enabled) features.push('MARGIN');
              if (account.is_options_enabled) features.push('OPTIONS');
              
              return {
                ...account,
                status: account.status || 'ACTIVE',
                accountType: account.account_type || account.accountType || 'VIRTUAL',
                features: features,
                // 添加hasApiKey字段，确保前端显示正确
                hasApiKey: !!account.has_api_key || !!account.api_key || !!account.apiKey || !!account.api_secret_masked
              }
            });
            
            totalSubaccounts.value = result.data.total || subaccountData.length;
            console.log('成功处理子账号数据，数量:', subaccounts.value.length);
          } else {
            subaccounts.value = [];
            totalSubaccounts.value = 0;
            console.error('API返回数据无法转换为子账号列表:', result.data);
          }
        } else {
          ElMessage.error(result.error || '获取子账号列表失败');
        }
      } catch (error) {
        console.error('加载子账号列表出错:', error);
        ElMessage.error('加载子账号列表失败');
      } finally {
        loading.value = false;
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
      // 支持直接传入账户对象或仅包含email的对象
      if (account && account.email) {
        // 如果传入的是详细的账户对象
        if (account.details) {
          // 直接使用details作为账户对象
          selectedAccount.value = account.details
        } else {
          // 查找当前子账户列表中是否已有该账户信息
          const existingAccount = subaccounts.value.find(acc => acc.email === account.email)
          if (existingAccount) {
            selectedAccount.value = existingAccount
          } else {
            // 如果找不到现有账户信息，创建一个仅包含email的最小对象
            selectedAccount.value = {
              email: account.email
            }
          }
        }
        accountDetailsDialogVisible.value = true
      } else {
        ElMessage.warning('无法查看详情：账户信息不完整')
      }
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
        // 确保使用数字ID而不是用户名
        const userId = user?.id || 1  // 默认使用ID为1

        const response = await fetch('/api/subaccounts/batch-details', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails,
            user_id: userId  // 使用正确的参数名称和用户ID
          })
        })

        if (response.ok) {
          const result = await response.json()
          console.log('批量查询详情结果:', result)
          
          if (result.success) {
            // 准备详细的结果数据，包含完整的账户信息
            let detailsFound = false
            
            if (result.results && result.results.length > 0) {
              // 将详细信息添加到结果中
              batchResults.value = result.results.map(result => {
                // 保存详细信息的变量
                let detailData = null
                
                // 尝试从详情中获取详细数据
                if (result.details) {
                  detailData = result.details
                  detailsFound = true
                }
                
                return {
                  email: result.email,
                  success: result.success,
                  details: detailData, // 包含完整的账户详情
                  message: result.success 
                    ? (result.details ? '查询详情成功，详情已加载' : '查询成功，但无详细数据')
                    : result.message || result.error || '查询详情失败',
                  showDetailsButton: result.success && result.details // 如果有详情数据，显示查看详情按钮
                }
              })
            } else if (result.accounts && result.accounts.length > 0) {
              // 使用accounts数组
              batchResults.value = result.accounts.map(account => {
                detailsFound = true
                return {
                  email: account.email,
                  success: true,
                  details: account, // 直接使用账户对象
                  message: '查询详情成功，详情已加载',
                  showDetailsButton: true
                }
              })
            } else {
              batchResults.value = emails.map(email => ({
                email: email,
                success: false,
                message: '未返回有效的账户详情数据'
              }))
            }
            
            // 设置对话框标题并区分是否找到详情
            batchResultTitle.value = detailsFound 
              ? '批量查询详情结果 (包含详细信息)' 
              : '批量查询详情结果 (仅状态信息)'
            
            batchResultDialogVisible.value = true
            
            // 更新子账户列表中的账号信息
            if (result.accounts && result.accounts.length > 0) {
              const updatedAccounts = result.accounts
              updatedAccounts.forEach(updatedAcc => {
                const index = subaccounts.value.findIndex(acc => acc.email === updatedAcc.email)
                if (index !== -1) {
                  subaccounts.value[index] = { ...subaccounts.value[index], ...updatedAcc }
                }
              })
            }
            
            ElMessage.success(detailsFound 
              ? '批量查询详情操作完成，可查看详细信息' 
              : '批量查询详情操作完成')
          } else {
            ElMessage.error(result.message || result.error || '批量查询详情失败')
          }
        } else {
          ElMessage.error('批量查询详情失败，服务器返回错误状态码')
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
        // 确保使用数字ID而不是用户名
        const userId = user?.id || 1  // 默认使用ID为1

        const response = await fetch('/api/subaccounts/batch-balance', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ 
            emails,
            user_id: userId  // 使用正确的参数名称和用户ID
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
      batchActivateMode.value = false
      batchTransferDialogVisible.value = true
    }
    
    // 显示批量激活对话框
    const showBatchActivateDialog = () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择要激活的账号')
        return
      }
      
      // 使用万能划转对话框实现批量激活
      universalTransferDialogVisible.value = true;
      
      // 通过事件总线告知万能划转对话框为激活模式，预设批量子账号和账户类型
      // 延迟执行以确保组件已渲染
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('activate-accounts', {
          detail: {
            accounts: selectedAccounts.value,
            fromType: 'SPOT', // 主账号现货
            toType: 'MARGIN', // 子账号杠杆
            isBatchActivate: true,
            asset: 'USDT',
            defaultAmount: 50 // 默认激活金额
          }
        }));
      }, 100);
    }
    
    // 显示持仓模式对话框
    const showPositionModeDialog = () => {
      // 如果未选择任何账号，提示错误
      if (!hasSelectedAccounts.value) {
        ElMessage.warning('请先选择至少一个子账号')
        return
      }
      
      // 显示对话框
      positionModeDialogVisible.value = true
    }
    
    // 批量设置持仓模式
    const setBatchPositionMode = async () => {
      if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择要设置的子账号')
        return
      }
      
      try {
        positionModeLoading.value = true
        
        const mode = positionModeForm.value.dualSidePosition ? '双向持仓' : '单向持仓'
        
        // 确认操作
        await ElMessageBox.confirm(
          `确认要为选中的 ${selectedAccounts.value.length} 个子账号设置${mode}模式吗？`,
          '批量设置持仓模式',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const emails = selectedAccounts.value.map(account => account.email)
        const user = getCurrentUser()
        console.log('当前用户:', user)
        
        if (!user || !user.token) {
          ElMessage.error('用户未登录或无效，请重新登录')
          return
        }
        
        const results = []
        let successCount = 0
        let failedCount = 0
        
        // 创建加载提示
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量设置持仓模式 (0/${emails.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        })
        
        // 逐个设置，避免API限流
        for (let i = 0; i < emails.length; i++) {
          const email = emails[i]
          
          // 更新加载提示
          loadingInstance.setText(`正在设置持仓模式 (${i+1}/${emails.length})`)
          console.log(`处理账号 ${i+1}/${emails.length}: ${email}`)
          
          try {
            const requestData = {
              email: email,
              dualSidePosition: positionModeForm.value.dualSidePosition
            }
            console.log('请求数据:', requestData)
            
            const response = await fetch('/api/subaccounts/futures-positions/dual-side', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${user.token}`
              },
              body: JSON.stringify(requestData)
            })
            
            console.log('响应状态:', response.status)
            const responseText = await response.text()
            console.log('原始响应:', responseText)
            
            let result
            try {
              result = JSON.parse(responseText)
            } catch (e) {
              console.error('解析JSON失败:', e)
              result = { success: false, error: '解析响应失败' }
            }
            
            console.log('解析结果:', result)
            
            if (result.success) {
              successCount++
              results.push({
                email: email,
                success: true,
                message: `成功设置为${mode}`
              })
            } else {
              failedCount++
              results.push({
                email: email,
                success: false,
                message: result.error || '设置失败'
              })
            }
            
            // 添加延迟，避免API限流
            if (i < emails.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 300))
            }
          } catch (error) {
            console.error(`账号 ${email} 设置出错:`, error)
            failedCount++
            results.push({
              email: email,
              success: false,
              message: error.message || '请求出错'
            })
          }
        }
        
        // 关闭加载提示
        loadingInstance.close()
        
        // 显示结果
        batchResults.value = results
        batchResultTitle.value = '批量设置持仓模式结果'
        batchResultDialogVisible.value = true
        
        // 根据结果显示消息
        if (successCount > 0) {
          ElMessage.success(`成功为 ${successCount}/${emails.length} 个子账号设置${mode}`)
        }
        
        if (failedCount > 0) {
          ElMessage.warning(`${failedCount} 个子账号设置失败`)
        }
        
        // 关闭对话框
        positionModeDialogVisible.value = false
        
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量设置持仓模式出错:', error)
          ElMessage.error('批量设置持仓模式失败')
        }
      } finally {
        positionModeLoading.value = false
      }
    }
    
    // 显示创建账号对话框
    const showCreateAccountDialog = () => {
      createAccountDialogVisible.value = true
    }
    
    // 显示批量创建对话框
    const showBatchCreateDialog = () => {
      batchCreateDialogVisible.value = true
    }
    
    // 显示万能划转对话框
    const showUniversalTransferDialog = () => {
      console.log('打开万能划转对话框 - 当前状态:', universalTransferDialogVisible.value);
      universalTransferDialogVisible.value = true;
      console.log('对话框状态设置为:', universalTransferDialogVisible.value);
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
      ElMessage.success('划转操作已成功执行')
      refreshSubaccounts() // 更新子账户列表
    }
    
    // 批量转账成功处理
    const handleBatchTransferSuccess = () => {
      ElMessage.success('批量转账操作成功')
    }
    
    // 批量查询详情的显示处理
    const handleViewDetailFromBatchResult = (accountInfo) => {
      if (!accountInfo || !accountInfo.email) {
        ElMessage.warning('无法查看详情：账户信息不完整')
        return
      }

      // 如果有详情数据，直接使用
      if (accountInfo.details) {
        viewAccountDetails({
          email: accountInfo.email,
          details: accountInfo.details
        })
      } else {
        // 否则直接使用email查询详情
        viewAccountDetails({
          email: accountInfo.email
        })
      }
    }
    
    // 显示激活账户对话框
    const showActivateDialog = (account) => {
      selectedAccount.value = account
      accountActivateDialogVisible.value = true
    }
    
    // 处理账户激活成功事件
    const handleActivateSuccess = (result) => {
      ElMessage.success(`账户 ${result.email} 激活成功`)
      refreshSubaccounts() // 刷新列表以显示最新状态
    }
    
    // 显示批量选择对话框
    const showBatchSelectDialog = () => {
      if (subaccounts.value.length === 0) {
        ElMessage.warning('请先加载子账户列表')
        return
      }
      
      // 显示一个选择账户的弹窗
      ElMessageBox.alert(
        `请在下方子账户列表中勾选需要激活的账户，然后点击"批量转账"按钮进行激活。`,
        '账户激活说明',
        {
          confirmButtonText: '我知道了',
          type: 'info',
          callback: () => {
            // 滚动到子账户列表
            const tableElement = document.querySelector('.subaccount-manage-container .el-table')
            if (tableElement) {
              tableElement.scrollIntoView({ behavior: 'smooth' })
            }
          }
        }
      )
    }
    
    // 打开杠杆账户查询对话框
    const openMarginAccountDialog = (account) => {
      if (account) {
        // 如果传入了特定账号，使用单个账号模式
        selectedAccount.value = account;
      } else if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择至少一个子账号');
        return;
      }
      
      marginAccountDialogVisible.value = true;
    };
    
    // 打开市场交易对话框
    const openMarketTradeDialog = (account) => {
      if (account) {
        // 如果传入了特定账号，使用单个账号模式
        selectedAccount.value = account;
      } else if (selectedAccounts.value.length === 0) {
        ElMessage.warning('请先选择至少一个子账号');
        return;
      }
      
      marketTradeDialogVisible.value = true;
    };
    
    // 处理交易成功事件
    const handleTradeSuccess = (result) => {
      if (result && result.success) {
        ElMessage.success(`交易操作已成功执行，共 ${result.results.filter(r => r.success).length} 笔交易成功`);
        refreshSubaccounts(); // 更新子账户列表
      }
    };
    
    // 处理自动化套利事件
    const handleOpenArbitrage = (params) => {
      arbitrageAccount.value = params.account || null
      arbitrageSelectedAccounts.value = params.selectedAccounts || []
      autoArbitrageDialogVisible.value = true
    }
    
    // 显示市场交易对话框
    const showMarketTradeDialog = (account) => {
      selectedAccount.value = account
      marketTradeDialogVisible.value = true
    }
    
    // 显示主账号资产对话框
    const showMasterAccountDialog = () => {
      masterAccountDialogVisible.value = true
    }
    
    // 显示修改子账号API对话框
    const updateApiSettings = (account) => {
      selectedAccount.value = { ...account }
      updateSubAccountApiVisible.value = true
    }
    
    // 处理API更新成功
    const handleUpdateApiSuccess = () => {
      ElMessage.success('子账号API设置修改成功')
      refreshSubaccounts() // 刷新列表
    }
    
    // 显示统一账户对话框
    const showUnifiedAccountDialog = () => {
      if (selectedAccounts.value.length === 0 && !selectedAccount.value) {
        ElMessage.warning('请先选择一个子账号')
        return
      }
      unifiedAccountDialogVisible.value = true
    }
    
    // 从账户详情对话框打开统一账户管理
    const handleOpenUnifiedAccount = (account) => {
      selectedAccount.value = account
      unifiedAccountDialogVisible.value = true
    }
    
    // 处理统一账户操作成功
    const handleUnifiedAccountSuccess = () => {
      ElMessage.success('统一账户操作成功')
      refreshSubaccounts() // 刷新子账号列表
    }
    
    // 导入API设置相关方法
    const importApiSettings = () => {
      importDialogVisible.value = true
    }
    
    const handleFileUpload = (file) => {
      if (file && file.raw) {
        apiFile.value = file.raw
      }
    }
    
    const exportApiSettings = async () => {
      try {
        const user = getCurrentUser()
        const token = user?.token
        
        // 询问用户是否包含主账号API
        await ElMessageBox.confirm(
          '是否包含主账号API设置？',
          '导出API设置',
          {
            confirmButtonText: '是',
            cancelButtonText: '否',
            type: 'info'
          }
        ).then(async () => {
          // 包含主账号API
          const response = await fetch('/api/subaccounts/api-export?include_master=true', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (response.ok) {
            const data = await response.json()
            // 创建下载链接
            const dataStr = JSON.stringify(data, null, 2)
            const blob = new Blob([dataStr], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            
            // 创建下载链接并点击
            const link = document.createElement('a')
            link.href = url
            link.download = 'api-settings.json'
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            
            ElMessage.success('API设置导出成功(包含主账号)')
          } else {
            ElMessage.error('API设置导出失败')
          }
        }).catch(() => {
          // 不包含主账号API，仅导出子账号
          fetch('/api/subaccounts/api-export', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }).then(async response => {
            if (response.ok) {
              const data = await response.json()
              // 创建下载链接
              const dataStr = JSON.stringify(data, null, 2)
              const blob = new Blob([dataStr], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              
              // 创建下载链接并点击
              const link = document.createElement('a')
              link.href = url
              link.download = 'api-settings.json'
              document.body.appendChild(link)
              link.click()
              document.body.removeChild(link)
              
              ElMessage.success('API设置导出成功(仅子账号)')
            } else {
              ElMessage.error('API设置导出失败')
            }
          })
        })
      } catch (error) {
        if (error !== 'cancel') {
          console.error('导出API设置出错:', error)
          ElMessage.error('API设置导出失败: ' + error.message)
        }
      }
    }
    
    const confirmImport = async () => {
      const user = getCurrentUser()
      const token = user?.token
      
      if (apiFile.value) {
        const formData = new FormData()
        formData.append('file', apiFile.value)
        
        try {
          const response = await fetch('/api/subaccounts/api-import', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`
            },
            body: formData
          })
          
          if (response.ok) {
            const result = await response.json()
            
            importDialogVisible.value = false
            apiFile.value = null
            apiJsonContent.value = ''
            selectedImportAccount.value = ''
            importToMasterAccount.value = false
            
            // 刷新子账号列表
            await refreshSubaccounts()
            
            ElMessage.success(`API设置导入成功: ${result.success_count || 0}个成功`)
          } else {
            const errResult = await response.json()
            ElMessage.error('API设置导入失败: ' + (errResult.error || '未知错误'))
          }
        } catch (error) {
          console.error('API设置导入出错:', error)
          ElMessage.error('API设置导入失败: ' + error.message)
        }
      } else if (apiJsonContent.value.trim() !== '') {
        try {
          // 验证JSON格式
          let jsonData
          try {
            jsonData = JSON.parse(apiJsonContent.value)
          } catch (jsonError) {
            ElMessage.error('JSON格式无效，请检查输入')
            return
          }
          
          // 如果是导入到主账号
          if (importToMasterAccount.value) {
            // 创建符合后端格式的数据结构
            const apiSettings = {
              settings: {
                "master_account": {
                  apiKey: jsonData.apiKey,
                  apiSecret: jsonData.secretKey || jsonData.apiSecret
                }
              },
              is_master_account: true
            }
            
            const response = await fetch('/api/subaccounts/api-import', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify(apiSettings)
            })
            
            if (response.ok) {
              importDialogVisible.value = false
              apiJsonContent.value = ''
              importToMasterAccount.value = false
              
              ElMessage.success('主账号API设置导入成功')
            } else {
              const errResult = await response.json()
              ElMessage.error('主账号API设置导入失败: ' + (errResult.error || '未知错误'))
            }
          }
          // 如果是导入到子账号且选择了子账号
          else if (selectedImportAccount.value) {
            // 添加邮箱信息
            const email = selectedImportAccount.value
            
            // 创建符合后端格式的数据结构
            const apiSettings = {
              settings: {
                [email]: {
                  apiKey: jsonData.apiKey,
                  apiSecret: jsonData.secretKey || jsonData.apiSecret
                }
              }
            }
            
            const response = await fetch('/api/subaccounts/api-import', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify(apiSettings)
            })
            
            if (response.ok) {
              const result = await response.json()
              
              importDialogVisible.value = false
              apiJsonContent.value = ''
              selectedImportAccount.value = ''
              
              // 刷新子账号列表
              await refreshSubaccounts()
              
              ElMessage.success(`API设置导入成功: ${result.count || 0}个成功`)
            } else {
              const errResult = await response.json()
              ElMessage.error('API设置导入失败: ' + (errResult.error || '未知错误'))
            }
          }
        } catch (error) {
          console.error('API设置导入出错:', error)
          ElMessage.error('API设置导入失败: ' + error.message)
        }
      } else {
        ElMessage.warning('请选择文件或输入JSON内容并选择账号')
      }
    }
    
    // 生命周期钩子
    onMounted(() => {
      getServerTime() // 在组件挂载时获取服务器时间
      fetchSubaccounts()
    })
    
    // 显示批量杠杆设置对话框
    const showBatchLeverageDialog = () => {
      // 如果未选择任何账号，提示错误
      if (!hasSelectedAccounts.value) {
        ElMessage.warning('请先选择至少一个子账号')
        return
      }
      
      // 显示对话框
      batchLeverageDialogVisible.value = true
    }
    
    // 批量设置杠杆倍数
    const setBatchLeverage = async () => {
      try {
        // 确认操作
        await ElMessageBox.confirm(
          `确定为选中的${selectedAccounts.value.length}个子账号设置杠杆倍数为${batchLeverageForm.value.leverage}吗？`,
          '确认设置杠杆倍数',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        // 设置加载状态
        batchLeverageLoading.value = true
        
        const emails = selectedAccounts.value.map(account => account.email)
        const user = getCurrentUser()
        
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效')
          batchLeverageLoading.value = false
          return
        }
        
        // 创建API请求数据
        const requestData = {
          emails: emails,
          symbol: batchLeverageForm.value.symbol,
          leverage: batchLeverageForm.value.leverage,
          contractType: batchLeverageForm.value.contractType
        }
        
        console.log('批量设置杠杆请求数据:', requestData)
        
        // 创建加载提示
        const loadingInstance = ElLoading.service({
          lock: true,
          text: `正在批量设置杠杆倍数 (0/${emails.length})`,
          background: 'rgba(0, 0, 0, 0.7)'
        })
        
        try {
          // 发送API请求
          const response = await fetch('/api/subaccounts/portfolio-margin/um/batch-leverage', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${user.token}`
            },
            body: JSON.stringify(requestData)
          })
          
          loadingInstance.close()
          
          if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`)
          }
          
          const result = await response.json()
          
          if (result.success) {
            // 处理成功响应
            const { success_count, failed_count, total, results } = result.data
            
            // 显示结果
            batchResults.value = results.map(res => ({
              email: res.email,
              success: res.success,
              message: res.success ? `杠杆倍数设置成功: ${batchLeverageForm.value.leverage}x` : (res.error || '未知错误')
            }))
            
            batchResultTitle.value = '批量设置杠杆倍数结果'
            batchResultDialogVisible.value = true
            
            // 根据结果显示消息
            if (success_count > 0) {
              ElMessage.success(`成功为 ${success_count}/${total} 个子账号设置杠杆倍数为 ${batchLeverageForm.value.leverage}x`)
            }
            
            if (failed_count > 0) {
              ElMessage.warning(`${failed_count} 个子账号设置失败`)
            }
            
          } else {
            // 处理失败响应
            ElMessage.error(`批量设置杠杆倍数失败: ${result.error || '未知错误'}`)
          }
          
        } catch (error) {
          loadingInstance.close()
          console.error('批量设置杠杆倍数网络请求错误:', error)
          ElMessage.error(`批量设置杠杆倍数请求错误: ${error.message}`)
        }
        
        // 关闭对话框
        batchLeverageDialogVisible.value = false
        
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量设置杠杆倍数出错:', error)
          ElMessage.error('批量设置杠杆倍数失败')
        }
      } finally {
        batchLeverageLoading.value = false
      }
    }
    
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
      accountActivateDialogVisible,
      batchActivateMode,
      universalTransferDialogVisible,
      marginAccountDialogVisible,
      marketTradeDialogVisible,
      masterAccountDialogVisible,
      updateSubAccountApiVisible,
      unifiedAccountDialogVisible,
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
      showBatchActivateDialog,
      showCreateAccountDialog,
      showBatchCreateDialog,
      handleAccountCreated,
      handleBatchAccountCreated,
      handleTransferSuccess,
      handleBatchTransferSuccess,
      getCurrentServerTime,
      batchQueryDetails,
      batchQueryBalance,
      handleViewDetailFromBatchResult,
      showActivateDialog,
      handleActivateSuccess,
      showBatchSelectDialog,
      showUniversalTransferDialog,
      openMarginAccountDialog,
      openMarketTradeDialog,
      handleTradeSuccess,
      autoArbitrageDialogVisible,
      arbitrageAccount,
      arbitrageSelectedAccounts,
      handleOpenArbitrage,
      showMarketTradeDialog,
      showMasterAccountDialog,
      updateApiSettings,
      handleUpdateApiSuccess,
      showUnifiedAccountDialog,
      handleOpenUnifiedAccount,
      handleUnifiedAccountSuccess,
      importDialogVisible,
      apiFile,
      apiJsonContent,
      selectedImportAccount,
      importToMasterAccount,
      canImport,
      importApiSettings,
      handleFileUpload,
      exportApiSettings,
      confirmImport,
      leverageSettingDialogVisible,
      leverageLoading,
      leverageFormRef,
      leverageForm,
      positionModeDialogVisible,
      positionModeLoading,
      positionModeFormRef,
      positionModeForm,
      showPositionModeDialog,
      setBatchPositionMode,
      batchLeverageDialogVisible,
      batchLeverageLoading,
      batchLeverageFormRef,
      batchLeverageForm,
      showBatchLeverageDialog,
      setBatchLeverage
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