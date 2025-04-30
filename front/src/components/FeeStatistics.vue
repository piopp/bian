<template>
  <div class="fee-statistics-container">
    <el-card class="fee-stats-card">
      <template #header>
        <div class="card-header">
          <span>手续费统计</span>
          <div class="header-actions">
            <el-button type="primary" @click="refreshFeeStats" :loading="loading">
              <i class="bi bi-arrow-clockwise me-1"></i>刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="mb-3">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="统计概览" name="summary">
            <div class="statistics-summary">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-card shadow="hover" class="stat-card">
                    <div class="stat-title">今日手续费</div>
                    <div class="stat-value">{{ formatValue(todayFees) }}</div>
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card shadow="hover" class="stat-card">
                    <div class="stat-title">本周手续费</div>
                    <div class="stat-value">{{ formatValue(weekFees) }}</div>
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card shadow="hover" class="stat-card">
                    <div class="stat-title">本月手续费</div>
                    <div class="stat-value">{{ formatValue(monthFees) }}</div>
                  </el-card>
                </el-col>
              </el-row>
              
              <el-divider content-position="center">费率参考</el-divider>
              
              <el-table :data="feeRatesData" border style="width: 100%">
                <el-table-column prop="type" label="交易类型" width="180" />
                <el-table-column prop="taker" label="市价单 (Taker) 手续费" />
                <el-table-column prop="maker" label="限价单 (Maker) 手续费" />
              </el-table>
              
              <div class="fee-notes mt-3">
                <p><small>* 根据账户等级和交易量，实际费率可能有所不同</small></p>
                <p><small>* 使用BNB支付手续费可享受25%折扣</small></p>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="历史记录" name="history">
            <div class="fee-history">
              <div class="filter-container mb-3">
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-select v-model="filterAccount" clearable placeholder="选择子账号" style="width: 100%">
                      <el-option
                        v-for="account in subaccounts"
                        :key="account.email"
                        :label="account.email"
                        :value="account.email"
                      />
                    </el-select>
                  </el-col>
                  <el-col :span="8">
                    <el-date-picker
                      v-model="dateRange"
                      type="daterange"
                      range-separator="至"
                      start-placeholder="开始日期"
                      end-placeholder="结束日期"
                      style="width: 100%"
                    />
                  </el-col>
                  <el-col :span="8">
                    <el-button type="primary" @click="searchFeeHistory">
                      <i class="bi bi-search me-1"></i>查询
                    </el-button>
                  </el-col>
                </el-row>
              </div>
              
              <el-table
                :data="feeHistory"
                border
                style="width: 100%"
                v-loading="loading"
              >
                <el-table-column prop="date" label="日期" width="120" sortable>
                  <template #default="scope">
                    {{ formatDate(scope.row.date) }}
                  </template>
                </el-table-column>
                <el-table-column prop="email" label="子账号" width="180" sortable />
                <el-table-column prop="symbol" label="交易对" width="120" sortable />
                <el-table-column prop="type" label="订单类型" width="100" sortable />
                <el-table-column prop="side" label="方向" width="80" sortable>
                  <template #default="scope">
                    <el-tag :type="scope.row.side === '买入' ? 'success' : 'danger'">
                      {{ scope.row.side }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="数量" width="100" sortable />
                <el-table-column prop="price" label="价格" width="120" sortable />
                <el-table-column prop="fee" label="手续费" width="120" sortable>
                  <template #default="scope">
                    <span>{{ scope.row.fee }} {{ scope.row.feeCurrency }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="feeUSDT" label="手续费(USDT)" width="120" sortable>
                  <template #default="scope">
                    {{ calculateOrderFeeDisplay(scope.row) }}
                  </template>
                </el-table-column>
              </el-table>
              
              <div class="pagination-container mt-3">
                <el-pagination
                  background
                  layout="prev, pager, next, sizes, total"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="totalRecords"
                  :page-size="pageSize"
                  :current-page="currentPage"
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
                />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { calculateOrderFee, FEE_RATES } from '../utils/feeCalculator';
import { getCurrentUser } from '../services/auth';

export default {
  name: 'FeeStatistics',
  props: {
    subaccounts: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const loading = ref(false);
    const activeTab = ref('summary');
    const feeHistory = ref([]);
    const totalRecords = ref(0);
    const pageSize = ref(20);
    const currentPage = ref(1);
    const filterAccount = ref('');
    const dateRange = ref(null);
    
    // 费率数据
    const feeRatesData = computed(() => [
      { type: '现货及杠杆', taker: (FEE_RATES.SPOT.TAKER * 100) + '%', maker: (FEE_RATES.SPOT.MAKER * 100) + '%' },
      { type: 'U本位合约(USDT)', taker: (FEE_RATES.USDT_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.USDT_FUTURE.MAKER * 100) + '%' },
      { type: 'U本位合约(USDC)', taker: (FEE_RATES.USDC_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.USDC_FUTURE.MAKER * 100) + '%' },
      { type: '币本位合约', taker: (FEE_RATES.COIN_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.COIN_FUTURE.MAKER * 100) + '%' }
    ]);
    
    // 统计数据
    const todayFees = ref(0);
    const weekFees = ref(0);
    const monthFees = ref(0);
    
    // 格式化日期
    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN');
    };
    
    // 格式化数值
    const formatValue = (value) => {
      return parseFloat(value).toFixed(4) + ' USDT';
    };
    
    // 计算订单手续费并显示
    const calculateOrderFeeDisplay = (order) => {
      // 如果已经有feeUSDT，直接使用
      if (order.feeUSDT) {
        return parseFloat(order.feeUSDT).toFixed(4);
      }
      
      // 否则使用计算工具计算
      const orderData = {
        symbol: order.symbol,
        orderType: order.type === '市价单' ? 'MARKET' : 'LIMIT',
        productType: order.symbol && order.symbol.endsWith('USDT') ? 'USDT_FUTURE' : 'SPOT',
        amount: parseFloat(order.amount) || 0,
        price: parseFloat(order.price) || 0,
        status: 'FILLED', // 假设所有显示的订单都是已成交的
        feeCurrency: order.feeCurrency || 'USDT'
      };
      
      const { feeUSDT } = calculateOrderFee(orderData);
      return parseFloat(feeUSDT).toFixed(4);
    };
    
    // 刷新统计数据
    const refreshFeeStats = async () => {
      loading.value = true;
      try {
        const user = getCurrentUser();
        const token = user?.token;
        
        const params = {};
        
        // 如果选择了特定子账号，则使用该子账号
        if (filterAccount.value) {
          params.email = filterAccount.value;
        } else if (props.subaccounts.length > 0) {
          // 如果未选择特定子账号但有子账号列表，则获取所有子账号的汇总数据
          // 不传递email参数，后端应返回所有子账号的汇总
        } else {
          ElMessage.warning('没有可用的子账号');
          loading.value = false;
          return;
        }
        
        const response = await axios.get('/api/statistics/fee-summary', {
          params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.data && response.data.success) {
          todayFees.value = response.data.data.today || 0;
          weekFees.value = response.data.data.week || 0;
          monthFees.value = response.data.data.month || 0;
        } else {
          ElMessage.error('获取手续费统计失败');
        }
      } catch (error) {
        console.error('获取手续费统计失败:', error);
        ElMessage.error('获取手续费统计失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    // 查询历史记录
    const searchFeeHistory = async () => {
      loading.value = true;
      try {
        const user = getCurrentUser();
        const token = user?.token;
        
        const params = {
          page: currentPage.value,
          pageSize: pageSize.value
        };
        
        // 如果选择了特定子账号，则使用该子账号
        if (filterAccount.value) {
          params.email = filterAccount.value;
        } else if (props.subaccounts.length > 0) {
          // 如果未选择特定子账号，并且有可用子账号，则查询所有子账号
          // 不指定email参数，后端将返回所有子账号的数据
        } else {
          ElMessage.warning('没有可用的子账号');
          loading.value = false;
          return;
        }
        
        if (dateRange.value && dateRange.value.length === 2) {
          params.startDate = dateRange.value[0].toISOString().split('T')[0];
          params.endDate = dateRange.value[1].toISOString().split('T')[0];
        }
        
        const response = await axios.get('/api/statistics/fee-trend', { 
          params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.data && response.data.success) {
          feeHistory.value = response.data.data.records || [];
          totalRecords.value = response.data.data.total || 0;
        } else {
          ElMessage.error('获取手续费历史记录失败');
        }
      } catch (error) {
        console.error('获取手续费历史记录失败:', error);
        ElMessage.error('获取手续费历史记录失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    // 处理分页大小变化
    const handleSizeChange = (size) => {
      pageSize.value = size;
      searchFeeHistory();
    };
    
    // 处理页码变化
    const handleCurrentChange = (page) => {
      currentPage.value = page;
      searchFeeHistory();
    };
    
    // 组件挂载时加载数据
    onMounted(() => {
      refreshFeeStats();
      searchFeeHistory();
    });
    
    return {
      loading,
      activeTab,
      feeHistory,
      totalRecords,
      pageSize,
      currentPage,
      filterAccount,
      dateRange,
      feeRatesData,
      todayFees,
      weekFees,
      monthFees,
      formatDate,
      formatValue,
      calculateOrderFeeDisplay,
      refreshFeeStats,
      searchFeeHistory,
      handleSizeChange,
      handleCurrentChange
    };
  }
};
</script>

<style scoped>
.fee-statistics-container {
  padding: 10px;
}

.fee-stats-card {
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

.statistics-summary {
  padding: 10px 0;
}

.stat-card {
  text-align: center;
  height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-title {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.fee-notes {
  color: #606266;
  font-size: 12px;
}

.filter-container {
  background-color: #f8f8f8;
  padding: 15px;
  border-radius: 4px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
}
</style> 