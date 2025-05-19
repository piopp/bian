<!-- 修复自动平仓功能问题：确保关闭开关后不再执行自动平仓操作 -->
<template>  <div class="mark-price-container">
    <!-- 添加通知窗口 -->
    <el-dialog
      v-model="showMessageDialog"
      title="自动平仓通知"
      width="50%"
      :before-close="handleCloseMessageDialog"
    >
      <div class="message-list">
        <div class="message-item" v-for="(message, index) in processingMessages" :key="index">
          <el-alert
            :type="message.type"
            :title="message.title"
            :description="message.description"
            :closable="false"
            show-icon
          />
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showMessageDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 添加自动平仓控制面板 - 始终显示 -->
    <div class="auto-close-control-panel">
      <div class="panel-header">
        <div class="panel-title">自动平仓控制</div>
        <el-switch
          v-model="autoCloseEnabled"
          :active-text="autoCloseEnabled ? '已开启' : '已关闭'"
          inline-prompt
          size="small"
        />
      </div>
      
      <div class="panel-content">
                <!-- 平仓模式为收益率模式 -->        <div class="setting-item">          <div class="setting-label">平仓模式:</div>          <div class="setting-value">            <div class="setting-readonly">              达到目标收益率时平仓            </div>          </div>        </div>                <!-- 目标收益率设置 -->        <div class="setting-item">
          <div class="setting-label">目标收益率(%):</div>
          <div class="setting-value">
            <template v-if="isEditing">
              <el-input-number 
                v-model="tempTargetProfitPercentage" 
                :min="0.01" 
                :max="100" 
                :step="0.01" 
                size="small"
                :precision="2"
                style="width: 120px;"
              />
              <el-tooltip 
                content="当某个方向的总收益率达到设置的目标值时，触发自动平仓" 
                placement="top"
              >
                <el-icon class="help-icon"><question-filled /></el-icon>
              </el-tooltip>
            </template>
            <template v-else>
              <div class="setting-readonly">{{ targetProfitPercentage.toFixed(2) }}%</div>
            </template>
          </div>
        </div>
        
        <!-- 当前状态显示 -->
        <div class="current-status" v-if="hasPositions">
          <div class="status-item">
            <div class="status-label">多仓收益率:</div>
                        <div :class="longProfitPercentage >= 0 ? 'status-value positive' : 'status-value negative'">              {{ formatTotalProfitPercentage(longProfitPercentage) }}%              <span v-if="autoCloseEnabled && longProfitPercentage >= targetProfitPercentage" class="status-icon">                <el-icon><check /></el-icon>              </span>            </div>
          </div>
          <div class="status-item">
            <div class="status-label">空仓收益率:</div>
                        <div :class="shortProfitPercentage >= 0 ? 'status-value positive' : 'status-value negative'">              {{ formatTotalProfitPercentage(shortProfitPercentage) }}%              <span v-if="autoCloseEnabled && shortProfitPercentage >= targetProfitPercentage" class="status-icon">                <el-icon><check /></el-icon>              </span>            </div>
          </div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="control-buttons">
          <template v-if="isEditing">
            <el-button size="small" type="primary" @click="saveSettings">确认</el-button>
            <el-button size="small" @click="cancelEdit">取消</el-button>
          </template>
          <template v-else>
            <el-button size="small" type="primary" @click="startEdit">编辑设置</el-button>
          </template>
        </div>
        
        <div class="tip" v-if="autoCloseEnabled">
          <i class="el-icon-info"></i>
          开启后，系统将根据选择的模式自动执行平仓和资金归集操作。
        </div>
      </div>
    </div>
    
    <!-- 标记价格卡片 -->
    <div class="price-section">
      <div class="section-title">实时标记价</div>
      <div class="cards-container">
        <div class="price-card" v-for="(price, symbol) in markPrices" :key="symbol">
          <div class="symbol">{{ symbol }}</div>
          <div class="price">{{ price }}</div>
        </div>
      </div>
    </div>
    
    <!-- 多空收益统计 -->
    <div class="profit-summary-section" v-if="hasPositions">
      <div class="section-title">收益统计</div>
      <!-- 移除多空合计卡片，但保留建仓本金的合计计算 -->
      <div class="profit-cards-container">
        <!-- 多仓收益 -->
        <div class="profit-card" :class="{'profit': totalLongProfit > 0, 'loss': totalLongProfit < 0}">
          <div class="profit-header">多仓收益详情</div>
          <div class="profit-details">
            <div class="profit-detail-item">
              <span class="detail-label">总仓价值:</span>
              <span class="detail-value">{{ formatTotalValue(longTotalValue) }}</span>
            </div>
            <div class="profit-detail-item">
              <span class="detail-label">建仓本金(合计):</span>
              <span class="detail-value">{{ formatTotalValue(totalInitialValue) }}</span>
            </div>
            <div class="profit-detail-item highlight">
              <span class="detail-label">未实现盈亏:</span>
              <span class="detail-value" :class="totalLongProfit >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfit(totalLongProfit) }}
              </span>
            </div>
            <div class="profit-detail-item highlight">
              <span class="detail-label">收益率:</span>
              <span class="detail-value" :class="longProfitPercentage >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfitPercentage(longProfitPercentage) }}%
              </span>
            </div>
          </div>
        </div>
        
        <!-- 空仓收益 -->
        <div class="profit-card" :class="{'profit': totalShortProfit > 0, 'loss': totalShortProfit < 0}">
          <div class="profit-header">空仓收益详情</div>
          <div class="profit-details">
            <div class="profit-detail-item">
              <span class="detail-label">总仓价值:</span>
              <span class="detail-value">{{ formatTotalValue(shortTotalValue) }}</span>
            </div>
            <div class="profit-detail-item">
              <span class="detail-label">建仓本金(合计):</span>
              <span class="detail-value">{{ formatTotalValue(totalInitialValue) }}</span>
            </div>
            <div class="profit-detail-item highlight">
              <span class="detail-label">未实现盈亏:</span>
              <span class="detail-value" :class="totalShortProfit >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfit(totalShortProfit) }}
              </span>
            </div>
            <div class="profit-detail-item highlight">
              <span class="detail-label">收益率:</span>
              <span class="detail-value" :class="shortProfitPercentage >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfitPercentage(shortProfitPercentage) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 多空仓位监控 -->
    <div class="position-monitor-section" v-if="hasPositions">
      <div class="section-title">仓位监控</div>
      <div class="cards-container">
        <!-- 多仓监控 -->
        <div class="monitor-card" v-if="longPositionsSummary.count > 0">
          <div class="card-header">
            <span class="position-type long">多仓({{ longPositionsSummary.count }})</span>
            <span class="profit-status" :class="longPositionsSummary.profitCount > 0 ? 'profit' : 'loss'">
              盈利: {{ longPositionsSummary.profitCount }}/{{ longPositionsSummary.count }}
            </span>
          </div>
          <div class="price-info">
            <div class="price-row">
              <span class="price-label">最高入场价</span>
              <span class="price-value">{{ longPositionsSummary.highestEntry }}</span>
            </div>
            <div class="price-row">
              <span class="price-label">当前标记价</span>
              <span class="price-value" :class="{'higher': longPositionsSummary.markHigherThanHighest, 'lower': !longPositionsSummary.markHigherThanHighest}">
                {{ longPositionsSummary.markPrice }}
                <i class="price-arrow" v-if="longPositionsSummary.markHigherThanHighest">↑</i>
                <i class="price-arrow" v-else>↓</i>
              </span>
            </div>
            <div class="price-row">
              <span class="price-label">多头收益率</span>
              <span class="price-value" :class="longProfitPercentage >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfitPercentage(longProfitPercentage) }}%
                <span v-if="longProfitPercentage >= targetProfitPercentage" class="threshold-indicator">(达标)</span>
              </span>
            </div>
          </div>
          <div class="action-buttons" v-if="autoCloseEnabled && longProfitPercentage >= targetProfitPercentage">            
            <el-button size="small" type="success" @click="handleAutoClosePositions('LONG')">              
              平多仓 ({{ formatTotalProfitPercentage(longProfitPercentage) }}% ≥ {{ targetProfitPercentage.toFixed(2) }}%)
            </el-button>          
          </div>
        </div>
        
        <!-- 空仓监控 -->
        <div class="monitor-card" v-if="shortPositionsSummary.count > 0">
          <div class="card-header">
            <span class="position-type short">空仓({{ shortPositionsSummary.count }})</span>
            <span class="profit-status" :class="shortPositionsSummary.profitCount > 0 ? 'profit' : 'loss'">
              盈利: {{ shortPositionsSummary.profitCount }}/{{ shortPositionsSummary.count }}
            </span>
          </div>
          <div class="price-info">
            <div class="price-row">
              <span class="price-label">最低入场价</span>
              <span class="price-value">{{ shortPositionsSummary.lowestEntry }}</span>
            </div>
            <div class="price-row">
              <span class="price-label">当前标记价</span>
              <span class="price-value" :class="{'higher': !shortPositionsSummary.markLowerThanLowest, 'lower': shortPositionsSummary.markLowerThanLowest}">
                {{ shortPositionsSummary.markPrice }}
                <i class="price-arrow" v-if="!shortPositionsSummary.markLowerThanLowest">↑</i>
                <i class="price-arrow" v-else>↓</i>
              </span>
            </div>
            <div class="price-row">
              <span class="price-label">空头收益率</span>
              <span class="price-value" :class="shortProfitPercentage >= 0 ? 'positive' : 'negative'">
                {{ formatTotalProfitPercentage(shortProfitPercentage) }}%
                <span v-if="shortProfitPercentage >= targetProfitPercentage" class="threshold-indicator">(达标)</span>
              </span>
            </div>
          </div>
          <div class="action-buttons" v-if="autoCloseEnabled && shortProfitPercentage >= targetProfitPercentage">            
            <el-button size="small" type="danger" @click="handleAutoClosePositions('SHORT')">              
              平空仓 ({{ formatTotalProfitPercentage(shortProfitPercentage) }}% ≥ {{ targetProfitPercentage.toFixed(2) }}%)
            </el-button>          
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
import axios from 'axios';
import { getCurrentUser } from '@/services/auth';
import { parseApiResult } from '@/utils/apiHelper';
import { QuestionFilled, Check } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

export default {
  name: 'MarkPriceDisplay',
  components: {
    QuestionFilled,
    Check
  },
  props: {
    positions: {
      type: Array,
      default: () => []
    },
    contractType: { // 添加合约类型属性
      type: String,
      default: 'UM'  // 默认为U本位合约
    },
    autoRefresh: { // 添加自动刷新开关属性
      type: Boolean,
      default: false
    },
    refreshInterval: { // 添加刷新间隔属性
      type: Number,
      default: 5000 // 默认5秒
    }
  },
  emits: ['auto-close-positions', 'refresh-mark-prices', 'system-message', 'request-positions-refresh'],
  setup(props, { emit }) {
    // 存储每个交易对的标记价
    const markPrices = ref({});
    // 存储API获取的最新标记价格
    const apiMarkPrices = ref({});
    // 自动平仓开关
    const autoCloseEnabled = ref(false);
    console.log('MarkPriceDisplay组件初始化，自动平仓状态:', autoCloseEnabled.value ? '已开启' : '已关闭');
    
    // 自动平仓处理锁，防止重复操作
    const isProcessingAutoClose = ref(false);
    
    // 消息处理相关
    const showMessageDialog = ref(false);
    const processingMessages = ref([]);
    
    // 处理消息窗口关闭
    const handleCloseMessageDialog = () => {
      showMessageDialog.value = false;
    };
    
    // 自动平仓设置
    const closeMode = ref('profit_percentage'); // 只使用profit_percentage模式
    const targetProfitPercentage = ref(5.00); // 默认目标收益率5.00%
    
    // 编辑状态和临时值
    const isEditing = ref(false);
    const tempTargetProfitPercentage = ref(5.00);
    
    // 当前正在查询的交易对列表
    const currentSymbols = ref([]);
    
    // 多空仓位统计
    const longPositionsSummary = ref({
      count: 0,
      profitCount: 0,
      highestEntry: 0,
      markPrice: 0,
      markHigherThanHighest: false,
      allProfit: false,
      symbol: ''
    });
    
    const shortPositionsSummary = ref({
      count: 0,
      profitCount: 0,
      lowestEntry: 0,
      markPrice: 0,
      markLowerThanLowest: false,
      allProfit: false,
      symbol: ''
    });
    
    // 多空总收益
    const totalLongProfit = ref(0);
    const totalShortProfit = ref(0);
    const longProfitPercentage = ref(0);
    const shortProfitPercentage = ref(0);
    
    // 添加总仓价值和建仓本金变量
    const longTotalValue = ref(0);
    const longInitialValue = ref(0);
    const shortTotalValue = ref(0);
    const shortInitialValue = ref(0);
    const totalPositionValue = ref(0); // 新增：总仓价值（多空合计）
    const totalInitialValue = ref(0);  // 新增：总建仓本金（多空合计）
    const totalProfit = ref(0);        // 新增：总盈亏（多空合计）
    const totalProfitPercentage = ref(0); // 新增：总收益率
    
    // 上次盈利状态，用于检测状态变化
    const lastLongProfitStatus = ref(false);
    const lastShortProfitStatus = ref(false);
    
    // 是否有仓位
    const hasPositions = computed(() => {
      return props.positions && props.positions.length > 0;
    });
    
    // 格式化总收益
    const formatTotalProfit = (value) => {
      return value.toFixed(2);
    };
    
    // 格式化收益率
    const formatTotalProfitPercentage = (value) => {
      return value.toFixed(2);
    };
    
    // 格式化总仓价值和建仓本金
    const formatTotalValue = (value) => {
      return Math.abs(value).toFixed(2);
    };
    
    // 自动平仓处理函数
    const handleAutoClosePositions = (positionSide) => {
      // 根据仓位方向构建不同的参数
      const isLong = positionSide === 'LONG';
      const positionsToClose = isLong 
        ? props.positions.filter(p => parseFloat(p.positionAmt) > 0)
        : props.positions.filter(p => parseFloat(p.positionAmt) < 0);
      
      // 按子账号和交易对分组
      const positionGroups = {};
      positionsToClose.forEach(pos => {
        const key = `${pos.email}_${pos.symbol}`;
        if (!positionGroups[key]) {
          positionGroups[key] = [];
        }
        positionGroups[key].push(pos);
      });
      
      // 使用组件内部处理函数执行自动平仓
      processAutoClose({
        positionSide,
        positionGroups,
        isLong,
        trigger: 'manual_button',
        profitPercentage: isLong ? longProfitPercentage.value : shortProfitPercentage.value
      });
    };
    
    // 从后端API获取标记价格
    const fetchMarkPrices = async (symbols) => {
      try {
        if (!symbols || symbols.length === 0) {
          console.log('没有交易对需要查询标记价格');
          return;
        }
        
        // 保存当前查询的交易对列表，以便后续刷新使用
        currentSymbols.value = [...symbols];
        
        const user = getCurrentUser();
        if (!user || !user.token) {
          console.error('获取标记价格失败：未登录或token无效');
          return;
        }
        
        // 按合约类型选择不同接口
        const endpoint = props.contractType === 'UM' ? '/fapi/v1/ticker/price' : '/dapi/v1/ticker/price';
        
        console.log(`批量获取${symbols.length}个交易对的标记价格`);
        
        // 创建针对每个交易对的查询参数
        const queryPromises = symbols.map(async (symbol) => {
          try {
            const response = await axios.post('/api/binance/query', {
              endpoint: endpoint,
              method: 'GET',
              params: { symbol } // 添加symbol参数，只查询特定交易对
            }, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              }
            });
            
            const result = parseApiResult(response);
            if (result.success && result.data) {
              return { symbol, price: result.data.price };
            }
            return null;
          } catch (error) {
            console.error(`获取${symbol}价格出错:`, error);
            return null;
          }
        });
        
        // 并行执行所有查询
        const results = await Promise.all(queryPromises);
        
        // 处理结果
        const allPrices = {};
        results.filter(result => result !== null).forEach(result => {
          allPrices[result.symbol] = result.price;
        });
        
        console.log(`成功获取了${Object.keys(allPrices).length}个交易对的价格数据`);
        
        // 更新API获取的标记价格
        apiMarkPrices.value = { ...apiMarkPrices.value, ...allPrices };
        
        // 如果是币本位合约(CM)，需要获取标记价格(markPrice)
        if (props.contractType === 'CM') {
          // 获取标记价格需要单独调用premiumIndex接口
          await fetchCoinMarginMarkPrices(symbols);
        } else {
          // U本位合约可以直接使用价格作为标记价格
          updateFromPositions();
          
          // 无论是否传入immediateCheck参数，只要开启了自动平仓功能就检查
          if (autoCloseEnabled.value && !isProcessingAutoClose.value) {
            console.log("收益率变化检查 - 价格更新触发");
            
            // 检查多头收益率是否满足条件
            const longPositions = props.positions.filter(p => parseFloat(p.positionAmt) > 0);
            if (longPositions.length > 0 && longProfitPercentage.value >= targetProfitPercentage.value) {
              console.log(`检测到多头收益率(${longProfitPercentage.value.toFixed(2)}%)已达到或超过目标(${targetProfitPercentage.value.toFixed(2)}%)`);
              
              // 直接使用组件内部的处理函数
              processAutoClose({
                positionSide: 'LONG',
                positionGroups: groupPositionsByAccount(longPositions),
                isLong: true,
                trigger: 'price_update',
                profitPercentage: longProfitPercentage.value
              });
              
              // 不同时触发两个方向的平仓，避免并发问题
              return;
            }
            
            // 检查空头收益率是否满足条件
            const shortPositions = props.positions.filter(p => parseFloat(p.positionAmt) < 0);
            if (shortPositions.length > 0 && shortProfitPercentage.value >= targetProfitPercentage.value) {
              console.log(`检测到空头收益率(${shortProfitPercentage.value.toFixed(2)}%)已达到或超过目标(${targetProfitPercentage.value.toFixed(2)}%)`);
              
              // 直接使用组件内部的处理函数
              processAutoClose({
                positionSide: 'SHORT',
                positionGroups: groupPositionsByAccount(shortPositions),
                isLong: false,
                trigger: 'price_update',
                profitPercentage: shortProfitPercentage.value
              });
            }
          }
        }
      } catch (error) {
        console.error('标记价格处理出错:', error);
      }
    };
    
    // 币本位合约需要单独获取标记价格
    const fetchCoinMarginMarkPrices = async (symbols) => {
      if (!symbols || symbols.length === 0) return;
      
      const user = getCurrentUser();
      if (!user || !user.token) return;
      
      try {
        // 币本位合约使用/dapi/v1/premiumIndex接口
        const endpoint = '/dapi/v1/premiumIndex';
        
        // 创建针对每个交易对的查询参数
        const queryPromises = symbols.map(async (symbol) => {
          try {
            const response = await axios.post('/api/binance/query', {
              endpoint: endpoint,
              method: 'GET',
              params: { symbol } // 添加symbol参数，只查询特定交易对
            }, {
              headers: {
                'Authorization': `Bearer ${user.token}`
              }
            });
            
            const result = parseApiResult(response);
            if (result.success && result.data) {
              return { symbol, markPrice: result.data.markPrice };
            }
            return null;
          } catch (error) {
            console.error(`获取${symbol}标记价格出错:`, error);
            return null;
          }
        });
        
        // 并行执行所有查询
        const results = await Promise.all(queryPromises);
        
        // 处理结果
        const markPricesMap = {};
        results.filter(result => result !== null).forEach(result => {
          markPricesMap[result.symbol] = result.markPrice;
        });
        
        console.log(`成功获取了${Object.keys(markPricesMap).length}个币本位交易对的标记价格`);
        
        // 更新API获取的标记价格
        apiMarkPrices.value = { ...apiMarkPrices.value, ...markPricesMap };
        
        // 更新持仓统计
        updateFromPositions();
      } catch (error) {
        console.error('获取币本位标记价格出错:', error);
      }
    };
    
    // 计算标记价 - 优先使用API获取的价格，其次使用持仓数据计算
    const calculateMarkPrice = (position) => {
      const symbol = position.symbol;
      
      // 优先使用API获取的标记价格
      if (apiMarkPrices.value[symbol]) {
        return apiMarkPrices.value[symbol];
      }
      
      // 后备：使用持仓数据计算
      if (position.notional && position.positionAmt && position.positionAmt !== "0") {
        return Math.abs(Number(position.notional) / Number(position.positionAmt)).toFixed(7);
      }
      
      // 再后备：使用breakEvenPrice或entryPrice
      return position.breakEvenPrice || position.entryPrice || "未知";
    };

    // 从持仓数据更新标记价
    const updateFromPositions = () => {
      if (!props.positions || props.positions.length === 0) return;
      
      const prices = {};
      
      // 先使用现有数据
      props.positions.forEach(position => {
        const symbol = position.symbol;
        const price = calculateMarkPrice(position);
        prices[symbol] = price;
      });
      
      markPrices.value = prices;
      
      // 更新多空仓位统计
      updatePositionsSummary();
      
      // 计算多空总收益
      calculateTotalProfits();
      
      // 仅保留手动状态，不再自动触发平仓
      lastLongProfitStatus.value = longPositionsSummary.value.allProfit;
      lastShortProfitStatus.value = shortPositionsSummary.value.allProfit;
      
      // 当updateFromPositions由位置数据变化触发时，不再单独调用fetchMarkPrices
      // 让自动刷新定时器来控制API请求的频率
    };
    
    // 计算多空总收益
    const calculateTotalProfits = () => {
      // 过滤多仓和空仓
      const longPositions = props.positions.filter(p => parseFloat(p.positionAmt) > 0);
      const shortPositions = props.positions.filter(p => parseFloat(p.positionAmt) < 0);
      
      // 计算多仓总收益
      let longProfit = 0;
      let longMarginValue = 0;
      let longTotal = 0;
      let longInitial = 0;
      
      longPositions.forEach(position => {
        // 获取必要的值
        const symbol = position.symbol;
        const positionAmt = parseFloat(position.positionAmt || 0);
        const entryPrice = parseFloat(position.entryPrice || 0);
        const breakEvenPrice = parseFloat(position.breakEvenPrice || position.entryPrice || 0);
        const leverage = parseFloat(position.leverage || 1); // 获取杠杆倍数，默认为1
        
        // 获取当前标记价格
        const currentMarkPrice = parseFloat(apiMarkPrices.value[symbol] || markPrices.value[symbol] || entryPrice);
        
        // 计算当前持仓总价值（按照标记价计算）
        const currentValue = positionAmt * currentMarkPrice;
        longTotal += currentValue;
        
        // 计算按盈亏平衡价格计算的初始价值
        const initialValue = positionAmt * breakEvenPrice;
        longInitial += initialValue;
        
        // 计算该持仓的未实现盈亏（标记价 - 盈亏平衡价）
        const pnl = positionAmt * (currentMarkPrice - breakEvenPrice);
        longProfit += pnl;
        
        // 计算保证金价值用于计算收益率
        const marginValue = Math.abs(entryPrice * positionAmt) / leverage;
        longMarginValue += marginValue;
      });
      
      // 计算空仓总收益
      let shortProfit = 0;
      let shortMarginValue = 0;
      let shortTotal = 0;
      let shortInitial = 0;
      
      shortPositions.forEach(position => {
        // 获取必要的值
        const symbol = position.symbol;
        const positionAmt = parseFloat(position.positionAmt || 0); // 空仓为负值
        const entryPrice = parseFloat(position.entryPrice || 0);
        const breakEvenPrice = parseFloat(position.breakEvenPrice || position.entryPrice || 0);
        const leverage = parseFloat(position.leverage || 1);
        
        // 获取当前标记价格
        const currentMarkPrice = parseFloat(apiMarkPrices.value[symbol] || markPrices.value[symbol] || entryPrice);
        
        // 计算当前持仓总价值（按照标记价计算）
        // 对于空仓，总价值是负值，但我们需要其绝对值进行显示
        const currentValue = Math.abs(positionAmt * currentMarkPrice); 
        shortTotal += currentValue;
        
        // 计算按盈亏平衡价格计算的初始价值（同样取绝对值）
        const initialValue = Math.abs(positionAmt * breakEvenPrice);
        shortInitial += initialValue;
        
        // 计算该持仓的未实现盈亏（空仓：标记价下跌=盈利）
        // 注意：positionAmt为负值，保持正确的盈亏方向
        const pnl = positionAmt * (currentMarkPrice - breakEvenPrice);
        shortProfit += pnl;
        
        // 计算保证金价值用于计算收益率
        const marginValue = Math.abs(entryPrice * positionAmt) / leverage;
        shortMarginValue += marginValue;
      });
      
      // 计算总仓位汇总信息
      const combinedProfit = longProfit + shortProfit;
      // 删除未使用的变量 combinedMarginValue
      const combinedInitialValue = longInitial + shortInitial;
      
      // 保存旧的收益率值用于检测变化
      const oldLongProfitPercentage = longProfitPercentage.value;
      const oldShortProfitPercentage = shortProfitPercentage.value;
      
      // 更新多空总收益
      totalLongProfit.value = longProfit;
      totalShortProfit.value = shortProfit;
      totalProfit.value = combinedProfit;
      
      // 更新总仓价值和建仓本金
      longTotalValue.value = longTotal;
      longInitialValue.value = longInitial;
      shortTotalValue.value = shortTotal;
      shortInitialValue.value = shortInitial;
      totalPositionValue.value = longTotal + shortTotal;
      totalInitialValue.value = combinedInitialValue;
      
      // 计算多空收益率，避免除以0的情况
      const denominator = combinedInitialValue || 1; // 防止除以零，使用1作为默认值
      
      // 计算多空收益率（使用总建仓本金计算收益率）
      longProfitPercentage.value = (longProfit / denominator) * 100;
      shortProfitPercentage.value = (shortProfit / denominator) * 100;
      totalProfitPercentage.value = (combinedProfit / denominator) * 100;
      
      console.log('收益计算详情:', {
        多仓总价值: longTotal.toFixed(2),
        多仓初始价值: longInitial.toFixed(2),
        多仓未实现盈亏: longProfit.toFixed(2),
        多仓收益率: longProfitPercentage.value.toFixed(4) + '%',
        多仓保证金价值: longMarginValue.toFixed(2),
        空仓总价值: shortTotal.toFixed(2),
        空仓初始价值: shortInitial.toFixed(2),
        空仓未实现盈亏: shortProfit.toFixed(2),
        空仓收益率: shortProfitPercentage.value.toFixed(4) + '%',
        空仓保证金价值: shortMarginValue.toFixed(2),
        总仓位价值: totalPositionValue.value.toFixed(2),
        总建仓本金: totalInitialValue.value.toFixed(2),
        总盈亏: totalProfit.value.toFixed(2),
        总收益率: totalProfitPercentage.value.toFixed(4) + '%'
      });
      
      // 检查收益率变化是否达到或超过目标值
      if (longPositions.length > 0) {
        checkProfitThresholdReached(oldLongProfitPercentage, longProfitPercentage.value, 'LONG');
      }
      
      if (shortPositions.length > 0) {
        checkProfitThresholdReached(oldShortProfitPercentage, shortProfitPercentage.value, 'SHORT');
      }
    };
    
    // 新增：检查收益率是否已达到或超过目标值
    const checkProfitThresholdReached = (oldPercentage, newPercentage, positionSide) => {
      // 如果自动平仓功能未开启，则不检查
      if (!autoCloseEnabled.value) return;
      
      // 如果正在处理自动平仓，则不重复触发
      if (isProcessingAutoClose.value) return;
      
      // 创建一个微小的容差，增大容差值以解决浮点数比较问题
      const tolerance = 0.001;
      const targetWithTolerance = targetProfitPercentage.value - tolerance;
      
      // 使用容差比较收益率
      const isNowAboveThreshold = newPercentage >= targetWithTolerance;
      
      console.log(`收益率检查(${positionSide}): 旧值=${oldPercentage.toFixed(4)}%, 新值=${newPercentage.toFixed(4)}%, 目标=${targetProfitPercentage.value.toFixed(4)}%, 容差后目标=${targetWithTolerance.toFixed(4)}%`);
      
      // 如果新的收益率达到或超过目标值（考虑容差），则触发事件，无需检查旧值
      if (isNowAboveThreshold) {
        console.log(`${positionSide === 'LONG' ? '多头' : '空头'}收益率已达到目标阈值！新值=${newPercentage.toFixed(4)}%, 目标=${targetProfitPercentage.value.toFixed(4)}%`);
        
        // 过滤相应方向的持仓
        const positions = props.positions.filter(p => 
          positionSide === 'LONG' ? parseFloat(p.positionAmt) > 0 : parseFloat(p.positionAmt) < 0
        );
        
        // 只有当存在对应方向的持仓时才触发事件
        if (positions.length > 0) {
          // 使用内部处理函数执行自动平仓
          console.log(`触发自动平仓：方向=${positionSide}, 持仓数量=${positions.length}`);
          
          processAutoClose({
            positionSide,
            positionGroups: groupPositionsByAccount(positions),
            isLong: positionSide === 'LONG',
            trigger: 'threshold_reached',
            profitPercentage: newPercentage
          });
        }
      }
    };
    
    // 按子账号和交易对分组持仓
    const groupPositionsByAccount = (positions) => {
      const groups = {};
      positions.forEach(pos => {
        const key = `${pos.email}_${pos.symbol}`;
        if (!groups[key]) {
          groups[key] = [];
        }
        groups[key].push(pos);
      });
      return groups;
    };
    
    // 更新多空仓位统计
    const updatePositionsSummary = () => {
      // 过滤多仓和空仓
      const longPositions = props.positions.filter(p => parseFloat(p.positionAmt) > 0);
      const shortPositions = props.positions.filter(p => parseFloat(p.positionAmt) < 0);
      
      // 添加详细日志
      console.log(`更新持仓统计：多头持仓 ${longPositions.length} 个，空头持仓 ${shortPositions.length} 个，目标收益率 ${targetProfitPercentage.value.toFixed(2)}%`);
      
      // 按交易对分组
      const groupBySymbol = (positions) => {
        const groups = {};
        positions.forEach(position => {
          const symbol = position.symbol;
          if (!groups[symbol]) {
            groups[symbol] = [];
          }
          groups[symbol].push(position);
        });
        return groups;
      };
      
      const longGroups = groupBySymbol(longPositions);
      const shortGroups = groupBySymbol(shortPositions);
      
      // 计算多仓盈利数量
      const longProfitCount = longPositions.filter(p => parseFloat(p.unrealizedProfit || 0) > 0).length;
      
      // 处理多仓统计 - 只处理有持仓的第一个交易对
      if (longPositions.length > 0) {
        const firstSymbol = Object.keys(longGroups)[0];
        const symbolLongPositions = longGroups[firstSymbol];
        // 找到最高入场价格
        let highestEntry = 0;
        symbolLongPositions.forEach(position => {
          const entryPrice = parseFloat(position.entryPrice);
          if (entryPrice > highestEntry) {
            highestEntry = entryPrice;
          }
        });
        // 优先使用API获取的标记价格
        let currentMarkPrice = parseFloat(apiMarkPrices.value[firstSymbol] || markPrices.value[firstSymbol] || 0);
        const markHigherThanHighest = currentMarkPrice > highestEntry;
        
        // 只使用收益率判断是否需要平仓，添加0.001的容差
        const targetProfitWithTolerance = targetProfitPercentage.value - 0.001;
        const shouldAutoClose = longProfitPercentage.value >= targetProfitWithTolerance;
        
        console.log(`多头收益率检查: 当前=${longProfitPercentage.value.toFixed(2)}%, 目标=${targetProfitPercentage.value.toFixed(2)}%, 是否达标=${shouldAutoClose}`);
        
        longPositionsSummary.value = {
          count: longPositions.length,
          profitCount: longProfitCount,
          highestEntry: highestEntry.toFixed(7),
          markPrice: currentMarkPrice.toFixed(7),
          markHigherThanHighest,
          allProfit: shouldAutoClose,
          symbol: firstSymbol
        };
      } else {
        longPositionsSummary.value = {
          count: 0,
          profitCount: 0,
          highestEntry: 0,
          markPrice: 0,
          markHigherThanHighest: false,
          allProfit: false,
          symbol: ''
        };
      }
      
      // 计算空仓盈利数量
      const shortProfitCount = shortPositions.filter(p => parseFloat(p.unrealizedProfit || 0) > 0).length;
      
      // 处理空仓统计
      if (shortPositions.length > 0) {
        const firstSymbol = Object.keys(shortGroups)[0];
        const symbolShortPositions = shortGroups[firstSymbol];
        // 找到最低入场价格
        let lowestEntry = Number.MAX_VALUE;
        symbolShortPositions.forEach(position => {
          const entryPrice = parseFloat(position.entryPrice);
          if (entryPrice < lowestEntry) {
            lowestEntry = entryPrice;
          }
        });
        // 优先使用API获取的标记价格
        let currentMarkPrice = parseFloat(apiMarkPrices.value[firstSymbol] || markPrices.value[firstSymbol] || 0);
        const markLowerThanLowest = currentMarkPrice < lowestEntry;
        
        // 只使用收益率判断是否需要平仓，添加0.001的容差
        const targetProfitWithTolerance = targetProfitPercentage.value - 0.001;
        const shouldAutoClose = shortProfitPercentage.value >= targetProfitWithTolerance;
        
        console.log(`空头收益率检查: 当前=${shortProfitPercentage.value.toFixed(2)}%, 目标=${targetProfitPercentage.value.toFixed(2)}%, 是否达标=${shouldAutoClose}`);
        
        shortPositionsSummary.value = {
          count: shortPositions.length,
          profitCount: shortProfitCount,
          lowestEntry: lowestEntry.toFixed(7),
          markPrice: currentMarkPrice.toFixed(7),
          markLowerThanLowest,
          allProfit: shouldAutoClose,
          symbol: firstSymbol
        };
      } else {
        shortPositionsSummary.value = {
          count: 0,
          profitCount: 0,
          lowestEntry: 0,
          markPrice: 0,
          markLowerThanLowest: false,
          allProfit: false,
          symbol: ''
        };
      }
    };

    // 监听持仓变化
    watch(() => props.positions, () => {
      updateFromPositions();
      
      // 收集交易对，但不再启动定时器
      if (props.positions && props.positions.length > 0) {
        const symbols = [...new Set(props.positions.map(p => p.symbol))];
        currentSymbols.value = symbols;
        // 更新一次标记价格
        fetchMarkPrices(symbols);
      }
    }, { deep: true, immediate: true });
    
    // 监听合约类型变化
    watch(() => props.contractType, () => {
      // 合约类型变化时，重新获取标记价格
      if (props.positions && props.positions.length > 0) {
        const symbols = [...new Set(props.positions.map(p => p.symbol))];
        fetchMarkPrices(symbols);
      }
    });
    
    // 只监听目标收益率变化
    watch(targetProfitPercentage, () => {
      // 当目标收益率变化时，重新计算是否需要平仓
      updatePositionsSummary();
    });
    
    // 监听自动平仓开关状态变化
    watch(autoCloseEnabled, (newValue) => {
      console.log('自动平仓开关状态已变更为:', newValue ? '已开启' : '已关闭');
    });
    
    // 组件挂载时，初始化获取标记价格
    onMounted(() => {
      if (props.positions && props.positions.length > 0) {
        const symbols = [...new Set(props.positions.map(p => p.symbol))];
        fetchMarkPrices(symbols);
      }
    });
    
    // 开始编辑
    const startEdit = () => {
      // 复制当前值到临时变量
      tempTargetProfitPercentage.value = targetProfitPercentage.value;
      isEditing.value = true;
    };
    
    // 保存设置
    const saveSettings = () => {
      // 只保存收益率设置
      targetProfitPercentage.value = tempTargetProfitPercentage.value;
      isEditing.value = false;
      
      // 保存设置后重新计算是否需要平仓
      updatePositionsSummary();
    };
    
    // 取消编辑
    const cancelEdit = () => {
      isEditing.value = false;
    };

    // 公开刷新标记价格的方法，供父组件调用
    const refreshMarkPrices = async (immediateCheck = false) => {
      try {
        // 使用已保存的交易对列表刷新价格
        if (currentSymbols.value.length > 0) {
          console.log(`刷新标记价格，${immediateCheck ? '将立即检查收益率' : '使用正常流程检查'}`);
          await fetchMarkPrices(currentSymbols.value, immediateCheck);
          // 通知父组件标记价格已更新
          emit('refresh-mark-prices');
          return true;
        } else {
          console.log('没有可刷新的交易对列表');
          return false;
        }
      } catch (error) {
        console.error('刷新标记价格出错:', error);
        return false;
      }
    };

    // 添加处理消息，同时向父组件发送
    const addProcessingMessage = (type, title, description) => {
      const message = {
        type, // success, warning, info, error
        title,
        description,
        time: new Date().toLocaleTimeString()
      };
      
      // 保存消息到本地数组
      processingMessages.value.push(message);
      
      // 显示消息对话框
      showMessageDialog.value = true;
      
      // 向父组件发送消息
      emit('system-message', message);
    };
    
    // 执行平仓和资金归集操作
    const executeCloseAndCollection = async (email, symbol, positionSide, skipCollection = false) => {
      // 记录平仓信息
      console.log(`为子账号${email}执行${positionSide === 'LONG' ? '多' : '空'}仓平仓和资金归集操作，交易对: ${symbol}${skipCollection ? '，不执行归集' : ''}`);
      
      try {
        // 获取用户token
        const user = getCurrentUser();
        if (!user || !user.token) {
          return { success: false, error: '用户未登录或token无效' };
        }
        
        const token = user.token;
        
        // 步骤1: 执行平仓操作
        const closeResult = await axios.post(
          '/api/subaccounts/portfolio-margin/close-position',
          { 
            email: email,
            symbol: symbol,
            positionSide: positionSide,
            percentage: 100 // 全部平仓
          },
          { 
            headers: { 'Authorization': `Bearer ${token}` },
            timeout: 30000 // 30秒超时
          }
        );
        
        const closeData = parseApiResult(closeResult);
        
        if (!closeData.success) {
          // 检查是否是持仓模式不匹配的错误
          if (closeData.error && closeData.error.indexOf("position side does not match") !== -1) {
            // 尝试切换positionSide再重试一次
            const newPositionSide = positionSide === 'BOTH' ? 
                                 (positionSide === 'LONG' ? 'LONG' : 'SHORT') : 
                                 'BOTH';
                                 
            // 重新发送请求
            const retryResponse = await axios.post(
              '/api/subaccounts/portfolio-margin/close-position', 
              {
                email: email,
                symbol: symbol,
                positionSide: newPositionSide,
                percentage: 100 // 全部平仓
              }, 
              {
                headers: { 'Authorization': `Bearer ${token}` },
                timeout: 30000 // 30秒超时
              }
            );
            
            const retryData = parseApiResult(retryResponse);
            if (!retryData.success) {
              console.error(`子账号${email}平仓失败(重试后):`, retryData.error);
              return { success: false, error: retryData.error };
            }
            
            console.log(`子账号${email}平仓成功(重试后):`, retryData.data);
          } else {
            console.error(`子账号${email}平仓失败:`, closeData.error);
            return { success: false, error: closeData.error };
          }
        } else {
          console.log(`子账号${email}平仓成功:`, closeData.data);
        }
        
        // 如果设置了跳过资金归集，则直接返回成功
        if (skipCollection) {
          return { success: true, collectionSkipped: true };
        }
        
        // 步骤2: 执行资金归集
        try {
          const collectionResult = await axios.post(
            '/api/portfolio/papi/v1/auto-collection',
            { email },
            { 
              headers: { 'Authorization': `Bearer ${token}` },
              timeout: 30000 // 30秒超时
            }
          );
          
          const collectionData = parseApiResult(collectionResult);
          
          if (!collectionData.success) {
            console.error(`子账号${email}资金归集失败:`, collectionData.error);
            return {
              success: true, // 平仓操作成功
              collectionSuccess: false,
              collectionError: collectionData.error
            };
          }
          
          console.log(`子账号${email}资金归集成功:`, collectionData.data);
          return { success: true, collectionSuccess: true };
        } catch (error) {
          console.error(`子账号${email}资金归集异常:`, error);
          return {
            success: true, // 平仓操作成功
            collectionSuccess: false,
            collectionError: error.message || '未知错误'
          };
        }
      } catch (error) {
        console.error(`处理子账号${email}的平仓操作异常:`, error);
        return { success: false, error: error.message || '未知错误' };
      }
    };
    
    // 处理自动平仓
    const processAutoClose = async (data) => {
      const { positionSide, positionGroups, isLong, trigger } = data;
      
      // 如果已有平仓操作在进行中，则跳过
      if (isProcessingAutoClose.value) {
        console.log(`已有自动平仓操作进行中，忽略此次请求。触发方式: ${trigger || '未知'}`);
        return;
      }
      
      try {
        console.log(`收益率已达标，开始自动平仓: 方向=${positionSide}, 触发方式=${trigger || '未知'}, 收益率=${data.profitPercentage?.toFixed(2)}%`);
        
        if (!positionGroups || Object.keys(positionGroups).length === 0) {
          ElMessage.warning('没有找到符合条件的仓位');
          return;
        }
        
        // 设置标志，防止重复处理
        isProcessingAutoClose.value = true;
        console.log('设置isProcessingAutoClose=true，防止重复处理');
        
        // 提示用户正在自动处理
        ElMessage.info(`正在自动处理${isLong ? '多' : '空'}仓平仓和资金归集，请稍候...`);
        
        // 记录操作日志
        addProcessingMessage(
          'info',
          `开始自动平仓操作`,
          `方向: ${isLong ? '多仓' : '空仓'}, 共${Object.keys(positionGroups).length}个子账号持仓`
        );
        
        // 获取用户token
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          isProcessingAutoClose.value = false;
          return;
        }

        try {
          // 创建平仓任务数组，实现异步并行
          const closePositionTasks = [];
          
          // 为每个需要平仓的持仓创建异步任务
          for (const key in positionGroups) {
            const positions = positionGroups[key];
            if (!positions || positions.length === 0) continue;
            
            // 一组持仓共享同一个邮箱和交易对
            const position = positions[0];
            const email = position.email;
            const symbol = position.symbol;
            
            // 创建任务函数并立即添加到数组
            closePositionTasks.push(
              executeCloseAndCollection(email, symbol, positionSide)
                .then(result => {
                  if (!result.success) {
                    addProcessingMessage(
                      'error',
                      `平仓失败`,
                      `子账号: ${email}, 交易对: ${symbol}, 错误: ${result.error}`
                    );
                    return { success: false, email, symbol, error: result.error };
                  }
                  
                  addProcessingMessage(
                    'success',
                    `平仓成功`,
                    `子账号: ${email}, 交易对: ${symbol}, 方向: ${isLong ? '多仓' : '空仓'}`
                  );
                  
                  if (!result.collectionSuccess) {
                    addProcessingMessage(
                      'warning',
                      `资金归集失败`,
                      `子账号: ${email}, 错误: ${result.collectionError}`
                    );
                  } else {
                    addProcessingMessage(
                      'success',
                      `资金归集成功`,
                      `子账号: ${email}`
                    );
                  }
                  
                  return { 
                    success: true, 
                    email, 
                    symbol, 
                    collectionSuccess: result.collectionSuccess 
                  };
                })
                .catch(error => {
                  console.error(`处理子账号 ${email} 平仓和归集时出错:`, error);
                  addProcessingMessage(
                    'error',
                    `处理异常`,
                    `子账号: ${email}, 交易对: ${symbol}, 错误: ${error.message || '未知错误'}`
                  );
                  return { success: false, email, symbol, error: error.message };
                })
            );
          }
          
          // 并行执行所有平仓和归集任务
          const results = await Promise.all(closePositionTasks);
          
          // 计算成功和失败数量
          const successCount = results.filter(r => r.success).length;
          const failCount = results.filter(r => !r.success).length;
          
          // 记录总结信息
          addProcessingMessage(
            successCount > 0 ? 'success' : 'warning',
            `第一轮操作完成`,
            `成功平仓并归集: ${successCount}个, 失败: ${failCount}个`
          );
          
          // 如果有成功的平仓和归集，立即检查并平掉反向持仓
          if (successCount > 0) {
            // 查找反向持仓
            const oppositePositions = props.positions.filter(p => {
              return isLong 
                ? parseFloat(p.positionAmt) < 0 // 如果刚平了多仓，现在找空仓
                : parseFloat(p.positionAmt) > 0; // 如果刚平了空仓，现在找多仓
            });
            
            if (oppositePositions.length > 0) {
              const oppositePositionSide = isLong ? 'SHORT' : 'LONG';
              addProcessingMessage(
                'info',
                `发现反向持仓`,
                `存在${oppositePositions.length}个${!isLong ? '多' : '空'}头持仓，准备处理`
              );
              
              // 按子账号和交易对分组
              const oppositeGroups = {};
              oppositePositions.forEach(pos => {
                const key = `${pos.email}_${pos.symbol}`;
                if (!oppositeGroups[key]) {
                  oppositeGroups[key] = [];
                }
                oppositeGroups[key].push(pos);
              });
              
              // 创建反向平仓任务
              const oppositeCloseTasks = [];
              
              for (const key in oppositeGroups) {
                const positions = oppositeGroups[key];
                if (!positions || positions.length === 0) continue;
                
                const position = positions[0];
                const email = position.email;
                const symbol = position.symbol;
                
                // 创建任务函数并立即添加到数组
                oppositeCloseTasks.push(
                  executeCloseAndCollection(email, symbol, oppositePositionSide, true)
                    .then(result => {
                      if (!result.success) {
                        addProcessingMessage(
                          'error',
                          `反向平仓失败`,
                          `子账号: ${email}, 交易对: ${symbol}, 错误: ${result.error}`
                        );
                        return { success: false, email, symbol, error: result.error };
                      }
                      
                      addProcessingMessage(
                        'success',
                        `反向平仓成功`,
                        `子账号: ${email}, 交易对: ${symbol}, 方向: ${!isLong ? '多仓' : '空仓'}`
                      );
                      
                      if (result.collectionSkipped) {
                        addProcessingMessage(
                          'info',
                          `跳过资金归集`,
                          `子账号: ${email}, 第二轮平仓后不执行资金归集`
                        );
                      }
                      
                      return { success: true, email, symbol };
                    })
                    .catch(error => {
                      console.error(`处理子账号 ${email} 反向平仓时出错:`, error);
                      addProcessingMessage(
                        'error',
                        `反向平仓异常`,
                        `子账号: ${email}, 交易对: ${symbol}, 错误: ${error.message || '未知错误'}`
                      );
                      return { success: false, email, symbol, error: error.message };
                    })
                );
              }
              
              // 执行反向平仓任务
              const oppositeResults = await Promise.all(oppositeCloseTasks);
              
              // 计算反向平仓成功和失败数量
              const oppositeSuccessCount = oppositeResults.filter(r => r.success).length;
              const oppositeFailCount = oppositeResults.filter(r => !r.success).length;
              
              // 记录总结信息
              addProcessingMessage(
                oppositeSuccessCount > 0 ? 'success' : 'warning',
                `第二轮操作完成`,
                `成功平掉反向持仓: ${oppositeSuccessCount}个, 失败: ${oppositeFailCount}个, 不执行资金归集`
              );
              
              // 添加最终操作完成的明确提示
              setTimeout(() => {
                addProcessingMessage(
                  'success',
                  '自动平仓全流程已完成',
                  `两轮平仓操作已全部完成，共处理 ${successCount + oppositeSuccessCount} 个持仓，请刷新获取最新数据`
                );
                
                // 确保消息窗口显示
                showMessageDialog.value = true;
                
                // 关闭自动平仓开关，避免重复请求
                autoCloseEnabled.value = false;
                ElMessage.info('已自动关闭平仓控制开关，避免重复请求');
              }, 500);
            } else {
              addProcessingMessage(
                'info',
                `没有找到反向持仓`,
                `无需执行第二轮平仓操作`
              );
              
              // 添加最终操作完成的明确提示
              setTimeout(() => {
                addProcessingMessage(
                  'success',
                  '自动平仓已完成',
                  `第一轮平仓操作已完成，共处理 ${successCount} 个持仓，请刷新获取最新数据`
                );
                
                // 确保消息窗口显示
                showMessageDialog.value = true;
                
                // 关闭自动平仓开关，避免重复请求
                autoCloseEnabled.value = false;
                ElMessage.info('已自动关闭平仓控制开关，避免重复请求');
              }, 500);
            }
          } else {
            // 如果没有成功的平仓操作，也添加一个提示
            addProcessingMessage(
              'warning',
              '自动平仓未能成功执行',
              `未能成功处理任何持仓，请检查网络连接或手动平仓`
            );
            
            // 确保消息窗口显示
            showMessageDialog.value = true;
            
            // 关闭自动平仓开关，避免重复请求
            autoCloseEnabled.value = false;
            ElMessage.info('已自动关闭平仓控制开关，避免重复请求');
          }
          
          // 操作完成，通知父组件刷新数据
          emit('refresh-mark-prices');
          
          // 确保消息对话框显示
          showMessageDialog.value = true;
          
          console.log('自动平仓流程执行完成，将重置isProcessingAutoClose标志');
          
          // 添加延迟，给持仓数据刷新留出时间
          setTimeout(async () => {
            // 请求父组件执行一次完整的持仓数据刷新
            emit('request-positions-refresh');
            
            // 等待1秒，确保数据刷新完成
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // 检查是否还有剩余持仓
            const remainingPositions = props.positions.filter(p => parseFloat(p.positionAmt) !== 0);
            
            if (remainingPositions.length > 0) {
              // 还有剩余持仓，执行第三轮平仓
              addProcessingMessage(
                'info',
                `发现未平持仓`,
                `第一轮和第二轮平仓后仍有${remainingPositions.length}个未平持仓，开始清理所有剩余持仓`
              );
              
              // 按子账号和交易对分组
              const remainingGroups = {};
              remainingPositions.forEach(pos => {
                const key = `${pos.email}_${pos.symbol}`;
                if (!remainingGroups[key]) {
                  remainingGroups[key] = [];
                }
                remainingGroups[key].push(pos);
              });
              
              // 创建第三轮平仓任务
              const finalCloseTasks = [];
              
              for (const key in remainingGroups) {
                const positions = remainingGroups[key];
                if (!positions || positions.length === 0) continue;
                
                const position = positions[0];
                const email = position.email;
                const symbol = position.symbol;
                // 确定持仓方向
                const positionSide = parseFloat(position.positionAmt) > 0 ? 'LONG' : 'SHORT';
                
                // 创建任务并立即添加到数组
                finalCloseTasks.push(
                  executeCloseAndCollection(email, symbol, positionSide, true)
                    .then(result => {
                      if (!result.success) {
                        addProcessingMessage(
                          'error',
                          `清理持仓失败`,
                          `子账号: ${email}, 交易对: ${symbol}, 错误: ${result.error}`
                        );
                        return { success: false, email, symbol, error: result.error };
                      }
                      
                      addProcessingMessage(
                        'success',
                        `清理持仓成功`,
                        `子账号: ${email}, 交易对: ${symbol}, 方向: ${positionSide === 'LONG' ? '多仓' : '空仓'}`
                      );
                      
                      return { success: true, email, symbol };
                    })
                    .catch(error => {
                      console.error(`处理子账号 ${email} 剩余持仓平仓时出错:`, error);
                      addProcessingMessage(
                        'error',
                        `清理持仓异常`,
                        `子账号: ${email}, 交易对: ${symbol}, 错误: ${error.message || '未知错误'}`
                      );
                      return { success: false, email, symbol, error: error.message };
                    })
                );
              }
              
              // 执行第三轮平仓任务
              if (finalCloseTasks.length > 0) {
                const finalResults = await Promise.all(finalCloseTasks);
              
                // 计算成功和失败数量
                const finalSuccessCount = finalResults.filter(r => r.success).length;
                const finalFailCount = finalResults.filter(r => !r.success).length;
                
                // 记录总结信息
                addProcessingMessage(
                  finalSuccessCount > 0 ? 'success' : 'warning',
                  `最终清理完成`,
                  `成功清理剩余持仓: ${finalSuccessCount}个, 失败: ${finalFailCount}个`
                );
                
                // 再次通知刷新持仓
                emit('refresh-mark-prices');
                
                // 最终的结果提示
                addProcessingMessage(
                  'success',
                  '全部平仓操作已完成',
                  `三轮平仓处理已完成，请检查是否还有剩余持仓`
                );
                
                // 确保关闭自动平仓开关，避免重复请求
                autoCloseEnabled.value = false;
                ElMessage.info('已自动关闭平仓控制开关，避免重复请求');
              }
            } else {
              // 没有剩余持仓，所有平仓操作已完成
              addProcessingMessage(
                'success',
                '所有持仓已清空',
                `所有持仓已成功平仓，系统已无剩余持仓`
              );
              
              // 确保关闭自动平仓开关，避免重复请求
              autoCloseEnabled.value = false;
              ElMessage.info('已自动关闭平仓控制开关，避免重复请求');
            }
            
            // 确保对话框显示
            showMessageDialog.value = true;
          }, 1500);
        } catch (error) {
          console.error('自动平仓和归集内部操作出错:', error);
          ElMessage.error('自动平仓流程执行失败');
          addProcessingMessage(
            'error',
            `自动平仓流程执行失败`,
            error.message || '未知错误'
          );
        }
      } catch (error) {
        console.error('自动平仓和归集操作出错:', error);
        ElMessage.error('自动平仓流程执行失败');
        addProcessingMessage(
          'error',
          `自动平仓流程执行失败`,
          error.message || '未知错误'
        );
      } finally {
        // 重置处理标记，允许再次自动平仓
        isProcessingAutoClose.value = false;
        console.log('自动平仓流程已完成，isProcessingAutoClose已重置为:', isProcessingAutoClose.value);
      }
    };

    return {
      markPrices,
      apiMarkPrices,
      hasPositions,
      longPositionsSummary,
      shortPositionsSummary,
      autoCloseEnabled,
      handleAutoClosePositions,
      totalLongProfit,
      totalShortProfit,
      longProfitPercentage,
      shortProfitPercentage,
      formatTotalProfit,
      formatTotalProfitPercentage,
      fetchMarkPrices,
      refreshMarkPrices,
      closeMode,
      targetProfitPercentage,
      isEditing,
      tempTargetProfitPercentage,
      startEdit,
      saveSettings,
      cancelEdit,
      longTotalValue,
      longInitialValue,
      shortTotalValue,
      shortInitialValue,
      formatTotalValue,
      totalPositionValue,
      totalInitialValue,
      totalProfit,
      totalProfitPercentage,
      checkProfitThresholdReached,
      groupPositionsByAccount,
      addProcessingMessage,
      executeCloseAndCollection,
      processAutoClose,
      isProcessingAutoClose,
      showMessageDialog,
      processingMessages,
      handleCloseMessageDialog
    };
  }
};
</script>

<style scoped>
.mark-price-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 15px;
}

.section-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: #606266;
  font-size: 14px;
}

/* 自动平仓控制面板样式 */
.auto-close-control-panel {
  background-color: #f8f9fa;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  padding: 12px;
  border: 1px solid #e6e6e6;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.panel-title {
  font-weight: bold;
  color: #303133;
  font-size: 15px;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.setting-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.setting-label {
  min-width: 100px;
  color: #606266;
  font-size: 13px;
  padding-top: 2px;
}

.setting-value {
  display: flex;
  align-items: center;
  gap: 5px;
}

.help-icon {
  color: #909399;
  cursor: pointer;
  font-size: 14px;
}

.current-status {
  margin-top: 5px;
  background-color: #f2f6fc;
  padding: 8px 12px;
  border-radius: 4px;
}

.status-item {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.status-label {
  min-width: 100px;
  color: #606266;
  font-size: 13px;
}

.status-value {
  font-weight: 500;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.status-value.positive {
  color: #67c23a;
}

.status-value.negative {
  color: #f56c6c;
}

.status-icon {
  margin-left: 5px;
  color: #67c23a;
}

.tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  padding-top: 5px;
  border-top: 1px dashed #e0e0e0;
}

.price-section, .position-monitor-section, .profit-summary-section {
  background-color: #f8f9fa;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  padding: 10px;
}

.cards-container, .profit-cards-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.price-card {
  padding: 10px 15px;
  border-radius: 4px;
  background-color: #fff;
  border: 1px solid #eaeaea;
  min-width: 120px;
  text-align: center;
}

.symbol {
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
  font-size: 14px;
}

.price {
  font-size: 16px;
  color: #1890ff;
  font-weight: 500;
}

/* 收益统计卡片样式 */
.profit-card, .total-profit-card {
  padding: 12px 15px;
  border-radius: 4px;
  background-color: #fff;
  border: 1px solid #eaeaea;
  min-width: 150px;
  flex: 1;
}

.profit-card.profit, .total-profit-card.profit {
  background-color: rgba(103, 194, 58, 0.05);
  border: 1px solid rgba(103, 194, 58, 0.2);
}

.profit-card.loss, .total-profit-card.loss {
  background-color: rgba(245, 108, 108, 0.05);
  border: 1px solid rgba(245, 108, 108, 0.2);
}

/* 总仓位卡片样式 */
.total-profit-card {
  margin-bottom: 15px;
  border-width: 2px;
  background-color: #fcfcfc;
}

.total-profit-card.profit {
  background-color: rgba(103, 194, 58, 0.08);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.total-profit-card.loss {
  background-color: rgba(245, 108, 108, 0.08);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.profit-header {
  font-weight: bold;
  color: #333;
  margin-bottom: 10px;
  font-size: 14px;
  text-align: center;
}

/* profit-details样式 */
.profit-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profit-detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
}

.profit-detail-item.highlight {
  border-top: 1px dashed #eaeaea;
  padding-top: 8px;
  margin-top: 4px;
  font-weight: 500;
}

.detail-label {
  color: #606266;
}

.detail-value {
  font-weight: 500;
}

.detail-value.positive {
  color: #67c23a;
}

.detail-value.negative {
  color: #f56c6c;
}

.profit-value {
  font-size: 20px;
  font-weight: 500;
  text-align: center;
}

.profit-card.profit .profit-value {
  color: #67c23a;
}

.profit-card.loss .profit-value {
  color: #f56c6c;
}

.profit-percentage {
  font-size: 14px;
  margin-top: 5px;
  color: #909399;
  text-align: center;
}

/* 仓位监控样式 */
.monitor-card {
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #eaeaea;
  padding: 12px;
  min-width: 200px;
  flex: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.position-type {
  font-weight: bold;
  font-size: 14px;
  padding: 2px 8px;
  border-radius: 3px;
}

.position-type.long {
  background-color: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.position-type.short {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.profit-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
}

.profit-status.profit {
  background-color: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.profit-status.loss {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.price-info {
  margin-bottom: 10px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.price-label {
  color: #909399;
  font-size: 13px;
}

.price-value {
  font-weight: 500;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.price-value.higher {
  color: #67c23a;
}

.price-value.lower {
  color: #f56c6c;
}

.price-arrow {
  margin-left: 3px;
  font-style: normal;
  font-weight: bold;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
}

.setting-readonly {
  padding: 5px 0;
  color: #606266;
}

.control-buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  justify-content: flex-end;
}

.threshold-indicator {
  background-color: rgba(103, 194, 58, 0.2);
  color: #67c23a;
  font-size: 12px;
  padding: 0 5px;
  border-radius: 3px;
  margin-left: 5px;
}

/* 消息窗口样式 */
.message-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
}

.message-item {
  margin-bottom: 10px;
}

.message-item:last-child {
  margin-bottom: 0;
}

.message-item .el-alert {
  transition: all 0.3s ease;
}

.message-item:hover .el-alert {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 