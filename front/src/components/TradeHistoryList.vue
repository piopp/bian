<template>
  <div class="trade-history-container">
    <el-card class="trade-list-card">
      <template #header>
        <div class="card-header">
          <span>成交记录</span>
          <div class="header-actions">
            <div style="margin-right: 10px;" v-if="currentSymbol">当前交易对: {{ currentSymbol }}</div>
            <el-button type="primary" @click="queryTrades" :loading="isLoading">刷新</el-button>
          </div>
        </div>
      </template>
      
      <div class="d-flex align-items-center mb-3">
        <el-switch
          v-model="autoRefresh"
          :active-text="'自动刷新 (' + (autoRefresh ? '开启' : '关闭') + ')'"
          inline-prompt
          @change="handleAutoRefreshChange"
        />
        <template v-if="autoRefresh">
          <span class="ms-2">
            <small class="text-muted me-1">刷新间隔:</small>
        </span>
          <el-select v-model="localRefreshInterval" style="width: 90px" size="small" @change="handleIntervalChange">
            <el-option :value="1000" label="1秒" />
            <el-option :value="3000" label="3秒" />
            <el-option :value="5000" label="5秒" />
            <el-option :value="10000" label="10秒" />
            <el-option :value="30000" label="30秒" />
          </el-select>
        </template>
        <div class="ms-auto" v-if="isLoading">
          <small class="text-muted"><i class="el-icon-loading"></i> 正在查询成交记录...</small>
        </div>
      </div>

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
      <el-table
        v-if="flattenedTrades.length > 0"
        :data="flattenedTrades"
        stripe
        border
        style="width: 100%"
        max-height="500px"
        :default-sort="{ prop: 'time', order: 'descending' }"
      >
        <el-table-column prop="email" label="子账号" width="180" sortable show-overflow-tooltip />
        <el-table-column prop="symbol" label="交易对" width="100" sortable />
        <el-table-column prop="price" label="成交价格" width="100" sortable />
        <el-table-column prop="qty" label="成交数量" width="100" sortable />
        <el-table-column prop="quoteQty" label="成交额" width="120" sortable />
        <el-table-column prop="time" label="成交时间" width="160" sortable>
          <template #default="scope">
            {{ formatDateTime(scope.row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="commission" label="手续费" width="100" sortable />
        <el-table-column prop="commissionAsset" label="手续费资产" width="100" />
        <el-table-column prop="side" label="方向" width="80" sortable>
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
        <el-table-column prop="realizedPnl" label="已实现盈亏" width="120" sortable>
          <template #default="scope">
            <span :class="{'text-success': parseFloat(scope.row.realizedPnl) > 0, 'text-danger': parseFloat(scope.row.realizedPnl) < 0}">
              {{ scope.row.realizedPnl }}
            </span>
          </template>
        </el-table-column>
      </el-table>
      
      <div v-if="flattenedTrades.length === 0 && !isLoading" class="no-data">
        暂无交易对 {{ currentSymbol }} 的成交记录，请点击刷新按钮查询
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getTradesData, getCacheStatus } from '../services/tradesCache'

export default {
  name: 'TradeHistoryList',
  props: {
    subaccounts: {
      type: Array,
      required: true
    },
    queryStartTime: {
      type: [Number, String],
      default: null
    },
    globalSymbol: {
      type: String,
      default: ''
    },
    contractType: {
      type: String,
      default: 'UM' // 默认为U本位合约
    },
    globalAutoRefresh: {
      type: Boolean,
      default: false
    },
    refreshInterval: {
      type: Number,
      default: 5000
    },
    positionVersion: {
      type: Number, // 持仓数据版本，每当持仓变化时递增
      default: 0
    }
  },
  emits: ['system-message'],
  setup(props, { emit }) {
    // 交易对列表
    const tradingPairs = ref([])
    const isLoadingTradingPairs = ref(false)
    
    // 状态变量
    const isLoading = ref(false)
    const tradesData = ref([])
    const lastUpdateTime = ref('-') // 添加最后更新时间变量
    
    // 查询表单
    const tradesForm = reactive({
      symbol: props.globalSymbol || '',
      limit: 500
    })
    
    // 添加系统消息函数
    const addSystemMessage = (type, title, description) => {
      emit('system-message', {
        type, // success, warning, info, error
        title,
        description,
        time: new Date().toLocaleTimeString()
      });
    };
    
    // 发送组件状态函数
    const sendComponentStatus = (status, message) => {
      const statusMessage = {
        type: status === '正常' ? 'success' : status === '警告' ? 'warning' : 'error',
        title: '组件状态更新',
        description: `TradeHistoryList组件状态: ${message}`,
        componentStatus: {
          component: 'TradeHistoryList',
          status: status,
          message: message
        }
      };
      
      // 向父组件发送状态消息
      emit('system-message', statusMessage);
    };
    
    // 查询交易记录
    const queryTrades = async (showLoading = true) => {
      if (isLoading.value) return;
      
      if (!props.subaccounts || props.subaccounts.length === 0) {
        ElMessage.info('请选择至少一个子账户');
        return;
      }
      
      // 只在显式要求时才显示加载状态
      if (showLoading) {
      isLoading.value = true;
      sendComponentStatus('正常', '正在查询交易记录...');
      }
      
      try {
        // 准备请求参数
        const params = {
          emails: props.subaccounts.map(account => account.email),
          symbol: tradesForm.symbol || props.globalSymbol || '',
          contractType: props.contractType,
          limit: tradesForm.limit || 500
        };
        
        // 添加时间范围
        if (props.queryStartTime) {
          // 确保无论是字符串还是数字类型，都能正确处理
          params.startTime = typeof props.queryStartTime === 'string' 
            ? new Date(props.queryStartTime).getTime() 
            : props.queryStartTime;
          
          // 打印日志以便排查问题
          console.log('添加startTime参数:', params.startTime, '原始queryStartTime:', props.queryStartTime);
        }
        
        // 判断是手动刷新还是自动刷新
        const isManualRefresh = !autoRefresh.value;
        
        // 手动刷新时不使用缓存，自动刷新使用短期缓存
        const maxAge = isManualRefresh ? 0 : 3000; // 手动刷新不用缓存，自动刷新3秒内使用缓存
        
        // 获取交易数据
        const result = await getTradesData(params, isManualRefresh, maxAge);
        
        // 打印日志
        const cacheStatus = getCacheStatus();
        console.log(`使用${isManualRefresh ? '直接API请求' : '可能的缓存'}获取交易数据, 缓存信息:`, cacheStatus);
        
        if (result && result.success) {
          // 处理成功情况
          processTradeData(result.data);
          
          // 更新最后查询时间
          lastUpdateTime.value = new Date().toLocaleString();
          
          // 如果有数据，通知成功
          if (tradesData.value.length > 0) {
            addSystemMessage('success', `成功加载交易记录`, `共加载 ${tradesData.value.length} 条记录`);
            sendComponentStatus('正常', `成功加载${tradesData.value.length}条交易记录`);
          } else {
            addSystemMessage('info', '没有交易记录', '在指定条件下未找到交易记录');
            sendComponentStatus('正常', '没有交易记录');
          }
        } else {
          // 处理错误情况
          ElMessage.error(result?.message || '查询交易记录失败');
          addSystemMessage('error', '查询交易记录失败', result?.message || '未知错误');
          sendComponentStatus('错误', `查询交易记录失败: ${result?.message || '未知错误'}`);
        }
      } catch (error) {
        console.error('查询交易记录出错:', error);
        ElMessage.error('网络错误，查询交易记录失败');
        addSystemMessage('error', '查询交易记录出错', error.message || '网络错误');
        sendComponentStatus('错误', `查询交易记录网络错误: ${error.message || '未知错误'}`);
      } finally {
        isLoading.value = false;
      }
    };
    
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
    
    // 计算属性：当前使用的交易对
    const currentSymbol = computed(() => {
      if (!tradesForm.symbol) return '';
      
      // 根据合约类型调整交易对后缀
      if (props.contractType === 'CM') {
        // 币本位合约，将后缀改为USD_PERP
        if (tradesForm.symbol.endsWith('USDT')) {
          return tradesForm.symbol.replace('USDT', 'USD_PERP');
        }
        // 如果已经是币本位格式，不做改变
        return tradesForm.symbol;
      } else {
        // U本位合约，将后缀改为USDT
        if (tradesForm.symbol.endsWith('USD_PERP')) {
          return tradesForm.symbol.replace('USD_PERP', 'USDT');
        }
        // 如果已经是U本位格式，不做改变
        return tradesForm.symbol;
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
    
    // 格式化日期时间
    const formatDateTime = (timestamp) => {
      if (!timestamp) return ''
      try {
        const date = new Date(parseInt(timestamp))
        if (isNaN(date.getTime())) return '-'
        
        // 获取月日
        const month = (date.getMonth() + 1).toString().padStart(2, '0')
        const day = date.getDate().toString().padStart(2, '0')
        
        // 获取时分秒
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        const seconds = date.getSeconds().toString().padStart(2, '0')
        
        // 返回格式化的日期时间字符串：MM-DD HH:MM:SS
        return `${month}-${day} ${hours}:${minutes}:${seconds}`
      } catch (e) {
        console.error('日期格式化错误:', e)
        return '-'
      }
    }
    
    // 获取交易对列表
    const loadTradingPairs = async () => {
      // 不再需要加载交易对列表，直接从props.globalSymbol中获取
      if (props.globalSymbol) {
        tradesForm.symbol = props.globalSymbol;
        
        // 如果已经有子账号，自动查询
        if (props.subaccounts && props.subaccounts.length > 0 && tradesForm.symbol) {
          queryTrades();
        }
      } else {
        // 没有全局交易对，设置默认值
        tradesForm.symbol = props.contractType === 'CM' ? 'BTCUSD_PERP' : 'BTCUSDT';
      }
    }
    
    // 添加watch以监听全局交易对变化
    watch(() => props.globalSymbol, (newSymbol) => {
      if (newSymbol) {
        tradesForm.symbol = newSymbol;
        // 如果子账号已选择，自动查询
        if (props.subaccounts && props.subaccounts.length > 0) {
          queryTrades();
        }
      }
    });

    // 添加watch以监听合约类型变化
    watch(() => props.contractType, () => {
      // 交易对格式变化已经在父组件TradingCenter中处理
      // 合约类型改变会触发全局交易对格式调整，然后通过props.globalSymbol传递过来
      // 这里只需要使用调整后的全局交易对即可
    });
    
    // 监听持仓版本变化，当有新的持仓变动时刷新历史订单
    watch(() => props.positionVersion, (newValue, oldValue) => {
      // 如果持仓版本有变化且不是初始加载
      if (newValue > 0 && newValue !== oldValue) {
        console.log(`[TradeHistoryList] 检测到持仓变化(版本: ${newValue})，刷新历史订单`);
        if (props.subaccounts && props.subaccounts.length > 0) {
          queryTrades(false); // 不显示loading状态
        }
      }
    });
    
    // 监听props.queryStartTime变化
    watch(() => props.queryStartTime, (newVal, oldVal) => {
      console.log('queryStartTime变化:', newVal, '旧值:', oldVal);
      if (props.subaccounts && props.subaccounts.length > 0) {
      queryTrades();
      }
    });
    
    // 自动刷新相关变量
    const autoRefresh = ref(false);
    const refreshTimer = ref(null);
    const localRefreshInterval = ref(5000); // 默认5秒刷新一次
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      stopAutoRefresh(); // 先停止现有的定时器
      
      // 创建定时器实现自动刷新，使用本地刷新间隔设置，最短间隔1秒
      const interval = Math.max(1000, localRefreshInterval.value || 5000);
      console.log(`[TradeHistoryList] 启动自动刷新，间隔: ${interval}ms`);
      
      refreshTimer.value = setInterval(() => {
        queryTrades(false); // false表示不显示loading状态
      }, interval);
      
      sendComponentStatus('正常', `自动刷新已启动，间隔${interval/1000}秒`);
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
      }
    };
    
    // 处理自动刷新开关切换
    const handleAutoRefreshChange = (value) => {
      if (value) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
        sendComponentStatus('正常', '自动刷新已停止');
      }
    };
    
    // 处理刷新间隔变化
    const handleIntervalChange = () => {
      // 如果自动刷新已开启，则重新启动定时器使用新的间隔
      if (autoRefresh.value) {
        startAutoRefresh();
      }
    };
    
    // 监听刷新间隔变化
    watch(() => props.refreshInterval, (newValue) => {
      if (newValue && newValue !== localRefreshInterval.value) {
        localRefreshInterval.value = newValue;
        // 如果自动刷新已开启，则重新启动定时器
        if (autoRefresh.value) {
          stopAutoRefresh();
          startAutoRefresh();
        }
        sendComponentStatus('正常', `刷新间隔已更新为${newValue / 1000}秒`);
      }
    });
    
    // 处理交易数据的函数
    const processTradeData = (data) => {
      if (!data || !Array.isArray(data)) {
        tradesData.value = [];
        return;
      }
      
      // 将API返回的数据格式化为组件需要的格式
      tradesData.value = data.map(item => {
        return {
          email: item.email || '',
          success: item.success || false,
          trades: item.trades || []
        };
      });
    };
    
    // 组件挂载时执行
    onMounted(() => {
      // 加载交易对列表
      loadTradingPairs();
    
      // 设置表单中的全局交易对
      if (props.globalSymbol) {
        tradesForm.symbol = props.globalSymbol;
      }
      
      // 初始查询交易记录
      if (props.subaccounts && props.subaccounts.length > 0) {
        console.log('[TradeHistoryList] 组件挂载，执行初始查询');
        queryTrades();
      }
      
      // 设置初始刷新间隔
      if (props.refreshInterval) {
        localRefreshInterval.value = props.refreshInterval;
      }
      
      // 发送组件已加载状态
      sendComponentStatus('正常', '交易历史组件已加载');
    });
    
    // 组件卸载时清理资源
    onUnmounted(() => {
      // 停止自动刷新
      stopAutoRefresh();
      
      sendComponentStatus('正常', '交易历史组件已卸载');
    });
    
    return {
      tradingPairs,
      isLoadingTradingPairs,
      isLoading,
      tradesForm,
      queryTrades,
      tradesData,
      flattenedTrades,
      tradesStats,
      formatDateTime,
      currentSymbol,
      addSystemMessage,
      sendComponentStatus,
      lastUpdateTime,
      processTradeData,
      autoRefresh,
      localRefreshInterval,
      handleAutoRefreshChange,
      handleIntervalChange,
      startAutoRefresh,
      stopAutoRefresh
    }
  }
}
</script>

<style scoped>
.trade-history-container {
  padding: 10px;
}

.trade-list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #909399;
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