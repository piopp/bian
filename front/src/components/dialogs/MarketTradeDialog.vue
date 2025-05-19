<template>
  <div>
    <!-- 主对话框 -->
    <div v-if="dialogVisible" class="dialog-overlay" @click="closeDialog">
      <div class="dialog-content" @click.stop>
        <div class="market-trade-container">
          <header class="dialog-header">
            <h2>批量市场交易</h2>
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

              <!-- 市场类型选择 -->
              <div class="form-item">
                <label>市场类型</label>
                <div class="form-input">
                  <div class="radio-group">
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="tradeForm.marketType" 
                        value="portfolio_margin" 
                        @change="handleMarketTypeChange"
                        checked
                      >
                      统一账户杠杆
                    </label>
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="tradeForm.marketType" 
                        value="portfolio_margin_um" 
                        @change="handleMarketTypeChange"
                      >
                      统一账户UM合约
                    </label>
                  </div>
                </div>
              </div>

              <!-- 交易对选择 -->
              <div class="form-item">
                <label>交易对</label>
                <div class="form-input">
                  <div class="select-container">
                    <input 
                      class="form-select"
                      type="text"
                      v-model="tradeForm.symbolDisplay"
                      readonly
                      placeholder="选择交易对"
                      @click="showSymbolSelect = true"
                    />
                  </div>
                </div>
              </div>

              <!-- 交易方向 -->
              <div class="form-item">
                <label>交易方向</label>
                <div class="form-input">
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" v-model="tradeForm.side" value="BUY">
                      买入
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="tradeForm.side" value="SELL">
                      卖出
                    </label>
                  </div>
                </div>
              </div>

              <!-- 价格类型 -->
              <div class="form-item">
                <label>价格类型</label>
                <div class="form-input">
                  <div class="radio-group">
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="tradeForm.priceType" 
                        value="LIMIT" 
                        @change="handlePriceTypeChange"
                      >
                      限价
                    </label>
                    <label class="radio-label">
                      <input 
                        type="radio" 
                        v-model="tradeForm.priceType" 
                        value="MARKET" 
                        @change="handlePriceTypeChange"
                      >
                      市价
                    </label>
                  </div>
                </div>
              </div>

              <!-- 价格输入 -->
              <div class="form-item" v-if="tradeForm.priceType === 'LIMIT'">
                <label>价格</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <button @click="decrementPrice" class="number-btn">-</button>
                    <input
                      type="number"
                      v-model.number="tradeForm.price"
                      class="number-input"
                      :min="0.00000001"
                      :step="priceStep"
                    />
                    <button @click="incrementPrice" class="number-btn">+</button>
                  </div>
                </div>
              </div>

              <!-- 数量输入 -->
              <div class="form-item">
                <label>{{ tradeForm.side === 'BUY' && tradeForm.priceType === 'MARKET' ? '数量(币的数量)' : '数量(币的数量)' }}</label>
                <div class="form-input">
                  <div class="number-input-container">
                    <button @click="decrementQuantity" class="number-btn">-</button>
                    <input
                      type="number"
                      v-model.number="tradeForm.quantity"
                      class="number-input"
                      :min="minQuantity"
                      :step="quantityStep"
                    />
                    <button @click="incrementQuantity" class="number-btn">+</button>
                  </div>
                  <!-- 帮助提示 -->
                  <div class="help-tip" v-if="tradeForm.priceType === 'MARKET' && tradeForm.side === 'SELL'">
                    注意：市价卖单必须输入要卖出的币的数量，不是USDT金额。
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 高级操作区域 -->
          <div class="advanced-operations">
            <div class="section-title">
              <h3>高级操作</h3>
            </div>
            <div class="operations-buttons">
              <button 
                class="operation-button arbitrage-button" 
                @click="openArbitrageDialog"
              >
                自动化套利交易
              </button>
            </div>
          </div>

          <!-- 提交按钮区域 -->
          <div class="action-buttons">
            <button 
              class="submit-button" 
              @click="submitSingleTrade" 
              :disabled="isSubmitting" 
              v-if="!isBatchMode"
            >
              <span v-if="isSubmitting" class="loading-spinner"></span>
              {{ tradeForm.side === 'BUY' ? '买入' : '卖出' }}
            </button>
            <button 
              class="submit-button" 
              @click="submitBatchTrade" 
              :disabled="isSubmitting" 
              v-else
            >
              <span v-if="isSubmitting" class="loading-spinner"></span>
              批量{{ tradeForm.side === 'BUY' ? '买入' : '卖出' }}
            </button>
            <div class="button-group">
              <button class="secondary-button" @click="resetForm">重置</button>
              <button class="secondary-button" @click="dialogVisible = false">关闭</button>
            </div>
          </div>

          <!-- 批量结果展示区域 -->
          <div class="batch-results" v-if="batchResults.length > 0">
            <h3 class="results-title">批量交易结果</h3>
            <div class="results-list">
              <div class="result-item" v-for="(result, index) in batchResults" :key="index">
                <div class="result-header">
                  <span>{{ result.email }}</span>
                  <span class="tag" :class="result.success ? 'success-tag' : 'error-tag'">
                    {{ result.success ? '成功' : '失败' }}
                  </span>
                </div>
                <div class="result-body">
                  <div>{{ result.message }}</div>
                  <div v-if="result.orderId">订单ID: {{ result.orderId }}</div>
                </div>
              </div>
            </div>

            <!-- 结果统计 -->
            <div class="result-summary">
              <div class="summary-card">
                <div class="summary-title">交易统计</div>
                <div class="summary-content">
                  <div>总交易: {{ batchResults.length }}</div>
                  <div class="success-count">成功: {{ successCount }}</div>
                  <div class="failed-count">失败: {{ failedCount }}</div>
                </div>
              </div>
              <button 
                class="secondary-button" 
                @click="exportResults" 
                :disabled="batchResults.length === 0"
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
    
    <div v-if="showSymbolSelect" class="select-modal-overlay" @click="showSymbolSelect = false">
      <div class="select-modal" @click.stop>
        <div class="select-modal-header">
          <h3>选择交易对</h3>
          <button class="close-button" @click="showSymbolSelect = false">×</button>
        </div>
        <div class="select-modal-content">
          <div 
            v-for="item in symbolColumns" 
            :key="item.value" 
            class="select-option"
            @click="selectSymbol(item)"
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
import eventBus from '../../services/eventBus.js'

export default {
  name: 'MarketTradeDialog',
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
  emits: ['update:modelValue', 'success', 'open-arbitrage'],
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
    const showSymbolSelect = ref(false)
    const availableTradingPairs = ref([])
    const isSubmitting = ref(false)
    const batchResults = ref([])
    
    // 添加交易对加载状态
    const loadingTradingPairs = ref(false)
    
    // 添加arbitrageSettings变量
    const arbitrageSettings = ref({
      amount: 3011.5,
      futuresType: 'coin_futures'
    })
    
    // 设置默认精度
    const pricePrecision = ref(6)
    const quantityPrecision = ref(4)
    const priceStep = ref(0.000001)
    const quantityStep = ref(0.0001)
    const minQuantity = ref(0.0001)
    
    // 交易表单
    const tradeForm = ref({
      email: '',
      symbolDisplay: '', // 显示用
      symbol: '',
      side: 'BUY',
      priceType: 'LIMIT',
      price: null,
      quantity: null,
      marketType: 'portfolio_margin' // 默认统一账户杠杆
    })

    // Picker数据源
    const subaccountColumns = computed(() => {
      return subaccounts.value.map(item => ({
        text: item.email,
        value: item.email
      }))
    })

    // 检查交易对是否适合当前市场类型
    const isPairSuitableForMarketType = (pair, marketType) => {
      // 如果交易对没有marketType标记，认为它适用于任何市场
      if (!pair.marketType) return true;
      
      // 精确匹配
      if (pair.marketType === marketType) return true;
      
      // 特殊处理：portfolio_margin 可以使用 portfolio_margin_um 的交易对
      if (marketType === 'portfolio_margin' && pair.marketType === 'portfolio_margin_um') return true;
      
      // 特殊处理：反之亦然，portfolio_margin_um 也可以使用 portfolio_margin 的交易对
      if (marketType === 'portfolio_margin_um' && pair.marketType === 'portfolio_margin') return true;
      
      return false;
    };
    
    const symbolColumns = computed(() => {
      // 根据当前选择的市场类型过滤交易对
      const filteredPairs = availableTradingPairs.value.filter(pair => 
        isPairSuitableForMarketType(pair, tradeForm.value.marketType)
      );
      
      return filteredPairs.map(pair => ({
        text: `${pair.baseAsset}/${pair.quoteAsset}`,
        value: pair.symbol
      }));
    });
    
    // 选择处理函数 - 改名以适应原生实现
    const selectSubaccount = (item) => {
      tradeForm.value.email = item.value
      showSubaccountSelect.value = false
    }

    const selectSymbol = (item) => {
      tradeForm.value.symbol = item.value
      tradeForm.value.symbolDisplay = item.text
      showSymbolSelect.value = false
      handleSymbolChange(item.value)
    }
    
    // 处理对话框关闭
    const closeDialog = (e) => {
      // 只有点击遮罩层才关闭
      if (e.target.classList.contains('dialog-overlay')) {
        dialogVisible.value = false
      }
    }
    
    // 数字输入框辅助函数
    const incrementPrice = () => {
      if (!tradeForm.value.price) tradeForm.value.price = 0
      tradeForm.value.price = +(tradeForm.value.price + priceStep.value).toFixed(pricePrecision.value)
    }
    
    const decrementPrice = () => {
      if (!tradeForm.value.price) return
      const newValue = tradeForm.value.price - priceStep.value
      if (newValue >= 0.00000001) {
        tradeForm.value.price = +newValue.toFixed(pricePrecision.value)
      }
    }
    
    const incrementQuantity = () => {
      if (!tradeForm.value.quantity) tradeForm.value.quantity = 0
      tradeForm.value.quantity = +(tradeForm.value.quantity + quantityStep.value).toFixed(quantityPrecision.value)
    }
    
    const decrementQuantity = () => {
      if (!tradeForm.value.quantity) return
      const newValue = tradeForm.value.quantity - quantityStep.value
      if (newValue >= minQuantity.value) {
        tradeForm.value.quantity = +newValue.toFixed(quantityPrecision.value)
      }
    }
    
    // 结果统计
    const successCount = computed(() => batchResults.value.filter(r => r.success).length)
    const failedCount = computed(() => batchResults.value.filter(r => !r.success).length)
    
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

    // 加载交易对
    const loadTradingPairs = async () => {
      // 设置加载状态
      loadingTradingPairs.value = true;
      
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          loadingTradingPairs.value = false;
          return
        }

        // 获取多种市场类型的交易对
        const marketTypes = ['portfolio_margin', 'portfolio_margin_um'];
        const allPairs = [];
        
        // 依次获取各种市场类型的交易对
        for (const marketType of marketTypes) {
          // 首先尝试获取收藏的交易对
          let endpoint = `/api/trading-pairs/with-price?market_type=${marketType}&favorite=true`
          let response = await axios.get(endpoint, {
            headers: {
              Authorization: `Bearer ${user.token}`
            }
          })
  
          if (response.data.success) {
            // 验证和处理返回的数据
            const responseData = response.data.data || []
            
            // 确保数据是数组
            if (Array.isArray(responseData) && responseData.length > 0) {
              // 标准化处理每个交易对
              const validPairs = responseData.filter(pair => {
                // 确保pair是对象，且具有必要的属性
                return pair && typeof pair === 'object' && 
                      pair.symbol && // 必须有交易对代码
                      (pair.baseAsset !== undefined || pair.base_asset !== undefined) && // 必须有基础资产
                      (pair.quoteAsset !== undefined || pair.quote_asset !== undefined); // 必须有报价资产
              }).map(pair => {
                // 标准化字段名称 (处理snake_case和camelCase的差异)
                return {
                  ...pair,
                  baseAsset: pair.baseAsset || pair.base_asset || '',
                  quoteAsset: pair.quoteAsset || pair.quote_asset || '',
                  symbol: pair.symbol,
                  marketType: marketType // 记录该交易对来自哪个市场
                };
              });
              
              if (validPairs.length > 0) {
                // 添加到总交易对列表
                allPairs.push(...validPairs);
                continue; // 有收藏的交易对，继续处理下一个市场类型
              }
            }
            
            // 如果没有收藏的交易对或处理后无有效交易对，获取所有交易对作为fallback
            console.warn(`未找到${marketType}市场类型的收藏交易对，将获取所有交易对`);
            endpoint = `/api/trading-pairs/with-price?market_type=${marketType}`
            response = await axios.get(endpoint, {
              headers: {
                Authorization: `Bearer ${user.token}`
              }
            })
            
            if (response.data.success) {
              const allResponseData = response.data.data || []
              if (Array.isArray(allResponseData)) {
                const allValidPairs = allResponseData.filter(pair => {
                  return pair && typeof pair === 'object' && 
                        pair.symbol && 
                        (pair.baseAsset !== undefined || pair.base_asset !== undefined) && 
                        (pair.quoteAsset !== undefined || pair.quote_asset !== undefined);
                }).map(pair => {
                  return {
                    ...pair,
                    baseAsset: pair.baseAsset || pair.base_asset || '',
                    quoteAsset: pair.quoteAsset || pair.quote_asset || '',
                    symbol: pair.symbol,
                    marketType: marketType
                  };
                });
                
                allPairs.push(...allValidPairs);
              } else {
                console.warn(`${marketType}返回的所有交易对数据不是数组:`, allResponseData);
              }
            } else {
              console.warn(`获取${marketType}所有交易对失败:`, response.data.message || '未知错误');
            }
          } else {
            console.warn(`获取${marketType}收藏交易对失败:`, response.data.message || '未知错误');
            
            // 尝试获取所有交易对作为备选
            endpoint = `/api/trading-pairs/with-price?market_type=${marketType}`
            response = await axios.get(endpoint, {
              headers: {
                Authorization: `Bearer ${user.token}`
              }
            })
            
            if (response.data.success) {
              const allResponseData = response.data.data || []
              if (Array.isArray(allResponseData)) {
                const allValidPairs = allResponseData.filter(pair => {
                  return pair && typeof pair === 'object' && 
                        pair.symbol && 
                        (pair.baseAsset !== undefined || pair.base_asset !== undefined) && 
                        (pair.quoteAsset !== undefined || pair.quote_asset !== undefined);
                }).map(pair => {
                  return {
                    ...pair,
                    baseAsset: pair.baseAsset || pair.base_asset || '',
                    quoteAsset: pair.quoteAsset || pair.quote_asset || '',
                    symbol: pair.symbol,
                    marketType: marketType
                  };
                });
                
                allPairs.push(...allValidPairs);
              }
            }
          }
        }
        
        // 去重 - 基于symbol
        const uniquePairsMap = new Map();
        for (const pair of allPairs) {
          // 如果是新交易对或者是更倾向的市场类型，则更新
          if (!uniquePairsMap.has(pair.symbol) || 
             (uniquePairsMap.get(pair.symbol).marketType === 'portfolio_margin' && pair.marketType === 'portfolio_margin_um')) {
            uniquePairsMap.set(pair.symbol, pair);
          }
        }
        
        // 将Map转换回数组
        availableTradingPairs.value = Array.from(uniquePairsMap.values());
          
        // 排序交易对：先BTC，然后ETH，然后按字母顺序
        availableTradingPairs.value.sort((a, b) => {
          // 添加安全检查，确保a和b以及它们的baseAsset属性都存在
          if (!a || !b) return 0;
          
          // 检查baseAsset是否存在
          const aBase = a.baseAsset || '';
          const bBase = b.baseAsset || '';
          
          if (aBase === 'BTC' && bBase !== 'BTC') return -1;
          if (aBase !== 'BTC' && bBase === 'BTC') return 1;
          if (aBase === 'ETH' && bBase !== 'ETH') return -1;
          if (aBase !== 'ETH' && bBase === 'ETH') return 1;
          return aBase.localeCompare(bBase);
        });
        
        if (availableTradingPairs.value.length > 0) {
          const firstPair = availableTradingPairs.value[0];
          tradeForm.value.symbol = firstPair.symbol;
          tradeForm.value.symbolDisplay = `${firstPair.baseAsset}/${firstPair.quoteAsset}`;
        } else {
          console.warn('没有有效的交易对数据');
        }
      } catch (error) {
        console.error('加载交易对出错:', error)
        showToast('加载交易对失败', 'error')
      } finally {
        // 重置加载状态
        loadingTradingPairs.value = false;
      }
    }
    
    // 自定义通知函数 - 替代Vant的showNotify
    const showToast = (message, type = 'info') => {
      // 这里可以实现自定义toast，或使用第三方库
      // 简单起见，使用console和alert
      console.log(`[${type.toUpperCase()}]: ${message}`)
      
      // 可以根据实际需求使用以下方式：
      // 1. 简单提示
      alert(message)
      
      // 2. 或实现自定义toast：创建一个div添加到body，设置定时器自动删除
      /* const toast = document.createElement('div')
      toast.className = `toast toast-${type}`
      toast.textContent = message
      document.body.appendChild(toast)
      setTimeout(() => {
        document.body.removeChild(toast)
      }, 3000) */
    }
    
    // 事件处理函数
    const handleMarketTypeChange = (value) => {
      // 记录用户选择的市场类型
      console.log(`切换市场类型：${value.target.value}`)
      const newMarketType = value.target.value
      tradeForm.value.marketType = newMarketType
      
      // 当市场类型改变时，需要重新选择适合该市场类型的交易对
      // 获取当前市场类型的适合交易对
      const filteredPairs = availableTradingPairs.value.filter(pair => 
        isPairSuitableForMarketType(pair, newMarketType)
      );
      
      if (filteredPairs.length > 0) {
        const firstPair = filteredPairs[0]
        tradeForm.value.symbol = firstPair.symbol
        tradeForm.value.symbolDisplay = `${firstPair.baseAsset}/${firstPair.quoteAsset}`
      } else {
        // 如果没有适合当前市场类型的交易对，清空选择
        tradeForm.value.symbol = ''
        tradeForm.value.symbolDisplay = ''
        console.warn(`未找到适合市场类型${newMarketType}的交易对`)
      }
    }
    
    const handleSymbolChange = (value) => {
      // 使用传入的值，记录被选中的交易对
      console.log(`选择交易对：${value}`)
      tradeForm.value.symbol = value
      tradeForm.value.price = null
      tradeForm.value.quantity = null
      // 不需要返回值
    }
    
    const handlePriceTypeChange = (value) => {
      // 使用传入的值，更新价格类型
      console.log(`切换价格类型：${value.target.value}`)
      // 使用event对象中的值，而不是自我赋值
      tradeForm.value.priceType = value.target.value
      if (tradeForm.value.priceType === 'MARKET') {
        tradeForm.value.price = null
      }
      // 不需要返回值
    }

    // 提交单个交易
    const submitSingleTrade = async () => {
      if (!validateTradeForm()) return
      
      isSubmitting.value = true
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }

        const tradeData = {
          email: tradeForm.value.email,
          marketType: tradeForm.value.marketType,
          symbol: tradeForm.value.symbol,
          side: tradeForm.value.side,
          type: tradeForm.value.priceType,
          price: tradeForm.value.priceType === 'LIMIT' ? tradeForm.value.price : undefined,
          useSubAccountApi: true // 明确指定使用子账号API
        }
        
        // 针对市价单区分处理:
        // - 对于市价单，始终使用quantity(交易数量)，不再根据买卖方向区分
        // - 这样可以确保卖出市价单(SELL MARKET)使用正确的参数
        if (tradeForm.value.priceType === 'MARKET') {
          tradeData.quantity = tradeForm.value.quantity;
        } else {
          tradeData.quantity = tradeForm.value.quantity;
        }

        // 添加日志以便调试
        console.log('准备提交单个交易请求，数据:', JSON.stringify(tradeData))

        const response = await axios.post('/api/market/trade', tradeData, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })

        if (response.data.success) {
          showToast(`交易成功，订单ID: ${response.data.data.orderId}`, 'success')
          batchResults.value = [{
            email: tradeForm.value.email,
            success: true,
            message: '交易成功',
            orderId: response.data.data.orderId
          }]
          emit('success', { success: true, results: batchResults.value })
        } else {
          showToast(response.data.message || '交易失败', 'error')
          batchResults.value = [{
            email: tradeForm.value.email,
            success: false,
            message: response.data.message || '交易失败',
            orderId: null
          }]
        }
      } catch (error) {
        console.error('交易出错:', error)
        showToast('交易请求失败', 'error')
        batchResults.value = [{
          email: tradeForm.value.email,
          success: false,
          message: error.response?.data?.message || '请求处理失败',
          orderId: null
        }]
      } finally {
        isSubmitting.value = false
      }
    }

    // 批量交易
    const submitBatchTrade = async () => {
      if (!validateTradeForm(true)) return
      
      isSubmitting.value = true
      batchResults.value = []
      
      try {
        const user = await getCurrentUser()
        if (!user) {
          showToast('无法获取用户信息', 'error')
          isSubmitting.value = false
          return
        }

        const batchTradeData = {
          accounts: (props.selectedAccounts || []).map(acc => acc.email),
          marketType: tradeForm.value.marketType,
          symbol: tradeForm.value.symbol,
          side: tradeForm.value.side,
          type: tradeForm.value.priceType,
          price: tradeForm.value.priceType === 'LIMIT' ? tradeForm.value.price : undefined,
          useSubAccountApi: true // 明确指定使用子账号API
        }
        
        // 针对市价单区分处理:
        // - 对于市价单，始终使用quantity(交易数量)，不再根据买卖方向区分
        // - 这样可以确保卖出市价单(SELL MARKET)使用正确的参数
        if (tradeForm.value.priceType === 'MARKET') {
          batchTradeData.quantity = tradeForm.value.quantity;
        } else {
          batchTradeData.quantity = tradeForm.value.quantity;
        }

        // 添加日志以便调试
        console.log('准备提交批量交易请求，数据:', JSON.stringify(batchTradeData))

        const response = await axios.post('/api/market/batch-trade', batchTradeData, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        })

        if (response.data.success) {
          batchResults.value = response.data.data.results
          const successCount = batchResults.value.filter(r => r.success).length
          showToast(`批量交易完成，共 ${batchResults.value.length} 个账户，${successCount} 个成功`, 'success')
          emit('success', { success: true, results: batchResults.value })
        } else {
          showToast(response.data.message || '批量交易失败', 'error')
        }
      } catch (error) {
        console.error('批量交易出错:', error)
        showToast('批量交易请求失败', 'error')
      } finally {
        isSubmitting.value = false
      }
    }

    // 验证交易表单
    const validateTradeForm = (isBatch = false) => {
      if (!isBatch && !tradeForm.value.email) {
        showToast('请选择交易子账户', 'warning')
        return false
      }

      if (!tradeForm.value.symbol) {
        showToast('请选择交易对', 'warning')
        return false
      }

      if (tradeForm.value.priceType === 'LIMIT' && (!tradeForm.value.price || tradeForm.value.price <= 0)) {
        showToast('请输入有效价格', 'warning')
        return false
      }

      if (!tradeForm.value.quantity || tradeForm.value.quantity <= 0) {
        showToast('请输入有效数量', 'warning')
        return false
      }

      // 特别提醒市价卖单必须使用币的数量
      if (tradeForm.value.priceType === 'MARKET' && tradeForm.value.side === 'SELL') {
        const symbol = availableTradingPairs.value.find(pair => pair.symbol === tradeForm.value.symbol)
        const baseAsset = symbol ? symbol.baseAsset : ''
        showToast(`您正在进行市价卖单，输入的数量 ${tradeForm.value.quantity} 将被理解为 ${baseAsset} 币的数量`, 'info')
      }

      return true
    }

    // 导出结果
    const exportResults = () => {
      if (batchResults.value.length === 0) return
      
      const dataStr = JSON.stringify(batchResults.value, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      
      const a = document.createElement('a')
      a.href = url
      a.download = `market_trade_results_${new Date().toISOString().replace(/[:.]/g, '-')}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    // 重置表单
    const resetForm = () => {
      tradeForm.value = {
        email: props.account ? props.account.email : '',
        marketType: 'portfolio_margin',
        symbol: '',
        symbolDisplay: '',
        side: 'BUY',
        priceType: 'LIMIT',
        price: null,
        quantity: null
      }
      
      // 如果有交易对，选择第一个
      if (availableTradingPairs.value.length > 0) {
        const firstPair = availableTradingPairs.value[0];
        tradeForm.value.symbol = firstPair.symbol;
        tradeForm.value.symbolDisplay = `${firstPair.baseAsset}/${firstPair.quoteAsset}`;
      }
    }

    // 对话框打开处理
    const handleDialogOpen = async () => {
      // 加载子账户列表
      await loadSubaccounts()
      
      // 如果还没有加载交易对，则加载
      if (availableTradingPairs.value.length === 0 && !loadingTradingPairs.value) {
        await loadTradingPairs()
      }
    }

    // 对话框关闭处理
    const handleDialogClosed = () => {
      batchResults.value = []
    }

    // 组件加载时
    watch(() => dialogVisible.value, (newVal) => {
      if (newVal) {
        handleDialogOpen()
      } else {
        handleDialogClosed()
      }
    })
    
    // 组件初始化时立即加载交易对
    onMounted(async () => {
      // 立即开始加载交易对，不等待对话框打开
      if (availableTradingPairs.value.length === 0 && !loadingTradingPairs.value) {
        await loadTradingPairs()
      }
    })

    // 自动化套利对话框
    const showArbitrageDialog = ref(false)
    
    // 打开自动化套利对话框
    const openArbitrageDialog = () => {
      // 关闭当前对话框
      dialogVisible.value = false
      // 设置一个短暂的延迟，避免两个模态框冲突
      setTimeout(() => {
        // 使用事件总线发送打开套利对话框的事件
        eventBus.emit('open-arbitrage', {
          account: props.account,
          selectedAccounts: props.selectedAccounts
        })
      }, 300)
    }

    return {
      dialogVisible,
      isBatchMode,
      tradeForm,
      subaccounts,
      showSubaccountSelect,
      showSymbolSelect,
      subaccountColumns,
      symbolColumns,
      batchResults,
      isSubmitting,
      successCount,
      failedCount,
      availableTradingPairs,
      pricePrecision,
      priceStep,
      quantityPrecision,
      quantityStep,
      minQuantity,
      arbitrageSettings,
      showArbitrageDialog,
      handleDialogOpen,
      handleDialogClosed,
      resetForm,
      submitSingleTrade,
      submitBatchTrade,
      openArbitrageDialog,
      exportResults,
      handlePriceTypeChange,
      handleMarketTypeChange,
      handleSymbolChange,
      selectSubaccount,
      selectSymbol,
      closeDialog,
      incrementPrice,
      decrementPrice,
      incrementQuantity,
      decrementQuantity
    }
  }
}
</script>

<style scoped>
/* 基础布局 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: flex-end;
  z-index: 2000;
}

.dialog-content {
  width: 100%;
  height: 80%;
  background-color: #fff;
  border-radius: 16px 16px 0 0;
  overflow: hidden;
  animation: slide-up 0.3s ease;
}

.market-trade-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding-bottom: 20px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebedf0;
}

.close-button {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #666;
}

/* 表单样式 */
.trade-form {
  padding: 16px;
}

.form-group {
  background-color: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(100, 101, 102, 0.08);
}

.form-item {
  display: flex;
  padding: 12px 16px;
  border-bottom: 1px solid #ebedf0;
}

.form-item label {
  width: 120px;
  font-weight: 500;
  color: #323233;
}

.form-input {
  flex: 1;
}

/* 通知栏 */
.notice-bar {
  background-color: #ecf9ff;
  color: #1989fa;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 8px;
}

/* 标签样式 */
.tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 4px;
  margin-right: 4px;
  margin-bottom: 4px;
}

.account-tag {
  background-color: #1989fa;
  color: white;
}

.success-tag {
  background-color: #07c160;
  color: white;
}

.error-tag {
  background-color: #ee0a24;
  color: white;
}

/* 下拉选择器 */
.select-container {
  position: relative;
  width: 100%;
}

.form-select {
  width: 100%;
  height: 34px;
  padding: 0 12px;
  background-color: #f7f8fa;
  border: 1px solid #ebedf0;
  border-radius: 4px;
  cursor: pointer;
}

/* 单选框样式 */
.radio-group {
  display: flex;
  flex-wrap: wrap;
}

.radio-label {
  margin-right: 16px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.radio-label input {
  margin-right: 4px;
}

/* 数字输入框 */
.number-input-container {
  display: flex;
  align-items: center;
  border: 1px solid #ebedf0;
  border-radius: 4px;
  overflow: hidden;
  width: 80%;
}

.number-btn {
  width: 36px;
  height: 34px;
  background-color: #f7f8fa;
  border: none;
  cursor: pointer;
  font-size: 16px;
}

.number-input {
  flex: 1;
  height: 34px;
  border: none;
  text-align: center;
  -moz-appearance: textfield; /* Firefox */
}

.number-input::-webkit-outer-spin-button,
.number-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 按钮区域 */
.action-buttons {
  padding: 0 16px;
  margin-top: 20px;
}

.submit-button {
  width: 100%;
  height: 44px;
  background-color: #1989fa;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  position: relative;
}

.submit-button:disabled {
  background-color: #a0cfff;
  cursor: not-allowed;
}

.secondary-button {
  height: 40px;
  background-color: white;
  color: #323233;
  border: 1px solid #dcdee0;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.button-group {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
}

.button-group button {
  width: 48%;
}

/* 加载状态 */
.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
  margin-right: 4px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 批量结果区域 */
.batch-results {
  margin-top: 20px;
  padding: 0 16px;
}

.results-title {
  font-size: 16px;
  margin-bottom: 12px;
  color: #323233;
}

.results-list {
  background-color: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(100, 101, 102, 0.08);
}

.result-item {
  padding: 12px 16px;
  border-bottom: 1px solid #ebedf0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-body {
  font-size: 14px;
  color: #646566;
}

.result-summary {
  margin-top: 15px;
}

.summary-card {
  background-color: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(100, 101, 102, 0.08);
}

.summary-title {
  font-weight: bold;
  margin-bottom: 8px;
}

.summary-content {
  font-size: 14px;
  color: #646566;
}

.success-count {
  color: #07c160;
  font-weight: bold;
}

.failed-count {
  color: #ee0a24;
  font-weight: bold;
}

.selected-accounts-list {
  display: flex;
  flex-wrap: wrap;
  margin-top: 10px;
  max-height: 80px;
  overflow-y: auto;
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
  align-items: flex-end;
  z-index: 2001;
}

.select-modal {
  width: 100%;
  background-color: #fff;
  border-radius: 16px 16px 0 0;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  animation: slide-up 0.3s ease;
}

.select-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebedf0;
}

.select-modal-content {
  overflow-y: auto;
  max-height: calc(70vh - 60px);
}

.select-option {
  padding: 14px 16px;
  border-bottom: 1px solid #ebedf0;
  cursor: pointer;
}

.select-option:active {
  background-color: #f2f3f5;
}

@keyframes slide-up {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

/* 高级操作区域样式 */
.advanced-operations {
  margin-top: 20px;
  padding: 0 16px;
}

.section-title {
  margin-bottom: 12px;
}

.operations-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.operation-button {
  flex: 1;
  min-width: 150px;
  height: 44px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  color: white;
}

.arbitrage-button {
  background-color: #07c160;
}

.arbitrage-button:hover {
  background-color: #06ad56;
}

/* 帮助提示样式 */
.help-tip {
  font-size: 12px;
  color: #ff7d00;
  margin-top: 5px;
  background-color: #fff7e6;
  padding: 5px 8px;
  border-radius: 4px;
  border-left: 2px solid #ff7d00;
}
</style> 