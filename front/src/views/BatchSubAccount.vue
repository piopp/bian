<template>
  <div class="container-fluid mt-4">
    <div class="row mb-3">
      <div class="col">
        <h2>批量子账号操作</h2>
      </div>
    </div>

    <div class="row mb-3">
      <div class="col d-flex gap-2">
        <el-button type="primary" @click="refreshSubaccounts">
          <i class="bi bi-arrow-clockwise me-1"></i>刷新子账号
        </el-button>
        <el-button type="success" @click="importApiSettings">
          <i class="bi bi-cloud-upload me-1"></i>导入API设置
        </el-button>
        <el-button type="info" @click="exportApiSettings">
          <i class="bi bi-cloud-download me-1"></i>导出API设置
        </el-button>
      </div>
    </div>

    <div class="row mb-3">
      <div class="col">
        <el-tabs v-model="activeTab" class="demo-tabs">
          <el-tab-pane label="批量开仓" name="open">
            <div class="card">
              <div class="card-body">
                <div class="row mb-3">
                  <div class="col-12 col-md-6">
                    <h5>选择子账号</h5>
                    <div class="mb-3">
                      <el-checkbox v-model="selectAllAccounts" @change="handleSelectAllChange">
                        全选/取消全选
                      </el-checkbox>
                    </div>
                    <div class="mb-3 subaccount-list" style="max-height: 300px; overflow-y: auto;">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccountsWithApi" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                          </el-checkbox>
                        </div>
                      </el-checkbox-group>
                    </div>
                  </div>
                  <div class="col-12 col-md-6">
                    <h5>开仓设置</h5>
                    <div class="mb-3">
                      <label class="form-label">交易对</label>
                      <el-select v-model="openForm.symbol" class="w-100" filterable placeholder="选择或输入交易对">
                        <el-option
                          v-for="pair in tradingPairs"
                          :key="pair.value"
                          :label="pair.label"
                          :value="pair.value">
                        </el-option>
                      </el-select>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">订单类型</label>
                      <el-select v-model="openForm.orderType" class="w-100">
                        <el-option label="市价单" value="MARKET"></el-option>
                        <el-option label="限价单" value="LIMIT"></el-option>
                      </el-select>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">方向</label>
                      <el-select v-model="openForm.side" placeholder="选择方向">
                        <el-option label="买入" value="BUY" />
                        <el-option label="卖出" value="SELL" />
                        <el-option label="同时买卖" value="BOTH" />
                      </el-select>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">数量计算方式</label>
                      <el-select v-model="openForm.quantityType" class="w-100">
                        <el-option label="本币" value="CONTRACT"></el-option>
                        <el-option label="USDT" value="USD"></el-option>
                      </el-select>
                    </div>
                    
                    <el-form-item v-if="openForm.side !== 'BOTH'" label="数量">
                      <el-input
                        v-model="openForm.quantity"
                        placeholder="请输入数量"
                        type="number"
                        style="width: 100%"
                      />
                    </el-form-item>
                    
                    <template v-if="openForm.side === 'BOTH'">
                      <el-form-item label="买入数量">
                        <el-input
                          v-model="openForm.buyQuantity"
                          placeholder="请输入买入数量"
                          type="number"
                          style="width: 100%"
                        />
                      </el-form-item>
                      <el-form-item label="卖出数量">
                        <el-input
                          v-model="openForm.sellQuantity"
                          placeholder="请输入卖出数量"
                          type="number"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </template>

                    <div class="mb-3" v-if="openForm.orderType === 'LIMIT'">
                      <label class="form-label">价格</label>
                      <el-input v-model="openForm.price" placeholder="输入价格"></el-input>
                    </div>
                    <div class="mb-3" v-if="openForm.orderType === 'LIMIT' && openForm.price && (openForm.quantity || openForm.buyQuantity || openForm.sellQuantity)">
                      <label class="form-label">预估手续费</label>
                      <div class="fee-container">
                        <el-select v-model="openForm.feeType" class="fee-type-select" size="small">
                          <el-option label="挂单(Maker)" value="MAKER"></el-option>
                          <el-option label="吃单(Taker)" value="TAKER"></el-option>
                        </el-select>
                        <div class="fee-info">
                          <div v-if="openForm.side !== 'BOTH'">
                            <span class="fee-label">手续费({{openForm.quantityType === 'USD' ? 'USDT' : openForm.symbol.replace('USDT', '')}}): </span>
                            <span class="fee-value">{{ calculatedFee }}</span>
                          </div>
                          <div v-else>
                            <div v-if="openForm.buyQuantity">
                              <span class="fee-label">买入手续费: </span>
                              <span class="fee-value">{{ calculatedBuyFee }}</span>
                            </div>
                            <div v-if="openForm.sellQuantity">
                              <span class="fee-label">卖出手续费: </span>
                              <span class="fee-value">{{ calculatedSellFee }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <small class="form-text text-muted">
                        * Maker费率: 0.02%, Taker费率: 0.07%
                        <a href="https://www.binance.com/zh-CN/fee/futures" target="_blank">查看详情</a>
                      </small>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">杠杆</label>
                      <el-input v-model="openForm.leverage" type="number" placeholder="输入杠杆倍数(2-125)" min="2" max="125"></el-input>
                      <small class="form-text text-muted">可输入2至125之间的整数</small>
                    </div>
                    <div class="d-grid">
                      <el-button type="primary" :disabled="!isOpenFormValid || isSubmitting" @click="submitBatchOpen">
                        批量开仓
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="批量平仓" name="close">
            <div class="card">
              <div class="card-body">
                <div class="row mb-3">
                  <div class="col-12 col-md-6">
                    <h5>选择子账号</h5>
                    <div class="mb-3">
                      <el-checkbox v-model="selectAllAccounts" @change="handleSelectAllChange">
                        全选/取消全选
                      </el-checkbox>
                    </div>
                    <div class="mb-3 subaccount-list" style="max-height: 300px; overflow-y: auto;">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccountsWithApi" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                          </el-checkbox>
                        </div>
                      </el-checkbox-group>
                    </div>
                  </div>
                  <div class="col-12 col-md-6">
                    <h5>平仓设置</h5>
                    <div class="mb-3">
                      <label class="form-label">交易对</label>
                      <el-select v-model="closeForm.symbol" class="w-100" filterable placeholder="选择或输入交易对">
                        <el-option
                          v-for="pair in tradingPairs"
                          :key="pair.value"
                          :label="pair.label"
                          :value="pair.value">
                        </el-option>
                      </el-select>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">平仓类型</label>
                      <el-select v-model="closeForm.closeType" class="w-100">
                        <el-option label="全部平仓" value="ALL"></el-option>
                        <el-option label="部分平仓" value="PARTIAL"></el-option>
                      </el-select>
                    </div>
                    <div class="mb-3" v-if="closeForm.closeType === 'PARTIAL'">
                      <label class="form-label">平仓比例 (%)</label>
                      <el-input v-model="closeForm.percentage" placeholder="输入平仓比例"></el-input>
                    </div>
                    <div class="d-grid">
                      <el-button type="warning" :disabled="!isCloseFormValid || isSubmitting" @click="submitBatchClose">
                        批量平仓
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="批量划转" name="transfer">
            <div class="card">
              <div class="card-body">
                <div class="row mb-3">
                  <div class="col-12 col-md-6">
                    <h5>选择子账号</h5>
                    <div class="mb-3">
                      <el-checkbox v-model="selectAllAccounts" @change="handleSelectAllChange">
                        全选/取消全选
                      </el-checkbox>
                    </div>
                    <div class="mb-3 subaccount-list" style="max-height: 300px; overflow-y: auto;">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccountsWithApi" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                          </el-checkbox>
                        </div>
                      </el-checkbox-group>
                    </div>
                  </div>
                  <div class="col-12 col-md-6">
                    <h5>划转设置</h5>
                    <div class="mb-3">
                      <label class="form-label">划转方向</label>
                      <el-select v-model="transferForm.direction" class="w-100">
                        <el-option label="从现货账户到合约账户" value="SPOT_TO_FUTURE"></el-option>
                        <el-option label="从合约账户到现货账户" value="FUTURE_TO_SPOT"></el-option>
                      </el-select>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">货币</label>
                      <el-input v-model="transferForm.asset" placeholder="例如：USDT"></el-input>
                    </div>
                    <div class="mb-3">
                      <label class="form-label">划转数量</label>
                      <el-input v-model="transferForm.amount" placeholder="输入划转数量"></el-input>
                    </div>
                    <div class="d-grid">
                      <el-button type="success" :disabled="!isTransferFormValid || isSubmitting" @click="submitBatchTransfer">
                        批量划转
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="网格建仓" name="gridOrder">
            <div class="card">
              <div class="card-body">
                <div class="row mb-3">
                  <div class="col-12 col-md-6">
                    <h5>选择子账号</h5>
                    <div class="mb-3">
                      <el-checkbox v-model="selectAllAccounts" @change="handleSelectAllChange">
                        全选/取消全选
                      </el-checkbox>
                    </div>
                    <div class="mb-3 subaccount-list" style="max-height: 300px; overflow-y: auto;">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccountsWithApi" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                          </el-checkbox>
                        </div>
                      </el-checkbox-group>
                    </div>
                  </div>
                  <div class="col-12 col-md-6">
                    <h5>网格建仓设置</h5>
                      <div class="mb-3">
                      <label class="form-label">交易对</label>
                      <el-select v-model="gridForm.symbol" class="w-100" filterable placeholder="选择或输入交易对">
                        <el-option
                          v-for="pair in tradingPairs"
                          :key="pair.value"
                          :label="pair.label"
                          :value="pair.value">
                        </el-option>
                        </el-select>
                      </div>
                    <div class="mb-3">
                      <label class="form-label">限价</label>
                      <el-input v-model="gridForm.price" type="number" placeholder="输入限价" />
                    </div>
                    <div class="mb-3">
                      <label class="form-label">单笔数量（本币）</label>
                      <el-input v-model="gridForm.singleAmount" type="number" placeholder="输入单笔数量" />
                  </div>
                    <div class="mb-3">
                      <label class="form-label">订单总数</label>
                      <el-input-number v-model="gridForm.totalOrders" :min="1" :max="20" />
                      </div>
                    <div class="mb-3">
                      <label class="form-label">总仓位数量（本币）</label>
                      <el-input 
                        v-model="totalAmount" 
                        type="text" 
                        placeholder="总仓位数量" 
                        disabled 
                      />
                      <small class="form-text text-muted">总数 = 单笔数量 × 订单数</small>
                    </div>
                      <div class="mb-3">
                      <label class="form-label">杠杆</label>
                      <el-input v-model="gridForm.leverage" type="number" placeholder="输入杠杆倍数(2-125)" min="2" max="125" />
                      <small class="form-text text-muted">可输入2至125之间的整数</small>
                      </div>
                    <div class="mb-3">
                      <label class="form-label">订单间隔时间</label>
                      <el-input v-model="gridForm.interval" type="number" disabled />
                      <small class="form-text text-muted">每笔订单相隔5秒</small>
                    </div>
                    <div class="d-grid">
                      <el-button 
                        type="primary" 
                        :disabled="!isGridFormValid || isGridSubmitting" 
                        @click="submitGridOrders"
                      >
                        开始网格建仓
                      </el-button>
                      </div>
                    </div>
                </div>
                <div class="row mt-3" v-if="gridProgress.isRunning">
                  <div class="col-12">
                    <el-alert
                      type="info"
                      :title="`正在执行: ${gridProgress.current}/${gridProgress.total} 订单`"
                      show-icon
                    >
                      <el-progress :percentage="gridProgress.percentage" />
                    </el-alert>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="合约余额" name="balance">
            <div class="card">
              <div class="card-body">
                <div class="row mb-3">
                  <div class="col-12 col-md-6">
                    <h5>选择子账号</h5>
                    <div class="mb-3">
                      <el-checkbox v-model="selectAllAccounts" @change="handleSelectAllChange">
                        全选/取消全选
                      </el-checkbox>
                    </div>
                    <div class="mb-3 subaccount-list" style="max-height: 300px; overflow-y: auto;">
                      <el-checkbox-group v-model="selectedBalanceAccounts">
                        <div v-for="account in subaccountsWithApi" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                          </el-checkbox>
                        </div>
                      </el-checkbox-group>
                    </div>
                    <div class="d-grid mt-3">
                      <div class="mb-3">
                        <label class="form-label">筛选资产</label>
                        <el-select v-model="balanceAssetFilter" class="w-100" placeholder="全部资产">
                          <el-option value="" label="全部资产" />
                          <el-option value="USDT" label="USDT" />
                          <el-option value="BTC" label="BTC" />
                          <el-option value="ETH" label="ETH" />
                          <el-option value="BNB" label="BNB" />
                          <el-option value="USDC" label="USDC" />
                          <el-option value="FDUSD" label="FDUSD" />
                        </el-select>
                      </div>
                      <el-button type="primary" :disabled="selectedBalanceAccounts.length === 0 || isLoadingBalance" @click="queryFuturesBalance">
                        <i class="bi bi-search me-1"></i>查询合约余额
                      </el-button>
                    </div>
                  </div>
                  <div class="col-12 col-md-6">
                    <h5>合约余额信息</h5>
                    <div v-if="isLoadingBalance" class="text-center py-4">
                      <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                      </div>
                      <div class="mt-2">正在查询合约余额，请稍候...</div>
                    </div>
                    <div v-else>
                      <div class="mb-3">
                        <small class="text-muted">* 仅显示余额大于0的资产</small>
                      </div>
                        <el-table
                        v-if="futuresBalances.length > 0"
                        :data="futuresBalances"
                          stripe
                          border
                          style="width: 100%"
                        >
                        <el-table-column prop="email" label="子账号" width="220" show-overflow-tooltip />
                        <el-table-column prop="asset" label="资产" width="80" />
                        <el-table-column prop="balance" label="余额" />
                        <el-table-column prop="available" label="可用余额" />
                        </el-table>
                      <div v-else class="text-center py-4 text-muted">
                        <i class="bi bi-info-circle me-1"></i>暂无合约余额数据，请选择子账号并点击查询
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="持仓信息" name="positions">
            <PositionList :subaccounts="subaccountsWithApi" />
          </el-tab-pane>

          <el-tab-pane label="订单管理" name="orderManage">
            <LimitOrderList ref="orderListRef" :subaccounts="subaccountsWithApi" />
          </el-tab-pane>
          
          <el-tab-pane label="历史成交" name="tradesHistory">
            <TradeHistoryList :subaccounts="subaccountsWithApi" />
          </el-tab-pane>
          
          <el-tab-pane label="手续费统计" name="feeStats">
            <FeeStatistics :subaccounts="subaccountsWithApi" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 批量操作结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="操作结果" width="80%">
      <div class="table-responsive">
        <table class="table table-striped">
          <thead>
            <tr>
              <th>子账号</th>
              <th>状态</th>
              <th>消息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(result, index) in operationResults" :key="index">
              <td>{{ result.email }}</td>
              <td>
                <el-tag :type="result.success ? 'success' : 'danger'">
                  {{ result.success ? '成功' : '失败' }}
                </el-tag>
              </td>
              <td>{{ result.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </el-dialog>

    <!-- 导入API设置对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入API设置" width="50%">
      <div class="mb-3">
        <label class="form-label">选择JSON文件</label>
        <input type="file" class="form-control" @change="handleFileUpload" accept=".json">
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
            v-for="account in subaccountsWithoutApi"
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
import { ref, reactive, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { getCurrentUser } from '../services/auth'
import LimitOrderList from '@/components/LimitOrderList.vue'
import PositionList from '@/components/PositionList.vue'
import FeeStatistics from '@/components/FeeStatistics.vue'
import TradeHistoryList from '@/components/TradeHistoryList.vue'
import { calculateOrderFee } from '@/utils/feeCalculator.js'

export default {
  name: 'BatchSubAccount',
  components: {
    LimitOrderList,
    PositionList,
    FeeStatistics,
    TradeHistoryList,
  },
  setup() {
    // 交易对列表
    const tradingPairs = ref([])
    const isLoadingTradingPairs = ref(false)
    
    // 状态
    const activeTab = ref('open')
    const subaccounts = ref([])
    const selectedAccounts = ref([])
    const selectAllAccounts = ref(false)
    const isSubmitting = ref(false)
    const resultDialogVisible = ref(false)
    const operationResults = ref([])
    const importDialogVisible = ref(false)
    const apiFile = ref(null)
    const apiJsonContent = ref('')
    const selectedImportAccount = ref('')
    const importToMasterAccount = ref(false)
    const selectedBalanceAccounts = ref([])
    const isLoadingBalance = ref(false)
    const futuresBalances = ref([])
    const balanceAssetFilter = ref('USDT')
    const selectedPositionsAccounts = ref([])
    const isLoadingPositions = ref(false)
    const futuresPositions = ref([])

    // 表单数据
    const openForm = reactive({
      symbol: '',
      side: 'BUY',
      orderType: 'MARKET',
      quantity: '',
      buyQuantity: '',
      sellQuantity: '',
      price: '',
      leverage: '',
      reduceOnly: false,
      quantityType: 'USDT',
      feeType: 'MAKER',
    })

    const closeForm = reactive({
      symbol: '',
      closeType: 'ALL',
      percentage: 100
    })

    const transferForm = reactive({
      direction: 'SPOT_TO_FUTURE',
      asset: 'USDT',
      amount: ''
    })

    const gridForm = reactive({
      symbol: '',
      price: '',
      singleAmount: '',
      totalOrders: 1,
      leverage: '',
      interval: 5,
    })

    // 计算属性
    const isOpenFormValid = computed(() => {
      if (selectedAccounts.value.length === 0 || 
          !openForm.symbol || 
          (openForm.orderType === 'LIMIT' && !openForm.price) ||
          !openForm.leverage || openForm.leverage < 2) {
        return false;
      }

      if (openForm.side === 'BOTH') {
        // 当选择"同时买卖"时，至少需要一个有效的买入或卖出数量
        return (openForm.buyQuantity > 0 || openForm.sellQuantity > 0);
      } else {
        // 单向交易验证
        return !!openForm.quantity;
      }
    })

    const isCloseFormValid = computed(() => {
      return selectedAccounts.value.length > 0 && 
             closeForm.symbol && 
             (closeForm.closeType !== 'PARTIAL' || closeForm.percentage)
    })

    const isTransferFormValid = computed(() => {
      return selectedAccounts.value.length > 0 && 
             transferForm.asset && 
             transferForm.amount
    })

    const isGridFormValid = computed(() => {
      return selectedAccounts.value.length > 0 && 
             gridForm.symbol && 
             gridForm.price && 
             gridForm.singleAmount && 
             gridForm.totalOrders && 
             gridForm.leverage && 
             gridForm.interval
    })

    const totalAmount = computed(() => {
      if (!gridForm.singleAmount || !gridForm.totalOrders) {
        return '0';
      }
      return (parseFloat(gridForm.singleAmount) * gridForm.totalOrders).toFixed(4);
    })

    const gridProgress = reactive({
      isRunning: false,
      current: 0,
      total: 0,
      percentage: 0
    })
    
    // 在script的setup中添加新的isGridSubmitting状态
    const isGridSubmitting = ref(false);
    
    // 在script的setup中添加新的submitGridOrders方法
    const submitGridOrders = async () => {
      try {
        // 检查表单数据
        if (!isGridFormValid.value) {
          ElMessage.warning('请完善表单');
          return;
        }
        
        // 确认操作
        await ElMessageBox.confirm(
          `将为${selectedAccounts.value.length}个子账号同时建立${gridForm.totalOrders}笔多空仓位，总计${totalAmount.value}个${gridForm.symbol.slice(0, -4)}，确认执行？`,
          '确认网格建仓',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        isGridSubmitting.value = true;
        gridProgress.isRunning = true;
        gridProgress.current = 0;
        gridProgress.total = selectedAccounts.value.length * gridForm.totalOrders;
        gridProgress.percentage = 0;
        
        // 存储所有结果
        const results = [];
        
        // 按批次处理订单
        for (let batch = 0; batch < gridForm.totalOrders; batch++) {
          // 记录批次开始时间
          const batchStartTime = Date.now();
          
          console.log(`开始处理第${batch + 1}批订单...`);
          
          // 当前批次的所有子账号并行请求
          const batchPromises = selectedAccounts.value.map(async (email) => {
            try {
              // 使用网格交易API
              const response = await axios.post('/api/trading/grid/submit-and-monitor', {
                email: email,
                symbol: gridForm.symbol,
                upper_price: parseFloat(gridForm.price) * 1.005,
                lower_price: parseFloat(gridForm.price) * 0.995,
                grid_num: 2,
                total_investment: parseFloat(gridForm.singleAmount) * parseFloat(gridForm.price) * 2,
                is_bilateral: true,
                leverage: parseInt(gridForm.leverage)
              });
              
              // 更新进度
              gridProgress.current += 1;
              gridProgress.percentage = Math.floor((gridProgress.current / gridProgress.total) * 100);
              
              return {
                email: email,
                order: batch + 1,
                time: new Date().toLocaleTimeString(),
                success: response.data.success,
                message: response.data.message || "网格交易提交成功",
                data: response.data.data || {}
              };
            } catch (error) {
              console.error(`子账号${email}第${batch+1}批网格建仓失败:`, error);
              
              // 更新进度（即使失败也要更新进度）
              gridProgress.current += 1;
              gridProgress.percentage = Math.floor((gridProgress.current / gridProgress.total) * 100);
              
              return {
                email: email,
                order: batch + 1,
                time: new Date().toLocaleTimeString(),
                success: false,
                error: error.response?.data?.error || error.message
              };
            }
          });
          
          // 并行执行当前批次的所有请求
          const batchResults = await Promise.all(batchPromises);
          results.push(...batchResults);
          
          // 如果不是最后一批，确保从批次开始到下一批次开始有固定的间隔
          if (batch < gridForm.totalOrders - 1) {
            const elapsed = Date.now() - batchStartTime;
            const targetInterval = gridForm.interval * 1000; // 转换为毫秒
            
            // 只有当已经过去的时间小于目标间隔时才等待
            if (elapsed < targetInterval) {
              const waitTime = targetInterval - elapsed;
              console.log(`第${batch + 1}批完成，已用时${elapsed}ms，再等待${waitTime}ms后发送下一批...`);
              await new Promise(resolve => setTimeout(resolve, waitTime));
            } else {
              console.log(`第${batch + 1}批处理耗时${elapsed}ms，已超过间隔时间(${targetInterval}ms)，立即发送下一批`);
            }
          }
        }
        
        // 完成所有订单
        gridProgress.percentage = 100;
        
        // 计算成功和失败的数量
        let successCount = results.filter(r => r.success).length;
        let failCount = results.length - successCount;
        
        // 显示结果
        if (failCount === 0) {
          ElMessage.success(`网格建仓完成: ${successCount}个操作全部成功`);
        } else if (successCount === 0) {
          ElMessage.error(`网格建仓失败: ${failCount}个操作全部失败`);
        } else {
          ElMessage.warning(`网格建仓部分成功: ${successCount}个成功, ${failCount}个失败`);
        }
        
        // 更新结果对话框数据
        resultDialogVisible.value = true;
        operationResults.value = results.map(r => ({
          email: r.email,
          status: r.success ? '成功' : '失败', 
          message: r.message || r.error || ''
        }));
        
        // 自动切换到订单管理界面
        setTimeout(() => {
          activeTab.value = 'orderManage';
          
          // 开启自动刷新订单列表
          startAutoRefreshOrders();
        }, 2000); // 延迟2秒后切换，让用户先看到结果
        
      } catch (error) {
        if (error !== 'cancel') {
          console.error('网格建仓执行出错:', error);
          ElMessage.error('网格建仓执行失败: ' + (error.response?.data?.error || error.message));
        }
      } finally {
        isGridSubmitting.value = false;
        // 5秒后隐藏进度条
        setTimeout(() => {
          gridProgress.isRunning = false;
        }, 5000);
      }
    };

    // 在这里添加订单自动刷新相关变量和函数
    const orderRefreshTimer = ref(null);
    const orderListRef = ref(null); // 添加对LimitOrderList组件的引用

    // 开始自动刷新订单列表
    const startAutoRefreshOrders = () => {
      // 清除可能存在的旧定时器
      if (orderRefreshTimer.value) {
        clearInterval(orderRefreshTimer.value);
      }
      
      // 创建新的定时器，每5秒刷新一次
      orderRefreshTimer.value = setInterval(() => {
        // 如果当前不在订单管理页面，则停止刷新
        if (activeTab.value !== 'orderManage') {
          stopAutoRefreshOrders();
          return;
        }
        
        // 通过ref调用LimitOrderList组件的刷新方法
        if (orderListRef.value && typeof orderListRef.value.refreshOrderList === 'function') {
          console.log('正在自动刷新订单列表...');
          orderListRef.value.refreshOrderList();
          
          // 显示刷新提示
          ElMessage.info({
            message: '正在自动刷新订单列表...',
            duration: 1000,
            showClose: false
          });
        } else {
          console.warn('找不到订单列表组件或刷新方法');
        }
      }, 5000);
      
      // 显示开始自动刷新的提示
      ElMessage.success({
        message: '已开启订单自动刷新(每5秒)',
        duration: 3000
      });
    };

    // 停止自动刷新
    const stopAutoRefreshOrders = () => {
      if (orderRefreshTimer.value) {
        clearInterval(orderRefreshTimer.value);
        orderRefreshTimer.value = null;
        console.log('已停止自动刷新订单列表');
      }
    };

    // 监听标签页变化，当离开订单管理页面时停止自动刷新
    watch(activeTab, (newTab, oldTab) => {
      if (oldTab === 'orderManage' && newTab !== 'orderManage') {
        stopAutoRefreshOrders();
      }
    });

    // 组件卸载时清除定时器
    onBeforeUnmount(() => {
      stopAutoRefreshOrders();
    });

    const subaccountsWithoutApi = computed(() => {
      return subaccounts.value.filter(account => !account.apiKey || account.apiKey.trim() === '');
    });

    const subaccountsWithApi = computed(() => {
      return subaccounts.value.filter(account => account.apiKey && account.apiKey.trim() !== '');
    });

    const canImport = computed(() => {
      return (apiFile.value || (apiJsonContent.value.trim() !== '' && (importToMasterAccount.value || selectedImportAccount.value)))
    })

    // 方法
    const refreshSubaccounts = async () => {
      try {
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        const response = await axios.get('/api/subaccounts', {
          params: {
            user_id: userIdValue
          },
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        // 提取正确的子账号数据结构
        if (response.data && response.data.data && response.data.data.subaccounts) {
          // 获取子账号数据
          const subaccountsList = response.data.data.subaccounts;
          
          // 获取API设置信息
          try {
            const apiSettingsResponse = await axios.get('/api/subaccounts/api-export', {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            const apiSettings = apiSettingsResponse.data.data || {};
            
            // 合并子账号信息和API设置
            subaccounts.value = subaccountsList.map(account => {
              const email = account.email;
              const apiInfo = apiSettings[email] || {};
              
              return {
                ...account,
                apiKey: apiInfo.apiKey || '',
                apiSecret: apiInfo.apiSecret || '',
                name: apiInfo.name || ''
              };
            });
          } catch (apiError) {
            console.error('获取API设置失败:', apiError);
            subaccounts.value = subaccountsList;
          }
        } else {
          subaccounts.value = [];
          ElMessage.warning('子账号数据格式异常');
        }
      } catch (error) {
        ElMessage.error('获取子账号列表失败: ' + error.message);
      }
    }

    const handleSelectAllChange = (val) => {
      if (val) {
        selectedAccounts.value = subaccountsWithApi.value.map(account => account.email)
        selectedBalanceAccounts.value = subaccountsWithApi.value.map(account => account.email)
        selectedPositionsAccounts.value = subaccountsWithApi.value.map(account => account.email)
      } else {
        selectedAccounts.value = []
        selectedBalanceAccounts.value = []
        selectedPositionsAccounts.value = []
      }
    }

    const submitBatchOpen = async () => {
      try {
        isSubmitting.value = true
        
        // 确认操作
        await ElMessageBox.confirm(
          `确定要为${selectedAccounts.value.length}个子账号执行批量开仓操作吗？`,
          '确认操作',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        let responseData = [];
        
        // 如果选择了"同时买卖"
        if (openForm.side === 'BOTH') {
          // 准备请求数组
          const requests = [];
          
          // 买入请求
          if (openForm.buyQuantity > 0) {
            const buyRequest = axios.post('/api/subaccounts/batch-open', {
              emails: selectedAccounts.value,
              userId: userIdValue,
              symbol: openForm.symbol,
              orderType: openForm.orderType,
              side: 'BUY',
              quantityType: openForm.quantityType === 'CONTRACT' ? 'CONTRACT' : 'USD',
              quantity: openForm.buyQuantity,
              price: openForm.orderType === 'LIMIT' ? openForm.price : undefined,
              leverage: openForm.leverage
            }, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            requests.push(buyRequest);
          }
          
          // 卖出请求
          if (openForm.sellQuantity > 0) {
            const sellRequest = axios.post('/api/subaccounts/batch-open', {
              emails: selectedAccounts.value,
              userId: userIdValue,
              symbol: openForm.symbol,
              orderType: openForm.orderType,
              side: 'SELL',
              quantityType: openForm.quantityType === 'CONTRACT' ? 'CONTRACT' : 'USD',
              quantity: openForm.sellQuantity,
              price: openForm.orderType === 'LIMIT' ? openForm.price : undefined,
              leverage: openForm.leverage
            }, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            requests.push(sellRequest);
          }
          
          // 并行执行所有请求
          const responses = await Promise.all(requests);
          
          // 处理结果
          if (responses.length > 0) {
            // 处理买入结果（如果有）
            if (openForm.buyQuantity > 0) {
              const buyResponse = responses.shift();
              const buyResults = buyResponse.data.map(item => ({
                ...item,
                message: `买入: ${item.message}`
              }));
              responseData = [...buyResults];
              
              // 记录手续费（仅限价单）
              if (openForm.orderType === 'LIMIT' && openForm.price) {
                // 为每个成功的订单记录手续费
                buyResults.filter(item => item.success).forEach(async (item) => {
                  const orderId = item.message.match(/订单ID: (\d+)/)?.[1];
                  if (orderId) {
                    try {
                      // 查询订单状态
                      const orderStatus = await axios.post('/api/subaccounts/check-order', {
                        email: item.email,
                        symbol: openForm.symbol,
                        orderId: orderId
                      });
                      
                      // 记录订单历史
                      await axios.post('/api/order-history/record', {
                        email: item.email,
                        symbol: openForm.symbol,
                        orderType: openForm.orderType,
                        side: 'BUY',
                        amount: openForm.buyQuantity,
                        price: openForm.price,
                        status: orderStatus.data.status,
                        executedQty: orderStatus.data.executedQty,
                        orderId: orderId,
                        leverage: openForm.leverage
                      });
                    } catch (error) {
                      console.error('记录买入订单历史失败:', error);
                    }
                  }
                });
              }
            }
            
            // 处理卖出结果（如果有）
            if (openForm.sellQuantity > 0) {
              const sellResponse = responses.shift();
              const sellResults = sellResponse.data.map(item => ({
                ...item,
                message: `卖出: ${item.message}`
              }));
              
              // 记录手续费（仅限价单）
              if (openForm.orderType === 'LIMIT' && openForm.price) {
                // 为每个成功的订单记录手续费
                sellResults.filter(item => item.success).forEach(async (item) => {
                  const orderId = item.message.match(/订单ID: (\d+)/)?.[1];
                  if (orderId) {
                    try {
                      // 查询订单状态
                      const orderStatus = await axios.post('/api/subaccounts/check-order', {
                        email: item.email,
                        symbol: openForm.symbol,
                        orderId: orderId
                      });
                      
                      // 记录订单历史
                      await axios.post('/api/order-history/record', {
                        email: item.email,
                        symbol: openForm.symbol,
                        orderType: openForm.orderType,
                        side: 'SELL',
                        amount: openForm.sellQuantity,
                        price: openForm.price,
                        status: orderStatus.data.status,
                        executedQty: orderStatus.data.executedQty,
                        orderId: orderId,
                        leverage: openForm.leverage
                      });
                    } catch (error) {
                      console.error('记录卖出订单历史失败:', error);
                    }
                  }
                });
              }
              
              // 整合结果
              // 如果是同一个邮箱，则合并其买入和卖出结果
              sellResults.forEach(sellItem => {
                const existingItem = responseData.find(item => item.email === sellItem.email);
                if (existingItem) {
                  existingItem.message += ` | ${sellItem.message}`;
                  existingItem.success = existingItem.success && sellItem.success;
                } else {
                  responseData.push(sellItem);
                }
              });
            }
          }
        } else {
          // 原有的单向操作逻辑
          const response = await axios.post('/api/subaccounts/batch-open', {
            emails: selectedAccounts.value,
            userId: userIdValue,
            symbol: openForm.symbol,
            orderType: openForm.orderType,
            side: openForm.side,
            quantityType: openForm.quantityType === 'CONTRACT' ? 'CONTRACT' : 'USD',
            quantity: openForm.quantity,
            price: openForm.orderType === 'LIMIT' ? openForm.price : undefined,
            leverage: openForm.leverage
          }, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          responseData = response.data;
          
          // 记录手续费（仅限价单）
          if (openForm.orderType === 'LIMIT' && openForm.price) {
            // 为每个成功的订单记录手续费
            responseData.filter(item => item.success).forEach(async (item) => {
              const orderId = item.message.match(/订单ID: (\d+)/)?.[1];
              if (orderId) {
                try {
                  // 查询订单状态
                  const orderStatus = await axios.post('/api/subaccounts/check-order', {
                    email: item.email,
                    symbol: openForm.symbol,
                    orderId: orderId
                  });
                  
                  // 记录订单历史
                  await axios.post('/api/order-history/record', {
                    email: item.email,
                    symbol: openForm.symbol,
                    orderType: openForm.orderType,
                    side: openForm.side,
                    amount: openForm.quantity,
                    price: openForm.price,
                    status: orderStatus.data.status,
                    executedQty: orderStatus.data.executedQty,
                    orderId: orderId,
                    leverage: openForm.leverage
                  });
                } catch (error) {
                  console.error('记录买入订单历史失败:', error);
                }
              }
            });
          }
        }
        
        operationResults.value = responseData;
        resultDialogVisible.value = true;
        
        // 统计成功和失败数量
        const success = operationResults.value.filter(r => r.success).length;
        const failed = operationResults.value.length - success;
        
        if (failed === 0) {
          ElMessage.success(`批量开仓成功: ${success}个子账号操作成功`);
        } else if (success === 0) {
          ElMessage.error(`批量开仓失败: ${failed}个子账号操作失败`);
        } else {
          ElMessage.warning(`批量开仓部分成功: ${success}个成功, ${failed}个失败`);
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量开仓失败: ' + (error.response?.data?.message || error.message));
        }
      } finally {
        isSubmitting.value = false;
      }
    }

    const submitBatchClose = async () => {
      try {
        isSubmitting.value = true
        
        // 确认操作
        await ElMessageBox.confirm(
          `确定要为${selectedAccounts.value.length}个子账号执行批量平仓操作吗？`,
          '确认操作',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        const response = await axios.post('/api/subaccounts/batch-close', {
          emails: selectedAccounts.value,
          userId: userIdValue,
          symbol: closeForm.symbol,
          closeType: closeForm.closeType,
          percentage: closeForm.closeType === 'PARTIAL' ? closeForm.percentage : 100
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        operationResults.value = response.data
        resultDialogVisible.value = true
        
        // 统计成功和失败数量
        const success = operationResults.value.filter(r => r.success).length
        const failed = operationResults.value.length - success
        
        if (failed === 0) {
          ElMessage.success(`批量平仓成功: ${success}个子账号操作成功`)
        } else if (success === 0) {
          ElMessage.error(`批量平仓失败: ${failed}个子账号操作失败`)
        } else {
          ElMessage.warning(`批量平仓部分成功: ${success}个成功, ${failed}个失败`)
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量平仓失败: ' + (error.response?.data?.message || error.message))
        }
      } finally {
        isSubmitting.value = false
      }
    }

    const submitBatchTransfer = async () => {
      try {
        isSubmitting.value = true
        
        // 检查是否选择了子账号
        if (selectedAccounts.value.length === 0) {
          ElMessage.warning('请至少选择一个子账号')
          isSubmitting.value = false
          return
        }
        
        // 确认操作
        await ElMessageBox.confirm(
          `确定要为${selectedAccounts.value.length}个子账号执行批量划转操作吗？`,
          '确认操作',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        // 检查转账数量是否合法
        if (!transferForm.amount || isNaN(parseFloat(transferForm.amount)) || parseFloat(transferForm.amount) <= 0) {
          ElMessage.warning('请输入有效的划转数量')
          isSubmitting.value = false
          return
        }
        
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        // 批量操作结果
        const results = [];
        
        // 对每个选中的子账户执行资金划转操作
        for (const email of selectedAccounts.value) {
          try {
            console.log(`正在为子账户 ${email} 执行划转操作`);
            
            // 使用新的API接口 - 现货和合约账户之间的资金划转
            const response = await axios.post('/api/subaccounts/batch-spot-futures-transfer', {
              email: email,
              userId: userIdValue,
              direction: transferForm.direction,
              asset: transferForm.asset.trim(),
              amount: parseFloat(transferForm.amount)
            }, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            if (response.data && response.data.success) {
              results.push({
                email: email,
                success: true,
                message: response.data.message || "划转成功"
              });
            } else {
              results.push({
                email: email,
                success: false,
                message: response.data?.error || "划转失败"
              });
            }
          } catch (error) {
            console.error(`子账户 ${email} 划转出错:`, error);
            results.push({
              email: email,
              success: false,
              message: error.response?.data?.error || error.message || "划转异常"
            });
          }
        }
        
        // 显示操作结果
        operationResults.value = results;
        resultDialogVisible.value = true;
        
        // 统计成功和失败数量
        const success = results.filter(r => r.success).length;
        const failed = results.length - success;
        
        if (failed === 0) {
          ElMessage.success(`批量划转成功: ${success}个子账号操作成功`);
        } else if (success === 0) {
          ElMessage.error(`批量划转失败: ${failed}个子账号操作失败`);
        } else {
          ElMessage.warning(`批量划转部分成功: ${success}个成功, ${failed}个失败`);
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量划转出错:', error);
          ElMessage.error('批量划转失败: ' + (error.response?.data?.error || error.message));
        }
      } finally {
        isSubmitting.value = false;
      }
    }

    const importApiSettings = () => {
      importDialogVisible.value = true
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
          const response = await axios.get('/api/subaccounts/api-export?include_master=true', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          // 创建下载链接
          const data = JSON.stringify(response.data, null, 2)
          const blob = new Blob([data], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          
          // 创建下载链接并点击
          const link = document.createElement('a')
          link.href = url
          link.download = 'api-settings.json'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          
          ElMessage.success('API设置导出成功(包含主账号)')
        }).catch(() => {
          // 不包含主账号API，仅导出子账号
          axios.get('/api/subaccounts/api-export', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }).then(response => {
            // 创建下载链接
            const data = JSON.stringify(response.data, null, 2)
            const blob = new Blob([data], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            
            // 创建下载链接并点击
            const link = document.createElement('a')
            link.href = url
            link.download = 'api-settings.json'
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            
            ElMessage.success('API设置导出成功(仅子账号)')
          })
        })
      } catch (error) {
        ElMessage.error('API设置导出失败: ' + error.message)
      }
    }

    const handleFileUpload = (event) => {
      apiFile.value = event.target.files[0]
    }

    const confirmImport = async () => {
      const user = getCurrentUser()
      const token = user?.token
      
      if (apiFile.value) {
        const formData = new FormData()
        formData.append('file', apiFile.value)
        
        try {
          const response = await axios.post('/api/subaccounts/api-import', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
              'Authorization': `Bearer ${token}`
            }
          })
          
          importDialogVisible.value = false
          apiFile.value = null
          apiJsonContent.value = ''
          selectedImportAccount.value = ''
          importToMasterAccount.value = false
          
          // 刷新子账号列表
          await refreshSubaccounts()
          
          ElMessage.success(`API设置导入成功: ${response.data.success_count || 0}个成功`)
        } catch (error) {
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
            };
            
            await axios.post('/api/subaccounts/api-import', apiSettings, {
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              }
            });
            
            importDialogVisible.value = false
            apiJsonContent.value = ''
            importToMasterAccount.value = false
            
            ElMessage.success('主账号API设置导入成功')
          }
          // 如果是导入到子账号且选择了子账号
          else if (selectedImportAccount.value) {
            // 添加邮箱信息
            const email = selectedImportAccount.value;
            
            // 创建符合后端格式的数据结构
            const apiSettings = {
              settings: {
                [email]: {
                  apiKey: jsonData.apiKey,
                  apiSecret: jsonData.secretKey || jsonData.apiSecret
                }
              }
            };
            
            const response = await axios.post('/api/subaccounts/api-import', apiSettings, {
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              }
            });
            
            importDialogVisible.value = false
            apiJsonContent.value = ''
            selectedImportAccount.value = ''
            
            // 刷新子账号列表
            await refreshSubaccounts()
            
            ElMessage.success(`API设置导入成功: ${response.data.count || 0}个成功`)
          }
        } catch (error) {
          ElMessage.error('API设置导入失败: ' + error.message)
        }
      } else {
        ElMessage.warning('请选择文件或输入JSON内容并选择账号')
      }
    }

    // 查询子账号合约余额
    const queryFuturesBalance = async () => {
      if (selectedBalanceAccounts.value.length === 0) {
        ElMessage.warning('请至少选择一个子账号')
        return
      }

      try {
        isLoadingBalance.value = true
        futuresBalances.value = []
        
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        console.log("当前资产筛选:", balanceAssetFilter.value); // 添加日志记录
        
        // 查询每个选中子账号的合约余额
        for (const email of selectedBalanceAccounts.value) {
          try {
            const requestData = {
              email: email,
              userId: userIdValue
            };
            
            // 只有当选择了特定资产时才添加asset参数
            if (balanceAssetFilter.value) {
              requestData.asset = balanceAssetFilter.value;
            }
            
            console.log(`向后端发送请求:`, requestData); // 打印请求数据
            
            const response = await axios.post('/api/subaccounts/futures-balance', requestData, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            if (response.data && response.data.success) {
              // 处理返回的余额数据
              const balances = response.data.data || []
              
              // 将数据转换为表格所需格式
              const formattedBalances = balances.map(item => ({
                email: email,
                asset: item.asset,
                balance: parseFloat(item.balance).toFixed(6),
                available: parseFloat(item.availableBalance || 0).toFixed(6)
              }))
              
              // 添加到结果列表
              futuresBalances.value.push(...formattedBalances)
            } else {
              // 添加错误信息
              futuresBalances.value.push({
                email: email,
                asset: 'ERROR',
                balance: '查询失败',
                available: response.data?.error || '未知错误'
              })
            }
          } catch (err) {
            console.error(`查询${email}合约余额出错:`, err)
            futuresBalances.value.push({
              email: email,
              asset: 'ERROR',
              balance: '查询失败',
              available: err.message
            })
          }
        }
        
        // 按子账号和资产排序
        futuresBalances.value.sort((a, b) => {
          if (a.email !== b.email) return a.email.localeCompare(b.email)
          return a.asset.localeCompare(b.asset)
        })
        
        if (futuresBalances.value.length === 0) {
          ElMessage.info('所选子账号没有合约余额数据')
        }
      } catch (error) {
        console.error('查询合约余额时出错:', error)
        ElMessage.error('查询合约余额失败: ' + error.message)
      } finally {
        isLoadingBalance.value = false
      }
    }

    // 查询子账号持仓信息
    const queryFuturesPositions = async () => {
      if (selectedPositionsAccounts.value.length === 0) {
        ElMessage.warning('请至少选择一个子账号')
        return
      }

      try {
        isLoadingPositions.value = true
        futuresPositions.value = []
        
        const user = getCurrentUser()
        const userIdValue = user?.id
        const token = user?.token
        
        // 批量查询所有选中子账号的持仓信息
        const response = await axios.post('/api/subaccounts/futures-positions', {
          emails: selectedPositionsAccounts.value,
          userId: userIdValue
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data && response.data.success) {
          futuresPositions.value = response.data.data || [];
        } else {
          ElMessage.error(response.data?.error || '查询持仓信息失败');
        }
        
        if (futuresPositions.value.length === 0) {
          ElMessage.info('所选子账号没有持仓信息')
        }
      } catch (error) {
        console.error('查询持仓信息时出错:', error)
        ElMessage.error('查询持仓信息失败: ' + error.message)
      } finally {
        isLoadingPositions.value = false
      }
    }

    // 获取交易对列表
    const loadTradingPairs = async () => {
      isLoadingTradingPairs.value = true
      try {
        const response = await axios.get('/api/trading-pairs/', {
          params: {
            favorite: 'true' // 只获取收藏的交易对
          }
        })
        
        if (response.data.success) {
          tradingPairs.value = response.data.data.map(pair => ({
            label: `${pair.symbol} - ${pair.description}`,
            value: pair.symbol
          }))
        } else {
          console.error('获取交易对失败:', response.data.error)
          // 使用默认交易对列表作为备用
          tradingPairs.value = [
            { label: 'BTCUSDT - 比特币/USDT', value: 'BTCUSDT' },
            { label: 'ETHUSDT - 以太坊/USDT', value: 'ETHUSDT' },
            { label: 'BNBUSDT - 币安币/USDT', value: 'BNBUSDT' }
          ]
        }
      } catch (error) {
        console.error('获取交易对失败:', error)
        // 使用默认交易对列表作为备用
        tradingPairs.value = [
          { label: 'BTCUSDT - 比特币/USDT', value: 'BTCUSDT' },
          { label: 'ETHUSDT - 以太坊/USDT', value: 'ETHUSDT' },
          { label: 'BNBUSDT - 币安币/USDT', value: 'BNBUSDT' }
        ]
      } finally {
        isLoadingTradingPairs.value = false
      }
    }

    // 初始化函数
    const initialize = async () => {
      await refreshSubaccounts() // 加载子账户列表
      loadTradingPairs() // 加载交易对列表
    }

    // 生命周期钩子
    onMounted(initialize)

    
    // 计算单个订单手续费
    const calculateFee = (price, amount, feeType) => {
      if (!price || !amount) return '0';
      
      // 使用feeCalculator.js中的功能
      const order = {
        symbol: gridForm.symbol || openForm.symbol,
        orderType: 'LIMIT',
        productType: 'USDT_FUTURE',
        amount: amount,
        price: price,
        status: 'FILLED',
        isMaker: feeType === 'MAKER'
      };
      
      const { fee } = calculateOrderFee(order);
      return fee;
    }
    
    // 计算普通订单手续费
    const calculatedFee = computed(() => {
      if (openForm.orderType !== 'LIMIT' || !openForm.price) return '0'
      
      if (openForm.side !== 'BOTH') {
        if (openForm.quantityType === 'USD') {
          // USDT计价时，手续费以USDT支付
          return calculateFee(1, openForm.quantity, openForm.feeType) + ' USDT'
        } else {
          // 本币计价时，手续费以交易币种支付
          return calculateFee(openForm.price, openForm.quantity, openForm.feeType) + 
            (openForm.symbol ? ' ' + openForm.symbol.replace('USDT', '') : '')
        }
      }
      return '0'
    })
    
    // 计算买入订单手续费
    const calculatedBuyFee = computed(() => {
      if (openForm.orderType !== 'LIMIT' || !openForm.price || !openForm.buyQuantity) return '0'
      
      if (openForm.quantityType === 'USD') {
        return calculateFee(1, openForm.buyQuantity, openForm.feeType) + ' USDT'
      } else {
        return calculateFee(openForm.price, openForm.buyQuantity, openForm.feeType) + 
          (openForm.symbol ? ' ' + openForm.symbol.replace('USDT', '') : '')
      }
    })
    
    // 计算卖出订单手续费
    const calculatedSellFee = computed(() => {
      if (openForm.orderType !== 'LIMIT' || !openForm.price || !openForm.sellQuantity) return '0'
      
      if (openForm.quantityType === 'USD') {
        return calculateFee(1, openForm.sellQuantity, openForm.feeType) + ' USDT'
      } else {
        return calculateFee(openForm.price, openForm.sellQuantity, openForm.feeType) + 
          (openForm.symbol ? ' ' + openForm.symbol.replace('USDT', '') : '')
      }
    })

    return {
      tradingPairs,
      isLoadingTradingPairs,
      activeTab,
      subaccounts,
      selectedAccounts,
      selectAllAccounts,
      isSubmitting,
      resultDialogVisible,
      operationResults,
      importDialogVisible,
      apiFile,
      apiJsonContent,
      selectedImportAccount,
      importToMasterAccount,
      subaccountsWithoutApi,
      subaccountsWithApi,
      selectedBalanceAccounts,
      isLoadingBalance,
      futuresBalances,
      queryFuturesBalance,
      openForm,
      closeForm,
      transferForm,
      gridForm,
      isOpenFormValid,
      isCloseFormValid,
      isTransferFormValid,
      refreshSubaccounts,
      handleSelectAllChange,
      submitBatchOpen,
      submitBatchClose,
      submitBatchTransfer,
      importApiSettings,
      exportApiSettings,
      handleFileUpload,
      confirmImport,
      canImport,
      balanceAssetFilter,
      selectedPositionsAccounts,
      isLoadingPositions,
      futuresPositions,
      queryFuturesPositions,
      isGridFormValid,
      totalAmount,
      gridProgress,
      isGridSubmitting,
      submitGridOrders,
      calculatedFee,
      calculatedBuyFee,
      calculatedSellFee,
      orderListRef, // 添加orderListRef到返回值
      orderRefreshTimer,
      startAutoRefreshOrders,
      stopAutoRefreshOrders
    }
  }
}
</script>

<style scoped>
.subaccount-list {
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 10px;
}

.order-filled-row {
  background-color: rgba(103, 194, 58, 0.1) !important;
}

.order-canceled-row {
  background-color: rgba(245, 108, 108, 0.1) !important;
}

.fee-container {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.fee-type-select {
  width: 140px;
  margin-right: 12px;
}

.fee-info {
  flex: 1;
  background-color: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.fee-label {
  font-weight: 500;
  color: #606266;
}

.fee-value {
  color: #409EFF;
}
</style>