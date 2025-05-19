<template>
  <div class="margin-trade-history-container">
    <el-card class="trade-list-card">
      <template #header>
        <div class="card-header">
          <span>杠杆成交记录</span>
          <div class="header-actions">
            <el-select 
              v-model="tradesForm.symbol" 
              clearable 
              filterable
              placeholder="选择交易对" 
              style="margin-right: 10px; width: 120px;"
            >
              <el-option 
                v-for="pair in tradingPairs"
                :key="pair.value"
                :label="pair.label"
                :value="pair.value">
              </el-option>
            </el-select>
            <el-button type="primary" @click="queryTrades" :loading="isLoading">查询</el-button>
            <el-button type="info" @click="handleAutoRefresh" :class="{'is-active': autoRefresh}" :disabled="globalAutoRefresh">
              {{ autoRefresh ? '停止自动刷新' : '自动刷新' }}
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="d-flex align-items-center mb-3">
        <div class="refresh-status" v-if="autoRefresh || globalAutoRefresh">
          <span v-if="globalAutoRefresh" class="global-refresh-status">
            <i class="el-icon-refresh-right"></i> 
            使用全局自动刷新 ({{refreshInterval/1000}}秒)
          </span>
          <span v-else-if="autoRefresh" class="local-refresh-status">
            <i class="el-icon-refresh-right"></i> 
            本地自动刷新 ({{localRefreshInterval/1000}}秒)
          </span>
        </div>
        <div class="stats-container mb-3" v-if="marginTrades.length > 0">
          <div class="stat-item">
            <span class="stat-label">总成交笔数:</span>
            <span class="stat-value">{{ marginTrades.length }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">总手续费:</span>
            <span class="stat-value">{{ totalCommissionFormatted }}</span>
            <el-tooltip v-if="Math.abs(totalCommission - storeTotalCommission) > 0.000001" effect="dark" placement="top">
              <template #content>
                本地计算: {{ totalCommissionFormatted }}<br>
                Store计算: {{ storeTotalCommissionFormatted }}<br>
                差值: {{ (totalCommission - storeTotalCommission).toFixed(6) }}
              </template>
              <el-tag size="small" type="warning" style="margin-left: 5px;">
                <i class="el-icon-warning"></i>
              </el-tag>
            </el-tooltip>
          </div>
          <div class="stat-item">
            <span class="stat-label">最近更新:</span>
            <span class="stat-value">{{ lastUpdateTime }}</span>
          </div>
        </div>
        <div class="ms-auto" v-if="isLoading">
          <small class="text-muted"><i class="el-icon-loading"></i> 正在查询杠杆成交记录...</small>
        </div>
      </div>

      <!-- 成交明细表格 -->
      <el-table
        v-if="marginTrades.length > 0"
        :data="marginTrades"
        stripe
        border
        style="width: 100%"
        max-height="500px"
        :default-sort="{ prop: 'time', order: 'descending' }"
      >
        <el-table-column prop="symbol" label="交易对" width="100" sortable />
        <el-table-column prop="orderId" label="订单号" width="120" sortable />
        <el-table-column prop="price" label="价格" width="100" sortable />
        <el-table-column prop="qty" label="数量" width="100" sortable />
        <el-table-column prop="quoteAmount" label="金额(USDT)" width="120" sortable />
        <el-table-column prop="commission" label="手续费" width="120" sortable />
        <el-table-column prop="commissionAsset" label="手续费币种" width="100" sortable />
        <el-table-column prop="time" label="成交时间" width="160" sortable>
          <template #default="scope">
            {{ formatDateTime(scope.row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="isBuyer" label="方向" width="80" sortable>
          <template #default="scope">
            <el-tag :type="scope.row.isBuyer ? 'success' : 'danger'" size="small">
              {{ scope.row.isBuyer ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="isMaker" label="成交类型" width="100" sortable>
          <template #default="scope">
            <el-tag :type="scope.row.isMaker ? 'info' : 'warning'" size="small">
              {{ scope.row.isMaker ? 'Maker' : 'Taker' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="成交ID" width="120" sortable />
      </el-table>
      
      <div v-if="marginTrades.length === 0 && !isLoading" class="no-data">
        暂无杠杆成交记录，请选择交易对并点击查询
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getCurrentUser } from '../services/auth'
import { parseApiResult } from '../utils/apiHelper'
import { useMarginTradesStore } from '../stores/marginTradesStore'

export default {
  name: 'MarginTradeHistory',
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
    globalAutoRefresh: {
      type: Boolean,
      default: false
    },
    refreshInterval: {
      type: Number,
      default: 5000
    }
  },
  emits: ['system-message'],
  setup(props, { emit }) {
    // u521du59cbu5316u5e93
    const marginTradesStore = useMarginTradesStore();
    
    // 交易对列表
    const tradingPairs = ref([
      { value: 'BTCUSDT', label: 'BTC/USDT' },
      { value: 'ETHUSDT', label: 'ETH/USDT' },
      { value: 'BNBUSDT', label: 'BNB/USDT' },
      { value: 'ADAUSDT', label: 'ADA/USDT' },
      { value: 'SOLUSDT', label: 'SOL/USDT' },
      { value: 'XRPUSDT', label: 'XRP/USDT' },
      { value: 'DOGEUSDT', label: 'DOGE/USDT' }
    ])
    
    // 状态变量
    const isLoading = ref(false)
    const marginTrades = ref([])
    const lastUpdateTime = ref('-')
    const autoRefresh = ref(false)
    const refreshTimer = ref(null)
    const localRefreshInterval = 60000 // 60秒自动刷新，作为本地刷新间隔
    
    // 查询表单
    const tradesForm = reactive({
      symbol: props.globalSymbol || '',
      limit: 50
    })
    
    // u8ba1u7b97u603bu624bu7eedu8d39
    const totalCommission = computed(() => {
      if (!marginTrades.value || marginTrades.value.length === 0) return 0;
      
      let total = 0;
      marginTrades.value.forEach(trade => {
        if (trade.commission) {
          // u6839u636eu624bu7eedu8d39u8d44u4ea7u7c7bu578bu8fdbu884cu5904u7406
          if (trade.commissionAsset === 'USDT') {
            // u76f4u63a5u7d2fu52a0 USDT u624bu7eedu8d39
            total += parseFloat(trade.commission || 0);
          } else if (trade.commissionAsset && trade.price) {
            // u5bf9u4e8eu975e USDT u8d44u4ea7uff0cu4f7fu7528u4ea4u6613u4ef7u683cu8ba1u7b97USDTu4ef7u503c
            if (['BTC', 'ETH', 'BNB', 'SOL', 'DOGE', 'XRP'].includes(trade.commissionAsset)) {
              const estimatedUsdtValue = parseFloat(trade.commission || 0) * parseFloat(trade.price || 0);
              total += estimatedUsdtValue;
            }
          }
        }
      });
      
      return total;
    });
    
    // 格式化总手续费
    const totalCommissionFormatted = computed(() => {
      return `${totalCommission.value.toFixed(6)} USDT`;
    });
    
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
        description: `MarginTradeHistory组件状态: ${message}`,
        componentStatus: {
          component: 'MarginTradeHistory',
          status: status,
          message: message
        }
      };
      
      // 向父组件发送状态消息
      emit('system-message', statusMessage);
    };
    
    // u67e5u8be2u676cu6746u8ba2u5355u8bb0u5f55
    const queryMarginTrades = async () => {
      if (isLoading.value) return;
      
      if (!props.subaccounts || props.subaccounts.length === 0) {
        ElMessage.info('请选择至少一个子账户');
        return;
      }
      
      isLoading.value = true;
      sendComponentStatus('正常', '正在查询杠杆交易记录...');
      
      try {
        // 构建查询参数
        const emails = props.subaccounts.map(account => account.email);
        const symbol = tradesForm.symbol || props.globalSymbol || '';
        const startTime = props.queryStartTime || undefined;
        
        // 首先使用Store获取数据
        const storeParams = {
          emails: emails,
          symbol: symbol,
          limit: tradesForm.limit,
          startTime: startTime,
          useCache: false // 强制刷新，获取最新数据
        };
        
        // 通过Store获取数据
        await marginTradesStore.fetchMarginTrades(storeParams);
        
        // 如果Store成功获取数据，则直接使用
        if (marginTradesStore.hasMarginTrades) {
          // 从Store获取处理后的数据
          marginTrades.value = marginTradesStore.marginTrades;
          lastUpdateTime.value = new Date().toLocaleString();
          
          // 数据获取成功
          ElMessage.success(`成功获取${marginTrades.value.length}条杠杆交易记录`);
          sendComponentStatus('正常', `成功加载${marginTrades.value.length}条杠杆交易记录`);
          
          console.log('成功从Store获取杠杆交易记录: ', marginTrades.value.length, '条，总手续费: ', totalCommission.value.toFixed(6), ' USDT');
          
          // 更新状态并返回
          return;
        }
        
        // 如果Store没有获取到数据，尝试直接从API获取（兼容性处理）
        // 获取当前用户信息
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          isLoading.value = false;
          sendComponentStatus('错误', '用户未登录或token无效');
          return;
        }
        
        // 并行查询多个子账号的杠杆交易记录
        const promises = emails.map(email => 
          axios.post('/api/margin/trades', {
            email: email,
            symbol: symbol,
            limit: tradesForm.limit,
            startTime: startTime
          }, {
          headers: {
              'Authorization': `Bearer ${user.token}`
          }
        })
        );
        
        // 等待所有请求完成
        const responses = await Promise.all(promises);
        
        // 处理所有返回结果
        const allTrades = [];
        let hasError = false;
        
        responses.forEach((response, index) => {
          try {
            const result = parseApiResult(response);
            if (result.success && result.data) {
              // 添加子账号信息到每条记录
              const tradesWithEmail = result.data.map(trade => ({
              ...trade,
                email: emails[index]
              }));
              allTrades.push(...tradesWithEmail);
            } else {
              hasError = true;
              console.error(`获取子账号 ${emails[index]} 的杠杆交易记录失败:`, result.error || '未知错误');
            }
          } catch (err) {
            hasError = true;
            console.error(`处理子账号 ${emails[index]} 的杠杆交易记录响应时出错:`, err);
            }
          });
          
        // 对结果按时间降序排序
        marginTrades.value = allTrades.sort((a, b) => b.time - a.time);
        lastUpdateTime.value = new Date().toLocaleString();
        
        // 将获取到的数据同步更新到Store中，确保两处数据一致
        if (marginTrades.value.length > 0) {
          // 这里不需要重新获取，直接更新Store中的数据
          marginTradesStore.marginTrades = marginTrades.value;
          marginTradesStore.lastUpdateTime = Date.now();
          console.log('已将API获取的杠杆交易记录同步到Store');
        }
        
        if (hasError) {
          ElMessage.warning('部分子账号的杠杆交易记录获取失败');
          addSystemMessage('warning', '部分数据加载失败', '部分子账号的杠杆交易记录获取失败');
          sendComponentStatus('警告', '部分子账号的杠杆交易记录获取失败');
        } else if (marginTrades.value.length === 0) {
          ElMessage.info('未找到杠杆交易记录');
          sendComponentStatus('正常', '未找到杠杆交易记录');
        } else {
          ElMessage.success(`成功获取${marginTrades.value.length}条杠杆交易记录`);
          sendComponentStatus('正常', `成功加载${marginTrades.value.length}条杠杆交易记录`);
        }
      } catch (error) {
        console.error('查询杠杆交易记录失败:', error);
        ElMessage.error('网络错误，查询杠杆交易记录失败');
        addSystemMessage('error', '查询杠杆交易记录失败', error.message || '网络错误');
        sendComponentStatus('错误', `查询杠杆交易记录网络错误: ${error.message || '网络错误'}`);
      } finally {
        isLoading.value = false;
      }
    };
    
    // 监听全局自动刷新状态变化
    watch(() => props.globalAutoRefresh, (newValue) => {
      autoRefresh.value = newValue;
      
      if (newValue) {
        startAutoRefresh();
        sendComponentStatus('正常', `自动刷新已启动，间隔${props.refreshInterval / 1000}秒`);
      } else {
        stopAutoRefresh();
        sendComponentStatus('正常', '自动刷新已停止');
      }
    });
    
    // 监听刷新间隔变化
    watch(() => props.refreshInterval, (newValue) => {
      if (autoRefresh.value) {
        stopAutoRefresh();
        startAutoRefresh();
        sendComponentStatus('正常', `刷新间隔已更新为${newValue / 1000}秒`);
      }
    });
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      stopAutoRefresh(); // 先停止现有的定时器
      
      refreshTimer.value = setInterval(() => {
        if (!isLoading.value) {
          queryMarginTrades();
        }
      }, props.refreshInterval || localRefreshInterval);
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
      }
    };
    
    // 自动刷新控制
    const handleAutoRefresh = () => {
      autoRefresh.value = !autoRefresh.value;
      
      if (autoRefresh.value && !props.globalAutoRefresh) {
        // 启动自动刷新
        startAutoRefresh();
      } else {
        // 停止自动刷新
        stopAutoRefresh();
        ElMessage.info('已停止自动刷新')
      }
    };
    
    // 监听全局交易对变化
    watch(() => props.globalSymbol, (newSymbol) => {
      if (newSymbol) {
        tradesForm.symbol = newSymbol;
        if (autoRefresh.value || props.globalAutoRefresh) {
          queryMarginTrades();
        }
      }
    });
    
    // 监听子账号变化
    watch(() => props.subaccounts, (newAccounts) => {
      if (newAccounts && newAccounts.length > 0 && tradesForm.symbol) {
        queryMarginTrades();
      }
    });
    
    // 监听查询时间变化
    watch(() => props.queryStartTime, () => {
      if (props.subaccounts && props.subaccounts.length > 0 && tradesForm.symbol) {
        queryMarginTrades();
      }
    });
    
    // 格式化日期时间
    const formatDateTime = (timestamp) => {
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
    
    // 获取订单状态类型
    const getStatusType = (status) => {
      switch (status) {
        case 'NEW': return 'primary'
        case 'PARTIALLY_FILLED': return 'warning'
        case 'FILLED': return 'success'
        case 'CANCELED': return 'info'
        case 'REJECTED': return 'danger'
        case 'EXPIRED': return 'info'
        default: return 'info'
      }
    }
    
    // 获取订单状态文本
    const getStatusText = (status) => {
      switch (status) {
        case 'NEW': return '未成交'
        case 'PARTIALLY_FILLED': return '部分成交'
        case 'FILLED': return '已成交'
        case 'CANCELED': return '已取消'
        case 'REJECTED': return '已拒绝'
        case 'EXPIRED': return '已过期'
        default: return status
      }
    }
    
    // 组件挂载时执行
    onMounted(() => {
      // 设置自动刷新初始状态
      autoRefresh.value = props.globalAutoRefresh;
      
      // 设置表单中的全局交易对
      if (props.globalSymbol) {
        tradesForm.symbol = props.globalSymbol;
      }
      
      // 初始查询杠杆交易记录
      if (props.subaccounts && props.subaccounts.length > 0) {
        queryMarginTrades();
      }
      
      // 如果开启自动刷新，启动定时器
      if (autoRefresh.value) {
        startAutoRefresh();
      }
      
      // 发送组件已加载状态
      sendComponentStatus('正常', '杠杆交易历史组件已加载');
    });
    
    // 组件卸载时清理资源
    onUnmounted(() => {
      stopAutoRefresh();
      sendComponentStatus('正常', '杠杆交易历史组件已卸载');
    });

    return {
      tradingPairs,
      isLoading,
      marginTrades,
      tradesForm,
      queryMarginTrades,
      formatDateTime,
      getStatusType,
      getStatusText,
      lastUpdateTime,
      autoRefresh,
      handleAutoRefresh,
      totalCommission,
      totalCommissionFormatted,
      localRefreshInterval,
      addSystemMessage,
      sendComponentStatus,
      // u6dfbu52a0Store u7684u624bu7eedu8d39u6570u636eu4f9du8bbau5bf9u7167
      storeTotalCommission: computed(() => marginTradesStore.totalCommission),
      storeTotalCommissionFormatted: computed(() => marginTradesStore.totalCommissionFormatted),
    }
  }
}
</script>

<style scoped>
.margin-trade-history-container {
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

.mb-3 {
  margin-bottom: 1rem;
}

.stats-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 10px;
}

.stat-item {
  display: flex;
  align-items: center;
  background-color: #f5f7fa;
  padding: 5px 10px;
  border-radius: 4px;
}

.stat-label {
  color: #606266;
  margin-right: 8px;
  font-weight: 500;
}

.stat-value {
  color: #409EFF;
  font-weight: 600;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

.text-muted {
  color: #909399;
}

.is-active {
  background-color: #ecf5ff;
  color: #409EFF;
  border-color: #d9ecff;
}

.refresh-status {
  margin-right: 20px;
}

.global-refresh-status,
.local-refresh-status {
  display: flex;
  align-items: center;
  gap: 5px;
}
</style> 