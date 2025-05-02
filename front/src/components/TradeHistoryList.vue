<template>
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
              <div v-for="account in subaccounts" :key="account.email" class="mb-2">
                <el-checkbox :label="account.email">
                  {{ account.email }}
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <h5>查询设置</h5>
          <div class="mb-3">
            <label class="form-label">交易对</label>
            <el-select v-model="tradesForm.symbol" class="w-100" filterable placeholder="必须选择交易对">
              <el-option 
                v-for="pair in tradingPairs"
                :key="pair.value"
                :label="pair.label"
                :value="pair.value">
              </el-option>
            </el-select>
          </div>
          <div class="mb-3">
            <label class="form-label">时间范围</label>
            <el-date-picker
              v-model="tradesForm.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="width: 100%"
              value-format="x"
            />
          </div>
          <div class="mb-3">
            <label class="form-label">查询数量限制</label>
            <el-input-number v-model="tradesForm.limit" :min="1" :max="1000" :step="50" style="width: 100%" />
          </div>
          <div class="d-grid">
            <el-button type="primary" :disabled="!isTradesFormValid || isLoading" @click="queryTrades">
              <i class="bi bi-search me-1"></i>查询成交记录
            </el-button>
          </div>
        </div>
      </div>

      <div class="row mt-4">
        <div class="col-12">
          <div v-if="isLoading" class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">加载中...</span>
            </div>
            <div class="mt-2">正在查询历史成交，请稍候...</div>
          </div>
          <div v-else>
            <!-- 成交统计信息 -->
            <div class="mb-3" v-if="flattenedTrades.length > 0">
              <h5>成交统计</h5>
              <div class="summary-stats">
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-card shadow="hover">
                      <div class="stats-item">
                        <div class="stats-title">总成交数量</div>
                        <div class="stats-value">{{ tradesStats.totalTrades }}</div>
                      </div>
                    </el-card>
                  </el-col>
                  <el-col :span="8">
                    <el-card shadow="hover">
                      <div class="stats-item">
                        <div class="stats-title">总手续费</div>
                        <div class="stats-value">{{ tradesStats.totalFee }}</div>
                      </div>
                    </el-card>
                  </el-col>
                  <el-col :span="8">
                    <el-card shadow="hover">
                      <div class="stats-item">
                        <div class="stats-title">总实现盈亏</div>
                        <div class="stats-value" :class="{'text-success': tradesStats.realizedPnl > 0, 'text-danger': tradesStats.realizedPnl < 0}">
                          {{ tradesStats.realizedPnl }}
                        </div>
                      </div>
                    </el-card>
                  </el-col>
                </el-row>
              </div>
            </div>

            <!-- 成交明细表格 -->
            <h5>成交明细</h5>
            <div class="table-responsive">
              <el-table
                v-if="flattenedTrades.length > 0"
                :data="flattenedTrades"
                stripe
                border
                style="width: 100%"
                max-height="500"
              >
                <el-table-column prop="email" label="子账号" width="180" show-overflow-tooltip />
                <el-table-column prop="symbol" label="交易对" width="100" />
                <el-table-column prop="price" label="成交价格" width="100" />
                <el-table-column prop="qty" label="成交数量" width="100" />
                <el-table-column prop="quoteQty" label="成交额" width="120" />
                <el-table-column prop="time" label="成交时间" width="160">
                  <template #default="scope">
                    {{ new Date(parseInt(scope.row.time)).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column prop="commission" label="手续费" width="100" />
                <el-table-column prop="commissionAsset" label="手续费资产" width="100" />
                <el-table-column prop="side" label="方向" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.side === '买入' ? 'success' : 'danger'" size="small">
                      {{ scope.row.side }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="maker" label="Maker/Taker" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.maker ? 'info' : 'warning'" size="small">
                      {{ scope.row.maker ? 'Maker' : 'Taker' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="realizedPnl" label="已实现盈亏" width="120">
                  <template #default="scope">
                    <span :class="{'text-success': parseFloat(scope.row.realizedPnl) > 0, 'text-danger': parseFloat(scope.row.realizedPnl) < 0}">
                      {{ scope.row.realizedPnl }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="text-center py-4 text-muted">
                <i class="bi bi-info-circle me-1"></i>暂无成交记录，请选择子账号和交易对并点击查询
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getCurrentUser } from '../services/auth'

export default {
  name: 'TradeHistoryList',
  props: {
    subaccounts: {
      type: Array,
      required: true
    }
  },
  setup(props) {
    // 交易对列表
    const tradingPairs = ref([])
    const isLoadingTradingPairs = ref(false)
    
    // 状态变量
    const selectedAccounts = ref([])
    const selectAllAccounts = ref(false)
    const isLoading = ref(false)
    const tradesData = ref([])
    
    // 查询表单
    const tradesForm = reactive({
      symbol: '',
      dateRange: null,
      limit: 500
    })
    
    // 计算属性：验证表单
    const isTradesFormValid = computed(() => {
      return selectedAccounts.value.length > 0 && tradesForm.symbol
    })
    
    // 计算属性：统计数据
    const tradesStats = computed(() => {
      if (!tradesData.value.length) {
        return {
          totalTrades: 0,
          totalFee: '0.000000',
          realizedPnl: '0.000000'
        }
      }
      
      let totalTrades = 0
      let totalFee = 0
      let totalPnl = 0
      
      tradesData.value.forEach(result => {
        if (result.success && result.trades && result.trades.length) {
          totalTrades += result.trades.length
          
          // 计算手续费总额
          result.trades.forEach(trade => {
            // 累加手续费和已实现盈亏
            totalFee += parseFloat(trade.commission || 0)
            totalPnl += parseFloat(trade.realizedPnl || 0)
          })
        }
      })
      
      return {
        totalTrades: totalTrades,
        totalFee: totalFee.toFixed(6),
        realizedPnl: totalPnl.toFixed(6)
      }
    })
    
    // 计算属性：扁平化的成交记录
    const flattenedTrades = computed(() => {
      const trades = []
      tradesData.value.forEach(result => {
        if (result.success && result.trades && result.trades.length) {
          result.trades.forEach(trade => {
            trades.push({
              ...trade,
              email: result.email
            })
          })
        }
      })
      // 按时间倒序排序
      return trades.sort((a, b) => parseInt(b.time) - parseInt(a.time))
    })
    
    // 全选/取消全选
    const handleSelectAllChange = (val) => {
      if (val) {
        selectedAccounts.value = props.subaccounts.map(account => account.email)
      } else {
        selectedAccounts.value = []
      }
    }
    
    // 查询交易记录
    const queryTrades = async () => {
      if (!isTradesFormValid.value) {
        ElMessage.warning('请选择子账号和交易对')
        return
      }
      
      try {
        isLoading.value = true
        tradesData.value = []
        
        const user = getCurrentUser()
        const token = user?.token
        
        // 构建请求参数
        const requestData = {
          emails: selectedAccounts.value,
          symbol: tradesForm.symbol,
          limit: tradesForm.limit
        }
        
        // 添加可选时间范围
        if (tradesForm.dateRange && tradesForm.dateRange.length === 2) {
          requestData.startTime = tradesForm.dateRange[0]
          requestData.endTime = tradesForm.dateRange[1]
        }
        
        // 调用API
        const response = await axios.post('/api/subaccounts/futures-trades', requestData, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data && response.data.success) {
          tradesData.value = response.data.data || []
          
          if (flattenedTrades.value.length === 0) {
            ElMessage.info('未找到符合条件的成交记录')
          } else {
            ElMessage.success(`成功获取${flattenedTrades.value.length}条成交记录`)
          }
        } else {
          ElMessage.error(response.data?.error || '查询成交记录失败')
        }
      } catch (error) {
        console.error('查询成交记录时出错:', error)
        ElMessage.error('查询成交记录失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isLoading.value = false
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
    
    // 监听子账号变化，重置选中
    watch(() => props.subaccounts, (newVal) => {
      if (selectAllAccounts.value) {
        selectedAccounts.value = newVal.map(account => account.email)
      }
    }, { deep: true })
    
    // 初始化
    onMounted(() => {
      loadTradingPairs()
    })
    
    return {
      tradingPairs,
      isLoadingTradingPairs,
      selectedAccounts,
      selectAllAccounts,
      handleSelectAllChange,
      isLoading,
      tradesForm,
      isTradesFormValid,
      queryTrades,
      tradesData,
      flattenedTrades,
      tradesStats
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

.stats-item {
  text-align: center;
}

.stats-title {
  color: #606266;
  font-size: 14px;
}

.stats-value {
  font-size: 22px;
  font-weight: bold;
  margin-top: 8px;
}

.text-success {
  color: #67C23A;
}

.text-danger {
  color: #F56C6C;
}

.summary-stats {
  margin-bottom: 20px;
}
</style> 