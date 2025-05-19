<template>
  <el-dialog
    title="统一账户管理"
    v-model="dialogVisible"
    width="800px"
    :close-on-click-modal="false"
    class="unified-account-dialog"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <p>统一账户是币安的Portfolio Margin账户，将现货、合约和杠杆交易整合在一起，共享风险和保证金。</p>
    </el-alert>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane label="账户概览" name="overview">
        <div v-loading="loading.overview">
          <el-descriptions v-if="accountData" :column="2" border>
            <el-descriptions-item label="账号邮箱" span="2">{{ selectedAccount?.email }}</el-descriptions-item>
            <el-descriptions-item label="账户状态">
              <el-tag :type="accountData.portfolioMarginEnabled ? 'success' : 'info'">
                {{ accountData.portfolioMarginEnabled ? '已开启统一账户' : '未开启统一账户' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="账户类型">
              {{ accountData.accountType || 'N/A' }}
            </el-descriptions-item>
            
            <!-- 新增统一账户特有的字段 -->
            <el-descriptions-item label="钱包余额">
              {{ accountData.totalWalletBalance || '0' }}
            </el-descriptions-item>
            <el-descriptions-item label="可用余额">
              {{ accountData.totalAvailableBalance || '0' }}
            </el-descriptions-item>
            
            <el-descriptions-item label="未实现盈亏" span="2">
              <span :class="{ 'positive-value': parseFloat(accountData.totalUnrealizedProfit || 0) > 0, 'negative-value': parseFloat(accountData.totalUnrealizedProfit || 0) < 0 }">
                {{ accountData.totalUnrealizedProfit || '0' }}
              </span>
            </el-descriptions-item>
            
            <el-descriptions-item label="保证金余额">
              {{ accountData.totalMarginBalance || '0' }}
            </el-descriptions-item>
            <el-descriptions-item label="最大可提款金额">
              {{ accountData.maxWithdrawAmount || '0' }}
            </el-descriptions-item>
            
            <el-descriptions-item label="初始保证金">
              {{ accountData.totalInitialMargin || '0' }}
            </el-descriptions-item>
            <el-descriptions-item label="维持保证金">
              {{ accountData.totalMaintMargin || '0' }}
            </el-descriptions-item>
          </el-descriptions>
          
          <!-- 调试信息区域 - 开发环境可见 -->
          <div v-if="accountData" class="debug-info">
            <el-divider>调试信息</el-divider>
            <el-button size="small" type="info" @click="showDebugInfo = !showDebugInfo">
              {{ showDebugInfo ? '隐藏' : '显示' }}原始数据
            </el-button>
            <pre v-if="showDebugInfo" class="json-data">{{ JSON.stringify(accountData, null, 2) }}</pre>
          </div>
          
          <div v-if="!accountData" class="empty-data">
            <el-empty description="暂无统一账户数据"></el-empty>
            <el-button type="primary" @click="queryAccountData">刷新数据</el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="资产余额" name="balance">
        <div v-loading="loading.balance">
          <div class="operation-bar">
            <el-button type="primary" size="small" @click="refreshBalance">
              <el-icon><Refresh /></el-icon> 刷新余额
            </el-button>
          </div>
          
          <el-table
            v-if="accountData && accountData.assets && accountData.assets.length > 0"
            :data="accountData.assets"
            style="width: 100%"
            border
            max-height="400px"
          >
            <el-table-column prop="asset" label="币种" width="100"></el-table-column>
            <el-table-column prop="walletBalance" label="钱包余额" width="150">
              <template #default="scope">
                {{ formatNumber(scope.row.walletBalance) }}
              </template>
            </el-table-column>
            <el-table-column prop="unrealizedProfit" label="未实现盈亏" width="150">
              <template #default="scope">
                <span :class="parseFloat(scope.row.unrealizedProfit || 0) >= 0 ? 'positive-value' : 'negative-value'">
                  {{ formatNumber(scope.row.unrealizedProfit) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="marginBalance" label="保证金余额" width="150">
              <template #default="scope">
                {{ formatNumber(scope.row.marginBalance) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="scope">
                <el-button size="small" type="primary" @click="showTransferDialog(scope.row)">划转</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 如果没有assets数据，则依然显示之前的balanceData -->
          <el-table
            v-else-if="balanceData && balanceData.length > 0"
            :data="balanceData"
            style="width: 100%"
            border
            max-height="400px"
          >
            <el-table-column prop="asset" label="币种" width="100"></el-table-column>
            <el-table-column prop="free" label="可用余额" width="150">
              <template #default="scope">
                {{ formatNumber(scope.row.free) }}
              </template>
            </el-table-column>
            <el-table-column prop="locked" label="锁定余额" width="150">
              <template #default="scope">
                {{ formatNumber(scope.row.locked) }}
              </template>
            </el-table-column>
            <el-table-column prop="usdtValuation" label="USDT估值" width="150">
              <template #default="scope">
                {{ formatNumber(scope.row.usdtValuation) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="scope">
                <el-button size="small" type="primary" @click="showTransferDialog(scope.row)">划转</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div v-else class="empty-data">
            <el-empty description="暂无资产数据"></el-empty>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="合约持仓" name="positions">
        <div class="dialog-toolbar">
          <el-button @click="refreshPositions" :loading="loading.positions">
            <el-icon><Refresh /></el-icon> 刷新持仓
          </el-button>
        </div>
        
        <div class="um-positions-section">
          <h4>U本位合约持仓</h4>
          <el-table 
            :data="positionsData.filter(p => p.marginType === 'cross')" 
            style="width: 100%" 
            v-loading="loading.positions"
          >
            <el-table-column prop="symbol" label="交易对" width="120"></el-table-column>
            <el-table-column prop="positionSide" label="方向" width="80">
              <template #default="scope">
                {{ scope.row.positionSide === 'LONG' ? '多' : '空' }}
              </template>
            </el-table-column>
            <el-table-column prop="entryPrice" label="开仓均价" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.entryPrice).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="markPrice" label="标记价格" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.markPrice).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="positionAmt" label="持仓数量" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.positionAmt).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="unrealizedProfit" label="未实现盈亏" width="130">
              <template #default="scope">
                <span :class="parseFloat(scope.row.unrealizedProfit) >= 0 ? 'profit' : 'loss'">
                  {{ parseFloat(scope.row.unrealizedProfit).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="leverage" label="杠杆" width="80">
              <template #default="scope">
                {{ scope.row.leverage || '1' }}x
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <div class="button-group">
                  <el-button size="small" type="primary" @click="showLeverageDialog(scope.row)">
                    调整杠杆
                  </el-button>
                <el-button size="small" type="danger" @click="closeUmPosition(scope.row)">平仓</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="positionsData.filter(p => p.marginType === 'cross').length === 0" description="暂无持仓数据"></el-empty>
        </div>
        
        <div class="cm-positions-section" style="margin-top: 20px;">
          <h4>币本位合约持仓</h4>
          <el-table 
            :data="cmPositionsData.filter(p => p.marginType === 'cross')" 
            style="width: 100%" 
            v-loading="loading.cmPositions"
          >
            <el-table-column prop="symbol" label="交易对" width="120"></el-table-column>
            <el-table-column prop="positionSide" label="方向" width="80">
              <template #default="scope">
                {{ scope.row.positionSide === 'LONG' ? '多' : '空' }}
              </template>
            </el-table-column>
            <el-table-column prop="entryPrice" label="开仓均价" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.entryPrice).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="markPrice" label="标记价格" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.markPrice).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="positionAmt" label="持仓数量" width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.positionAmt).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="unrealizedProfit" label="未实现盈亏" width="130">
              <template #default="scope">
                <span :class="parseFloat(scope.row.unrealizedProfit) >= 0 ? 'profit' : 'loss'">
                  {{ parseFloat(scope.row.unrealizedProfit).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button size="small" type="danger" @click="closeCmPosition(scope.row)">平仓</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="cmPositionsData.filter(p => p.marginType === 'cross').length === 0" description="暂无币本位持仓数据"></el-empty>
        </div>
      </el-tab-pane>

      <el-tab-pane label="划转记录" name="transfers">
        <div v-loading="loading.transfers">
          <div class="operation-bar">
            <el-button type="primary" size="small" @click="refreshTransfers">
              <el-icon><Refresh /></el-icon> 刷新记录
            </el-button>
          </div>
          
          <el-table
            v-if="transfersData && transfersData.length > 0"
            :data="transfersData"
            style="width: 100%"
            border
            max-height="400px"
          >
            <el-table-column prop="asset" label="币种" width="100"></el-table-column>
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="scope">
                {{ formatNumber(scope.row.amount) }}
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="180">
              <template #default="scope">
                <el-tag 
                  :type="scope.row.type === 'MAIN_PORTFOLIO_MARGIN' ? 'success' : 'danger'"
                  size="small"
                >
                  {{ scope.row.type === 'MAIN_PORTFOLIO_MARGIN' ? '现货→统一账户' : '统一账户→现货' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="fromAccountType" label="转出账户" width="120">
              <template #default="scope">
                {{ getAccountTypeText(scope.row.fromAccountType) }}
              </template>
            </el-table-column>
            <el-table-column prop="toAccountType" label="转入账户" width="120">
              <template #default="scope">
                {{ getAccountTypeText(scope.row.toAccountType) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag 
                  :type="scope.row.status === 'CONFIRMED' ? 'success' : scope.row.status === 'PENDING' ? 'warning' : 'info'"
                  size="small"
                >
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="timestamp" label="时间" min-width="160">
              <template #default="scope">
                {{ formatDate(scope.row.timestamp) }}
              </template>
            </el-table-column>
          </el-table>
          
          <div v-else class="empty-data">
            <el-empty description="暂无划转记录"></el-empty>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="showTransferDialog(null)" :disabled="!accountData || !accountData.portfolioMarginEnabled">
          <el-icon><Connection /></el-icon> 资产划转
        </el-button>
        <el-button 
          v-if="accountData && !accountData.portfolioMarginEnabled" 
          type="success" 
          @click="enableUnifiedAccount"
          :loading="loading.enable"
        >
          开通统一账户
        </el-button>
      </div>
    </template>

    <!-- 划转对话框 -->
    <el-dialog
      v-model="transferDialogVisible"
      title="统一账户资产划转"
      width="500px"
      append-to-body
    >
      <el-form
        ref="transferFormRef"
        :model="transferForm"
        :rules="transferRules"
        label-width="120px"
        label-position="right"
      >
        <el-form-item label="币种" prop="asset">
          <el-select v-model="transferForm.asset" placeholder="请选择币种" style="width: 100%">
            <el-option
              v-for="coin in commonCoins"
              :key="coin.value"
              :label="coin.label"
              :value="coin.value"
            ></el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="转出账户类型" prop="fromType">
          <el-select v-model="transferForm.fromType" placeholder="请选择转出账户类型" style="width: 100%">
            <el-option
              v-for="type in accountTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            ></el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="转入账户类型" prop="toType">
          <el-select v-model="transferForm.toType" placeholder="请选择转入账户类型" style="width: 100%">
            <el-option
              v-for="type in accountTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
              :disabled="type.value === transferForm.fromType"
            ></el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="转账金额" prop="amount">
          <el-input v-model="transferForm.amount" type="number" placeholder="请输入转账金额">
            <template #append>{{ transferForm.asset }}</template>
          </el-input>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="transferDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitTransfer" :loading="loading.transferSubmit">确认划转</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 批量平仓对话框 -->
    <el-dialog
      v-model="closePositionDialogVisible"
      title="批量平仓"
      width="500px"
      append-to-body
    >
      <el-table
        v-if="positionsData && positionsData.length > 0"
        :data="positionsData"
        style="width: 100%"
        border
        max-height="400px"
        @selection-change="handleClosePositionSelectionChange"
      >
        <el-table-column type="selection" width="55"></el-table-column>
        <el-table-column prop="symbol" label="交易对" width="120"></el-table-column>
        <el-table-column prop="positionAmt" label="持仓数量" width="120">
          <template #default="scope">
            <span :class="{'positive-value': parseFloat(scope.row.positionAmt) > 0, 'negative-value': parseFloat(scope.row.positionAmt) < 0}">
              {{ formatNumber(scope.row.positionAmt) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="unRealizedProfit" label="未实现盈亏" width="120">
          <template #default="scope">
            <span :class="{'positive-value': parseFloat(scope.row.unRealizedProfit) > 0, 'negative-value': parseFloat(scope.row.unRealizedProfit) < 0}">
              {{ formatNumber(scope.row.unRealizedProfit) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
      
      <div v-else class="empty-data">
        <el-empty description="暂无持仓数据"></el-empty>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closePositionDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="submitClosePositions" :loading="loading.closePositions" :disabled="selectedPositions.length === 0">
            确认平仓 ({{ selectedPositions.length }}个)
          </el-button>
        </div>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Connection } from '@element-plus/icons-vue'
import { getCurrentUser } from '../../services/auth'

export default {
  name: 'UnifiedAccountDialog',
  components: {
    Refresh,
    Connection
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    account: {
      type: Object,
      default: null
    },
    selectedAccounts: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:visible', 'success'],
  setup(props, { emit }) {
    // 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 当前选中的账户
    const selectedAccount = computed(() => {
      return props.account || (props.selectedAccounts && props.selectedAccounts.length > 0 ? props.selectedAccounts[0] : null)
    })
    
    // 选项卡
    const activeTab = ref('overview')
    
    // 调试信息显示状态
    const showDebugInfo = ref(false)
    
    // 加载状态
    const loading = ref({
      overview: false,
      balance: false,
      positions: false,
      transfers: false,
      enable: false,
      transferSubmit: false,
      closePositions: false,
      cmPositions: false
    })
    
    // 数据存储
    const accountData = ref(null)
    const balanceData = ref([])
    const positionsData = ref([])
    const cmPositionsData = ref([])
    const transfersData = ref([])
    
    // 划转对话框
    const transferDialogVisible = ref(false)
    const transferFormRef = ref(null)
    const transferForm = ref({
      asset: 'USDT',
      fromType: 'SPOT',
      toType: 'MARGIN',
      amount: ''
    })
    
    // 平仓对话框
    const closePositionDialogVisible = ref(false)
    const selectedPositions = ref([])
    
    // 常用币种列表
    const commonCoins = [
      { label: 'USDT - 泰达币', value: 'USDT' },
      { label: 'BTC - 比特币', value: 'BTC' },
      { label: 'BNB - 币安币', value: 'BNB' },
      { label: 'ETH - 以太坊', value: 'ETH' },
      { label: 'SOL - 索拉纳', value: 'SOL' },
      { label: 'ADA - 艾达币', value: 'ADA' },
      { label: 'XRP - 瑞波币', value: 'XRP' },
      { label: 'DOGE - 狗狗币', value: 'DOGE' }
    ]
    
    // 账户类型列表
    const accountTypes = [
      { label: '现货账户', value: 'SPOT' },
      { label: 'U本位合约', value: 'FUTURES' },
      { label: '杠杆账户', value: 'MARGIN' },
      { label: '币本位合约', value: 'COIN_FUTURES' },
      { label: '资金账户', value: 'FUNDING' }
    ]
    
    // 表单验证规则
    const transferRules = {
      asset: [
        { required: true, message: '请选择币种', trigger: 'change' }
      ],
      fromType: [
        { required: true, message: '请选择转出账户类型', trigger: 'change' }
      ],
      toType: [
        { required: true, message: '请选择转入账户类型', trigger: 'change' }
      ],
      amount: [
        { required: true, message: '请输入转账金额', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value === '') {
              callback(new Error('转账金额不能为空'))
            } else if (isNaN(Number(value)) || Number(value) <= 0) {
              callback(new Error('请输入大于0的有效金额'))
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ]
    }
    
    // 监听对话框显示状态
    watch(() => props.visible, (newVal) => {
      if (newVal && selectedAccount.value) {
        queryAccountData()
      }
    })
    
    // 查询账户数据
    const queryAccountData = async () => {
      if (!selectedAccount.value || !selectedAccount.value.email) {
        ElMessage.warning('请先选择账号')
        return
      }
      
      loading.value.overview = true
      try {
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/account', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          // 直接使用API返回的数据，统一账户数据结构已调整
          accountData.value = result.data
          console.log('统一账户数据:', JSON.stringify(result.data))
          
          // 自动加载其他模块的数据
          refreshBalance()
          refreshPositions()
          refreshTransfers()
        } else {
          ElMessage.error(result.error || '获取统一账户数据失败')
        }
      } catch (error) {
        console.error('获取统一账户数据出错:', error)
        ElMessage.error('获取统一账户数据失败')
      } finally {
        loading.value.overview = false
      }
    }
    
    // 刷新余额数据
    const refreshBalance = async () => {
      if (!selectedAccount.value || !selectedAccount.value.email) {
        ElMessage.warning('请先选择账号')
        return
      }
      
      loading.value.balance = true
      try {
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/balance', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          balanceData.value = result.data || []
        } else {
          ElMessage.error(result.error || '获取余额数据失败')
        }
      } catch (error) {
        console.error('获取余额数据出错:', error)
        ElMessage.error('获取余额数据失败')
      } finally {
        loading.value.balance = false
      }
    }
    
    // 刷新持仓数据
    const refreshPositions = async () => {
      if (!selectedAccount.value || !selectedAccount.value.email) {
        ElMessage.warning('请先选择账号')
        return
      }
      
      // 1. 获取U本位合约持仓
      loading.value.positions = true
      try {
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/um/positions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          positionsData.value = result.data || []
          console.log('已获取U本位合约持仓:', positionsData.value.length)
        } else {
          ElMessage.error(result.error || '获取U本位持仓数据失败')
        }
      } catch (error) {
        console.error('获取U本位持仓数据出错:', error)
        ElMessage.error('获取U本位持仓数据失败')
      } finally {
        loading.value.positions = false
      }
      
      // 2. 获取币本位合约持仓
      loading.value.cmPositions = true
      try {
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/cm/positions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          cmPositionsData.value = result.data || []
          console.log('已获取币本位合约持仓:', cmPositionsData.value.length)
        } else {
          ElMessage.error(result.error || '获取币本位持仓数据失败')
        }
      } catch (error) {
        console.error('获取币本位持仓数据出错:', error)
        ElMessage.error('获取币本位持仓数据失败')
      } finally {
        loading.value.cmPositions = false
      }
    }
    
    // 刷新划转记录
    const refreshTransfers = async () => {
      if (!selectedAccount.value || !selectedAccount.value.email) {
        ElMessage.warning('请先选择账号')
        return
      }
      
      loading.value.transfers = true
      try {
        console.log('开始获取转账历史数据')
        const user = getCurrentUser()
        
        // 尝试多种类型的转账查询
        const requestData = {
          email: selectedAccount.value.email,
          limit: 50
        }
        
        console.log('转账历史查询参数:', JSON.stringify(requestData))
        
        const response = await fetch('/api/subaccounts/portfolio-margin/transfer-history', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify(requestData)
        })
        
        const result = await response.json()
        console.log('转账历史API返回结果:', result)
        
        if (result.success) {
          // 确保数据是数组
          const transfers = Array.isArray(result.data) ? result.data : []
          transfersData.value = transfers
          console.log(`获取到 ${transfers.length} 条转账历史记录`)
          
          if (result.message) {
            console.log('转账历史消息:', result.message)
          }
          
          if (transfers.length === 0) {
            // 显示提示消息但不报错
            ElMessage.info(result.message || '暂无划转记录')
          }
        } else {
          // 即使API返回错误，也不应该阻止用户使用其他功能
          console.error('获取转账历史失败:', result.error)
          ElMessage.warning(result.error || '获取划转记录失败')
          transfersData.value = []
        }
      } catch (error) {
        console.error('获取转账历史出错:', error)
        ElMessage.warning('获取划转记录失败，但您仍可使用其他功能')
        transfersData.value = []
      } finally {
        loading.value.transfers = false
      }
    }
    
    // 开通统一账户
    const enableUnifiedAccount = async () => {
      if (!selectedAccount.value || !selectedAccount.value.email) {
        ElMessage.warning('请先选择账号')
        return
      }
      
      try {
        await ElMessageBox.confirm(
          `确定要为子账号 ${selectedAccount.value.email} 开通统一账户吗？`,
          '开通统一账户确认',
          {
            confirmButtonText: '确认开通',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        loading.value.enable = true
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          ElMessage.success('成功开通统一账户')
          queryAccountData() // 刷新账户数据
        } else {
          ElMessage.error(result.error || '开通统一账户失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('开通统一账户出错:', error)
          ElMessage.error('开通统一账户失败')
        }
      } finally {
        loading.value.enable = false
      }
    }
    
    // 显示划转对话框
    const showTransferDialog = (asset) => {
      transferForm.value = {
        asset: asset ? asset.asset : 'USDT',
        fromType: 'SPOT',
        toType: 'MARGIN',
        amount: ''
      }
      transferDialogVisible.value = true
    }
    
    // 提交划转
    const submitTransfer = async () => {
      if (!transferFormRef.value) return
      
      transferFormRef.value.validate(async (valid) => {
        if (!valid) return
        
        try {
          await ElMessageBox.confirm(
            `确认要从 ${getAccountTypeText(transferForm.value.fromType)} 转移 ${transferForm.value.amount} ${transferForm.value.asset} 到 ${getAccountTypeText(transferForm.value.toType)} 吗？`,
            '划转确认',
            {
              confirmButtonText: '确认划转',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )
          
          loading.value.transferSubmit = true
          const user = getCurrentUser()
          const response = await fetch('/api/subaccounts/internal-transfer', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${user.token}`
            },
            body: JSON.stringify({
              email: selectedAccount.value.email,
              asset: transferForm.value.asset,
              amount: transferForm.value.amount,
              from_type: transferForm.value.fromType,
              to_type: transferForm.value.toType
            })
          })
          
          const result = await response.json()
          
          if (result.success) {
            ElMessage.success('划转成功')
            transferDialogVisible.value = false
            refreshBalance() // 刷新余额
            refreshTransfers() // 刷新划转记录
          } else {
            ElMessage.error(result.error || '划转失败')
          }
        } catch (error) {
          if (error !== 'cancel') {
            console.error('划转出错:', error)
            ElMessage.error('划转操作失败')
          }
        } finally {
          loading.value.transferSubmit = false
        }
      })
    }
    
    // 显示批量平仓对话框
    const showBatchCloseDialog = () => {
      if (!positionsData.value || positionsData.value.length === 0) {
        ElMessage.warning('没有可平仓的持仓')
        return
      }
      
      selectedPositions.value = []
      closePositionDialogVisible.value = true
    }
    
    // 处理平仓选择变化
    const handleClosePositionSelectionChange = (selection) => {
      selectedPositions.value = selection
    }
    
    // 平仓单个持仓
    const closeUmPosition = async (position) => {
      try {
        // 确保positionSide是LONG或SHORT
        const positionSide = parseFloat(position.positionAmt) > 0 ? 'LONG' : 'SHORT';
        
        await ElMessageBox.confirm(
          `确认要平掉 ${position.symbol} ${positionSide === 'LONG' ? '多' : '空'}单持仓吗？`,
          '平仓确认',
          {
            confirmButtonText: '确认平仓',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/close-position', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email,
            symbol: position.symbol,
            positionSide: positionSide  // 使用我们确定的positionSide值
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          ElMessage.success('平仓成功')
          refreshPositions() // 刷新持仓
        } else {
          ElMessage.error(result.error || '平仓失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('平仓出错:', error)
          ElMessage.error('平仓操作失败')
        }
      }
    }
    
    // 平仓币本位持仓
    const closeCmPosition = async (position) => {
      try {
        // 确保positionSide是LONG或SHORT
        const positionSide = parseFloat(position.positionAmt) > 0 ? 'LONG' : 'SHORT';
        
        await ElMessageBox.confirm(
          `确认要平掉 ${position.symbol} ${positionSide === 'LONG' ? '多' : '空'}单持仓吗？`,
          '平仓确认',
          {
            confirmButtonText: '确认平仓',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const user = getCurrentUser()
        const response = await fetch('/api/subaccounts/portfolio-margin/close-cm-position', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            email: selectedAccount.value.email,
            symbol: position.symbol,
            positionSide: positionSide  // 使用我们确定的positionSide值
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          ElMessage.success('币本位合约平仓成功')
          refreshPositions() // 刷新持仓
        } else {
          ElMessage.error(result.error || '币本位合约平仓失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('币本位合约平仓出错:', error)
          ElMessage.error('币本位合约平仓操作失败')
        }
      }
    }
    
    // 批量平仓
    const submitClosePositions = async () => {
      if (selectedPositions.value.length === 0) {
        ElMessage.warning('请选择要平仓的持仓')
        return
      }
      
      try {
        await ElMessageBox.confirm(
          `确认要平掉选中的 ${selectedPositions.value.length} 个持仓吗？`,
          '批量平仓确认',
          {
            confirmButtonText: '确认平仓',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        loading.value.closePositions = true
        const user = getCurrentUser()
        const positions = selectedPositions.value.map(p => ({
          email: selectedAccount.value.email,
          symbol: p.symbol,
          positionAmt: p.positionAmt
        }))
        
        const response = await fetch('/api/subaccounts/batch-close', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            positions: positions
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          const successCount = result.data.success_count || 0
          ElMessage.success(`成功平仓 ${successCount}/${positions.length} 个持仓`)
          closePositionDialogVisible.value = false
          refreshPositions() // 刷新持仓
        } else {
          ElMessage.error(result.error || '批量平仓失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量平仓出错:', error)
          ElMessage.error('批量平仓操作失败')
        }
      } finally {
        loading.value.closePositions = false
      }
    }
    
    // 格式化数字
    const formatNumber = (value) => {
      if (!value) return '0'
      
      // 转换为数字
      const num = parseFloat(value)
      
      // 如果是整数，返回整数形式
      if (Number.isInteger(num)) {
        return num.toString()
      }
      
      // 如果是小数，根据大小选择合适的小数位
      if (Math.abs(num) < 0.0001) {
        return num.toFixed(8)
      } else if (Math.abs(num) < 0.01) {
        return num.toFixed(6)
      } else if (Math.abs(num) < 1) {
        return num.toFixed(4)
      } else if (Math.abs(num) < 1000) {
        return num.toFixed(2)
      } else {
        return num.toFixed(2)
      }
    }
    
    // 格式化日期
    const formatDate = (timestamp) => {
      if (!timestamp) return '-'
      
      const date = new Date(timestamp)
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
    
    // 获取账户类型文本
    const getAccountTypeText = (type) => {
      const typeMap = {
        'SPOT': '现货账户',
        'FUTURES': 'U本位合约',
        'MARGIN': '杠杆账户',
        'COIN_FUTURES': '币本位合约',
        'FUNDING': '资金账户',
        'ISOLATED_MARGIN': '逐仓杠杆'
      }
      return typeMap[type] || type
    }
    
    // 获取状态文本
    const getStatusText = (status) => {
      const statusMap = {
        'CONFIRMED': '已确认',
        'PENDING': '处理中',
        'FAILED': '失败',
        'CANCELLED': '已取消'
      }
      return statusMap[status] || status
    }
    
    return {
      dialogVisible,
      selectedAccount,
      activeTab,
      loading,
      accountData,
      balanceData,
      positionsData,
      cmPositionsData,
      transfersData,
      transferDialogVisible,
      transferFormRef,
      transferForm,
      transferRules,
      closePositionDialogVisible,
      selectedPositions,
      commonCoins,
      accountTypes,
      queryAccountData,
      refreshBalance,
      refreshPositions,
      refreshTransfers,
      enableUnifiedAccount,
      showTransferDialog,
      submitTransfer,
      showBatchCloseDialog,
      handleClosePositionSelectionChange,
      closeUmPosition,
      closeCmPosition,
      submitClosePositions,
      formatNumber,
      formatDate,
      getAccountTypeText,
      getStatusText,
      showDebugInfo
    }
  }
}
</script>

<style scoped>
.unified-account-dialog {
  --el-dialog-padding-primary: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.operation-bar {
  margin-bottom: 15px;
  display: flex;
  justify-content: flex-start;
  gap: 10px;
}

.empty-data {
  padding: 30px 0;
  text-align: center;
}

.empty-data .el-button {
  margin-top: 15px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.account-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.positive-value {
  color: #67c23a;
}

.negative-value {
  color: #f56c6c;
}

.debug-info {
  margin-top: 20px;
  padding: 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
}

.json-data {
  margin-top: 10px;
  padding: 8px;
  background-color: #f0f0f0;
  border-radius: 4px;
  max-height: 300px;
  overflow: auto;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
}

.button-group {
  display: flex;
  gap: 5px;
}

.mt-4 {
  margin-top: 1rem;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}
</style> 