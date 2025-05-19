<template>
  <div class="container-fluid mt-4">
    <div class="row mb-4">
      <div class="col">
        <h2 class="page-title">批量子账号操作</h2>
        <p class="page-description">在此页面可以对多个子账号进行批量操作，包括开仓、平仓、划转资金和网格建仓等功能。</p>
      </div>
    </div>

    <div class="row mb-4">
      <div class="col d-flex gap-3 action-buttons">
        <el-button type="primary" @click="refreshSubaccounts" class="action-btn">
          <i class="bi bi-arrow-clockwise me-2"></i>刷新子账号
        </el-button>
        <el-button type="success" @click="importApiSettings" class="action-btn">
          <i class="bi bi-cloud-upload me-2"></i>导入API设置
        </el-button>
        <el-button type="info" @click="exportApiSettings" class="action-btn">
          <i class="bi bi-cloud-download me-2"></i>导出API设置
        </el-button>
      </div>
    </div>

    <div class="row mb-3">
      <div class="col">
        <el-tabs v-model="activeTab" class="custom-tabs">
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
                    <div class="mb-3 subaccount-list">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                            <span v-if="!account.hasApiKey" class="text-danger">(无API密钥)</span>
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
                    <div class="mb-3">
                      <label class="form-label">杠杆</label>
                      <el-input v-model="openForm.leverage" type="number" placeholder="输入杠杆倍数(1-125)" min="1" max="125"></el-input>
                      <small class="form-text text-muted">可输入1至125之间的整数</small>
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
                    <div class="mb-3 subaccount-list">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                            <span v-if="!account.hasApiKey" class="text-danger">(无API密钥)</span>
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
                    <div class="mb-3 subaccount-list">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                            <span v-if="!account.hasApiKey" class="text-danger">(无API密钥)</span>
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
                    <div class="mb-3 subaccount-list">
                      <el-checkbox-group v-model="selectedAccounts">
                        <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                            <span v-if="!account.hasApiKey" class="text-danger">(无API密钥)</span>
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
                    
                    <div class="section-divider">
                      <span class="section-title">合约设置</span>
                    </div>
                    
                    <div class="highlight-form-item">
                      <div class="mb-3">
                        <label class="form-label">合约类型</label>
                        <el-radio-group v-model="gridForm.contractType">
                          <el-radio label="usdt_futures">U本位合约</el-radio>
                          <el-radio label="coin_futures">币本位合约</el-radio>
                        </el-radio-group>
                      </div>
                      
                    <div class="mb-3">
                      <label class="form-label">限价</label>
                        <el-input 
                          v-model="gridForm.price" 
                          type="number" 
                          placeholder="输入限价" 
                          @input="validatePrice"
                        />
                    </div>
                      
                      <!-- U本位合约显示数量计算方式选择 -->
                      <div class="mb-3" v-if="gridForm.contractType === 'usdt_futures'">
                        <label class="form-label">数量计算方式</label>
                        <el-radio-group v-model="gridForm.quantityType">
                          <el-radio label="CONTRACT">本币</el-radio>
                          <el-radio label="USD">USDT</el-radio>
                        </el-radio-group>
                      </div>
                      
                      <!-- 币本位合约固定使用张数 -->
                      <div class="mb-3" v-if="gridForm.contractType === 'coin_futures'">
                        <label class="form-label">单位说明</label>
                        <div class="text-muted small">
                          币本位合约使用"张"作为单位，每个交易对的面值可能不同
                        </div>
                      </div>
                    </div>
                    
                    <div class="section-divider">
                      <span class="section-title">数量设置</span>
                    </div>
                      
                    <!-- 根据合约类型显示不同的数量输入 -->
                    <div class="mb-3">
                      <label class="form-label">
                        {{ 
                          gridForm.contractType === 'coin_futures' 
                            ? '单笔数量（张）' 
                            : (gridForm.quantityType === 'CONTRACT' ? '单笔数量（本币）' : '单笔金额（USDT）')
                        }}
                      </label>
                      <el-input 
                        v-model="gridForm.singleAmount" 
                        type="number" 
                        :placeholder="
                          gridForm.contractType === 'coin_futures' 
                            ? '输入合约张数(整数)' 
                            : (gridForm.quantityType === 'CONTRACT' ? '输入单笔数量' : '输入单笔USDT金额')
                        "
                        :step="gridForm.contractType === 'coin_futures' ? 1 : 0.001"
                        @input="handleCoinFuturesInput"
                      />
                  </div>
                    <div class="mb-3">
                      <label class="form-label">订单总数</label>
                      <el-input-number v-model="gridForm.totalOrders" :min="1" :max="20" />
                      </div>
                    <div class="mb-3">
                      <label class="form-label">
                        {{ 
                          gridForm.contractType === 'coin_futures' 
                            ? '总仓位数量（张）' 
                            : (gridForm.quantityType === 'CONTRACT' ? '总仓位数量（本币）' : '总仓位金额（USDT）')
                        }}
                      </label>
                      <el-input 
                        v-model="totalAmount" 
                        type="text" 
                        placeholder="总仓位数量" 
                        disabled 
                      />
                      <small class="form-text text-muted">总数 = 单笔{{ gridForm.contractType === 'coin_futures' ? '张数' : (gridForm.quantityType === 'CONTRACT' ? '数量' : '金额') }} × 订单数</small>
                    </div>
                    
                    <div class="section-divider">
                      <span class="section-title">高级设置</span>
                    </div>
                    
                      <div class="mb-3">
                      <label class="form-label">杠杆</label>
                      <el-input v-model="gridForm.leverage" type="number" placeholder="输入杠杆倍数(1-125)" min="1" max="125" />
                      <small class="form-text text-muted">可输入1至125之间的整数</small>
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
                    
                    <!-- 添加统计信息卡片 -->
                    <div class="stats-card mt-4" v-if="gridForm.symbol && gridForm.price && gridForm.singleAmount">
                      <div class="stats-card-header">
                        <span>订单统计</span>
                    </div>
                      <div class="stats-card-body">
                        <div class="stats-item">
                          <span class="stats-label">合约类型</span>
                          <span class="stats-value">{{ gridForm.contractType === 'usdt_futures' ? 'U本位合约' : '币本位合约' }}</span>
                </div>
                        <div class="stats-item">
                          <span class="stats-label">交易对</span>
                          <span class="stats-value">{{ gridForm.symbol }}</span>
                        </div>
                        <div class="stats-item">
                          <span class="stats-label">价格</span>
                          <span class="stats-value">{{ gridForm.price }}</span>
                        </div>
                        <div class="stats-item">
                          <span class="stats-label">单位</span>
                          <span class="stats-value">{{ gridForm.contractType === 'coin_futures' ? '张' : (gridForm.quantityType === 'CONTRACT' ? '本币' : 'USDT') }}</span>
                        </div>
                        <div class="stats-item">
                          <span class="stats-label">选择账号数</span>
                          <span class="stats-value">{{ selectedAccounts.length }}</span>
                        </div>
                        <div class="stats-item">
                          <span class="stats-label">总订单数</span>
                          <span class="stats-value highlight">{{ selectedAccounts.length * gridForm.totalOrders }}</span>
                        </div>
                      </div>
                    </div>
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
                    <div class="mb-3 subaccount-list">
                      <el-checkbox-group v-model="selectedBalanceAccounts">
                        <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                          <el-checkbox :label="account.email">
                            {{ account.email }}
                            <span v-if="!account.hasApiKey" class="text-danger">(无API密钥)</span>
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
            <PositionMonitor 
              :subaccounts="subaccounts" 
              :active-tab="activeTab" 
            />
            <PositionList :subaccounts="subaccounts" />
          </el-tab-pane>

          <el-tab-pane label="订单管理" name="orderManage">
            <LimitOrderList id="batch-order-list" ref="orderListRef" :subaccounts="subaccounts" />
          </el-tab-pane>
          
          <el-tab-pane label="历史成交" name="tradesHistory">
            <TradeHistoryList :subaccounts="subaccounts" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 批量操作结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="操作结果" width="80%" class="result-dialog">
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
import { ref, reactive, computed, onMounted, watch, onBeforeUnmount, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { getCurrentUser } from '../services/auth'
import LimitOrderList from '@/components/LimitOrderList.vue'
import PositionList from '@/components/PositionList.vue'
import TradeHistoryList from '@/components/TradeHistoryList.vue'
import PositionMonitor from '@/components/PositionMonitor.vue'
import { useSubaccountsStore } from '@/stores/subaccounts'

export default {
  name: 'BatchSubAccount',
  components: {
    LimitOrderList,
    PositionList,
    TradeHistoryList,
    PositionMonitor,
  },
  setup() {
    const subaccountsStore = useSubaccountsStore()
    
    // 使用 store 中的状态
    const subaccounts = computed(() => subaccountsStore.subaccounts)
    const subaccountsWithApi = computed(() => subaccountsStore.getSubaccountsWithApi())
    const subaccountsWithoutApi = computed(() => subaccountsStore.getSubaccountsWithoutApi())
    
    // 交易对列表
    const tradingPairs = ref([])
    const isLoadingTradingPairs = ref(false)
    
    // 状态
    const activeTab = ref('open')
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
      leverage: 1,  // 将空字符串改为1，设置默认杠杆倍数为1
      reduceOnly: false,
      quantityType: 'USDT',
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
      leverage: 1,  // 将空字符串改为1，设置默认杠杆倍数为1
      interval: 5,
      contractType: 'usdt_futures',
      quantityType: 'CONTRACT',
    })

    // 标签页切换监控
    watch(activeTab, () => {
      // 组件内已处理标签页切换逻辑
    });
    
    // 组件卸载时清除定时器
    onBeforeUnmount(() => {
      // 组件内已处理定时器清理
    });

    // 计算属性
    const isOpenFormValid = computed(() => {
      if (selectedAccounts.value.length === 0 || 
          !openForm.symbol || 
          (openForm.orderType === 'LIMIT' && !openForm.price) ||
          !openForm.leverage || openForm.leverage < 1) {  // 将杠杆倍数最小值从2改为1
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
      // 只验证是否填写了价格，不验证大小
      const priceValid = gridForm.price && !isNaN(parseFloat(gridForm.price));
      
      return selectedAccounts.value.length > 0 && 
             gridForm.symbol && 
             priceValid &&
             gridForm.contractType &&
             gridForm.quantityType &&
             gridForm.singleAmount && 
             gridForm.totalOrders && 
             gridForm.leverage && 
             gridForm.interval
    })

    const totalAmount = computed(() => {
      if (!gridForm.singleAmount || !gridForm.totalOrders) {
        return '0';
      }
      
      const amount = parseFloat(gridForm.singleAmount);
      const orders = gridForm.totalOrders;
      
      // 币本位合约确保总数也是整数
      if (gridForm.contractType === 'coin_futures') {
        return (Math.floor(amount) * orders).toString();
      }
      
      // U本位合约保留小数位
      return (amount * orders).toFixed(4);
    })

    // 在script的setup中添加新的isGridSubmitting状态
    const isGridSubmitting = ref(false);
    
    // 辅助函数：确保价格格式正确
    const formatPrice = (price) => {
      // 确保是数字
      const numPrice = Number(price);
      if (isNaN(numPrice)) {
        throw new Error(`无效价格: ${price}`);
      }
      
      // 使用标准浮点数表示，避免科学计数法
      return numPrice.toString();
    };
    
    // 在script的setup中修改submitGridOrders方法
    const submitGridOrders = async () => {
      try {
        // 检查表单数据
        if (!isGridFormValid.value) {
          ElMessage.warning('请完善表单');
          return;
        }
        
        // 准备确认消息
        let confirmMessage = `将为${selectedAccounts.value.length}个子账号同时建立${gridForm.totalOrders}笔多空仓位，\n`;
        confirmMessage += `合约类型: ${gridForm.contractType === 'usdt_futures' ? 'U本位合约' : '币本位合约'}\n`;
        
        if (gridForm.contractType === 'coin_futures') {
          confirmMessage += `总数量: ${totalAmount.value}张 ${gridForm.symbol}\n`;
          confirmMessage += `每笔: ${gridForm.singleAmount}张\n`;
        } else if (gridForm.quantityType === 'CONTRACT') {
          confirmMessage += `总数量: ${totalAmount.value}个 ${gridForm.symbol.slice(0, -4)}\n`;
          confirmMessage += `每笔: ${gridForm.singleAmount}个 ${gridForm.symbol.slice(0, -4)}\n`;
        } else {
          confirmMessage += `总金额: ${totalAmount.value} USDT\n`;
          confirmMessage += `每笔: ${gridForm.singleAmount} USDT\n`;
        }
        
        confirmMessage += `价格: ${gridForm.price} USDT\n`;
        confirmMessage += `确认执行？`;
        
        // 确认操作
        await ElMessageBox.confirm(
          confirmMessage,
          '确认网格建仓',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        isGridSubmitting.value = true;
        
        // 设置进度状态
        const gridProgress = {
          isRunning: true,
          current: 0,
          total: selectedAccounts.value.length * gridForm.totalOrders,
          percentage: 0
        };
        
        // 触发进度更新事件，传递给订单管理页面
        window.dispatchEvent(new CustomEvent('grid-progress-update', { 
          detail: gridProgress 
        }));
        
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
              // 构建API请求参数
              const requestData = {
                email: email,
                symbol: gridForm.symbol,
                upper_price: parseFloat(gridForm.price) * 1.005,
                lower_price: parseFloat(gridForm.price) * 0.995,
                grid_num: 2,
                is_bilateral: true,
                leverage: parseInt(gridForm.leverage),
                market_type: gridForm.contractType
              };
              
              // 确保价格字段为正数并格式化
              try {
                requestData.upper_price = formatPrice(requestData.upper_price);
                requestData.lower_price = formatPrice(requestData.lower_price);
              } catch (error) {
                throw new Error(`价格格式化错误: ${error.message}`);
              }
              
              // 直接设置网格价格，避免后端计算为0
              requestData.grid_prices = [requestData.lower_price, requestData.upper_price];
              
              // 根据合约类型和数量计算方式设置参数
              if (gridForm.contractType === 'coin_futures') {
                // 币本位合约使用张数(整数)
                requestData.quantity = Math.floor(parseFloat(gridForm.singleAmount));
                requestData.quantity_type = 'CONTRACTS'; // 使用张数单位
                
                // 币本位合约API端点和参数
                requestData.contract_type = 'PERPETUAL'; // 永续合约
                requestData.api_path = '/dapi/v1'; // 币本位API路径
              } else {
                // U本位合约
                if (gridForm.quantityType === 'CONTRACT') {
                  // 使用本币数量
                  requestData.single_amount = parseFloat(gridForm.singleAmount);
                } else {
                  // 使用USDT金额
                  requestData.quote_order_qty = parseFloat(gridForm.singleAmount);
                }
                
                // U本位合约API路径
                requestData.api_path = '/fapi/v1';
              }
              
              // 打印请求数据以便调试
              console.log('网格建仓请求参数:', JSON.stringify(requestData, null, 2));
              
              // 使用网格交易API
              const response = await axios.post('/api/trading/grid/submit-and-monitor', requestData);
              
              // 调试信息
              console.log('网格建仓响应:', response.data);
              
              // 检查返回的网格价格
              if (response.data?.data?.grid_info?.grid_prices) {
                console.log('返回的网格价格:', response.data.data.grid_info.grid_prices);
                
                // 检查是否有价格为0
                const gridPrices = JSON.parse(response.data.data.grid_info.grid_prices);
                if (gridPrices.some(price => parseFloat(price) === 0)) {
                  console.error('警告: 返回的网格价格中有0值:', gridPrices);
                  ElMessage.warning('服务器返回的网格价格有误，请联系管理员');
                }
              }
              
              // 更新进度
              gridProgress.current += 1;
              gridProgress.percentage = Math.floor((gridProgress.current / gridProgress.total) * 100);
              
              // 触发进度更新事件
              window.dispatchEvent(new CustomEvent('grid-progress-update', { 
                detail: gridProgress 
              }));
              
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
              
              // 触发进度更新事件
              window.dispatchEvent(new CustomEvent('grid-progress-update', { 
                detail: gridProgress 
              }));
              
              return {
                email: email,
                order: batch + 1,
                time: new Date().toLocaleTimeString(),
                success: false,
                message: error.response?.data?.error || error.message
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
        
        // 发送最终进度更新
        window.dispatchEvent(new CustomEvent('grid-progress-update', { 
          detail: gridProgress 
        }));
        
        // 5秒后隐藏进度条
        setTimeout(() => {
          gridProgress.isRunning = false;
          window.dispatchEvent(new CustomEvent('grid-progress-update', { 
            detail: gridProgress 
          }));
        }, 5000);
        
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
      }
    };

    // 在这里添加订单自动刷新相关变量和函数
    const orderRefreshTimer = ref(null);
    const orderListRef = ref(null); // 添加对LimitOrderList组件的引用
    const refreshLockKey = 'order_refresh_lock'; // 用于储存刷新锁的key
    const refreshLockDuration = 10000; // 锁定时间，10秒
    const debounceTimer = ref(null); // 添加debounceTimer的定义

    // 检查是否可以获得刷新锁
    const canAcquireRefreshLock = () => {
      const now = Date.now();
      const lockInfo = localStorage.getItem(refreshLockKey);
      
      if (!lockInfo) {
        return true;
      }
      
      try {
        const lock = JSON.parse(lockInfo);
        // 如果锁已经过期
        if (now > lock.expiry) {
          return true;
        }
        
        // 如果是当前页面设置的锁
        if (lock.pageId === getPageId()) {
          return true;
        }
        
        // 否则锁仍然有效且被其他页面持有
        return false;
      } catch (e) {
        console.error('解析刷新锁信息出错:', e);
        return true; // 出错时允许刷新
      }
    };
    
    // 获取或生成页面唯一ID
    const getPageId = () => {
      // 尝试从sessionStorage获取当前页面ID
      let pageId = sessionStorage.getItem('page_id');
      if (!pageId) {
        // 如果不存在则生成新ID
        pageId = `page_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        sessionStorage.setItem('page_id', pageId);
      }
      return pageId;
    };
    
    // 获取刷新锁
    const acquireRefreshLock = () => {
      if (!canAcquireRefreshLock()) {
        return false;
      }
      
      const now = Date.now();
      const lock = {
        pageId: getPageId(),
        acquired: now,
        expiry: now + refreshLockDuration
      };
      
      localStorage.setItem(refreshLockKey, JSON.stringify(lock));
      return true;
    };
    
    // 释放刷新锁
    const releaseRefreshLock = () => {
      const lockInfo = localStorage.getItem(refreshLockKey);
      if (!lockInfo) return;
      
      try {
        const lock = JSON.parse(lockInfo);
        // 只释放自己的锁
        if (lock.pageId === getPageId()) {
          localStorage.removeItem(refreshLockKey);
        }
      } catch (e) {
        console.error('释放刷新锁出错:', e);
      }
    };

    // 开始自动刷新订单列表
    const startAutoRefreshOrders = () => {
      // 清除可能存在的旧定时器
      if (orderRefreshTimer.value) {
        clearInterval(orderRefreshTimer.value);
      }
      
      // 创建新的定时器，每1秒刷新一次
      orderRefreshTimer.value = setInterval(() => {
        // 如果当前不在订单管理页面，则停止刷新
        if (activeTab.value !== 'orderManage') {
          stopAutoRefreshOrders();
          return;
        }
        
        // 只有获取到锁的页面才执行刷新
        if (!acquireRefreshLock()) {
          console.log('其他页面正在刷新订单，本页面暂停刷新');
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
          // 尝试直接获取组件实例并刷新
          const orderListComponent = document.querySelector('#order-list-component');
          if (orderListComponent && orderListComponent.__vue__) {
            console.log('尝试使用DOM方式获取组件实例...');
            const instance = orderListComponent.__vue__;
            if (typeof instance.refreshOrderList === 'function') {
              instance.refreshOrderList();
            } else if (typeof instance.fetchOrders === 'function') {
              instance.fetchOrders(false);
            }
          }
        }
      }, 1000);
      
      // 显示开始自动刷新的提示
      ElMessage.success({
        message: '已开启订单自动刷新(每1秒)',
        duration: 3000
      });
    };

    // 停止自动刷新
    const stopAutoRefreshOrders = () => {
      if (orderRefreshTimer.value) {
        clearInterval(orderRefreshTimer.value);
        orderRefreshTimer.value = null;
        console.log('已停止自动刷新订单列表');
        // 释放刷新锁
        releaseRefreshLock();
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

    const canImport = computed(() => {
      return (apiFile.value || (apiJsonContent.value.trim() !== '' && (importToMasterAccount.value || selectedImportAccount.value)))
    })

    // 方法
    const refreshSubaccounts = async () => {
      try {
        await subaccountsStore.fetchSubaccounts(true)
      } catch (error) {
        console.error('刷新子账号列表失败:', error)
        ElMessage.error('刷新子账号列表失败: ' + error.message)
      }
    }

    const handleSelectAllChange = (val) => {
      if (val) {
        selectedAccounts.value = subaccounts.value.map(account => account.email)
        selectedBalanceAccounts.value = subaccounts.value.map(account => account.email)
        selectedPositionsAccounts.value = subaccounts.value.map(account => account.email)
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
              user_id: userIdValue,
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
              user_id: userIdValue,
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
            }
            
            // 处理卖出结果（如果有）
            if (openForm.sellQuantity > 0) {
              const sellResponse = responses.shift();
              const sellResults = sellResponse.data.map(item => ({
                ...item,
                message: `卖出: ${item.message}`
              }));
              
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
            user_id: userIdValue,
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
          user_id: userIdValue,
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
            
            // 构造请求体，确保格式正确
            const requestData = {
              email: email,
              user_id: userIdValue,
              direction: transferForm.direction,
              asset: transferForm.asset.trim().toUpperCase(), // 确保大写并移除空格
              amount: parseFloat(transferForm.amount)
            };
            
            console.log('划转请求参数:', JSON.stringify(requestData));
            
            // 发送请求 - 需要在后端实现该接口
            const response = await axios.post('/api/subaccounts/batch-spot-futures-transfer', requestData, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              // 增加超时时间
              timeout: 30000
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
            
            // 捕获并记录详细错误信息
            const errorMessage = error.response?.data?.error || 
                                 error.response?.data?.message || 
                                 error.message || 
                                 "未知错误";
            
            console.error('详细错误信息:', errorMessage);
            console.error('错误状态码:', error.response?.status);
            console.error('完整错误响应:', error.response?.data);
            
            results.push({
              email: email,
              success: false,
              message: errorMessage
            });
          }
          
          // 每个请求之间稍微等待一下，避免请求过于密集
          await new Promise(resolve => setTimeout(resolve, 300));
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
              user_id: userIdValue
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
          user_id: userIdValue
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
      try {
        // 先加载子账户列表
        await subaccountsStore.fetchSubaccounts()
        // 再加载交易对列表
        await loadTradingPairs()
      } catch (error) {
        console.error('初始化数据失败:', error)
        ElMessage.error('初始化数据失败: ' + error.message)
      }
    }

    // 生命周期钩子
    onMounted(() => {
      initialize()

      // 监听网格建仓完成事件 - 同时在window和document级别添加
      window.addEventListener('grid-trade-completed', handleGridTradeCompleted);
      document.addEventListener('grid-trade-completed', handleGridTradeCompleted);
      
      // 监听网格建仓开始事件 - 同时在window和document级别添加
      window.addEventListener('grid-trade-started', handleGridTradeStarted);
      document.addEventListener('grid-trade-started', handleGridTradeStarted);
      
      console.log('[BatchSubAccount] 组件已挂载，已添加grid-trade事件监听器');
    })

    onBeforeUnmount(() => {
      stopAutoRefreshOrders()
      
      // 移除网格建仓完成事件监听器 - 同时移除window和document级别的监听
      window.removeEventListener('grid-trade-completed', handleGridTradeCompleted);
      document.removeEventListener('grid-trade-completed', handleGridTradeCompleted);
      
      // 移除网格建仓开始事件监听器 - 同时移除window和document级别的监听
      window.removeEventListener('grid-trade-started', handleGridTradeStarted);
      document.removeEventListener('grid-trade-started', handleGridTradeStarted);
    })

    // 处理币本位合约输入，确保输入为整数
    const handleCoinFuturesInput = (value) => {
      if (gridForm.contractType === 'coin_futures') {
        // 将输入值转换为整数
        gridForm.singleAmount = Math.floor(parseFloat(value) || 0).toString();
      }
    };

    // 验证价格，确保格式正确
    const validatePrice = (value) => {
      // 只验证是否为有效数字，不限制大小
      if (value !== '' && isNaN(parseFloat(value))) {
        ElMessage.warning('请输入有效的数字');
        gridForm.price = '';
      }
    };

    // 监听合约类型变化，当切换到币本位合约时确保数量为整数
    watch(() => gridForm.contractType, (newType) => {
      if (newType === 'coin_futures') {
        // 当切换到币本位合约时，将数量转为整数
        gridForm.singleAmount = Math.floor(parseFloat(gridForm.singleAmount) || 0).toString();
        // 币本位合约固定使用CONTRACT类型
        gridForm.quantityType = 'CONTRACT';
      }
    });

    // 组件卸载时清除定时器和事件监听
    onUnmounted(() => {
      stopAutoRefreshOrders();
      releaseRefreshLock(); // 确保释放锁
      if (debounceTimer.value) {
        clearTimeout(debounceTimer.value);
        debounceTimer.value = null;
      }
      // 移除事件监听器，但不再引用不存在的updateGridProgress函数
      window.removeEventListener('grid-progress-update', function() {
        console.log('清理grid-progress-update事件监听器');
      });
    });

    // 处理网格建仓完成事件
    const handleGridTradeCompleted = (event) => {
      if (event && event.detail && event.detail.success) {
        console.log('接收到网格建仓完成事件，订单数量:', event.detail.ordersCount);
        
        // 切换到订单管理页面
        activeTab.value = 'orderManage';
        
        // 开启自动刷新
        setTimeout(() => {
          startAutoRefreshOrders();
          
          // 显示提示
          ElMessage.success({
            message: `网格建仓完成，已创建${event.detail.ordersCount}个订单，开始自动刷新`,
            duration: 3000
          });
        }, 500); // 短暂延迟以确保页面已切换
      }
    };

    // 处理网格建仓开始事件
    const handleGridTradeStarted = (event) => {
      if (event && event.detail) {
        console.log('接收到网格建仓开始事件，订单数量:', event.detail.ordersCount);
        
        // 立即切换到订单管理页面
        activeTab.value = 'orderManage';
        
        // 开启自动刷新
        setTimeout(() => {
          startAutoRefreshOrders();
          
          // 显示提示
          ElMessage.info({
            message: `网格建仓已开始执行，正在自动刷新订单列表...`,
            duration: 3000
          });
        }, 100); // 短暂延迟以确保页面已切换
      }
    };

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
      isGridSubmitting,
      submitGridOrders,
      orderListRef,
      orderRefreshTimer,
      startAutoRefreshOrders,
      stopAutoRefreshOrders,
      handleCoinFuturesInput,
      validatePrice,
      handleGridTradeStarted,
      handleGridTradeCompleted,
      // 返回刷新锁相关函数
      getPageId,
      acquireRefreshLock,
      releaseRefreshLock,
      canAcquireRefreshLock
    }
  }
}
</script>

<style scoped>
.subaccount-list {
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 10px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
  background-color: #fcfcfc;
}

.subaccount-list::-webkit-scrollbar {
  width: 8px;
}

.subaccount-list::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 4px;
}

.subaccount-list::-webkit-scrollbar-track {
  background-color: #f5f5f5;
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

/* 新增样式 */
.card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  margin-bottom: 20px;
  background-color: #fff;
}

.card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-body {
  padding: 20px;
}

h5 {
  font-weight: 600;
  margin-bottom: 20px;
  color: #303133;
  border-left: 3px solid #409EFF;
  padding-left: 10px;
}

.form-label {
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.form-text {
  font-size: 12px;
  line-height: 1.4;
  margin-top: 5px;
  color: #909399;
}

.mb-3 {
  margin-bottom: 20px !important;
}

.d-grid .el-button {
  width: 100%;
  border-radius: 4px;
  padding: 12px 20px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.d-grid .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.el-tabs__nav {
  border-radius: 4px;
}

.el-tabs__item {
  height: 48px;
  line-height: 48px;
  font-weight: 500;
}

.el-tabs__item.is-active {
  color: #409EFF;
}

.el-button--primary {
  background-color: #409EFF;
}

.el-button--warning {
  background-color: #E6A23C;
}

.el-button--success {
  background-color: #67C23A;
}

.el-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.el-radio-group {
  display: flex;
  gap: 16px;
}

.text-muted {
  color: #909399 !important;
}

.small {
  padding: 8px;
  background-color: #f8f9fa;
  border-radius: 4px;
  display: block;
  line-height: 1.5;
}

/* 响应式布局优化 */
@media (max-width: 768px) {
  .card-body {
    padding: 15px;
  }
  
  .el-radio-group {
    flex-direction: column;
    gap: 8px;
  }
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 10px;
  position: relative;
  display: inline-block;
}

.page-title::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 0;
  width: 60px;
  height: 3px;
  background-color: #409EFF;
  border-radius: 3px;
}

.page-description {
  color: #606266;
  font-size: 15px;
  margin-top: 15px;
  max-width: 800px;
}

.action-buttons {
  flex-wrap: wrap;
}

.action-btn {
  border-radius: 6px;
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
  min-width: 150px;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-btn i {
  font-size: 16px;
  vertical-align: middle;
}

.custom-tabs .el-tabs__header {
  margin-bottom: 20px;
  border-bottom: none;
}

.custom-tabs .el-tabs__nav-wrap::after {
  height: 1px;
  background-color: #ebeef5;
}

.custom-tabs .el-tabs__active-bar {
  height: 3px;
  border-radius: 3px;
}

.custom-tabs .el-tabs__item {
  font-size: 16px;
  font-weight: 500;
  padding: 0 20px;
}

/* 表单组件美化 */
.el-select,
.el-input,
.el-input-number {
  width: 100%;
}

.el-input .el-input__inner,
.el-select .el-input__inner {
  border-radius: 4px;
  height: 40px;
  border-color: #dcdfe6;
  transition: all 0.3s;
}

.el-input .el-input__inner:hover,
.el-select .el-input__inner:hover {
  border-color: #c0c4cc;
}

.el-input .el-input__inner:focus,
.el-select .el-input__inner:focus {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.section-divider {
  height: 1px;
  background-color: #ebeef5;
  margin: 15px 0;
  position: relative;
}

.section-title {
  display: inline-block;
  position: absolute;
  top: -10px;
  left: 20px;
  background-color: #fff;
  padding: 0 8px;
  font-size: 14px;
  font-weight: 500;
  color: #909399;
}

/* 表单组视觉改进 */
.form-group {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.form-group:hover {
  background-color: #f2f6fc;
}

/* 表单项突出显示 */
.highlight-form-item {
  background-color: #ecf5ff;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 20px;
  border-left: 3px solid #409EFF;
}

.result-dialog .el-dialog__body {
  padding: 20px;
}

.result-dialog .table {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.result-dialog .table-striped tbody tr:nth-of-type(odd) {
  background-color: #f9f9f9;
}

.result-dialog .table th {
  background-color: #f5f7fa;
  font-weight: 500;
  color: #606266;
}

.result-dialog .table td, 
.result-dialog .table th {
  padding: 12px 16px;
  border-color: #ebeef5;
}

.stats-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.stats-card-header {
  background-color: #f5f7fa;
  padding: 12px 16px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
}

.stats-card-body {
  padding: 16px;
}

.stats-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #ebeef5;
}

.stats-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.stats-label {
  color: #606266;
  font-size: 14px;
}

.stats-value {
  font-weight: 500;
  color: #303133;
}

.stats-value.highlight {
  color: #409EFF;
  font-weight: 700;
  font-size: 16px;
}
</style>