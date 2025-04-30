<template>
  <div class="limit-order-container">
    <el-card class="order-list-card">
      <template #header>
        <div class="card-header">
          <span>订单管理</span>
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
            <el-select
              v-model="orderTypeFilter"
              style="margin-right: 10px; width: 120px;"
            >
              <el-option label="所有订单" value="ALL" />
              <el-option label="仅限价单" value="LIMIT" />
              <el-option label="仅市价单" value="MARKET" />
            </el-select>
            <el-button type="primary" @click="fetchOrders" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>
      
      <div class="d-flex align-items-center mb-3">
        <el-switch
          v-model="autoRefresh"
          :active-text="'自动刷新 (' + (autoRefresh ? '开启' : '关闭') + ')'"
          inline-prompt
        />
        <span class="ms-2" v-if="autoRefresh">
          <small class="text-muted">每3秒自动刷新</small>
        </span>
        <div class="ms-auto" v-if="loading">
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
        <el-table-column prop="订单编号" label="订单编号" width="120" sortable />
        <el-table-column prop="symbol" label="交易对" width="120" sortable />
        <el-table-column prop="type" label="类型" width="100" sortable>
          <template #default="scope">
            {{ getOrderType(scope.row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="方向" label="操作" width="80" sortable>
          <template #default="scope">
            <el-tag :type="scope.row.方向 === '开多' || scope.row.方向 === '平空' ? 'success' : 'danger'">
              {{ scope.row.方向 }}
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import { parseApiResult } from '@/utils/apiHelper';
import { getCurrentUser } from '@/services/auth';

export default {
  name: 'LimitOrderList',
  props: {
    subaccounts: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const loading = ref(false);
    const ordersData = ref([]);
    const selectedSymbol = ref('');
    const orderTypeFilter = ref('ALL'); // 默认显示所有订单
    const autoRefresh = ref(false);
    const refreshTimer = ref(null);
    
    // 根据筛选条件过滤订单
    const filteredOrdersData = computed(() => {
      if (orderTypeFilter.value === 'ALL') {
        return ordersData.value;
      }
      
      return ordersData.value.filter(order => order.type === orderTypeFilter.value);
    });
    
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
    
    const fetchOrders = async () => {
      loading.value = true;
      
      try {
        // 使用传递的子账号列表
        const emails = props.subaccounts.map(account => account.email);
        
        if (emails.length === 0) {
          ElMessage.warning('没有可用的子账号');
          loading.value = false;
          return;
        }
        
        // 获取当前用户信息
        const user = getCurrentUser();
        const userIdValue = user?.id;
        const token = user?.token;
        
        console.log("发送请求参数：", { emails, userId: userIdValue });
        
        // 并行请求：同时获取普通订单和限价单
        const [ordersResponse, limitOrdersResponse] = await Promise.all([
          // 获取普通订单
          axios.post('/api/subaccounts/futures-orders', {
            emails: emails,
            symbol: selectedSymbol.value,
            limit: 50, // 每个账号最多获取50条数据
            userId: userIdValue
          }, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }),
          // 获取限价单
          axios.post('/api/subaccounts/futures-limit-orders', {
            emails: emails,
            symbol: selectedSymbol.value,
            limit: 50, // 每个账号最多获取50条数据
            userId: userIdValue
          }, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
        ]);
        
        // 处理普通订单结果
        const ordersResult = parseApiResult(ordersResponse);
        // 处理限价单结果
        const limitOrdersResult = parseApiResult(limitOrdersResponse);
        
        if (!ordersResult.success && !limitOrdersResult.success) {
          ElMessage.error('获取订单列表失败');
          loading.value = false;
          return;
        }
        
        // 合并所有子账号的订单
        const allOrders = [];
        
        // 添加普通订单
        if (ordersResult.success && ordersResult.data) {
          ordersResult.data.forEach(accountOrders => {
            if (accountOrders.success && accountOrders.orders) {
              // 为每个订单添加子账号信息
              const ordersWithEmail = accountOrders.orders.map(order => ({
                ...order,
                email: accountOrders.email
              }));
              allOrders.push(...ordersWithEmail);
            }
          });
        }
        
        // 添加限价单
        if (limitOrdersResult.success && limitOrdersResult.data) {
          limitOrdersResult.data.forEach(accountOrders => {
            if (accountOrders.success && accountOrders.orders) {
              // 为每个订单添加子账号信息，并确保type是LIMIT
              const ordersWithEmail = accountOrders.orders.map(order => ({
                ...order,
                email: accountOrders.email,
                type: 'LIMIT'
              }));
              
              // 添加到订单列表中，注意避免重复
              ordersWithEmail.forEach(limitOrder => {
                // 检查是否已经存在相同的订单（通过orderId比较）
                const existingOrderIndex = allOrders.findIndex(
                  order => order.orderId === limitOrder.orderId && order.email === limitOrder.email
                );
                
                if (existingOrderIndex === -1) {
                  allOrders.push(limitOrder);
                }
              });
            }
          });
        }
        
        // 按时间降序排序并更新数据
        ordersData.value = allOrders.sort((a, b) => b.time - a.time);
      } catch (error) {
        console.error('获取订单失败:', error);
        ElMessage.error('网络错误，获取订单失败');
      } finally {
        loading.value = false;
      }
    };
    
    const cancelOrder = async (order) => {
      try {
        await ElMessageBox.confirm(
          `确定要取消子账号 ${order.email} 的 ${order.symbol} ${order.方向}订单吗？\n订单编号: ${order.订单编号 || order.orderId}`,
          '确认取消订单',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        loading.value = true;
        
        // 发送取消订单请求
        const response = await axios.post('/api/subaccounts/cancel-order', {
          email: order.email,
          symbol: order.symbol,
          orderId: parseInt(order.订单编号 || order.orderId, 10)
        });
        
        const result = parseApiResult(response);
        
        if (result.success) {
          ElMessage.success('订单取消成功');
          // 重新获取最新订单列表
          fetchOrders();
        } else {
          ElMessage.error(result.error || '取消订单失败');
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('取消订单失败:', error);
          ElMessage.error('取消订单失败');
        }
      } finally {
        loading.value = false;
      }
    };
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      if (!refreshTimer.value) {
        // 立即执行一次查询
        fetchOrders();
        
        // 设置定时器，每3秒查询一次
        refreshTimer.value = setInterval(() => {
          if (!loading.value) {
            fetchOrders();
          }
        }, 3000);
      }
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value);
        refreshTimer.value = null;
      }
    };
    
    // 监听自动刷新开关
    watch(autoRefresh, (newValue) => {
      if (newValue) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
      }
    });
    
    onMounted(() => {
      fetchOrders();
    });
    
    // 组件销毁时清除定时器
    onUnmounted(() => {
      stopAutoRefresh();
    });
    
    return {
      loading,
      ordersData,
      filteredOrdersData,
      selectedSymbol,
      orderTypeFilter,
      commonSymbols,
      autoRefresh,
      formatOrderTime,
      getOrderType,
      getStatusTagType,
      translateStatus,
      getShortEmail,
      fetchOrders,
      cancelOrder
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
</style> 