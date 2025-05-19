<template>
  <div>
    <!-- 主对话框 -->
    <div v-if="dialogVisible" class="dialog-overlay" @click="closeDialog">
      <div class="dialog-content" @click.stop>
        <div class="auto-arbitrage-container">
          <header class="dialog-header">
            <h2>自动化套利交易</h2>
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
                      批量交易模式：已选择 {{ selectedAccounts.length }} 个子账户进行批量交易
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
                      v-model="tradeForm.email"
                      readonly
                      placeholder="选择子账户"
                      @click="showSubaccountSelect = true"
                    />
                  </div>
                </div>
              </div>

              <!-- 套利类型选择 -->
              <div class="form-item">
                <label>套利币种</label>
                <div class="form-input">
                  <select v-model="tradeForm.arbitrageType" class="form-select" :disabled="loadingCoins">
                    <option v-if="loadingCoins" value="">加载币种中...</option>
                    <option v-for="coin in availableCoins" :key="coin.value" :value="coin.value">
                      {{ coin.text }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- 设置金额 -->
              <div class="form-item">
                <label>交易金额</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <button @click="decrementAmount" class="number-btn">-</button>
                    <input
                      type="number"
                      v-model.number="tradeForm.amount"
                      class="number-input"
                      placeholder="USDT金额(默认3011.5)"
                      :min="0.1"
                      :step="0.1"
                    />
                    <button @click="incrementAmount" class="number-btn">+</button>
                  </div>
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
                        v-model="tradeForm.futuresType" 
                        value="portfolio_margin_cm"
                        checked
                      >
                      统一账户CM合约
                    </label>
                  </div>
                </div>
              </div>
              
              <!-- 合约数量设置 -->
              <div class="form-item">
                <label>合约张数</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <button @click="decrementCoinFuturesQty" class="number-btn">-</button>
                    <input
                      type="number"
                      v-model.number="tradeForm.coinFuturesQty"
                      class="number-input"
                      placeholder="币本位合约张数"
                      :min="1"
                      :step="1"
                    />
                    <button @click="incrementCoinFuturesQty" class="number-btn">+</button>
                    <span class="input-suffix">张</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 提交按钮区域 -->
          <div class="action-buttons">
            <button 
              class="submit-button" 
              @click="executeTrade" 
              :disabled="isSubmitting" 
              v-if="!isBatchMode"
            >
              <span v-if="isSubmitting" class="loading-spinner"></span>
              执行自动化套利
            </button>
            <button 
              class="submit-button" 
              @click="executeBatchTrade" 
              :disabled="isSubmitting" 
              v-else
            >
              <span v-if="isSubmitting" class="loading-spinner"></span>
              批量执行自动化套利
            </button>
            
            <!-- 调试按钮区域 -->
            <div class="debug-buttons">
              <button 
                class="debug-button spot-button" 
                @click="executeSpotTradeOnly" 
                :disabled="isSubmitting"
              >
                仅统一账户买入(调试)
              </button>
              <button 
                class="debug-button futures-button" 
                @click="executeFuturesTradeOnly" 
                :disabled="isSubmitting"
              >
                仅合约开空(调试)
              </button>
            </div>
            
            <div class="button-group">
              <button class="secondary-button" @click="resetForm">重置</button>
              <button class="secondary-button" @click="dialogVisible = false">关闭</button>
            </div>
          </div>

          <!-- 批量结果展示区域 -->
          <div class="batch-results" v-if="tradeResults.length > 0">
            <h3 class="results-title">交易结果</h3>
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
                  <!-- 显示套利详情 -->
                  <div v-if="result.details && result.details.length > 0" class="trade-details">
                    <div v-for="(detail, detailIndex) in result.details" :key="detailIndex" class="detail-item">
                      <div class="detail-step">{{ detail.step }}</div>
                      <div>订单ID: {{ detail.orderId }}</div>
                      <div>交易对: {{ detail.symbol }}</div>
                      <div>方向: {{ detail.side === 'BUY' ? '买入' : '卖出' }}</div>
                      <div v-if="detail.amount">金额: {{ detail.amount }} USDT</div>
                      <div v-if="detail.quantity">数量: {{ detail.quantity }}</div>
                      <div>手续费: {{ detail.fee }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 结果统计 -->
            <div class="result-summary">
              <div class="summary-card">
                <div class="summary-title">套利统计</div>
                <div class="summary-content">
                  <div>总交易: {{ tradeResults.length }}</div>
                  <div class="success-count">成功: {{ successCount }}</div>
                  <div class="failed-count">失败: {{ failedCount }}</div>
                </div>
              </div>
              <button 
                class="secondary-button" 
                @click="exportResults" 
                :disabled="tradeResults.length === 0"
              >
                导出结果
              </button>
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
import { debounce } from '../../utils/performance.js'

export default {
  name: 'AutoArbitrageDialog',
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
    const availableCoins = ref([])
    const loadingCoins = ref(false)
    
    // 交易对价格和建议交易量信息
    const pairPriceInfo = ref({}) // 存储交易对价格信息
    
    // 交易表单
    const tradeForm = ref({
      email: '',
      arbitrageType: '',
      amount: 3011.5,
      futuresType: 'portfolio_margin_cm',
      coinFuturesQty: 1,
      _coinFuturesQtyTouched: false
    })

    // Picker数据源
    const subaccountColumns = computed(() => {
      return subaccounts.value.map(item => ({
        text: item.email,
        value: item.email
      }))
    })
    
    // 选择处理函数
    const selectSubaccount = (item) => {
      tradeForm.value.email = item.value
      showSubaccountSelect.value = false
    }
    
    // 处理对话框关闭
    const closeDialog = (e) => {
      // 只有点击遮罩层才关闭
      if (e.target.classList.contains('dialog-overlay')) {
        dialogVisible.value = false
      }
    }
    
    // 数字输入框辅助函数 - 金额
    const incrementAmount = () => {
      if (!tradeForm.value.amount) tradeForm.value.amount = 0
      tradeForm.value.amount = +(tradeForm.value.amount + 0.1).toFixed(1)
    }
    
    const decrementAmount = () => {
      if (!tradeForm.value.amount) return
      const newValue = tradeForm.value.amount - 0.1
      if (newValue >= 0.1) {
        tradeForm.value.amount = +newValue.toFixed(1)
      }
    }
    
    // 数字输入框辅助函数 - 币本位合约张数
    const incrementCoinFuturesQty = () => {
      if (!tradeForm.value.coinFuturesQty) {
        // 如果未设置，使用默认值
        const defaultValue = tradeForm.value.arbitrageType === 'ETH' ? 30 : 3
        tradeForm.value.coinFuturesQty = defaultValue
      }
      tradeForm.value.coinFuturesQty += 1
    }
    
    const decrementCoinFuturesQty = () => {
      if (!tradeForm.value.coinFuturesQty) {
        // 如果未设置，使用默认值
        const defaultValue = tradeForm.value.arbitrageType === 'ETH' ? 30 : 3
        tradeForm.value.coinFuturesQty = defaultValue
      }
      
      if (tradeForm.value.coinFuturesQty > 1) {
        tradeForm.value.coinFuturesQty -= 1
      }
    }
    
    // 结果统计
    const successCount = computed(() => tradeResults.value.filter(r => r.success).length)
    const failedCount = computed(() => tradeResults.value.filter(r => !r.success).length)
    
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
            tradeForm.value.email = props.account.email
          }
        } else {
          showToast(response.data.message || '获取子账户列表失败', 'error')
        }
      } catch (error) {
        console.error('加载子账户出错:', error)
        showToast('加载子账户失败', 'error')
      }
    }

    // 加载可用币种
    const loadAvailableCoins = async () => {
      loadingCoins.value = true
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          loadingCoins.value = false
          return
        }

        // 1. 首先获取现货市场的交易对
        const spotResponse = await axios.get('/api/trading-pairs/with-price', {
          params: {
            market_type: 'spot',  // 使用现货市场获取所有支持的币种
            favorite: true        // 只获取收藏的币种
          },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (!spotResponse.data.success) {
          showToast(spotResponse.data.error || '获取现货交易对失败', 'error')
          loadingCoins.value = false
          return
        }
        
        // 验证现货数据
        const spotData = spotResponse.data.data || {};
        let spotPairs = [];
        
        // 处理不同的数据格式
        if (Array.isArray(spotData)) {
          // 如果直接返回了数组
          spotPairs = spotData;
        } else if (typeof spotData === 'object') {
          // 如果返回了对象（按市场类型分组）
          for (const marketType in spotData) {
            const marketPairs = spotData[marketType];
            if (Array.isArray(marketPairs)) {
              spotPairs = spotPairs.concat(marketPairs);
            }
          }
        }
        
        // 标准化现货交易对数据
        const normalizedSpotPairs = spotPairs.filter(pair => {
          return pair && typeof pair === 'object' && pair.symbol;
        }).map(pair => {
          return {
            ...pair,
            base_asset: pair.baseAsset || pair.base_asset || '',
            quote_asset: pair.quoteAsset || pair.quote_asset || '',
            symbol: pair.symbol
          };
        });
        
        // 2. 然后获取合约市场的交易对
        const futuresResponse = await axios.get('/api/trading-pairs/with-price', {
          params: {
            market_type: 'futures',  // U本位合约市场
            user_id: user.id         // 添加用户ID
          },
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (!futuresResponse.data.success) {
          showToast(futuresResponse.data.error || '获取合约交易对失败', 'error')
          loadingCoins.value = false
          return
        }
        
        // 验证合约数据
        const futuresData = futuresResponse.data.data || {};
        let futuresPairs = [];
        
        // 处理不同的数据格式 
        if (Array.isArray(futuresData)) {
          // 如果直接返回了数组
          futuresPairs = futuresData;
        } else if (typeof futuresData === 'object') {
          // 如果返回了对象（按市场类型分组）
          for (const marketType in futuresData) {
            const marketPairs = futuresData[marketType];
            if (Array.isArray(marketPairs)) {
              futuresPairs = futuresPairs.concat(marketPairs);
            }
          }
        }
        
        // 标准化合约交易对数据
        const normalizedFuturesPairs = futuresPairs.filter(pair => {
          return pair && typeof pair === 'object' && pair.symbol;
        }).map(pair => {
          return {
            ...pair,
            base_asset: pair.baseAsset || pair.base_asset || '',
            quote_asset: pair.quoteAsset || pair.quote_asset || '',
            symbol: pair.symbol
          };
        });
        
        // 检查返回的数据是否有效
        if (!normalizedFuturesPairs.length) {
          console.warn('未能获取到有效的合约市场交易对数据')
          showToast('未能获取到合约市场数据，将使用现货市场数据', 'warning')
          
          // 如果无法获取合约数据，仍使用现货数据
          // 直接使用所有现货交易对中的USDT/USDC计价币种
          const uniqueCoins = new Set()
          normalizedSpotPairs.forEach(pair => {
            if ((pair.quote_asset === 'USDT' || pair.quote_asset === 'USDC') && pair.base_asset) {
              uniqueCoins.add(pair.base_asset)
              
              // 同时保存价格信息，用于后续计算
              if (pair.price_info && pair.price_info.price) {
                pairPriceInfo.value[pair.base_asset] = {
                  price: parseFloat(pair.price_info.price),
                  suggested_quantity: pair.suggested_quantity || 1,
                  suggested_amount: pair.suggested_amount || 3000
                }
              }
            }
          })
          
          // 转换为选项格式
          const coinOptions = Array.from(uniqueCoins).map(coin => ({
            value: coin,
            text: `${coin}`
          }))
          
          // 按字母排序
          coinOptions.sort((a, b) => a.value.localeCompare(b.value))
          
          console.log(`仅使用现货市场数据，获取了${coinOptions.length}个交易币种`)
          availableCoins.value = coinOptions
          
          // 如果当前选择的币种不在可用列表中，设置为第一个可用币种
          if (coinOptions.length > 0 && !uniqueCoins.has(tradeForm.value.arbitrageType)) {
            tradeForm.value.arbitrageType = coinOptions[0].value
          }
          
          // 根据价格信息更新数量建议
          updateQuantitySuggestions()
          loadingCoins.value = false
          return
        }
        
        // 从合约市场获取可用的基础资产列表
        const availableFuturesBaseAssets = new Set()
        normalizedFuturesPairs.forEach(pair => {
          if (pair.base_asset) {
            availableFuturesBaseAssets.add(pair.base_asset)
          }
        })
        
        console.log('合约市场可用的基础资产:', Array.from(availableFuturesBaseAssets))
        
        // 从现货交易对中提取币种，但只保留在合约市场也存在的币种
        const filteredSpotPairs = normalizedSpotPairs.filter(pair => {
          return (pair.quote_asset === 'USDT' || pair.quote_asset === 'USDC') && 
                  pair.base_asset && 
                  availableFuturesBaseAssets.has(pair.base_asset);
        })
        
        // 提取所有合格币种的基础资产并保存价格信息
        const uniqueCoins = new Set()
        filteredSpotPairs.forEach(pair => {
          uniqueCoins.add(pair.base_asset)
          
          // 同时保存价格信息，用于后续计算
          if (pair.price_info && pair.price_info.price) {
            pairPriceInfo.value[pair.base_asset] = {
              price: parseFloat(pair.price_info.price),
              suggested_quantity: pair.suggested_quantity || 1,
              suggested_amount: pair.suggested_amount || 3000
            }
          }
        })
        
        // 转换为选项格式
        const coinOptions = Array.from(uniqueCoins).map(coin => ({
          value: coin,
          text: `${coin}`
        }))
        
        // 按字母排序
        coinOptions.sort((a, b) => a.value.localeCompare(b.value))
        
        console.log(`从数据库获取了${coinOptions.length}个同时在现货和合约市场可用的交易币种`)
        availableCoins.value = coinOptions
        
        // 如果当前选择的币种不在可用列表中，设置为第一个可用币种
        if (coinOptions.length > 0 && !availableFuturesBaseAssets.has(tradeForm.value.arbitrageType)) {
          tradeForm.value.arbitrageType = coinOptions[0].value
        }
        
        // 根据价格信息更新数量建议
        updateQuantitySuggestions()
      } catch (error) {
        console.error('加载币种出错:', error)
        showToast('从数据库加载币种失败: ' + (error.response?.data?.error || error.message), 'error')
      } finally {
        loadingCoins.value = false
      }
    }
    
    // 根据价格信息更新交易数量建议
    const updateQuantitySuggestions = () => {
      const coinType = tradeForm.value.arbitrageType
      const coinInfo = pairPriceInfo.value[coinType]
      
      if (coinInfo) {
        console.log(`更新${coinType}交易数量建议，价格: ${coinInfo.price}`)
        tradeForm.value.coinFuturesQty = coinInfo.suggested_quantity
      } else {
        console.log(`未找到${coinType}的价格信息，使用默认值`)
        tradeForm.value.coinFuturesQty = 1
      }
    }
    
    // 自定义通知函数
    const showToast = (message, type = 'info') => {
      console.log(`[${type.toUpperCase()}]: ${message}`)
      alert(message)
    }
    
    // 执行套利交易
    const executeTrade = async () => {
      if (!validateTradeForm()) return
      isSubmitting.value = true
      tradeResults.value = []
      const tradeRecords = []
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }
        const coinType = tradeForm.value.arbitrageType
        const amount = tradeForm.value.amount
        // 只走CM合约
        const spotSymbol = `${coinType}USDT`
        const buyAmount = amount
        const marginBuyData = {
          email: tradeForm.value.email,
          marketType: 'portfolio_margin',
          symbol: spotSymbol,
          side: 'BUY',
          type: 'MARKET',
          quoteOrderQty: buyAmount,
          user_id: user.id
        }
        const marginResponse = await axios.post('/api/market/trade', marginBuyData, {
          headers: { Authorization: `Bearer ${user.token}` }
        })
        if (!marginResponse.data.success) {
          showToast(`统一账户买入失败: ${marginResponse.data.message}`, 'error')
          isSubmitting.value = false
          return
        }
        const marginResult = {
          step: `统一账户买入${coinType}`,
          orderId: marginResponse.data.data.orderId,
          symbol: spotSymbol,
          side: 'BUY',
          amount: buyAmount,
          fee: marginResponse.data.data.fee || '未知'
        }
        tradeRecords.push(marginResult)
        await new Promise(resolve => setTimeout(resolve, 1000))
        const futuresSymbol = `${coinType}USD_PERP`
        const futuresSellData = {
          email: tradeForm.value.email,
          marketType: 'portfolio_margin_cm',
          symbol: futuresSymbol,
          side: 'SELL',
          type: 'MARKET',
          useAsset: coinType,
          quantity: tradeForm.value.coinFuturesQty || 1,
          minNotional: 5,
          leverage: 1
        }
        const futuresResponse = await axios.post('/api/market/trade', futuresSellData, {
          headers: { Authorization: `Bearer ${user.token}` }
        })
        if (!futuresResponse.data.success) {
          showToast(`合约市场开空失败: ${futuresResponse.data.message}`, 'error')
          isSubmitting.value = false
          return
        }
        const futuresResult = {
          step: `统一账户CM合约开空`,
          orderId: futuresResponse.data.data.orderId,
          symbol: futuresSymbol,
          side: 'SELL',
          quantity: `${futuresSellData.quantity}张`,
          fee: futuresResponse.data.data.fee || '未知'
        }
        tradeRecords.push(futuresResult)
        tradeResults.value = [
          {
            email: tradeForm.value.email,
            success: true,
            message: `自动化套利完成 - 先在统一账户买入${coinType}金额: ${buyAmount}USDT，然后用买入的${coinType}在统一账户CM合约开空${futuresSellData.quantity}张`,
            details: tradeRecords
          }
        ]
        showToast('自动化套利交易完成', 'success')
        emit('success', { success: true, results: tradeResults.value })
      } catch (error) {
        console.error('自动化套利出错:', error)
        showToast('自动化套利请求失败', 'error')
        tradeResults.value = [{
          email: tradeForm.value.email,
          success: false,
          message: error.response?.data?.message || '请求处理失败',
          details: tradeRecords
        }]
      } finally {
        isSubmitting.value = false
      }
    }
    
    // 批量执行套利交易
    const executeBatchTrade = async () => {
      if (!validateTradeForm(true)) return
      isSubmitting.value = true
      tradeResults.value = []
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }
        const coinType = tradeForm.value.arbitrageType
        const accounts = props.selectedAccounts
        if (!accounts || accounts.length === 0) {
          showToast('请选择至少一个账户', 'warning')
          isSubmitting.value = false
          return
        }
        const results = await Promise.all(accounts.map(async (account) => {
          const accountEmail = account.email
          const tradeRecords = []
          try {
            const spotSymbol = `${coinType}USDT`
            const buyAmount = tradeForm.value.amount
            const marginBuyData = {
              email: accountEmail,
              marketType: 'portfolio_margin',
              symbol: spotSymbol,
              side: 'BUY',
              type: 'MARKET',
              quoteOrderQty: buyAmount,
              user_id: user.id
            }
            const marginResponse = await axios.post('/api/market/trade', marginBuyData, {
              headers: { Authorization: `Bearer ${user.token}` }
            })
            if (!marginResponse.data.success) {
              return {
                email: accountEmail,
                success: false,
                message: `统一账户买入失败: ${marginResponse.data.message || '未知错误'}`
              }
            }
            const marginResult = {
              step: `统一账户买入${coinType}`,
              orderId: marginResponse.data.data.orderId,
              symbol: spotSymbol,
              side: 'BUY',
              amount: buyAmount,
              fee: marginResponse.data.data.fee || '未知'
            }
            tradeRecords.push(marginResult)
            const futuresSymbol = `${coinType}USD_PERP`
            const futuresSellData = {
              email: accountEmail,
              marketType: 'portfolio_margin_cm',
              symbol: futuresSymbol,
              side: 'SELL',
              type: 'MARKET',
              useAsset: coinType,
              quantity: tradeForm.value.coinFuturesQty || 1,
              minNotional: 5,
              leverage: 1
            }
            const futuresResponse = await axios.post('/api/market/trade', futuresSellData, {
              headers: { Authorization: `Bearer ${user.token}` }
            })
            if (!futuresResponse.data.success) {
              return {
                email: accountEmail,
                success: false,
                message: `合约市场开空失败: ${futuresResponse.data.message || '未知错误'}`,
                details: tradeRecords
              }
            }
            const futuresResult = {
              step: `统一账户CM合约开空`,
              orderId: futuresResponse.data.data.orderId,
              symbol: futuresSymbol,
              side: 'SELL',
              quantity: `${futuresSellData.quantity}张`,
              fee: futuresResponse.data.data.fee || '未知'
            }
            tradeRecords.push(futuresResult)
            return {
              email: accountEmail,
              success: true,
              message: `自动化套利完成 - 先在统一账户买入${coinType}金额: ${buyAmount}USDT，然后用买入的${coinType}在统一账户CM合约开空${futuresSellData.quantity}张`,
              details: tradeRecords
            }
          } catch (error) {
            return {
              email: accountEmail,
              success: false,
              message: error.response?.data?.message || '请求处理失败',
              details: tradeRecords
            }
          }
        }))
        tradeResults.value = results
        showToast('批量自动化套利交易完成', 'success')
        emit('success', { success: true, results })
      } catch (error) {
        console.error('批量自动化套利出错:', error)
        showToast('批量自动化套利请求失败', 'error')
        tradeResults.value = [{
          email: '',
          success: false,
          message: error.response?.data?.message || '请求处理失败',
          details: []
        }]
      } finally {
        isSubmitting.value = false
      }
    }
    
    // 验证套利表单
    const validateTradeForm = (isBatch = false) => {
      // 如果是批量模式或者检测到selectedAccounts有值，则跳过邮箱验证
      if (isBatch || (props.selectedAccounts && props.selectedAccounts.length > 0)) {
        if (!tradeForm.value.amount || tradeForm.value.amount <= 0) {
          showToast('请输入有效的USDT金额', 'warning')
          return false
        }
        return true
      }
      
      // 单账户模式验证
      if (!tradeForm.value.email) {
        showToast('请选择交易子账户', 'warning')
        return false
      }
      
      if (!tradeForm.value.amount || tradeForm.value.amount <= 0) {
        showToast('请输入有效的USDT金额', 'warning')
        return false
      }
      
      return true
    }
    
    // 导出结果
    const exportResults = () => {
      if (tradeResults.value.length === 0) return
      
      const dataStr = JSON.stringify(tradeResults.value, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      
      const a = document.createElement('a')
      a.href = url
      a.download = `arbitrage_results_${new Date().toISOString().replace(/[:.]/g, '-')}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
    
    // 重置表单
    const resetForm = () => {
      const defaultCoin = availableCoins.value && availableCoins.value.length > 0 
        ? availableCoins.value[0].value 
        : '';
      tradeForm.value = {
        email: props.account ? props.account.email : '',
        arbitrageType: defaultCoin,
        amount: 3011.5,
        futuresType: 'portfolio_margin_cm',
        coinFuturesQty: Math.max(1, Math.floor(3011.5 / 100)),
        _coinFuturesQtyTouched: false
      }
      setTimeout(() => {
        updateQuantitySuggestions()
      }, 0)
    }
    
    // 对话框打开处理
    const handleDialogOpen = async () => {
      await loadSubaccounts()
      await loadAvailableCoins()
    }
    
    // 使用防抖优化对话框关闭处理
    const handleDialogClosed = debounce(() => {
      tradeResults.value = []
    }, 100)
    
    // 组件加载时
    onMounted(() => {
      // 首先加载子账户列表
      loadSubaccounts()
      
      // 然后加载可用币种，加载完成后会自动设置第一个币种为默认值
      loadAvailableCoins().then(() => {
        // 币种加载完成后，设置当前选择的币种对应的建议数量
        if (tradeForm.value.arbitrageType) {
          updateQuantitySuggestions()
        } else if (availableCoins.value && availableCoins.value.length > 0) {
          // 如果没有设置默认币种但已有可用币种列表，设置第一个币种为默认
          tradeForm.value.arbitrageType = availableCoins.value[0].value
          updateQuantitySuggestions()
        }
      })
    })
    
    // 对话框打开关闭处理
    watch(() => dialogVisible.value, (newVal) => {
      if (newVal) {
        // 使用防抖处理打开过程
        debounce(handleDialogOpen, 50)()
      } else {
        handleDialogClosed()
      }
    })
    
    // 监听币种变化，更新数量建议
    watch(() => tradeForm.value.arbitrageType, 
    // eslint-disable-next-line no-unused-vars
    (newCoin) => {
      updateQuantitySuggestions()
    })
    
    // 监听合约类型变化，更新数量建议
    watch(() => tradeForm.value.futuresType, 
    // eslint-disable-next-line no-unused-vars
    (newType) => {
      updateQuantitySuggestions()
    })
    
    // 监听交易金额变化，每次都自动补全合约张数
    watch(() => tradeForm.value.amount, (newAmount) => {
      if (typeof newAmount === 'number' && newAmount > 0) {
        tradeForm.value.coinFuturesQty = Math.max(1, Math.floor(newAmount / 100))
      }
    })
    
    // 仅执行统一账户现货买入
    const executeSpotTradeOnly = async () => {
      if (!validateTradeForm()) return
      
      isSubmitting.value = true
      tradeResults.value = []
      const tradeRecords = [] // 创建交易记录数组
      
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }
        
        // 获取当前选择的货币类型和金额
        const coinType = tradeForm.value.arbitrageType
        const amount = tradeForm.value.amount
        
        console.log(`开始执行统一账户买入 - 账号: ${tradeForm.value.email}, 币种: ${coinType}, 金额: ${amount}USDT`)
        
        // 直接构建交易对，不再验证是否存在
        const spotSymbol = `${coinType}USDT`
        
        // 构建统一账户买入请求
        const marginBuyData = {
          email: tradeForm.value.email,
          marketType: 'portfolio_margin',
          symbol: spotSymbol,
          side: 'BUY',
          type: 'MARKET',
          quoteOrderQty: amount, // 使用USDT金额进行交易
          user_id: user.id  // 添加用户ID
        }
        
        // 发送统一账户买入请求
        const marginResponse = await axios.post('/api/market/trade', marginBuyData, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (!marginResponse.data.success) {
          showToast(`统一账户买入失败: ${marginResponse.data.message}`, 'error')
          isSubmitting.value = false
          return
        }
        
        // 记录买入结果和手续费
        const marginResult = {
          step: `统一账户买入${coinType}`,
          orderId: marginResponse.data.data.orderId,
          symbol: spotSymbol,
          side: 'BUY',
          amount: amount,
          fee: marginResponse.data.data.fee || '未知'
        }
        
        tradeRecords.push(marginResult)
        
        // 更新交易结果
        tradeResults.value = [
          {
            email: tradeForm.value.email,
            success: true,
            message: `统一账户买入${coinType}成功，金额: ${amount}USDT`,
            details: tradeRecords
          }
        ]
        
        showToast('统一账户买入完成', 'success')
        emit('success', { success: true, results: tradeResults.value })
      } catch (error) {
        console.error('统一账户买入出错:', error)
        showToast('统一账户买入请求失败', 'error')
        tradeResults.value = [{
          email: tradeForm.value.email,
          success: false,
          message: error.response?.data?.message || '请求处理失败'
        }]
      } finally {
        isSubmitting.value = false
      }
    }
    
    // 仅执行合约开空
    const executeFuturesTradeOnly = async () => {
      if (!validateTradeForm()) return
      
      isSubmitting.value = true
      tradeResults.value = []
      const tradeRecords = [] // 创建交易记录数组
      
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }
        
        // 获取当前选择的货币类型和合约类型
        const coinType = tradeForm.value.arbitrageType
        const futuresType = tradeForm.value.futuresType
        
        // 调整市场类型为后端API兼容的格式
        const apiMarketType = futuresType === 'portfolio_margin_cm' ? 'portfolio_margin_cm' : 'portfolio_margin_um'
        
        console.log(`开始执行合约开空 - 账号: ${tradeForm.value.email}, 币种: ${coinType}, 合约类型: ${apiMarketType}`)
        
        // 直接构建合约交易对名称
        let futuresSymbol = ''
        if (futuresType === 'portfolio_margin_cm') {
          // 币本位格式: BTCUSD_PERP
          futuresSymbol = `${coinType}USD_PERP`
        } else {
          // U本位格式: BTCUSDT
          futuresSymbol = `${coinType}USDT`
        }
        
        console.log(`将使用合约交易对: ${futuresSymbol}`)
        
        // 构建合约市场开空请求
        const futuresSellData = {
          email: tradeForm.value.email,
          marketType: 'portfolio_margin_cm',
          symbol: futuresSymbol,
          side: 'SELL',
          type: 'MARKET',
          useAsset: coinType,
          quantity: tradeForm.value.coinFuturesQty || 1,
          minNotional: 5,
          leverage: 1
        }
        
        // 根据合约类型和币种设置数量
        let usdtAmount = 3000 // 默认值
        
        // 根据合约类型和建议设置交易数量
        if (futuresType === 'portfolio_margin_cm') {
          // 币本位合约 - 设置张数
          futuresSellData.quantity = tradeForm.value.coinFuturesQty || 1
        } else {
          // U本位合约 - 获取USDT金额
          usdtAmount = tradeForm.value.usdtFuturesQty || 3000
          
          // 由于是卖出操作，必须使用quantity而不是quoteOrderQty
          // 计算卖出数量
          const result = await convertAmountToQuantity(futuresSymbol, usdtAmount)
          if (result.success) {
            futuresSellData.quantity = result.quantity
            console.log(`已计算卖出数量: ${result.quantity} (金额=${usdtAmount}USDT)`)
          } else {
            // 如果计算失败，使用默认数量
            futuresSellData.quantity = '1'
            console.warn(`计算卖出数量失败: ${result.error}, 使用默认数量1`)
          }
        }
        
        // 确保满足币安最低交易金额要求
        futuresSellData.minNotional = 5 // 确保订单的名义价值不小于5USDT
        
        // 发送合约市场开空请求
        const futuresResponse = await axios.post('/api/market/trade', futuresSellData, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (!futuresResponse.data.success) {
          showToast(`合约开空失败: ${futuresResponse.data.message}`, 'error')
          isSubmitting.value = false
          return
        }
        
        // 记录开空结果和手续费
        const futuresResult = {
          step: `合约开空`,
          orderId: futuresResponse.data.data.orderId,
          symbol: futuresSymbol,
          side: 'SELL',
          quantity: `${futuresType === 'portfolio_margin_cm' ? futuresSellData.quantity + '张' : usdtAmount + 'USDT'}`,
          fee: futuresResponse.data.data.fee || '未知'
        }
        
        tradeRecords.push(futuresResult)
        
        // 更新交易结果
        tradeResults.value = [
          {
            email: tradeForm.value.email,
            success: true,
            message: `${futuresType === 'portfolio_margin_cm' ? '币本位' : 'U本位'}合约开空成功，数量: ${futuresType === 'portfolio_margin_cm' ? futuresSellData.quantity + '张' : usdtAmount + 'USDT'}`,
            details: tradeRecords
          }
        ]
        
        showToast('合约开空交易完成', 'success')
        emit('success', { success: true, results: tradeResults.value })
      } catch (error) {
        console.error('合约开空出错:', error)
        showToast('合约开空请求失败', 'error')
        tradeResults.value = [{
          email: tradeForm.value.email,
          success: false,
          message: error.response?.data?.message || '请求处理失败',
          details: tradeRecords
        }]
      } finally {
        isSubmitting.value = false
      }
    }

    // 添加价格获取工具函数
    const getPriceFromCache = (symbol, coinType) => {
      // 从已加载的价格信息中获取价格数据
      if (pairPriceInfo.value[coinType] && pairPriceInfo.value[coinType].price) {
        console.log(`从缓存获取${coinType}价格: ${pairPriceInfo.value[coinType].price}`)
        return {
          success: true,
          data: {
            price: pairPriceInfo.value[coinType].price,
            symbol: symbol
          }
        }
      }
      
      console.warn(`缓存中没有${coinType}的价格信息`)
      return { 
        success: false, 
        error: `未找到${coinType}的价格信息` 
      }
    }

    // 获取交易对价格信息
    const getPriceInfo = async (symbol) => {
      // 先尝试从缓存获取
      const coinType = symbol.replace('USDT', '')
      const cachedPrice = getPriceFromCache(symbol, coinType)
      if (cachedPrice.success) {
        return cachedPrice
      }
      
      // 如果缓存没有，则通过API获取
      try {
        const user = await getCurrentUser()
        if (!user) {
          console.error('无法获取用户信息，无法请求价格')
          return { success: false, error: '无法获取用户信息' }
        }
        
        // 调用API获取价格
        const response = await axios.get(`/api/market/ticker?symbol=${symbol}`, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })
        
        if (response.data.success && response.data.data) {
          console.log(`从API获取${symbol}价格: ${response.data.data.price}`)
          return response.data
        }
        
        return { success: false, error: '获取价格失败' }
      } catch (error) {
        console.error(`获取${symbol}价格出错:`, error)
        return { success: false, error: '获取价格请求失败' }
      }
    }

    // 根据USDT金额转换为币数量的辅助函数
    const convertAmountToQuantity = async (symbol, amount) => {
      try {
        // 获取当前币价
        const priceInfo = await getPriceInfo(symbol)
        if (priceInfo && priceInfo.success && priceInfo.data && priceInfo.data.price) {
          const price = parseFloat(priceInfo.data.price)
          if (price > 0) {
            // 计算数量 = 金额 / 价格
            const quantity = parseFloat(amount) / price
            // 格式化数量，保留8位小数
            return {
              success: true,
              quantity: quantity.toFixed(8)
            }
          }
        }
        
        // 如果无法获取价格，返回默认数量
        return {
          success: false,
          quantity: '1',
          error: '无法获取价格或计算数量'
        }
      } catch (error) {
        console.error('转换金额到数量时出错:', error)
        return {
          success: false,
          quantity: '1',
          error: '计算过程出错'
        }
      }
    }

    // 返回所有需要在模板中使用的变量和函数
    return {
      dialogVisible,
      isBatchMode,
      subaccounts,
      showSubaccountSelect,
      isSubmitting,
      tradeResults,
      availableCoins,
      loadingCoins,
      pairPriceInfo,
      tradeForm,
      subaccountColumns,
      selectSubaccount,
      closeDialog,
      incrementAmount,
      decrementAmount,
      incrementCoinFuturesQty,
      decrementCoinFuturesQty,
      successCount,
      failedCount,
      executeTrade,
      executeBatchTrade,
      exportResults,
      resetForm,
      executeSpotTradeOnly,
      getPriceFromCache,
      updateQuantitySuggestions,
      executeFuturesTradeOnly,
      getPriceInfo,
      convertAmountToQuantity
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
  max-width: 800px;
  max-height: 85vh;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow-y: auto;
  color: #333;
}

.auto-arbitrage-container {
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

/* 数字输入容器 */
.number-input-container {
  display: flex;
  align-items: center;
  width: 100%;
}

.number-btn {
  width: 36px;
  height: 36px;
  background-color: #f5f7fa;
  border: 1px solid #ddd;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.number-btn:first-child {
  border-radius: 4px 0 0 4px;
}

.number-input {
  flex-grow: 1;
  text-align: center;
  border-left: none;
  border-right: none;
  border-radius: 0;
}

.number-btn:last-of-type {
  border-radius: 0 4px 4px 0;
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

.debug-buttons {
  display: flex;
  gap: 10px;
}

.debug-button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.spot-button {
  background-color: #67c23a;
  color: white;
}

.futures-button {
  background-color: #e6a23c;
  color: white;
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

/* 批量结果展示 */
.batch-results {
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 20px;
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

.trade-details {
  margin-top: 10px;
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.detail-item {
  padding: 6px 0;
  border-bottom: 1px dashed #eee;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-step {
  font-weight: 500;
  margin-bottom: 4px;
}

/* 结果统计 */
.result-summary {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-card {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  width: 70%;
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
  
  .debug-buttons {
    flex-direction: column;
  }
  
  .result-summary {
    flex-direction: column;
    gap: 12px;
  }
  
  .summary-card {
    width: 100%;
  }
}
</style>
