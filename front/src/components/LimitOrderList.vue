<template>
  <div id="order-list-component" class="limit-order-container">
    <!-- 网格建仓进度条 -->
    <el-card v-if="gridProgress.isRunning" class="mb-3">
      <el-alert
        type="info"
        :title="`正在执行网格建仓: ${gridProgress.current}/${gridProgress.total} 订单`"
        show-icon
      >
        <el-progress :percentage="gridProgress.percentage" />
        <div class="mt-2 text-muted">
          <small>正在为您执行网格建仓，订单将陆续出现在下方列表中。请勿刷新页面。</small>
        </div>
      </el-alert>
    </el-card>

    <el-card class="order-list-card">
      <template #header>
        <div class="card-header">
          <span>挂单列表</span>
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
            <el-select
              v-model="orderTypeFilter"
              style="margin-right: 10px; width: 120px;"
            >
              <el-option label="所有订单" value="ALL" />
              <el-option label="仅限价单" value="LIMIT" />
              <el-option label="仅市价单" value="MARKET" />
            </el-select>
            <el-button type="primary" @click="debouncedFetchOrders(true)" :loading="loading">刷新</el-button>
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
              <el-option :value="500" label="0.5秒" />
              <el-option :value="1000" label="1秒" />
              <el-option :value="2000" label="2秒" />
              <el-option :value="3000" label="3秒" />
              <el-option :value="5000" label="5秒" />
          </el-select>
        </template>
        
        <div class="ms-auto">
          <el-switch
            v-model="autoCloseTimeout"
            :active-text="'自动处理超时挂单 (' + (autoCloseTimeout ? '开启' : '关闭') + ')'"
            inline-prompt
          />
          <span class="ms-2" v-if="autoCloseTimeout">
            <small class="text-muted">15秒未成交自动取消并市价补单</small>
          </span>
        </div>
        <div class="ms-2" v-if="loading">
          <small class="text-muted"><i class="el-icon-loading"></i> 正在刷新数据...</small>
        </div>
      </div>
      
      <el-table 
        :data="filteredOrdersData" 
        border
        style="width: 100%"
        max-height="500px"
        :default-sort="{ prop: 'time', order: 'descending' }"
      >
        <el-table-column prop="email" label="子账号" width="180" sortable>
          <template #default="scope">
            <el-tooltip :content="scope.row.email" placement="top" :show-after="500">
              <span>{{ getShortEmail(scope.row.email) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="orderId" label="订单编号" width="120" sortable />
        <el-table-column prop="symbol" label="交易对" width="120" sortable />
        <el-table-column prop="type" label="类型" width="100" sortable>
          <template #default="scope">
            {{ getOrderType(scope.row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="side" label="操作" width="80" sortable>
          <template #default="scope">
            <el-tag :type="scope.row.side === 'BUY' ? 'success' : 'danger'">
              {{ getOrderDirection(scope.row.side, scope.row.positionSide) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="origQty" label="委托数量" width="120" sortable />
        <el-table-column prop="executedQty" label="成交数量" width="120" sortable />
        <el-table-column prop="price" label="价格" width="120" sortable>
          <template #default="scope">
            <span v-if="scope.row.type === 'LIMIT'">{{ scope.row.price }}</span>
            <span v-else-if="scope.row.type === 'MARKET'">市价</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="下单时间" width="180" sortable>
          <template #default="scope">
            {{ formatOrderTime(scope.row.time) }}
            <span v-if="isOrderTimeout(scope.row)" class="timeout-tag">
              <el-tag type="danger" size="small">超时</el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" sortable>
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ translateStatus(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button 
              size="small" 
              type="danger" 
              @click="cancelOrder(scope.row)"
              :disabled="scope.row.status !== 'NEW'"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div v-if="filteredOrdersData.length === 0 && !loading" class="no-data">
        暂无订单数据
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, reactive, nextTick } from 'vue';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import { parseApiResult } from '@/utils/apiHelper';
import { getCurrentUser } from '@/services/auth';

export default {
  name: 'LimitOrderList',
  components: {},
  props: {
    orders: {
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
      default: 1000
    },
    keepRefreshWhenHidden: {
      type: Boolean,
      default: true  // 默认为true，表示在组件隐藏时继续刷新
    }
  },
  emits: ['system-message'],
  setup(props, { emit }) {
    const loading = ref(false);
    const ordersData = ref([]);
    const selectedSymbol = ref('');
    const orderTypeFilter = ref('ALL'); // 默认显示所有订单
    const viewMode = ref('ALL'); // 默认查看全部挂单
    const debounceTimer = ref(null); // 保留防抖计时器
    const autoCloseTimeout = ref(true); // 默认启用自动处理超时挂单
    const timeoutDuration = 15 * 1000; // 15秒超时时间
    const processingOrders = ref(new Set()); // 正在处理的订单ID集合
    const localRefreshInterval = ref(3000); // 默认3秒刷新一次
    const isVisible = ref(true); // 组件是否可见
    const componentRef = ref(null); // 添加组件引用
    
    // 添加网格建仓进度状态
    const gridProgress = reactive({
      isRunning: false,
      current: 0,
      total: 0,
      percentage: 0
    });
    
    // 已移除限流相关代码
    
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
    
    // 处理嵌套订单数据为展平的数组（用于表格展示）
    const flattenedOrders = computed(() => {
      const result = [];
      
      // 如果订单数据是数组（多个子账号）
      if (Array.isArray(ordersData.value)) {
        ordersData.value.forEach(accountOrders => {
          if (accountOrders.success && accountOrders.orders && Array.isArray(accountOrders.orders)) {
            // 为每个订单添加子账号信息
            accountOrders.orders.forEach(order => {
              result.push({
                ...order,
                email: accountOrders.email
              });
            });
          }
        });
      } 
      // 如果订单数据是单个对象（单个子账号）
      else if (ordersData.value && ordersData.value.orders && Array.isArray(ordersData.value.orders)) {
        ordersData.value.orders.forEach(order => {
          result.push({
            ...order,
            email: ordersData.value.email
          });
        });
      }
      
      // 按时间降序排序
      return result.sort((a, b) => b.time - a.time);
    });
    
    // 根据筛选条件过滤订单
    const filteredOrdersData = computed(() => {
      let filteredOrders = flattenedOrders.value;
      
      // 按订单类型过滤
      if (orderTypeFilter.value !== 'ALL') {
        filteredOrders = filteredOrders.filter(order => order.type === orderTypeFilter.value);
      }
      
      // 按交易对过滤
      if (currentSymbol.value) {
        filteredOrders = filteredOrders.filter(order => order.symbol === currentSymbol.value);
      }
      
      return filteredOrders;
    });
    
    // 计算属性：是否有活跃订单可取消
    const hasActiveOrders = computed(() => {
      return filteredOrdersData.value.some(order => order.status === 'NEW');
    });
    
    // 监听prop变化，避免在子账号列表变化时触发多余请求
    watch(() => props.subaccounts, (newVal, oldVal) => {
      // 仅当子账号数量或内容有实质变化时才重新加载
      const oldEmails = oldVal.map(acc => acc.email).sort().join(',');
      const newEmails = newVal.map(acc => acc.email).sort().join(',');
      
      if (oldEmails !== newEmails) {
        console.log('子账号列表变化，重新加载订单数据');
        if (!loading.value) {
          debouncedFetchOrders();
        }
      }
    }, { deep: true });
    
    // 常用交易对
    const commonSymbols = ref([
      'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
      'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'LTCUSDT', 'MATICUSDT'
    ]);
    
    // 格式化订单时间
    const formatOrderTime = (timestamp) => {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      
      // 获取月日
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const day = date.getDate().toString().padStart(2, '0');
      
      // 获取时分秒
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const seconds = date.getSeconds().toString().padStart(2, '0');
      
      // 返回格式化的日期时间字符串：MM-DD HH:MM:SS
      return `${month}-${day} ${hours}:${minutes}:${seconds}`;
    };
    
    // 获取订单类型中文名称
    const getOrderType = (type) => {
      const types = {
        'LIMIT': '限价委托',
        'MARKET': '市价委托'
      };
      return types[type] || type;
    };
    
    const getStatusTagType = (status) => {
      switch (status) {
        case 'NEW': return 'primary';
        case 'PARTIALLY_FILLED': return 'warning';
        case 'FILLED': return 'success';
        case 'CANCELED': return 'info';
        case 'REJECTED': return 'danger';
        case 'EXPIRED': return 'info';
        default: return 'info';
      }
    };
    
    const translateStatus = (status) => {
      const statusMap = {
        'NEW': '未成交',
        'PARTIALLY_FILLED': '部分成交',
        'FILLED': '已成交',
        'CANCELED': '已取消',
        'REJECTED': '已拒绝',
        'EXPIRED': '已过期'
      };
      return statusMap[status] || status;
    };
    
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
    
    // 获取订单方向的中文描述
    const getOrderDirection = (side, positionSide) => {
      if (!side) return '';
      
      if (side === 'BUY') {
        return positionSide === 'SHORT' ? '平空' : '开多';
      } else if (side === 'SELL') {
        return positionSide === 'LONG' ? '平多' : '开空';
      }
      return side;
    };
    
    // 检查订单是否超时（15秒）
    const isOrderTimeout = (order) => {
      if (order.status !== 'NEW') return false;
      if (order.type !== 'LIMIT') return false;
      
      const now = Date.now();
      const orderTime = order.time;
      return (now - orderTime) > timeoutDuration;
    };
    
    // 执行市价补单操作
    const executeMarketOrder = async (params, token) => {
      try {
        const response = await axios.post('/api/subaccounts/place-order', params, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          timeout: 30000 // 30秒超时
        });
        
        const result = parseApiResult(response);
        
        if (result.success) {
          return { success: true, data: result.data };
        } else {
          return { success: false, error: result.message || '未知错误' };
        }
      } catch (error) {
        return { success: false, error: error.message || '网络错误' };
      }
    };
    
    // 处理单个超时订单
    const handleTimeoutOrder = async (order, email, token) => {
      const orderId = order.orderId.toString();
      
      // 如果订单已经在处理中，跳过
      if (processingOrders.value.has(orderId)) {
        return { processed: false, reason: 'already_processing' };
      }
      
      // 标记为正在处理
      processingOrders.value.add(orderId);
      
      try {
        // 1. 先取消订单
        const cancelResult = await executeCancelOrder({
          email: email,
          symbol: order.symbol,
          orderId: parseInt(order.orderId, 10),
          contractType: props.contractType
        }, token);
        
        if (!cancelResult.success) {
          // 取消失败，返回结果
          return { 
            processed: true, 
            cancelled: false, 
            error: cancelResult.error,
            order: {
              ...order,
              email: email
            }
          };
        }
        
        // 2. 计算需要补齐的数量
        const executedQty = parseFloat(order.executedQty || 0);
        const origQty = parseFloat(order.origQty || 0);
        const remainingQty = origQty - executedQty;
        
        // 取消成功，但无需补单
        if (remainingQty <= 0) {
          return { 
            processed: true, 
            cancelled: true, 
            filledWithMarket: false,
            order: {
              ...order,
              email: email
            }
          };
        }
        
        // 3. 下市价单补齐
        const marketParams = {
          email: email,
          symbol: order.symbol,
          side: order.side, // BUY 或 SELL
          type: 'MARKET',
          quantity: remainingQty.toString(),
          recvWindow: 60000,
          contractType: props.contractType
        };
        
        const marketResult = await executeMarketOrder(marketParams, token);
        
        // 返回处理结果
        return { 
          processed: true, 
          cancelled: true, 
          filledWithMarket: marketResult.success,
          marketError: marketResult.success ? null : marketResult.error,
          remainingQty: remainingQty,
          order: {
            ...order,
            email: email
          }
        };
      } catch (error) {
        // 处理过程中的错误
        return { 
          processed: true, 
          error: error.message || '未知错误',
          order: {
            ...order,
            email: email
          }
        };
      } finally {
        // 处理完成，从集合中移除
        processingOrders.value.delete(orderId);
      }
    };

    // 处理超时订单 - 主控函数
    const handleTimeoutOrders = async () => {
      if (!autoCloseTimeout.value) return;
      
      try {
        // 获取当前用户
        const user = getCurrentUser();
        if (!user || !user.token) {
          console.error('用户未登录或token无效');
          return;
        }
        
        const token = user.token;
        
        let ordersProcessed = 0;
        let ordersCancelled = 0;
        let ordersFilledWithMarket = 0;
        let ordersFailed = 0;
        
        // 并行处理所有子账号的超时订单
        const timeoutTasks = [];
        
        // 遍历已经获取到的订单数据
        if (Array.isArray(ordersData.value)) {
          for (const accountData of ordersData.value) {
            if (accountData.success && accountData.orders && accountData.orders.length > 0) {
              const email = accountData.email;
              
              // 过滤出挂单时间超过timeoutDuration的订单
              const now = Date.now();
              const timeoutOrders = accountData.orders.filter(order => {
                const orderTime = parseInt(order.time);
                const elapsedTimeMs = now - orderTime;
                return elapsedTimeMs > timeoutDuration && order.status === 'NEW';
              });
              
              if (timeoutOrders.length > 0) {
                addSystemMessage(
                  'warning',
                  `检测到${timeoutOrders.length}个超时挂单`,
                  `子账号: ${email}, 交易对: ${currentSymbol.value || '全部'}, 将尝试取消并补齐`
                );
                
                // 为每个超时订单创建异步任务
                for (const order of timeoutOrders) {
                  // 将任务添加到列表中，而不是立即执行
                  timeoutTasks.push(() => handleTimeoutOrder(order, email, token));
                }
              }
            }
          }
        }
        
        // 限制并发处理的订单数量，避免过多请求导致API限流
        const maxConcurrent = 5; // 最多同时处理5个订单
        const results = [];
        
        // 分批处理超时订单
        for (let i = 0; i < timeoutTasks.length; i += maxConcurrent) {
          const batch = timeoutTasks.slice(i, i + maxConcurrent).map(task => task());
          const batchResults = await Promise.all(batch);
          results.push(...batchResults);
          
          // 每批次处理完后暂停一小段时间，减轻API压力
          if (i + maxConcurrent < timeoutTasks.length) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }
        
        // 处理结果
        for (const result of results) {
          if (!result.processed) continue;
          
          if (result.error) {
            ordersFailed++;
            addSystemMessage(
              'error',
              `处理订单异常`,
              `子账号: ${result.order?.email}, 交易对: ${result.order?.symbol}, 错误: ${result.error}`
            );
            continue;
          }
          
          if (result.cancelled) {
            ordersCancelled++;
            
            if (result.filledWithMarket) {
              ordersFilledWithMarket++;
              addSystemMessage(
                'success',
                `订单补齐成功`,
                `子账号: ${result.order?.email}, 交易对: ${result.order?.symbol}, 数量: ${result.remainingQty}, 方向: ${result.order?.side === 'BUY' ? '买入' : '卖出'}`
              );
            } else if (result.marketError) {
              addSystemMessage(
                'error',
                `订单补齐失败`,
                `子账号: ${result.order?.email}, 交易对: ${result.order?.symbol}, 错误: ${result.marketError}`
              );
            }
          } else {
            addSystemMessage(
              'warning',
              `取消订单失败`,
              `子账号: ${result.order?.email}, 交易对: ${result.order?.symbol}, 错误: ${result.error || '未知错误'}`
            );
          }
        }
        
        // 如果有处理订单，显示总结
        if (results.length > 0) {
          ordersProcessed = results.length;
          addSystemMessage(
            'success',
            `订单处理完成`,
            `处理订单: ${ordersProcessed}, 取消: ${ordersCancelled}, 市价补齐: ${ordersFilledWithMarket}, 失败: ${ordersFailed}`
          );
          
          // 处理完成后刷新订单列表
          setTimeout(() => {
            fetchOrders(false);
          }, 1000);
        }
      } catch (error) {
        console.error('检查挂单异常:', error);
        addSystemMessage(
          'error',
          `检查挂单异常`,
          error.message || '未知错误'
        );
      }
    };
    
    // 已移除限流相关函数
    
    // 获取订单列表
    const fetchOrders = async (showLoading = true) => {
      // 如果已经在加载中，不要重复请求
      if (loading.value) return Promise.resolve();
      
      // 检查子账号列表是否为空
      if (!props.subaccounts || props.subaccounts.length === 0) {
        if (showLoading) {
          ElMessage.warning('请先选择至少一个子账号');
        }
        ordersData.value = []; // 清空订单数据
        return Promise.resolve();
      }
      
      if (showLoading) {
        loading.value = true;
      }
      
      try {
        // 获取当前用户
        const user = getCurrentUser();
        if (!user || !user.id) {
          ElMessage.error('获取用户信息失败');
          return Promise.reject(new Error('获取用户信息失败'));
        }
        
        // 创建子账号请求列表，每个子账号单独发送异步请求
        const requests = props.subaccounts.map(account => {
          // 构建每个子账号的查询参数
          const params = {
            emails: [account.email], // 单个子账号
            limit: 50,
            contractType: props.contractType
          };
          
          // 如果选择了特定交易对，添加筛选参数
          if (currentSymbol.value) {
            params.symbol = currentSymbol.value;
          }
          
          // 返回单个请求的Promise
          return axios.post('/api/subaccounts/futures-orders', params, {
            headers: {
              'Authorization': `Bearer ${user.token}`
            },
            timeout: 30000 // 30秒超时
          }).then(response => {
            const result = parseApiResult(response);
            if (result.success) {
              return result.data;
            } else {
              console.error(`获取子账号 ${account.email} 订单失败:`, result.message);
              return {
                success: false,
                email: account.email,
                message: result.message || '未知错误',
                orders: []
              };
            }
          }).catch(error => {
            console.error(`获取子账号 ${account.email} 订单网络错误:`, error);
            return {
              success: false,
              email: account.email,
              message: error.message || '网络错误',
              orders: []
            };
          });
        });
        
        // 并行执行所有子账号请求
        const results = await Promise.all(requests);
        
        // 合并结果
        const successResults = results.filter(result => result.success !== false);
        const failedResults = results.filter(result => result.success === false);
        
        // 更新订单数据
        ordersData.value = successResults;
        
        // 显示失败信息
        if (failedResults.length > 0) {
          const failedEmails = failedResults.map(r => getShortEmail(r.email)).join(', ');
          ElMessage.warning(`${failedResults.length}个子账号订单获取失败: ${failedEmails}`);
          addSystemMessage('warning', '部分子账号订单获取失败', 
            `以下子账号订单获取失败: ${failedEmails}, 总共${failedResults.length}/${props.subaccounts.length}个`);
        }
        
        // 计算订单总数
        let totalOrders = 0;
        if (Array.isArray(successResults)) {
          totalOrders = successResults.reduce((sum, account) => {
            return sum + (account.orders?.length || 0);
          }, 0);
        } else if (successResults?.orders) {
          totalOrders = successResults.orders.length;
        }
        
        // 更新组件状态
        if (totalOrders > 0) {
          const modeText = currentSymbol.value ? `(${currentSymbol.value})` : '(全部交易对)';
          sendComponentStatus('正常', `成功加载${totalOrders}个订单数据${modeText}`);
        } else {
          sendComponentStatus('正常', '暂无订单数据');
        }
        
        // 检查超时订单
        if (autoCloseTimeout.value) {
          handleTimeoutOrders();
        }
        
        // 如果网格建仓结束，检查是否有未成交订单，如果没有则停止自动刷新
        checkAndStopAutoRefresh();
        
        return Promise.resolve();
      } catch (error) {
        console.error('获取订单失败:', error);
        ElMessage.error('网络错误，获取订单失败');
        sendComponentStatus('错误', '网络错误，获取订单失败');
        return Promise.reject(error);
      } finally {
        loading.value = false;
      }
    };
    
    // 检查网格建仓状态并通知用户
    const checkAndStopAutoRefresh = () => {
      // 如果网格建仓已结束且开启了自动刷新
      if (!gridProgress.isRunning && autoRefresh.value) {
        // 检查是否有未成交订单
        const hasOpenOrders = filteredOrdersData.value.some(order => order.status === 'NEW');
        
        // 仅通知用户网格建仓状态，不自动停止刷新
        if (!hasOpenOrders) {
          addSystemMessage('info', '网格建仓已完成', '所有订单已成交，自动刷新将继续运行，可手动关闭');
          sendComponentStatus('正常', '网格建仓已完成，所有订单已成交');
        } else {
          addSystemMessage('info', '网格建仓已完成', `还有${filteredOrdersData.value.filter(o => o.status === 'NEW').length}个未成交订单，自动刷新将继续运行`);
          sendComponentStatus('正常', '网格建仓已完成，但仍有未成交订单');
        }
      }
    };
    
    // 添加系统消息函数
    const addSystemMessage = (type, title, description) => {
      emit('system-message', {
        type, // success, warning, info, error
        title,
        description,
        time: new Date().toLocaleTimeString()
      });
    };
    
    // 发送组件状态
    const sendComponentStatus = (status, message) => {
      const statusMessage = {
        type: status === '正常' ? 'success' : status === '警告' ? 'warning' : 'error',
        title: '组件状态更新',
        description: `LimitOrderList组件状态: ${message}`,
        componentStatus: {
          component: 'LimitOrderList',
          status: status,
          message: message
        }
      };
      
      // 向父组件发送状态消息
      emit('system-message', statusMessage);
    };
    
    // 执行取消订单操作的核心函数
    const executeCancelOrder = async (order, token) => {
      try {
        // 获取当前用户
        const user = getCurrentUser();
        if (!user || !user.id) {
          return { success: false, error: '用户未登录或ID无效' };
        }
        
        // 发送取消订单请求
        const response = await axios.post('/api/subaccounts/cancel-order', {
          email: order.email,
          symbol: order.symbol,
          orderId: parseInt(order.orderId, 10),
          user_id: user.id,
          contractType: props.contractType
        }, {
          headers: {
            'Authorization': `Bearer ${token || user.token}`
          },
          timeout: 30000 // 30秒超时
        });
        
        const result = parseApiResult(response);
        
        if (result.success) {
          return { success: true, data: result.data };
        } else {
          return { success: false, error: result.message || '未知错误' };
        }
      } catch (error) {
        return { success: false, error: error.message || '网络错误' };
      }
    };

    // 用户交互的取消订单函数
    const cancelOrder = async (order) => {
      try {
        await ElMessageBox.confirm(
          `确定要取消订单：${order.symbol} ${getOrderDirection(order.side, order.positionSide)} ${order.origQty} @ ${order.price}？`,
          '取消订单',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        loading.value = true;
        
        // 获取当前用户
        const user = getCurrentUser();
        if (!user || !user.id) {
          ElMessage.error('用户未登录或ID无效');
          loading.value = false;
          return;
        }
        
        // 执行取消订单操作
        const result = await executeCancelOrder(order, user.token);
        
        if (result.success) {
          ElMessage.success('取消订单成功');
          addSystemMessage('success', '取消订单成功', `交易对: ${order.symbol}, 订单ID: ${order.orderId}`);
          // 重新获取最新订单列表
          fetchOrders();
        } else {
          ElMessage.error(`取消订单失败: ${result.error}`);
          addSystemMessage('error', '取消订单失败', `交易对: ${order.symbol}, 错误: ${result.error}`);
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('取消订单失败:', error);
          ElMessage.error('取消订单失败');
          addSystemMessage('error', '取消订单网络错误', error.message || '未知错误');
        }
      } finally {
        loading.value = false;
      }
    };
    
    // 添加自动刷新相关变量和方法
    const refreshTimer = ref(null);
    const autoRefresh = ref(false); // 默认不开启自动刷新
    
    // 处理自动刷新开关切换
    const handleAutoRefreshChange = (value) => {
      // 强制设置autoRefresh值，以防事件处理中没有正确更新
      autoRefresh.value = value;
      
      console.log('[LimitOrderList] 自动刷新状态切换为:', value ? '开启' : '关闭');
      
      if (value) {
        // 如果之前没有启动过，则启动自动刷新
        startAutoRefresh();
      } else {
        // 停止自动刷新
        stopAutoRefresh();
        sendComponentStatus('正常', '自动刷新已停止');
      }
    };
    
    // 处理刷新间隔变化
    const handleIntervalChange = () => {
      // 现在使用固定延迟1秒，刷新间隔设置仅作为UI显示用
      console.log(`[LimitOrderList] 间隔设置已更改为${localRefreshInterval.value}ms，但实际使用1秒固定延迟`);
    };
    
    // 监听刷新间隔变化
    watch(() => props.refreshInterval, (newValue) => {
      if (newValue) {
        localRefreshInterval.value = newValue;
        // 如果自动刷新启用，则重新启动定时器
        if (autoRefresh.value) {
          stopAutoRefresh();
          startAutoRefresh();
        }
      }
    });
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      // 检查子账号列表是否为空
      if (!props.subaccounts || props.subaccounts.length === 0) {
        console.log('[LimitOrderList] 子账号列表为空，不启动自动刷新');
        ElMessage.warning('请先选择至少一个子账号');
        autoRefresh.value = false; // 重置自动刷新开关
        return;
      }
      
      stopAutoRefresh(); // 先停止现有的定时器
      
      // 立即执行一次刷新，确保启动时立即获取数据
      fetchOrders(false);
      
      // 改用递归定时器，确保在前一次请求完成并延迟1秒后再发送下一次请求
      const executeRefresh = () => {
        if (!autoRefresh.value) {
          return; // 如果自动刷新被关闭，不再继续
        }
        
        // 在每次刷新前检查子账号列表
        if (!props.subaccounts || props.subaccounts.length === 0) {
          stopAutoRefresh();
          console.log('[LimitOrderList] 子账号列表为空，停止自动刷新');
          return;
        }
        
        // 即使组件不可见，如果设置了keepRefreshWhenHidden为true，也继续刷新
        const shouldFetchData = isVisible.value || props.keepRefreshWhenHidden;
        
        if (shouldFetchData) {
          // 执行数据获取
          fetchOrders(false).then(() => {
            // 请求完成后，等待1秒再发送下一次请求
            refreshTimer.value = setTimeout(() => {
              // 使用递归调用，确保请求是串行的，而不是并行的
              executeRefresh();
              
              // 定期输出状态日志
              if (Math.random() < 0.1) { // 约10%概率输出日志，减少日志量
                console.log(`[LimitOrderList] 自动刷新运行中，延迟1秒，数据条数: ${filteredOrdersData.value.length}，组件状态: ${isVisible.value ? '可见' : '隐藏'}`);
              }
            }, 1000); // 固定等待1秒，不受刷新间隔影响
          }).catch(error => {
            console.error('[LimitOrderList] 刷新数据出错:', error);
            // 出错后也等待1秒再尝试
            refreshTimer.value = setTimeout(executeRefresh, 1000);
          });
        } else {
          // 组件不可见且设置了不在隐藏时刷新，等待并继续检查
          console.log('[LimitOrderList] 组件当前不可见，暂停数据获取但保持刷新状态');
          refreshTimer.value = setTimeout(executeRefresh, 1000);
        }
      };
      
      // 开始递归刷新
      executeRefresh();
      
      sendComponentStatus('正常', `自动刷新已启动，获取数据后延迟1秒再刷新`);
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
        console.log('[LimitOrderList] 自动刷新已停止');
      }
    };
    
    // 组件挂载时初始化
    onMounted(() => {
      // 初始化可见性检测
      initVisibilityDetection();
      
      // 初始化加载订单数据
      if (props.subaccounts && props.subaccounts.length > 0) {
        debouncedFetchOrders(true);
      
        // 强制设置刷新间隔为1000毫秒（1秒）
        localRefreshInterval.value = 1000;
        
        // 默认不开启自动刷新，需要用户手动开启
        // 移除自动刷新启动逻辑
      } else {
        // 强制设置刷新间隔为1000毫秒（1秒）
        localRefreshInterval.value = 1000;
        console.log('[LimitOrderList] 组件挂载时子账号列表为空，不加载数据');
      }
      
      // 添加网格建仓进度事件监听器
      window.addEventListener('grid-progress-update', handleGridProgressUpdate);
      
      // 添加网格建仓完成事件监听器 - 同时在window和document级别添加
      window.addEventListener('grid-trade-completed', handleGridTradeCompleted);
      document.addEventListener('grid-trade-completed', handleGridTradeCompleted);
      
      // 添加网格建仓开始事件监听器 - 同时在window和document级别添加
      window.addEventListener('grid-trade-started', handleGridTradeStarted);
      document.addEventListener('grid-trade-started', handleGridTradeStarted);
      
      // 发送组件已加载状态
      sendComponentStatus('正常', '挂单列表组件已加载');
      
      // 添加调试日志
      console.log('[LimitOrderList] 组件已挂载，已添加grid-trade事件监听器');
    });
    
    // 初始化可见性检测
    const initVisibilityDetection = () => {
      // 检查浏览器是否支持IntersectionObserver
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(
          (entries) => {
            // 只关注第一个条目，因为我们只观察一个元素
            const entry = entries[0];
            isVisible.value = entry.isIntersecting;
            console.log(`[LimitOrderList] 组件可见性变化: ${isVisible.value ? '可见' : '不可见'}`);
            
            // 如果组件变为可见并且自动刷新已开启，执行一次数据刷新
            if (isVisible.value && autoRefresh.value) {
              fetchOrders(false);
            }
          },
          {
            threshold: 0.1 // 当至少10%的组件可见时触发
          }
        );
        
        // 等待DOM更新后再添加观察者
        nextTick(() => {
          const element = document.getElementById('order-list-component');
          if (element) {
            observer.observe(element);
            componentRef.value = element;
            console.log('[LimitOrderList] 已添加可见性监听器');
          }
        });
        
        // 在组件卸载时清理观察者
        onUnmounted(() => {
          if (componentRef.value) {
            observer.unobserve(componentRef.value);
            console.log('[LimitOrderList] 已移除可见性监听器');
          }
        });
      } else {
        console.log('[LimitOrderList] 浏览器不支持IntersectionObserver，无法检测可见性');
        // 如果不支持，始终认为组件是可见的
        isVisible.value = true;
      }
    };
    
    // 组件卸载时清理资源
    onUnmounted(() => {
      // 停止自动刷新
      stopAutoRefresh();
      
      // 移除网格建仓进度事件监听器
      window.removeEventListener('grid-progress-update', handleGridProgressUpdate);
      
      // 移除网格建仓完成事件监听器 - 同时移除window和document级别的监听
      window.removeEventListener('grid-trade-completed', handleGridTradeCompleted);
      document.removeEventListener('grid-trade-completed', handleGridTradeCompleted);
      
      // 移除网格建仓开始事件监听器 - 同时移除window和document级别的监听
      window.removeEventListener('grid-trade-started', handleGridTradeStarted);
      document.removeEventListener('grid-trade-started', handleGridTradeStarted);
      
      // 发送组件已卸载状态
      sendComponentStatus('正常', '挂单列表组件已卸载');
    });
    
    // 处理网格建仓进度更新事件
    const handleGridProgressUpdate = (event) => {
      if (event && event.detail) {
        // 更新网格进度状态
        const wasRunningBefore = gridProgress.isRunning;
        const isRunningNow = event.detail.isRunning;
        
        gridProgress.isRunning = isRunningNow;
        gridProgress.current = event.detail.current;
        gridProgress.total = event.detail.total;
        gridProgress.percentage = event.detail.percentage;
        
        // 当网格建仓开始时，只更新UI，不自动启动刷新
        if (!wasRunningBefore && isRunningNow) {
          // 更新网格进度UI
          addSystemMessage('info', '网格建仓开始', '网格建仓进度已在挂单列表显示');
          sendComponentStatus('正常', '网格建仓已开始，进度条已显示');
        }
        
        // 当网格建仓结束时，通知用户建仓已完成
        if (!isRunningNow && wasRunningBefore) {
          // 延迟检查，以确保最后一批订单数据已加载
          setTimeout(() => {
            if (autoRefresh.value) {
              fetchOrders(true); // 只有当自动刷新已开启时，才刷新获取最新数据
            }
            setTimeout(() => {
              checkAndStopAutoRefresh(); // 只检查并通知
            }, 1000);
          }, 5000); // 5秒后检查，确保所有订单数据已更新
        }
      }
    };
    
    // 处理网格建仓完成事件
    const handleGridTradeCompleted = (event) => {
      console.log('[LimitOrderList] 接收到grid-trade-completed事件', event?.detail);
      if (event && event.detail && event.detail.success) {
        console.log('[LimitOrderList] 网格建仓完成，成功创建订单数:', event.detail.ordersCount);
        
        // 不再自动启动刷新
        // 只通知用户建仓成功
        addSystemMessage('success', '网格建仓完成', `成功创建${event.detail.ordersCount}个订单，如需监控订单状态，请手动开启自动刷新`);
        sendComponentStatus('正常', '网格建仓已完成');
        
        // 如果用户已经手动开启了自动刷新，则刷新一次数据
        if (autoRefresh.value) {
          fetchOrders(true);
        }
      } else {
        console.warn('[LimitOrderList] 收到grid-trade-completed事件但detail为空或success为false', event?.detail);
      }
    };
    
    // 处理网格建仓开始事件
    const handleGridTradeStarted = (event) => {
      console.log('[LimitOrderList] 接收到grid-trade-started事件', event?.detail);
      if (event && event.detail) {
        console.log('[LimitOrderList] 网格建仓开始，交易对:', event.detail.symbol, '预计订单数:', event.detail.ordersCount);
        
        // 不再自动启动刷新，只更新进度UI
        addSystemMessage('info', '网格建仓开始', `网格建仓开始执行，交易对: ${event.detail.symbol}，预计订单数: ${event.detail.ordersCount}。如需实时监控，请手动开启自动刷新`);
        sendComponentStatus('正常', '网格建仓已开始');
        
        // 如果用户已经手动开启了自动刷新，则刷新一次数据
        if (autoRefresh.value) {
          fetchOrders(true);
        }
      } else {
        console.warn('[LimitOrderList] 收到grid-trade-started事件但detail为空');
      }
    };
    
    // 监听全局交易对变化
    watch(() => props.globalSymbol, (newSymbol) => {
      if (newSymbol && !selectedSymbol.value && !loading.value && props.subaccounts && props.subaccounts.length > 0) {
        // 如果有全局交易对并且未选择特定交易对，并且有选中的子账号，自动查询
        debouncedFetchOrders(true);
      }
    });
    
    // 监听合约类型变化
    watch(() => props.contractType, () => {
      // 如果合约类型变化且使用全局交易对，并且有选中的子账号，重新查询
      if (props.globalSymbol && !selectedSymbol.value && !loading.value && props.subaccounts && props.subaccounts.length > 0) {
        debouncedFetchOrders(true);
      }
    });
    
    // 由于viewMode固定为ALL，不再需要监听其变化
    
    // 添加防抖处理，避免短时间内频繁刷新
    const debouncedFetchOrders = (immediate = false) => {
      if (loading.value) return Promise.resolve();
      
      // 检查子账号列表是否为空
      if (!props.subaccounts || props.subaccounts.length === 0) {
        ordersData.value = []; // 清空订单数据
        return Promise.resolve();
      }
      
      return new Promise((resolve, reject) => {
        // 如果标记为立即执行，则立即清除现有定时器并执行
        if (immediate && debounceTimer.value) {
          clearTimeout(debounceTimer.value);
          fetchOrders().then(resolve).catch(reject);
          return;
        }
        
        if (debounceTimer.value) {
          clearTimeout(debounceTimer.value);
        }
        
        debounceTimer.value = setTimeout(() => {
          if (!loading.value) {
            fetchOrders().then(resolve).catch(reject);
          } else {
            resolve();
          }
          debounceTimer.value = null;
        }, 300);
      });
    };
    
    // 提供给外部组件调用的公共刷新方法
    const refreshOrderList = (skipTimeoutCheck = true) => {
      console.log('[LimitOrderList] 外部触发刷新订单列表');
      
      // 暂存自动处理超时挂单的设置
      const originalAutoCloseTimeout = autoCloseTimeout.value;
      
      // 如果需要跳过超时检查，临时禁用自动处理超时挂单
      if (skipTimeoutCheck) {
        autoCloseTimeout.value = false;
      }
      
      // 刷新订单
      return debouncedFetchOrders(true).then(() => {
        // 恢复原始设置
        if (skipTimeoutCheck) {
          autoCloseTimeout.value = originalAutoCloseTimeout;
        }
      }).catch((error) => {
        // 恢复原始设置
        if (skipTimeoutCheck) {
          autoCloseTimeout.value = originalAutoCloseTimeout;
        }
        return Promise.reject(error);
      });
    };
    
    // 监听组件可见性变化
    watch(isVisible, (newValue) => {
      if (newValue && autoRefresh.value) {
        // 组件变为可见且自动刷新已开启，立即刷新一次最新数据
        console.log('[LimitOrderList] 组件变为可见，立即刷新数据');
        fetchOrders(false);
      }
    });
    
    return {
      loading,
      ordersData,
      filteredOrdersData,
      flattenedOrders,
      selectedSymbol,
      currentSymbol,
      orderTypeFilter,
      viewMode,
      commonSymbols,
      autoCloseTimeout,
      gridProgress,
      formatOrderTime,
      getOrderType,
      getStatusTagType,
      translateStatus,
      getShortEmail,
      getOrderDirection,
      isOrderTimeout,
      fetchOrders,
      debouncedFetchOrders,
      refreshOrderList, // 暴露给外部的刷新方法
      cancelOrder,
      handleTimeoutOrders,
      checkAndStopAutoRefresh,
      handleGridProgressUpdate,
      handleGridTradeStarted,
      addSystemMessage,
      sendComponentStatus,
      autoRefresh,
      localRefreshInterval,
      handleAutoRefreshChange,
      handleIntervalChange,
      startAutoRefresh,
      stopAutoRefresh,
      hasActiveOrders,
      handleGridTradeCompleted,
      isVisible,
      componentRef
    };
  }
}
</script>

<style scoped>
.limit-order-container {
  padding: 10px;
}

.order-list-card {
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

.mt-2 {
  margin-top: 0.5rem;
}

.text-muted {
  color: #6c757d;
}

.timeout-tag {
  margin-left: 5px;
}
</style> 