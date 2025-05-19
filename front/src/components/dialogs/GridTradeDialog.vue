<template>
  <div>
    <!-- 主对话框 -->
    <div v-if="dialogVisible" class="dialog-overlay" @click="closeDialog">
      <div class="dialog-content" @click.stop>
        <div class="grid-trade-container">
          <header class="dialog-header">
            <h2>网格交易建仓</h2>
            <button class="close-button" @click="dialogVisible = false">×</button>
          </header>
          
          <!-- 交易表单 -->
          <div class="trade-form">
            <div class="form-group">
              <!-- 子账户选择 -->
              <div class="form-item">
                <label>交易子账户</label>
                <div class="form-input">
                  <div v-if="isBatchMode">
                    <div class="notice-bar">
                      批量交易模式：已选择 {{ selectedAccounts.length }} 个子账户进行批量网格建仓
                    </div>
                    <div class="selected-accounts-list" v-if="selectedAccounts.length > 0">
                      <span v-for="(acc, index) in selectedAccounts" :key="index" class="tag account-tag">
                        {{ acc.email }}
                      </span>
                    </div>
                  </div>
                  <div v-else class="select-container">
                    <input 
                      class="form-select"
                      type="text"
                      v-model="gridForm.email"
                      readonly
                      placeholder="选择子账户"
                      @click="showSubaccountSelect = true"
                    />
                  </div>
                </div>
              </div>

              <!-- 交易对选择 -->
              <div class="form-item">
                <label>交易对</label>
                <div class="form-input">
                  <select v-model="gridForm.symbol" class="form-select" :disabled="loadingSymbols">
                    <option v-if="loadingSymbols" value="">加载交易对中...</option>
                    <option v-for="pair in availablePairs" :key="pair.value" :value="pair.value">
                      {{ pair.text }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- 合约类型选择 -->
              <div class="form-item">
                <label>合约类型</label>
                <div class="form-input">
                  <div class="radio-group">
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="gridForm.contractType" 
                        value="usdt_futures"
                        checked
                      >
                      U本位合约
                    </label>
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="gridForm.contractType" 
                        value="coin_futures"
                      >
                      币本位合约
                    </label>
                  </div>
                </div>
              </div>
              
              <!-- 单笔数量设置 -->
              <div class="form-item">
                <label>单笔本币数量</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <input
                      type="number"
                      v-model.number="gridForm.singleAmount"
                      class="number-input"
                      placeholder="输入单笔本币数量"
                      :min="0.001"
                      :step="0.001"
                    />
                    <span class="input-suffix">{{ getUnitText() }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 订单数量设置 -->
              <div class="form-item">
                <label>订单数量</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <input
                      type="number"
                      v-model.number="gridForm.ordersCount"
                      class="number-input"
                      placeholder="输入订单数量"
                      :min="1"
                      :step="1"
                    />
                    <span class="input-suffix">单</span>
                  </div>
                </div>
                <div class="helper-text">
                  建议订单数不超过20笔。
                </div>
              </div>
              
              <!-- 总金额显示 - 移除v-if条件 -->
              <div class="form-item">
                <label>总金额</label>
                <div class="total-amount-display">
                  <span>{{ totalAmountDisplay }}</span>
                  <span class="input-suffix">{{ getUnitText() }}</span>
                </div>
                <div class="usdt-value" v-if="usdtValueDisplay">
                  ≈ {{ usdtValueDisplay }} USDT
                </div>
              </div>
              
              <!-- 网格统计信息 -->
              <div class="form-item grid-info" v-if="isFormValid">
                <label>网格统计</label>
                <div class="grid-info-card">
                  <div class="grid-info-item">
                    <span class="label">总订单数：</span>
                    <span class="value">{{ totalOrders }}</span>
                  </div>
                  <div class="grid-info-item">
                    <span class="label">每笔间隔：</span>
                    <span class="value">5秒</span>
                  </div>
                  <div class="grid-info-item">
                    <span class="label">预计用时：</span>
                    <span class="value">{{ estimatedTime }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 提交按钮区域 -->
          <div class="action-buttons">
            <button 
              class="submit-button" 
              @click="executeGridTrade" 
              :disabled="!isFormValid || isSubmitting" 
            >
              <span v-if="isSubmitting" class="loading-spinner"></span>
              {{ isBatchMode ? '批量执行网格建仓' : '执行网格建仓' }}
            </button>
            
            <div class="button-group">
              <button class="secondary-button" @click="resetForm">重置</button>
              <button class="secondary-button" @click="dialogVisible = false">关闭</button>
            </div>
          </div>

          <!-- 结果展示区域 -->
          <div class="result-section" v-if="tradeResults.length > 0">
            <h3 class="results-title">建仓结果</h3>
            <div class="results-list">
              <div class="result-item" v-for="(result, index) in tradeResults" :key="index">
                <div class="result-header">
                  <span>{{ result.email }}</span>
                  <span class="tag" :class="result.success ? 'success-tag' : 'error-tag'">
                    {{ result.success ? '成功' : '失败' }}
                  </span>
                </div>
                <div class="result-body">
                  <div>{{ result.message }}</div>
                </div>
              </div>
            </div>
            
            <!-- 结果统计 -->
            <div class="result-summary">
              <div class="summary-card">
                <div class="summary-title">建仓统计</div>
                <div class="summary-content">
                  <div>总账户数: {{ tradeResults.length }}</div>
                  <div class="success-count">成功: {{ successCount }}</div>
                  <div class="failed-count">失败: {{ failedCount }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 选择器模态框 -->
    <div v-if="showSubaccountSelect" class="select-modal-overlay" @click="showSubaccountSelect = false">
      <div class="select-modal" @click.stop>
        <div class="select-modal-header">
          <h3>选择子账户</h3>
          <button class="close-button" @click="showSubaccountSelect = false">×</button>
        </div>
        <div class="select-modal-content">
          <div 
            v-for="item in subaccountColumns" 
            :key="item.value" 
            class="select-option"
            @click="selectSubaccount(item)"
          >
            {{ item.text }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import { getCurrentUser } from '../../services/auth.js'

export default {
  name: 'GridTradeDialog',
  props: {
    modelValue: {
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
  emits: ['update:modelValue', 'success'],
  setup(props, { emit }) {
    const dialogVisible = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    // 判断是否是批量模式
    const isBatchMode = computed(() => {
      if (props.account) {
        return false // 如果提供了特定账户，使用单个账户模式
      }
      return props.selectedAccounts && props.selectedAccounts.length > 0
    })

    // 响应式状态
    const subaccounts = ref([])
    const showSubaccountSelect = ref(false)
    const isSubmitting = ref(false)
    const tradeResults = ref([])
    const availablePairs = ref([])
    const loadingSymbols = ref(false)
    const loadingPrice = ref(false)
    
    // 网格交易表单
    const gridForm = ref({
      email: '',
      symbol: '',
      contractType: 'usdt_futures', // 默认U本位合约
      singleAmount: null, // 单笔本币数量
      ordersCount: 10, // 默认订单数量
      leverage: 1 // 默认x1杠杆
    })

    // 计算总金额
    const totalAmountDisplay = computed(() => {
      if (!gridForm.value.singleAmount || !gridForm.value.ordersCount) return 0
      
      const single = parseFloat(gridForm.value.singleAmount)
      const count = parseInt(gridForm.value.ordersCount)
      
      if (isNaN(single) || isNaN(count) || single <= 0 || count <= 0) return 0
      
      return (single * count).toFixed(4)
    })
    
    // 存储实时价格 - 仅用于UI显示，不再用于订单
    const realtimePrice = ref(null)
    
    // 获取实时价格 - 仅用于UI显示，不再用于订单
    const getRealtimePrice = async (symbol) => {
      if (!symbol) return
      
      loadingPrice.value = true
      try {
        const user = await getCurrentUser()
        if (!user) {
          console.error('获取用户信息失败')
          return
        }
        
        const response = await axios.get('/api/market/binance/ticker-price', {
          params: { symbol },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (response.data.success && response.data.data) {
          realtimePrice.value = parseFloat(response.data.data.price)
          // 保存价格作为UI参考，不再用于实际下单
          gridForm.value.price = realtimePrice.value
        } else {
          console.warn('获取实时价格失败:', response.data.message)
        }
      } catch (error) {
        console.error('获取实时价格出错:', error)
      } finally {
        loadingPrice.value = false
      }
    }
    
    // 计算USDT价值
    const usdtValueDisplay = computed(() => {
      if (!totalAmountDisplay.value || !gridForm.value.price) return null;
      
      const totalAmount = parseFloat(totalAmountDisplay.value);
      const price = parseFloat(gridForm.value.price);
      
      if (isNaN(totalAmount) || isNaN(price) || price <= 0) return null;
      
      // 只用于UI显示参考，实际下单价格由后端获取
      if (gridForm.value.contractType === 'usdt_futures') {
        // 对于U本位合约，总额是本币数量，需要乘以价格
        return (totalAmount * price).toFixed(2);
      } else {
        // 对于币本位合约，单位是合约张数，也需要乘以价格
        return (totalAmount * price).toFixed(2);
      }
    })
    
    // 总订单数直接使用输入的订单数量
    const totalOrders = computed(() => {
      return gridForm.value.ordersCount || 0
    })
    
    // 估计执行时间
    const estimatedTime = computed(() => {
      const orders = totalOrders.value
      if (orders <= 0) return '0秒'
      
      // 每笔订单间隔5秒
      const totalSeconds = orders * 5
      
      if (totalSeconds < 60) {
        return `${totalSeconds}秒`
      } else if (totalSeconds < 3600) {
        const minutes = Math.floor(totalSeconds / 60)
        const seconds = totalSeconds % 60
        return `${minutes}分${seconds}秒`
      } else {
        const hours = Math.floor(totalSeconds / 3600)
        const minutes = Math.floor((totalSeconds % 3600) / 60)
        return `${hours}小时${minutes}分`
      }
    })
    
    // 表单验证
    const isFormValid = computed(() => {
      if (!isBatchMode.value && !gridForm.value.email) return false
      if (isBatchMode.value && (!props.selectedAccounts || props.selectedAccounts.length === 0)) return false
      if (!gridForm.value.symbol) return false
      if (!gridForm.value.singleAmount || gridForm.value.singleAmount <= 0) return false
      if (!gridForm.value.ordersCount || gridForm.value.ordersCount < 1) return false
      return true
    })
    
    // 成功统计
    const successCount = computed(() => tradeResults.value.filter(r => r.success).length)
    
    // 失败统计
    const failedCount = computed(() => tradeResults.value.filter(r => !r.success).length)
    
    // Picker数据源
    const subaccountColumns = computed(() => {
      return subaccounts.value.map(item => ({
        text: item.email,
        value: item.email
      }))
    })
    
    // 选择处理函数
    const selectSubaccount = (item) => {
      gridForm.value.email = item.value
      showSubaccountSelect.value = false
    }
    
    // 获取单位文本
    const getUnitText = () => {
      if (gridForm.value.contractType === 'coin_futures') {
        // 币本位合约使用张为单位
        return '张'
      } else {
        // U本位合约使用本币为单位
        if (gridForm.value.symbol) {
          // 从交易对中提取本币名称（例如：BTCUSDT -> BTC）
          return gridForm.value.symbol.replace(/USDT$/, '')
        }
        return '本币'
      }
    }
    
    // 处理对话框关闭
    const closeDialog = (e) => {
      // 只有点击遮罩层才关闭
      if (e.target.classList.contains('dialog-overlay')) {
        dialogVisible.value = false
      }
    }
    
    // 加载子账户列表
    const loadSubaccounts = async () => {
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          return
        }

        const response = await axios.get('/api/subaccounts', {
          params: {
            user_id: user.id
          },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })

        if (response.data.success) {
          subaccounts.value = response.data.data
          
          // 如果提供了特定账户，设置表单中的email
          if (props.account) {
            gridForm.value.email = props.account.email
          }
        } else {
          showToast(response.data.message || '获取子账户列表失败', 'error')
        }
      } catch (error) {
        console.error('加载子账户出错:', error)
        showToast('加载子账户失败', 'error')
      }
    }
    
    // 加载交易对
    const loadTradingPairs = async () => {
      loadingSymbols.value = true
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          loadingSymbols.value = false
          return
        }

        // 确定市场类型
        const marketType = gridForm.value.contractType === 'coin_futures' ? 'coin_futures' : 'futures'
        
        // 首先尝试获取收藏的交易对
        let response = await axios.get('/api/trading-pairs/with-price', {
          params: {
            market_type: marketType,
            favorite: true
          },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        let pairsData = response.data.data || []
        let pairs = []
        
        // 如果没有收藏的交易对，则获取所有交易对
        if (!response.data.success || !Array.isArray(pairsData) || pairsData.length === 0) {
          console.warn(`未找到${marketType}市场类型的收藏交易对，将获取所有交易对`)
          
          response = await axios.get('/api/trading-pairs/with-price', {
            params: {
              market_type: marketType
            },
            headers: {
              Authorization: `Bearer ${user.token}`
            }
          })
          
          pairsData = response.data.data || []
        }
        
        // 处理交易对数据并提取选项
        if (Array.isArray(pairsData)) {
          // 直接是数组形式
          pairsData.forEach(pair => {
            if (pair.symbol) {
              pairs.push({
                value: pair.symbol,
                text: pair.symbol,
                price: pair.price_info ? pair.price_info.price : null
              })
            }
          })
        } else if (typeof pairsData === 'object') {
          // 对象形式，需要遍历各个市场
          Object.values(pairsData).forEach(marketPairs => {
            if (Array.isArray(marketPairs)) {
              marketPairs.forEach(pair => {
                if (pair.symbol) {
                  pairs.push({
                    value: pair.symbol,
                    text: pair.symbol,
                    price: pair.price_info ? pair.price_info.price : null
                  })
                }
              })
            }
          })
        }
        
        // 按名称排序
        pairs.sort((a, b) => a.text.localeCompare(b.text))
        
        availablePairs.value = pairs
          
        // 如果有有效的交易对，自动选择第一个
        if (availablePairs.value.length > 0 && !gridForm.value.symbol) {
          gridForm.value.symbol = availablePairs.value[0].value
          if (availablePairs.value[0].price) {
            gridForm.value.price = parseFloat(availablePairs.value[0].price)
          }
          // 获取实时价格
          getRealtimePrice(availablePairs.value[0].value)
        }
      } catch (error) {
        console.error('加载交易对出错:', error)
        showToast('加载交易对失败', 'error')
      } finally {
        loadingSymbols.value = false
      }
    }
    
    // 自定义通知函数
    const showToast = (message, type = 'info') => {
      console.log(`[${type.toUpperCase()}]: ${message}`)
      alert(message)
    }
    
    // 执行网格交易
    const executeGridTrade = async () => {
      if (!isFormValid.value) {
        showToast('请完善表单信息', 'warning')
        return
      }
      isSubmitting.value = true
      tradeResults.value = []
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }
        
        // 确认操作（只显示一次，不再获取具体标记价）
        const confirmMsg = `确定要执行网格建仓吗？\n交易对: ${gridForm.value.symbol}\n价格: 当前市价\n单笔数量: ${gridForm.value.singleAmount} ${getUnitText()}\n订单数量: ${gridForm.value.ordersCount}\n总金额: ${totalAmountDisplay.value} ${getUnitText()}`
        if (!confirm(confirmMsg)) {
          isSubmitting.value = false
          return
        }
        
        // 在发送请求前，立即触发事件，通知挂单列表开始自动刷新
        window.dispatchEvent(new CustomEvent('grid-trade-started', {
          detail: {
            timestamp: Date.now(),
            symbol: gridForm.value.symbol,
            ordersCount: gridForm.value.ordersCount
          }
        }))
        console.log('已触发grid-trade-started事件，交易对:', gridForm.value.symbol, '订单数量:', gridForm.value.ordersCount)

        // 同时直接使用document级别的事件分发，增加事件传播途径
        document.dispatchEvent(new CustomEvent('grid-trade-started', {
          detail: {
            timestamp: Date.now(),
            symbol: gridForm.value.symbol,
            ordersCount: gridForm.value.ordersCount
          },
          bubbles: true,
          cancelable: true
        }))
        
        // 批量模式或单账户模式处理
        let results = []
        const getOrderParams = async () => {
          // 组装参数，不再需要获取标记价
          const baseOrderParams = {
            symbol: gridForm.value.symbol,
            type: 'MARKET', // 使用市价单，后端将自动获取最新标记价
            timeInForce: 'GTC',
            leverage: 1 // 始终x1杠杆
          }
          if (gridForm.value.contractType === 'coin_futures') {
            baseOrderParams.quantity = Math.floor(parseFloat(gridForm.value.singleAmount)).toString()
          } else {
            baseOrderParams.quantity = parseFloat(gridForm.value.singleAmount).toString()
          }
          return baseOrderParams
        }
        if (isBatchMode.value) {
          const accounts = props.selectedAccounts || []
          const accountResults = accounts.map(account => {
            return {
              email: account.email,
              success: false,
              multipleOrders: [],
              successCount: 0,
              failedCount: 0,
              lastError: null,
              completed: false
            }
          })
          
          // 处理单个订单的发送 - 确保每个请求都等待完成
          const processOrder = async (account, index, accountResultIndex) => {
                try {
                  let apiEndpoint = '/api/portfolio/um/new-order'
                  if (gridForm.value.contractType === 'coin_futures') {
                    apiEndpoint = '/api/portfolio/cm/new-order'
                  }
              
              // 获取最新标记价
                  const orderParams = await getOrderParams()
                  const bothSidesRequest = {
                    email: account.email,
                    orders: [
                  { ...orderParams, side: 'BUY', positionSide: 'LONG' },
                  { ...orderParams, side: 'SELL', positionSide: 'SHORT' }
                    ]
                  }
              
              console.log(`发送第 ${index+1}/${gridForm.value.ordersCount} 单给账户 ${account.email}`)
              
              try {
                // 发送请求并等待响应完成
                  const response = await axios.post(apiEndpoint, bothSidesRequest, {
                    headers: {
                      Authorization: `Bearer ${user.token}`,
                      'Content-Type': 'application/json'
                  },
                  timeout: 30000 // 30秒超时
                });
                
                  if (response.data.success) {
                  accountResults[accountResultIndex].successCount += 2
                  accountResults[accountResultIndex].multipleOrders.push({ 
                    side: 'BUY', 
                    orderId: response.data?.data?.buyOrder?.orderId || 'unknown', 
                    status: 'SUCCESS' 
                  })
                  accountResults[accountResultIndex].multipleOrders.push({ 
                    side: 'SELL', 
                    orderId: response.data?.data?.sellOrder?.orderId || 'unknown', 
                    status: 'SUCCESS' 
                  })
                  } else {
                  accountResults[accountResultIndex].failedCount += 2
                  accountResults[accountResultIndex].lastError = response.data.error || '创建订单失败'
                  accountResults[accountResultIndex].multipleOrders.push({ 
                    side: 'BUY', 
                    status: 'FAILED', 
                    error: accountResults[accountResultIndex].lastError 
                  })
                  accountResults[accountResultIndex].multipleOrders.push({ 
                    side: 'SELL', 
                    status: 'FAILED', 
                    error: accountResults[accountResultIndex].lastError 
                  })
                  }
                
                return true; // 表示处理成功
              } catch (error) {
                console.error('创建订单出错:', error)
                accountResults[accountResultIndex].failedCount += 2
                accountResults[accountResultIndex].lastError = error.response?.data?.error || error.message || '请求失败'
                accountResults[accountResultIndex].multipleOrders.push({ 
                  side: 'BUY', 
                  status: 'FAILED', 
                  error: accountResults[accountResultIndex].lastError 
                })
                accountResults[accountResultIndex].multipleOrders.push({ 
                  side: 'SELL', 
                  status: 'FAILED', 
                  error: accountResults[accountResultIndex].lastError 
                })
                
                return false; // 表示处理失败
              }
            } catch (error) {
              console.error(`处理账户 ${account.email} 的订单时出错:`, error)
              return false;
            }
          }
          
          // 使用异步函数处理所有订单，替换原来的setInterval方式
          const executeAllOrders = async () => {
            // 创建精确定时器
            const timer = new PreciseTimer().setInterval(5000); // 5秒间隔
            
            // 创建每批订单的任务
            for (let orderIndex = 0; orderIndex < gridForm.value.ordersCount; orderIndex++) {
              // 包装为异步任务函数
              const batchTask = async () => {
                console.log(`开始执行第 ${orderIndex + 1} 批订单...`);
                
                // 为每个账户并行发送当前批次的订单
                const batchPromises = accounts.map((account, accountIndex) => 
                  processOrder(account, orderIndex, accountIndex)
                );
                
                // 等待所有账户的当前批次完成
                await Promise.all(batchPromises);
                
                console.log(`第 ${orderIndex + 1} 批完成`);
              };
              
              // 添加到定时器队列
              timer.addTask(batchTask);
            }
            
            // 添加结果处理任务
            timer.addTask(async () => {
              // 所有批次完成，处理最终结果
              console.log('所有网格订单已处理完成');
              
              // 准备最终结果
              results = accountResults.map(result => {
              return {
                  email: result.email,
                  success: result.successCount > 0,
                  message: result.successCount > 0 
                    ? `成功创建${result.successCount}个订单` 
                    : (result.lastError || '创建订单失败'),
                  details: result.multipleOrders,
                  successCount: result.successCount,
                  failedCount: result.failedCount
                }
              });
              
              // 更新UI
              tradeResults.value = results;
              const totalSuccessCount = results.filter(r => r.success).length;
              
              if (totalSuccessCount > 0) {
                showToast(`网格建仓完成，成功创建了${totalSuccessCount}个账户的网格订单`, 'success');
                emit('success', { success: true, results });
                
                // 发出事件，通知挂单列表自动刷新
                window.dispatchEvent(new CustomEvent('grid-trade-completed', {
                  detail: {
                    success: true,
                    timestamp: Date.now(),
                    ordersCount: totalSuccessCount
                  }
                }));
                
                console.log('已触发grid-trade-completed事件，成功创建账户数:', totalSuccessCount);
                
                // 同时使用document级别的事件分发，增加事件传播途径
                document.dispatchEvent(new CustomEvent('grid-trade-completed', {
                  detail: {
                    success: true,
                    timestamp: Date.now(),
                    ordersCount: totalSuccessCount
                  },
                  bubbles: true,
                  cancelable: true
                }));
        } else {
                showToast('网格建仓失败，未能成功创建任何订单', 'error');
              }
              
              isSubmitting.value = false;
            });
            
            // 启动定时器执行队列
            await timer.start();
          };
          
          // 启动执行
          executeAllOrders();
        } else {
          // 单账户模式
          const accountResult = {
            email: gridForm.value.email,
            success: false,
            multipleOrders: [],
            successCount: 0,
            failedCount: 0,
            lastError: null
          }
          
          // 处理单个订单的发送
          const processOrder = async (index) => {
              try {
                let apiEndpoint = '/api/portfolio/um/new-order'
                if (gridForm.value.contractType === 'coin_futures') {
                  apiEndpoint = '/api/portfolio/cm/new-order'
                }
                const orderParams = await getOrderParams()
                const bothSidesRequest = {
                  email: gridForm.value.email,
                  orders: [
                  { ...orderParams, side: 'BUY', positionSide: 'LONG' },
                  { ...orderParams, side: 'SELL', positionSide: 'SHORT' }
                  ]
                }
              
              console.log(`发送第 ${index+1}/${gridForm.value.ordersCount} 单给账户 ${gridForm.value.email}`)
              
              // 发送请求并等待响应
              try {
                const response = await axios.post(apiEndpoint, bothSidesRequest, {
                  headers: {
                    Authorization: `Bearer ${user.token}`,
                    'Content-Type': 'application/json'
                  },
                  timeout: 30000 // 30秒超时
                });
                
                if (response.data.success) {
                  accountResult.successCount += 2
                  accountResult.multipleOrders.push({ 
                    side: 'BUY', 
                    orderId: response.data?.data?.buyOrder?.orderId || 'unknown', 
                    status: 'SUCCESS' 
                  })
                  accountResult.multipleOrders.push({ 
                    side: 'SELL', 
                    orderId: response.data?.data?.sellOrder?.orderId || 'unknown', 
                    status: 'SUCCESS' 
                  })
                } else {
                  accountResult.failedCount += 2
                  accountResult.lastError = response.data.error || '创建订单失败'
                  accountResult.multipleOrders.push({ 
                    side: 'BUY', 
                    status: 'FAILED', 
                    error: accountResult.lastError 
                  })
                  accountResult.multipleOrders.push({ 
                    side: 'SELL', 
                    status: 'FAILED', 
                    error: accountResult.lastError 
                  })
                }
                
                // 返回响应，表示成功处理
                return response;
              } catch (error) {
                console.error('创建订单出错:', error)
                accountResult.failedCount += 2
                accountResult.lastError = error.response?.data?.error || error.message || '请求失败'
                accountResult.multipleOrders.push({ 
                  side: 'BUY', 
                  status: 'FAILED', 
                  error: accountResult.lastError 
                })
                accountResult.multipleOrders.push({ 
                  side: 'SELL', 
                  status: 'FAILED', 
                  error: accountResult.lastError 
                })
                
                // 抛出错误以便外部捕获
                throw error;
              }
            } catch (error) {
              console.error('处理订单时出错:', error)
            }
          }
          
          // 使用异步函数处理所有订单
          const executeAllOrders = async () => {
            const orderCount = parseInt(gridForm.value.ordersCount);
            
            // 创建精确定时器
            const timer = new PreciseTimer().setInterval(5000); // 5秒间隔
            
            // 逐个执行订单，放入队列中
            for (let i = 0; i < orderCount; i++) {
              // 包装为异步任务函数
              const orderTask = async () => {
                console.log(`开始执行第 ${i + 1}/${orderCount} 个订单...`);
                
                try {
                  await processOrder(i);
                  console.log(`第 ${i + 1} 个订单完成`);
          } catch (error) {
                  console.error(`执行第 ${i + 1} 个订单出错:`, error);
                  // 继续执行下一个订单，不中断整个流程
                }
              };
              
              // 添加到定时器队列
              timer.addTask(orderTask);
            }
            
            // 添加结果处理任务
            timer.addTask(async () => {
              // 所有订单处理完成，处理最终结果
              console.log('所有网格订单已处理完成');
              
              accountResult.success = accountResult.successCount > 0;
              results = [{
                email: accountResult.email,
                success: accountResult.success,
                message: accountResult.success ? 
                  `成功创建${accountResult.successCount}个订单` : 
                  (accountResult.lastError || '创建订单失败'),
                details: accountResult.multipleOrders,
                successCount: accountResult.successCount,
                failedCount: accountResult.failedCount
              }];
              
              tradeResults.value = results;
              
              if (accountResult.success) {
                showToast(`网格建仓完成，成功创建了${accountResult.successCount}个订单`, 'success');
                emit('success', { success: true, results });
                
                // 发出事件，通知挂单列表自动刷新
                window.dispatchEvent(new CustomEvent('grid-trade-completed', {
                  detail: {
                    success: true,
                    timestamp: Date.now(),
                    ordersCount: accountResult.successCount
                  }
                }));
                
                console.log('已触发单账户grid-trade-completed事件，成功订单数:', accountResult.successCount);
                
                // 同时使用document级别的事件分发，增加事件传播途径
                document.dispatchEvent(new CustomEvent('grid-trade-completed', {
                  detail: {
                    success: true,
                    timestamp: Date.now(),
                    ordersCount: accountResult.successCount
                  },
                  bubbles: true,
                  cancelable: true
                }));
        } else {
                showToast('网格建仓失败，未能成功创建任何订单', 'error');
              }
              
              isSubmitting.value = false;
            });
            
            // 启动定时器执行队列
            await timer.start();
          };
          
          // 启动执行
          executeAllOrders();
        }
      } catch (error) {
        console.error('网格建仓出错:', error)
        showToast('网格建仓请求失败', 'error')
        isSubmitting.value = false
      }
    }
    
    // 重置表单
    const resetForm = () => {
      gridForm.value = {
        email: props.account ? props.account.email : '',
        symbol: '',
        contractType: 'usdt_futures',
        singleAmount: null,
        ordersCount: 10,
        leverage: 1
      }
      tradeResults.value = []
    }
    
    // 精确的定时器类，用于控制订单执行的时间间隔
    class PreciseTimer {
      constructor() {
        this.queue = [];
        this.isRunning = false;
        this.intervalMs = 5000; // 默认5秒间隔
        this.lastExecutionTime = 0;
      }
      
      // 设置间隔时间
      setInterval(ms) {
        this.intervalMs = ms;
        return this;
      }
      
      // 添加任务到队列
      addTask(task) {
        this.queue.push({
          task,
          timestamp: Date.now()
        });
        
        if (!this.isRunning) {
          this.start();
        }
        
        return this;
      }
      
      // 添加多个任务
      addTasks(tasks) {
        tasks.forEach(task => this.addTask(task));
        return this;
      }
      
      // 开始执行队列
      async start() {
        if (this.isRunning || this.queue.length === 0) return;
        
        this.isRunning = true;
        console.log('定时器开始执行队列，队列长度:', this.queue.length);
        
        while (this.queue.length > 0) {
          const now = Date.now();
          const timeSinceLastExecution = now - this.lastExecutionTime;
          
          // 如果距离上次执行不足间隔时间，等待剩余时间
          if (this.lastExecutionTime > 0 && timeSinceLastExecution < this.intervalMs) {
            const waitTime = this.intervalMs - timeSinceLastExecution;
            console.log(`等待精确时间: ${waitTime}ms`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
          }
          
          // 取出队首任务并执行
          const nextTask = this.queue.shift();
          const executionTime = Date.now();
          const waitedTime = executionTime - nextTask.timestamp;
          
          console.log(`执行任务，已等待: ${waitedTime}ms, 目标间隔: ${this.intervalMs}ms`);
          
          try {
            await nextTask.task();
          } catch (error) {
            console.error('执行任务时出错:', error);
          }
          
          // 记录执行时间
          this.lastExecutionTime = Date.now();
        }
        
        this.isRunning = false;
        console.log('队列执行完毕');
      }
      
      // 清空队列
      clear() {
        this.queue = [];
        return this;
      }
    }
    
    // 组件加载时
    onMounted(() => {
      loadSubaccounts()
      loadTradingPairs()
    })
    
    // 监听合约类型变化，重新加载交易对
    watch(() => gridForm.value.contractType, () => {
      loadTradingPairs()
    })
    
    // 监听交易对变化，获取实时价格并自动填入最新价格
    watch(() => gridForm.value.symbol, (newSymbol) => {
      if (newSymbol) {
        // 获取实时价格
        getRealtimePrice(newSymbol)
        
        // 同时也从已加载的交易对中获取价格
        if (availablePairs.value.length > 0) {
          const selectedPair = availablePairs.value.find(p => p.value === newSymbol)
          if (selectedPair && selectedPair.price) {
            // 无论之前是否有价格，都更新为新交易对的价格
            gridForm.value.price = parseFloat(selectedPair.price)
          }
        }
      }
    })

    // 价格提示文本计算属性
    const pricePlaceholder = computed(() => {
      if (loadingPrice.value) {
        return '获取实时价格中...'
      }
      
      if (realtimePrice.value) {
        return `当前市价: ${realtimePrice.value}`
      }
      
      if (gridForm.value.symbol && availablePairs.value.length > 0) {
        const selectedPair = availablePairs.value.find(p => p.value === gridForm.value.symbol)
        if (selectedPair && selectedPair.price) {
          return `推荐价格: ${selectedPair.price}`
        }
      }
      
      return '输入市价'
    })

    return {
      dialogVisible,
      isBatchMode,
      gridForm,
      subaccounts,
      showSubaccountSelect,
      isSubmitting,
      tradeResults,
      availablePairs,
      loadingSymbols,
      loadingPrice,
      subaccountColumns,
      selectSubaccount,
      closeDialog,
      totalOrders,
      totalAmountDisplay,
      usdtValueDisplay,
      estimatedTime,
      isFormValid,
      successCount,
      failedCount,
      getUnitText,
      executeGridTrade,
      resetForm,
      pricePlaceholder
    }
  }
}
</script>

<style scoped>
/* 对话框基础样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.dialog-content {
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow-y: auto;
  color: #333;
}

.grid-trade-container {
  padding: 20px;
}

/* 对话框头部 */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.close-button:hover {
  color: #333;
}

/* 表单样式 */
.trade-form {
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-weight: 500;
  color: #333;
}

.form-input {
  display: flex;
  align-items: center;
}

.select-container {
  width: 100%;
}

.form-select, .number-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-select:focus, .number-input:focus {
  border-color: #409EFF;
  outline: none;
}

.helper-text {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

/* 数字输入容器 */
.number-input-container {
  display: flex;
  align-items: center;
  width: 100%;
}

.input-suffix {
  margin-left: 8px;
  color: #606266;
}

/* 单选按钮组 */
.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

/* 通知栏 */
.notice-bar {
  padding: 8px 12px;
  background-color: #ecf5ff;
  border-radius: 4px;
  margin-bottom: 8px;
  color: #409EFF;
}

/* 标签样式 */
.tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 6px;
  margin-bottom: 6px;
}

.account-tag {
  background-color: #f0f2f5;
  color: #606266;
}

.success-tag {
  background-color: #f0f9eb;
  color: #67c23a;
}

.error-tag {
  background-color: #fef0f0;
  color: #f56c6c;
}

/* 选择的账户列表 */
.selected-accounts-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

/* 网格信息卡片 */
.grid-info-card {
  background-color: #f9f9f9;
  border-radius: 4px;
  padding: 12px;
}

.grid-info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.grid-info-item:last-child {
  margin-bottom: 0;
}

.grid-info-item .label {
  color: #606266;
}

.grid-info-item .value {
  font-weight: 500;
  color: #333;
}

/* 按钮组 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.submit-button {
  padding: 12px;
  background-color: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
}

.submit-button:hover {
  background-color: #66b1ff;
}

.submit-button:disabled {
  background-color: #a0cfff;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  gap: 10px;
}

.secondary-button {
  flex: 1;
  padding: 10px;
  background-color: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #606266;
  cursor: pointer;
}

.secondary-button:hover {
  background-color: #e9ecef;
}

/* 结果展示区域 */
.result-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.results-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 500;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.result-item {
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 12px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #eee;
}

.result-body {
  font-size: 14px;
}

/* 结果统计 */
.result-summary {
  margin-top: 16px;
}

.summary-card {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
}

.summary-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.summary-content {
  display: flex;
  gap: 16px;
}

.success-count {
  color: #67c23a;
}

.failed-count {
  color: #f56c6c;
}

/* 加载动画 */
.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 选择器模态框 */
.select-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
}

.select-modal {
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
}

.select-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.select-modal-header h3 {
  margin: 0;
}

.select-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.select-option {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.select-option:last-child {
  border-bottom: none;
}

.select-option:hover {
  background-color: #f5f7fa;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .dialog-content {
    width: 95%;
  }
  
  .button-group {
    flex-direction: column;
  }
  
  .result-summary {
    flex-direction: column;
    gap: 12px;
  }
}

/* 总金额显示 */
.total-amount-display {
  background-color: #f0f9ff;
  border-radius: 4px;
  padding: 12px;
  font-size: 18px;
  font-weight: 600;
  color: #409EFF;
  text-align: center;
  border: 1px solid #b3e0ff;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.usdt-value {
  margin-top: 6px;
  text-align: center;
  font-size: 14px;
  color: #67c23a;
  font-weight: 500;
}
</style> 