<template>
  <div class="trade-fees-summary" :class="{'collapsed': isCollapsed}">
    <div class="fee-card">
      <div class="fee-card-header">
        <span>交易费用统计</span>
        <button class="collapse-button" @click="toggleCollapse">
          <span v-if="isCollapsed">展开</span>
          <span v-else>收起</span>
          <el-icon class="icon-margin" v-if="!isCollapsed"><arrow-right /></el-icon>
        </button>
      </div>
      <div class="fee-card-body" v-show="!isCollapsed">
        <div class="fee-item">
          <div class="fee-label">杠杆手续费</div>
          <div class="fee-value">{{ marginFeesFormatted }}</div>
        </div>
        <div class="fee-item">
          <div class="fee-label">合约手续费</div>
          <div class="fee-value">{{ futuresFeesFormatted }}</div>
        </div>
        <div class="fee-item">
          <div class="fee-label">总实现盈亏</div>
          <div class="fee-value" :class="{'fee-positive': realizedPnl > 0, 'fee-negative': realizedPnl < 0}">
            {{ realizedPnlFormatted }}
          </div>
        </div>
        <div class="fee-item total">
          <div class="fee-label">总手续费</div>
          <div class="fee-value">{{ totalFeesFormatted }}</div>
        </div>
        <div class="refresh-action" @click="refreshAllFees">
          <el-icon :class="{ 'rotating': isLoadingMarginFees || isLoadingFuturesFees }"><refresh /></el-icon>
          <span class="last-update">{{ lastUpdateText }}</span>
        </div>
      </div>
    </div>
    <!-- 收起时显示的展开按钮 -->
    <div class="expand-button" v-if="isCollapsed" @click="toggleCollapse">
      <el-icon><arrow-left /></el-icon>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { Refresh, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { getTradesData, getCacheStatus } from '../services/tradesCache'
import { useMarginTradesStore } from '../stores/marginTradesStore'

export default {
  name: 'TradeFeesSummary',
  components: {
    Refresh,
    ArrowLeft,
    ArrowRight
  },
  props: {
    subaccounts: {
      type: Array,
      required: true
    },
    queryStartTime: {
      type: [Number, String],
      default: null
    },
    activeTab: {
      type: String,
      default: 'trades'
    },
    globalSymbol: {
      type: String,
      default: ''
    },
    contractType: {
      type: String,
      default: 'UM' // 默认为U本位合约
    }
  },
  setup(props) {
    // 手续费数据
    const marginFees = ref(0);
    const futuresFees = ref(0);
    const realizedPnl = ref(0);
    const isLoadingMarginFees = ref(false);
    const isLoadingFuturesFees = ref(false);
    const lastUpdateTime = ref(null);
    const autoRefreshTimer = ref(null);
    const autoRefreshInterval = 300000; // 5分钟自动刷新一次
    const isCollapsed = ref(localStorage.getItem('tradeFeesSummaryCollapsed') === 'true'); // 从本地存储读取状态
    
    // 获取杠杆交易Store
    const marginTradesStore = useMarginTradesStore();
    
    // 计算最后更新时间文本
    const lastUpdateText = computed(() => {
      if (!lastUpdateTime.value) return '点击刷新';
      
      const now = new Date();
      const diff = now - lastUpdateTime.value;
      
      // 如果小于1分钟，显示"刚刚"
      if (diff < 60000) {
        return '刚刚更新';
      }
      
      // 如果小于1小时，显示分钟
      if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}分钟前更新`;
      }
      
      // 否则显示小时
      const hours = Math.floor(diff / 3600000);
      return `${hours}小时前更新`;
    });
    
    // 计算总手续费
    const totalFees = computed(() => {
      return marginFees.value + futuresFees.value;
    });
    
    // 格式化手续费显示
    const marginFeesFormatted = computed(() => {
      return formatFee(marginFees.value);
    });
    
    const futuresFeesFormatted = computed(() => {
      return formatFee(futuresFees.value);
    });
    
    const totalFeesFormatted = computed(() => {
      return formatFee(totalFees.value);
    });
    
    const realizedPnlFormatted = computed(() => {
      return formatFee(realizedPnl.value);
    });
    
    // 格式化费用函数
    const formatFee = (fee) => {
      return fee.toFixed(6) + ' USDT';
    };
    
    // 使用Store查询获取杠杆交易手续费
    const fetchMarginFees = async () => {
      if (!props.subaccounts || props.subaccounts.length === 0) {
        return;
      }
      
      try {
        isLoadingMarginFees.value = true;
        
        // 使用Store查询获取杠杆交易
        const params = {
          emails: props.subaccounts.map(account => account.email),
          symbol: props.globalSymbol || undefined,
          queryStartTime: props.queryStartTime,
          useCache: true // u5141u8bb8u4f7fu7528u7f13u5b58uff0cu51cfu5c11u670du52a1u5668u8d1fu62c5
        };
        
        // 使用Store获取杠杆交易手续费
        await marginTradesStore.fetchMarginTrades(params);
        
        // 检查是否成功获取到数据
        if (marginTradesStore.hasMarginTrades) {
          // 计算杠杆交易手续费总和
          marginFees.value = marginTradesStore.totalCommission;
          console.log(`u4ea4u6613u8d39u7528u7edf u8ba1 - u6760u6746u624bu7eedu8d39u66f4u65b0: ${marginFees.value.toFixed(6)} USDT, u5171${marginTradesStore.marginTrades.length}u6761u6760u6746u4ea4u6613u8bb0u5f55`);
        } else {
          // 如果没有获取到数据，则设置为0
          marginFees.value = 0;
          console.log('没有获取到杠杆交易记录，手续费总和设置为0');
        }
        
        // 更新最后更新时间
        lastUpdateTime.value = new Date();
      } catch (error) {
        console.error('获取杠杆交易手续费失败:', error);
        marginFees.value = 0; // 在获取失败时设置为0
      } finally {
        isLoadingMarginFees.value = false;
      }
    };
    
    // 查询合约交易手续费
    const fetchFuturesFees = async () => {
      if (!props.subaccounts || props.subaccounts.length === 0) {
        return;
      }
      
      try {
        isLoadingFuturesFees.value = true;
        futuresFees.value = 0;
        realizedPnl.value = 0;
        
        // 如果设置了全局交易对，则只查询这个交易对
        const symbols = props.globalSymbol ? [props.globalSymbol] : ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'DOGEUSDT', 'SOLUSDT'];
        let totalFuturesFees = 0;
        let totalRealizedPnl = 0;
        
        // 为每个交易对查询手续费并累加
        for (const symbol of symbols) {
          // 构建请求参数
          const params = {
            emails: props.subaccounts.map(account => account.email),
            symbol: symbol,
            limit: 500,
            contractType: props.contractType
          };
          
          // 使用全局查询起始时间到当前时间
          if (props.queryStartTime) {
            params.startTime = typeof props.queryStartTime === 'string' 
              ? new Date(props.queryStartTime).getTime() 
              : props.queryStartTime;
          }
          
          // 使用缓存服务获取数据，不强制刷新
          const result = await getTradesData(params, false, 60000); // 60秒缓存有效期
          
          if (result && result.success) {
            const results = result.data || [];
            
            // 遍历每个子账号的结果
            results.forEach(result => {
              if (result.success && result.trades && result.trades.length) {
                // 计算这个子账号的手续费总和和实现盈亏
                result.trades.forEach(trade => {
                  if (trade.commission) {
                    totalFuturesFees += parseFloat(trade.commission || 0);
                  }
                  if (trade.realizedPnl) {
                    totalRealizedPnl += parseFloat(trade.realizedPnl || 0);
                  }
                });
              }
            });
          }
        }
        
        futuresFees.value = totalFuturesFees;
        realizedPnl.value = totalRealizedPnl;
        lastUpdateTime.value = new Date();
        
        // 记录缓存使用情况
        const cacheStatus = getCacheStatus();
        console.log(`交易费用组件使用缓存数据，缓存信息:`, cacheStatus);
        
      } catch (error) {
        console.error('获取合约手续费失败:', error);
      } finally {
        isLoadingFuturesFees.value = false;
      }
    };
    
    // 刷新所有费用数据
    const refreshAllFees = () => {
      fetchMarginFees();
      fetchFuturesFees();
    };
    
    // 启动自动刷新定时器
    const startAutoRefresh = () => {
      // 先清除可能存在的定时器
      if (autoRefreshTimer.value) {
        clearInterval(autoRefreshTimer.value);
      }
      
      // 启动新的定时器
      autoRefreshTimer.value = setInterval(() => {
        if (props.subaccounts && props.subaccounts.length > 0) {
          refreshAllFees();
        }
      }, autoRefreshInterval);
    };
    
    // 监听子账号变化，刷新费用
    watch(() => props.subaccounts, (newVal) => {
      if (newVal && newVal.length > 0) {
        refreshAllFees();
      }
    }, { deep: true });
    
    // 监听查询时间变化，刷新费用
    watch(() => props.queryStartTime, () => {
      refreshAllFees();
    });
    
    // 监听全局交易对变化
    watch(() => props.globalSymbol, () => {
      if (props.subaccounts && props.subaccounts.length > 0) {
        refreshAllFees();
      }
    });
    
    // 监听合约类型变化
    watch(() => props.contractType, () => {
      if (props.subaccounts && props.subaccounts.length > 0) {
        refreshAllFees();
      }
    });
    
    // 初始化时加载数据
    onMounted(() => {
      if (props.subaccounts && props.subaccounts.length > 0) {
        refreshAllFees();
      }
      // 启动自动刷新
      startAutoRefresh();
    });
    
    // 组件销毁前清理定时器
    onBeforeUnmount(() => {
      if (autoRefreshTimer.value) {
        clearInterval(autoRefreshTimer.value);
        autoRefreshTimer.value = null;
      }
    });
    
    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value;
      // 保存到本地存储
      localStorage.setItem('tradeFeesSummaryCollapsed', isCollapsed.value);
    };
    
    return {
      marginFees,
      futuresFees,
      realizedPnl,
      marginFeesFormatted,
      futuresFeesFormatted,
      totalFeesFormatted,
      realizedPnlFormatted,
      refreshAllFees,
      isLoadingMarginFees,
      isLoadingFuturesFees,
      lastUpdateText,
      isCollapsed,
      toggleCollapse
    };
  }
}
</script>

<style scoped>
.trade-fees-summary {
  position: fixed;
  top: 100px;
  right: 20px;
  z-index: 1000;
  width: 200px;
  transition: all 0.3s ease;
}

.trade-fees-summary.collapsed {
  width: 30px;
  right: 10px;
}

.fee-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s;
}

.trade-fees-summary.collapsed .fee-card {
  display: none;
}

.fee-card:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.2);
}

.fee-card-header {
  background-color: #409EFF;
  color: white;
  padding: 10px;
  font-weight: bold;
  text-align: center;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fee-card-body {
  padding: 15px;
}

.fee-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.fee-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.fee-item.total {
  margin-top: 10px;
  font-weight: bold;
  color: #409EFF;
}

.fee-label {
  color: #606266;
}

.fee-value {
  color: #303133;
  font-weight: 500;
}

.fee-positive {
  color: #67C23A;
}

.fee-negative {
  color: #F56C6C;
}

.refresh-action {
  margin-top: 10px;
  text-align: center;
  color: #909399;
  font-size: 0.85em;
  cursor: pointer;
  padding: 5px;
  border-radius: 4px;
}

.refresh-action:hover {
  background-color: #ecf5ff;
  color: #409EFF;
}

.rotating {
  animation: rotate 1s linear infinite;
}

.last-update {
  margin-left: 5px;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.icon-margin {
  margin-left: 4px;
}

.collapse-button {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
  outline: inherit;
  color: white;
  margin-left: 10px;
  display: flex;
  align-items: center;
}

.expand-button {
  position: fixed;
  top: 100px;
  right: 10px;
  z-index: 1000;
  width: 30px;
  height: 30px;
  background-color: #409EFF;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.expand-button:hover {
  background-color: #66b1ff;
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.2);
}

.expand-button i {
  font-size: 16px;
}
</style> 