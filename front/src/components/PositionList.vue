<template>
  <div class="position-container">
    <!-- 添加消息通知窗口 -->
    <el-dialog
      v-model="showMessageDialog"
      title="自动处理通知"
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

    <el-card class="position-list-card">
      <template #header>
        <div class="card-header">
          <span>持仓管理</span>
          <div class="header-actions">
            <el-select 
              v-model="selectedSymbol" 
              clearable 
              placeholder="选择币种" 
              style="margin-right: 10px; width: 120px;"
            >
              <el-option 
                v-for="item in commonSymbols" 
                :key="item" 
                :label="item" 
                :value="item"
              />
            </el-select>
            <div style="margin-right: 10px;" v-if="currentSymbol">当前交易对: {{ currentSymbol }}</div>
            <el-button type="primary" @click="fetchPositions" :loading="loading">刷新</el-button>
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
          </el-select>
        </template>
        <div class="ms-auto" v-if="loading">
          <small class="text-muted"><i class="el-icon-loading"></i> 正在刷新数据...</small>
        </div>
      </div>
      
      <!-- 标记价格窗口 - 添加折叠功能 -->
      <div class="price-panel-header">
        <div class="d-flex align-items-center">
          <span class="panel-title">交易费用统计</span>
          <el-tag size="small" type="info" class="ms-2" v-if="positionsData.length > 0">{{ positionsData.length }}个持仓</el-tag>
        </div>
        <el-button 
          size="small" 
          type="primary"
          text
          @click="markPriceVisible = !markPriceVisible"
        >
          <template #icon>
            <el-icon>
              <arrow-up v-if="markPriceVisible" />
              <arrow-down v-else />
            </el-icon>
          </template>
          {{ markPriceVisible ? '收起' : '展开' }}
        </el-button>
      </div>
      
      <!-- 可收起的内容区域 -->
      <div v-show="markPriceVisible" class="price-panel-content">
      <mark-price-display 
        :positions="positionsData" 
        :contract-type="contractType"
        :auto-refresh="autoRefresh"
        :refresh-interval="localRefreshInterval"
        @refresh-mark-prices="handleMarkPricesRefreshed"
        @system-message="addProcessingMessage"
        ref="markPriceDisplayRef"
      />
      </div>
      
      <el-table 
        :data="filteredPositionsData" 
        border
        style="width: 100%"
        max-height="500px"
      >
        <el-table-column prop="email" label="子账号" width="180" sortable>
          <template #default="scope">
            <el-tooltip :content="scope.row.email" placement="top" :show-after="500">
              <span>{{ getShortEmail(scope.row.email) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="交易对" width="120" sortable />
        <el-table-column prop="side" label="方向" width="80" sortable>
          <template #default="scope">
            <el-tag :type="scope.row.side === '多头' ? 'success' : 'danger'">
              {{ scope.row.side }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="leverage" label="杠杆" width="60" sortable />
        <el-table-column prop="positionAmt" label="持仓量" width="100" sortable />
        <el-table-column prop="entryPrice" label="开仓价" width="100" sortable>
          <template #default="scope">
            {{ parseFloat(scope.row.entryPrice).toFixed(5) }}
          </template>
        </el-table-column>
        <el-table-column prop="unrealizedProfit" label="未实现盈亏" width="120" sortable>
          <template #default="scope">
            <span :class="getPnlValue(scope.row) >= 0 ? 'text-success' : 'text-danger'">
              {{ formatPnl(scope.row) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button 
              size="small" 
              type="warning" 
              @click="closePosition(scope.row)"
            >
              平仓
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div v-if="filteredPositionsData.length === 0 && !loading" class="no-data">
        暂无持仓数据
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue';
import { parseApiResult } from '@/utils/apiHelper';
import { getCurrentUser } from '@/services/auth';
import MarkPriceDisplay from '@/components/common/MarkPriceDisplay.vue';

export default {
  name: 'PositionList',
  components: {
    MarkPriceDisplay,
    ArrowUp,
    ArrowDown
  },
  props: {
    positions: {
      type: Array,
      default: () => []
    },
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
    }
  },
  emits: ['batch-close', 'system-message'],
  setup(props, { emit }) {
    const loading = ref(false);
    const positionsData = ref([]);
    const selectedSymbol = ref('');
    const autoRefresh = ref(false);
    const refreshTimer = ref(null);
    const localRefreshInterval = ref(200); // 默认使用200毫秒的高频刷新
    const refreshCounter = ref(0); // 添加刷新计数器，用于周期性完整刷新
    
    // 交易费用统计面板折叠状态控制
    const markPriceVisible = ref(true); // 默认展开
    
    // 消息处理相关
    const showMessageDialog = ref(false);
    const processingMessages = ref([]);
    
    // 添加处理消息，同时向父组件发送
    const addProcessingMessage = (type, title, description) => {
      const message = {
        type, // success, warning, info, error
        title,
        description,
        time: new Date().toLocaleTimeString()
      };
      
      processingMessages.value.push(message);
      
      // 显示本地消息窗口
      showMessageDialog.value = true;
      
      // 向父组件发送消息
      emit('system-message', message);
    };
    
    // 发送组件状态
    const sendComponentStatus = (status, message) => {
      const statusMessage = {
        type: status === '正常' ? 'success' : status === '警告' ? 'warning' : 'error',
        title: '组件状态更新',
        description: `PositionList组件状态: ${message}`,
        componentStatus: {
          component: 'PositionList',
          status: status,
          message: message
        }
      };
      
      // 向父组件发送状态消息
      emit('system-message', statusMessage);
    };
    
    // 标记价格显示组件引用
    const markPriceDisplayRef = ref(null);
    
    // 处理标记价格更新事件
    const handleMarkPricesRefreshed = () => {
      console.log('标记价格已更新');
      sendComponentStatus('正常', '标记价格已更新');
    };
    
    // 处理消息窗口关闭
    const handleCloseMessageDialog = () => {
      showMessageDialog.value = false;
    };
    
    // 计算属性：当前使用的交易对
    const currentSymbol = computed(() => {
      if (selectedSymbol.value) return selectedSymbol.value;
      if (!props.globalSymbol) return '';
      
      // 根据合约类型调整交易对后缀
      if (props.contractType === 'CM') {
        // 币本位合约，将后缀改为USD_PERP
        if (props.globalSymbol.endsWith('USDT')) {
          return props.globalSymbol.replace('USDT', 'USD_PERP');
        }
        // 如果已经是币本位格式，不做改变
        return props.globalSymbol;
      } else {
        // U本位合约，将后缀改为USDT
        if (props.globalSymbol.endsWith('USD_PERP')) {
          return props.globalSymbol.replace('USD_PERP', 'USDT');
        }
        // 如果已经是U本位格式，不做改变
        return props.globalSymbol;
      }
    });
    
    // 根据筛选条件过滤持仓
    const filteredPositionsData = computed(() => {
      if (!currentSymbol.value) {
        return positionsData.value;
      }
      
      return positionsData.value.filter(position => position.symbol === currentSymbol.value);
    });
    
    // 常用交易对
    const commonSymbols = ref([
      'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
      'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'LTCUSDT', 'MATICUSDT'
    ]);
    
    // 缩短邮箱显示
    const getShortEmail = (email) => {
      if (!email) return '';
      const parts = email.split('@');
      if (parts.length < 2) return email;
      
      const name = parts[0];
      // 如果名称部分超过10个字符，截取并添加省略号
      const shortName = name.length > 10 ? name.substring(0, 8) + '...' : name;
      return shortName;
    };
    
    // 获取盈亏值（处理字段名不一致的情况）
    const getPnlValue = (position) => {
      // 按照可能的字段名顺序尝试获取
      const pnlValue = position.unrealizedProfit || position.unRealizedProfit || position.unrealisedProfit || 0;
      return parseFloat(pnlValue);
    };
    
    // 格式化盈亏显示
    const formatPnl = (position) => {
      const pnlValue = getPnlValue(position);
      return pnlValue.toFixed(2);
    };
    
    // 获取收益率值（处理字段名不一致的情况和可能的计算错误）
    const getPnlPercentage = (position) => {
      // 尝试获取现有的收益率，如果不存在则尝试计算
      if (position.pnlPercentage !== undefined) {
        const pnlPercentage = parseFloat(position.pnlPercentage);
        console.log(`使用已有收益率数据: ${position.symbol}, ${position.side}, pnlPercentage=${pnlPercentage.toFixed(2)}%`);
        return pnlPercentage;
      }
      
      try {
        // 如果没有预计算的收益率，尝试重新计算
        const pnlValue = getPnlValue(position);
        const entryPrice = parseFloat(position.entryPrice || 0);
        const positionAmt = parseFloat(position.positionAmt || 0);
        const leverage = parseFloat(position.leverage || 1); // 获取杠杆倍数，默认为1
        
        if (entryPrice <= 0 || positionAmt === 0) {
          console.log(`计算收益率失败，无效的参数: entryPrice=${entryPrice}, positionAmt=${positionAmt}`);
          return 0;
        }
        
        // 计算开仓价值
        const positionValue = Math.abs(entryPrice * positionAmt);
        
        // 计算实际保证金价值（考虑杠杆）
        const marginValue = positionValue / leverage;
        
        // 预防除以零错误
        if (marginValue <= 0) {
          console.log(`计算收益率失败，保证金价值为0: positionValue=${positionValue}, leverage=${leverage}`);
          return 0;
        }
        
        // 计算收益率 = 未实现盈亏 / 保证金价值 * 100
        const percentage = (pnlValue / marginValue) * 100;
        console.log(`计算收益率: ${position.symbol}, ${position.side}, pnl=${pnlValue.toFixed(2)}, margin=${marginValue.toFixed(2)}, percentage=${percentage.toFixed(2)}%`);
        return percentage;
      } catch (e) {
        console.error('计算收益率失败:', e, position);
        return 0;
      }
    };
    
    // 格式化收益率显示
    const formatPnlPercentage = (position) => {
      const percentage = getPnlPercentage(position);
      return percentage.toFixed(2);
    };
    
    const fetchPositions = async (showLoading = true) => {
      if (!props.subaccounts || props.subaccounts.length === 0) {
        ElMessage.info('请选择至少一个子账户');
        return;
      }
      
      const emails = props.subaccounts.map(account => account.email);
      if (showLoading) {
      loading.value = true;
      }
      
      // 发送正在加载状态
      sendComponentStatus('正常', '正在加载持仓数据...');
      
      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          loading.value = false;
          return;
        }
        
        const token = user.token;
        
        console.log("发送请求参数：", { emails, symbol: currentSymbol.value });
        
        // 收集所有子账号的持仓数据
        const allPositions = [];
        let hasError = false;
        
        // 创建异步查询任务数组，实现并行查询
        const queryTasks = emails.map(email => {
          return (async () => {
          try {
              console.log(`开始查询子账号 ${email} 的持仓信息，合约类型: ${props.contractType}`);
              const emailPositions = [];
              
            if (props.contractType === 'UM') { // 仅当选择U本位合约时查询
              // 查询统一账户U本位持仓信息
                try {
                  console.log(`发送U本位持仓查询请求: ${email}`);
                  
            const umResponse = await axios.post('/api/subaccounts/portfolio-margin/um/positions', {
              email: email,
                    symbol: currentSymbol.value, // 使用当前交易对过滤
                    contractType: 'UM' // 添加合约类型参数
            }, {
              headers: {
                'Authorization': `Bearer ${token}`
                    },
                    // 添加超时设置
                    timeout: 30000 // 30秒
            });
            
            const umResult = parseApiResult(umResponse);
            
            if (umResult.success && umResult.data) {
              // 过滤掉数量为0的持仓
              const validPositions = umResult.data.filter(pos => parseFloat(pos.positionAmt) !== 0);
              
              if (validPositions.length > 0) {
                // 处理持仓数据格式，直接添加每个持仓记录，不做合并
                validPositions.forEach(position => {
                  // 确定持仓方向
                  const side = parseFloat(position.positionAmt) > 0 ? '多头' : '空头';
                  
                        emailPositions.push({
                    ...position,
                    email: email,
                    side: side,
                    accountType: 'UM_PORTFOLIO_MARGIN'  // 标记为U本位统一账户
                });
                });
              }
                    return { success: true, positions: emailPositions };
            } else if (!umResult.success) {
              console.error(`获取子账号 ${email} 的U本位持仓失败:`, umResult.error || '未知错误');
                    return { success: false, email, error: umResult.error || '未知错误' };
                  }
                } catch (umError) {
                  console.error(`U本位持仓查询出错:`, umError);
                  return { success: false, email, error: umError.message || '网络错误' };
            }
            } else if (props.contractType === 'CM') { // 仅当选择币本位合约时查询
              // 查询统一账户币本位持仓信息
                try {
            const cmResponse = await axios.post('/api/subaccounts/portfolio-margin/cm/positions', {
                    email: email,
                    symbol: currentSymbol.value, // 添加当前交易对过滤
                    contractType: 'CM' // 添加合约类型参数
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
                    },
                    timeout: 30000 // 30秒
        });
        
            const cmResult = parseApiResult(cmResponse);
        
            if (cmResult.success && cmResult.data) {
              // 过滤掉数量为0的持仓
              const validPositions = cmResult.data.filter(pos => parseFloat(pos.positionAmt) !== 0);
              
              if (validPositions.length > 0) {
                // 处理持仓数据格式，直接添加每个持仓记录，不做合并
                validPositions.forEach(position => {
                  // 确定持仓方向
                  const side = parseFloat(position.positionAmt) > 0 ? '多头' : '空头';
                  
                        emailPositions.push({
                ...position,
                    email: email,
                    side: side,
                    accountType: 'CM_PORTFOLIO_MARGIN'  // 标记为币本位统一账户
                });
                });
              }
                    return { success: true, positions: emailPositions };
            } else if (!cmResult.success) {
              console.error(`获取子账号 ${email} 的币本位持仓失败:`, cmResult.error || '未知错误');
                    return { success: false, email, error: cmResult.error || '未知错误' };
              }
                } catch (cmError) {
                  console.error(`币本位持仓查询出错:`, cmError);
                  return { success: false, email, error: cmError.message || '网络错误' };
            }
              }
              
              return { success: true, positions: emailPositions };
          } catch (error) {
            console.error(`处理子账号 ${email} 时出错:`, error);
              return { success: false, email, error: error.message || '未知错误' };
            }
          })();
        });
        
        // 并行执行所有查询任务
        const results = await Promise.all(queryTasks);
        
        // 处理查询结果
        results.forEach(result => {
          if (result.success) {
            // 将成功查询的持仓添加到总持仓列表
            allPositions.push(...(result.positions || []));
          } else {
            // 标记有错误发生
            hasError = true;
            console.error(`查询子账号 ${result.email} 持仓失败:`, result.error);
          }
        });
        
        console.log('收集到的持仓数据:', allPositions);
        
        // 赋值到当前持仓列表
        positionsData.value = allPositions;
        
        // 更新统计信息
        console.log(`刷新完成，获取到 ${allPositions.length} 个持仓记录`);
        
        // 更新标记价格
        if (markPriceDisplayRef.value) {
          console.log('更新标记价格');
          markPriceDisplayRef.value.refreshMarkPrices();
        }
        
        // 发送正常状态
        sendComponentStatus('正常', `持仓数据已更新 (${allPositions.length}个持仓)`);
        
        if (hasError) {
          ElMessage.warning('部分子账户查询失败，请检查网络连接');
        }
      } catch (error) {
        console.error('获取持仓信息失败:', error);
        ElMessage.error('获取持仓信息失败');
        sendComponentStatus('错误', `获取持仓信息失败: ${error.message || '未知错误'}`);
      } finally {
        loading.value = false;
      }
    };
    
    const closePosition = async (position) => {
      try {
        // 确定正确的positionSide - 双向持仓模式下
        let positionSide;
        
        // 根据持仓方向（正负）确定positionSide
        if (parseFloat(position.positionAmt) > 0) {
          positionSide = 'LONG';
        } else {
          positionSide = 'SHORT';
        }
        
        await ElMessageBox.confirm(
          `确定要平掉子账号 ${position.email} 的 ${position.symbol} ${position.side}仓位吗？`,
          '确认平仓',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        loading.value = true;
        
        // 获取当前用户
        const user = getCurrentUser();
        if (!user || !user.token) {
          ElMessage.error('用户未登录或token无效');
          loading.value = false;
          return;
        }
        
        // 执行平仓操作，包含自动重试机制
        const closeWithRetry = async (email, symbol, initialPositionSide) => {
          // 第一次尝试
          try {
        const response = await axios.post('/api/subaccounts/portfolio-margin/close-position', {
              email: email,
              symbol: symbol,
              positionSide: initialPositionSide,
          percentage: 100 // 全部平仓
        }, {
          headers: {
            'Authorization': `Bearer ${user.token}`
              },
              timeout: 30000 // 30秒超时
        });
        
        const result = parseApiResult(response);
        if (result.success) {
              return { success: true, message: '平仓成功' };
            }
            
          // 检查是否是持仓模式不匹配的错误
          if (result.error && result.error.indexOf("position side does not match") !== -1) {
            // 尝试切换positionSide再重试一次
              const newPositionSide = initialPositionSide === 'BOTH' ? 
                                    (parseFloat(position.positionAmt) > 0 ? 'LONG' : 'SHORT') : 
                                    'BOTH';
                                    
            ElMessage.warning(`尝试使用${newPositionSide === 'BOTH' ? '单向' : '双向'}持仓模式重新平仓`);
            
            // 重新发送请求
            const retryResponse = await axios.post('/api/subaccounts/portfolio-margin/close-position', {
                email: email,
                symbol: symbol,
              positionSide: newPositionSide,
              percentage: 100 // 全部平仓
            }, {
              headers: {
                'Authorization': `Bearer ${user.token}`
                },
                timeout: 30000 // 30秒超时
            });
            
            const retryResult = parseApiResult(retryResponse);
            if (retryResult.success) {
                return { success: true, message: '平仓成功(重试)' };
            } else {
                return { success: false, message: retryResult.message || '未知错误' };
            }
          } else {
              return { success: false, message: result.message || '未知错误' };
            }
          } catch (error) {
            return { success: false, message: error.message || '网络错误' };
          }
        };
        
        // 执行平仓并获取结果
        const closeResult = await closeWithRetry(position.email, position.symbol, positionSide);
        
        if (closeResult.success) {
          ElMessage.success(closeResult.message);
          // 刷新持仓列表
          fetchPositions(true);
        } else {
          ElMessage.error(`平仓失败: ${closeResult.message}`);
          }
      } catch (error) {
        if (error === 'cancel') {
          // 用户取消操作，不提示错误
          return;
        }
        console.error('平仓操作失败:', error);
        ElMessage.error('网络错误，平仓失败');
      } finally {
        loading.value = false;
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
    
    // 监听全局自动刷新状态变化
    watch(() => props.globalAutoRefresh, (newValue) => {
      autoRefresh.value = newValue;
      
      if (newValue) {
        // 从props获取刷新间隔，如果有的话
        if (props.refreshInterval) {
          localRefreshInterval.value = props.refreshInterval;
        }
        startAutoRefresh();
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
      
      // 创建定时器实现自动刷新，使用本地刷新间隔设置，最短间隔为200毫秒
      const interval = Math.max(200, localRefreshInterval.value || 5000);
      console.log(`[PositionList] 启动自动刷新，间隔: ${interval}ms，优化收益率检测频率`);
      
      refreshTimer.value = setInterval(() => {
        if (markPriceDisplayRef.value) {
          // 如果已经有持仓数据且markPriceDisplay组件已加载，则优先刷新标记价格
          if (positionsData.value.length > 0) {
            console.log('执行轻量级刷新，立即更新标记价格并检查收益率');
            
            // 传递true参数，确保价格更新后立即检查收益率
            markPriceDisplayRef.value.refreshMarkPrices(true); 
            
            // 每5次轻量级刷新后执行1次完整刷新
            refreshCounter.value++;
            if (refreshCounter.value >= 100) {
              refreshCounter.value = 0;
              console.log('执行周期性完整刷新，获取最新持仓数据');
              fetchPositions(false);
            }
          } else {
            // 如果没有持仓数据，则执行完整刷新
            console.log('执行完整刷新，获取持仓数据');
            fetchPositions(false); // false表示不显示loading状态
          }
        } else {
          // 如果没有找到markPriceDisplay组件引用，则执行完整刷新
          fetchPositions(false);
        }
      }, interval);
      
      sendComponentStatus('正常', `自动刷新已启动，间隔${interval/1000}秒，已优化检测频率`);
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
      }
    };
    
    // 监听全局交易对变化
    watch(() => props.globalSymbol, (newSymbol) => {
      if (newSymbol && !selectedSymbol.value) {
        // 如果有全局交易对并且未选择特定交易对，自动查询
        fetchPositions(true);
      }
    });
    
    // 监听合约类型变化
    watch(() => props.contractType, () => {
      // 如果合约类型变化且使用全局交易对，重新查询
      if (props.globalSymbol && !selectedSymbol.value) {
        fetchPositions(true);
      }
    });
    
    // 组件挂载时执行
    onMounted(() => {
      // 设置自动刷新初始状态
      autoRefresh.value = props.globalAutoRefresh;
      
      // 设置初始刷新间隔
      if (props.refreshInterval) {
        localRefreshInterval.value = props.refreshInterval;
      }
      
      // 组件启动时立即获取一次数据
      fetchPositions(true);
      
      // 启动自动刷新
      if (autoRefresh.value) {
        startAutoRefresh();
      }
      
      // 组件挂载时发送状态信息
      sendComponentStatus('正常', '持仓列表组件已加载');
    });
    
    // 组件卸载时清理资源
    onUnmounted(() => {
      stopAutoRefresh();
      sendComponentStatus('正常', '持仓列表组件已卸载');
    });
    
    return {
      loading,
      positionsData,
      filteredPositionsData,
      selectedSymbol,
      currentSymbol,
      commonSymbols,
      autoRefresh,
      localRefreshInterval,
      getShortEmail,
      getPnlValue,
      formatPnl,
      getPnlPercentage,
      formatPnlPercentage,
      fetchPositions,
      closePosition,
      startAutoRefresh,
      stopAutoRefresh,
      handleAutoRefreshChange,
      handleIntervalChange,
      showMessageDialog,
      processingMessages,
      handleCloseMessageDialog,
      addProcessingMessage,
      markPriceVisible,
      markPriceDisplayRef,
      handleMarkPricesRefreshed
    };
  }
}
</script>

<style scoped>
.position-container {
  padding: 10px;
}

.position-list-card {
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

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

/* 折叠面板样式 */
.mb-3 {
  margin-bottom: 1rem;
}

.ms-2 {
  margin-left: 0.5rem;
}

.d-flex {
  display: flex;
}

.align-items-center {
  align-items: center;
}

.collapse-header {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
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

/* 新添加的样式 */
.price-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px 4px 0 0;
  border: 1px solid #e6e6e6;
  margin-bottom: 0;
}

.panel-title {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
}

.price-panel-content {
  padding: 10px;
  border: 1px solid #e6e6e6;
  border-top: none;
  margin-bottom: 15px;
  border-radius: 0 0 4px 4px;
  background-color: #ffffff;
}
</style> 