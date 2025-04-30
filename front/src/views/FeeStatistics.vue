<template>
  <div class="fee-statistics-container">
    <el-card class="filter-card">
      <div class="filter-form">
        <el-form :model="filterForm" inline>
          <el-form-item label="账户邮箱">
            <el-input v-model="filterForm.email" placeholder="输入账户邮箱" clearable></el-input>
          </el-form-item>
          <el-form-item label="交易对">
            <el-input v-model="filterForm.symbol" placeholder="输入交易对" clearable></el-input>
          </el-form-item>
          <el-form-item label="时间范围">
            <el-date-picker
              v-model="filterForm.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              format="YYYY-MM-DD"
            ></el-date-picker>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="searchFees">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-row :gutter="20" class="statistics-row">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-title">总手续费(USDT)</div>
          <div class="stat-value">{{ formatUsdtValue(stats.totalFeeUSDT) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-title">总订单数</div>
          <div class="stat-value">{{ stats.totalCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-title">平均每单手续费(USDT)</div>
          <div class="stat-value">{{ calculateAvgFee() }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="明细记录" name="details">
        <el-card>
          <el-table :data="feeList" border style="width: 100%" v-loading="loading">
            <el-table-column prop="email" label="账户邮箱" min-width="180"></el-table-column>
            <el-table-column prop="symbol" label="交易对" min-width="100"></el-table-column>
            <el-table-column prop="side" label="方向" min-width="80">
              <template #default="scope">
                <el-tag :type="scope.row.side === 'BUY' ? 'success' : 'danger'">
                  {{ scope.row.side === 'BUY' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="orderType" label="订单类型" min-width="100">
              <template #default="scope">
                {{ formatOrderType(scope.row.orderType) }}
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="数量" min-width="100"></el-table-column>
            <el-table-column prop="price" label="价格" min-width="100"></el-table-column>
            <el-table-column label="手续费" min-width="150">
              <template #default="scope">
                {{ calculateOrderFeeDisplay(scope.row) }}
              </template>
            </el-table-column>
            <el-table-column prop="timestamp" label="时间" min-width="180">
              <template #default="scope">
                {{ formatDate(scope.row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column prop="orderId" label="订单ID" min-width="120"></el-table-column>
          </el-table>
          
          <div class="pagination-container">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next, jumper"
              :total="pagination.total"
              :page-size="pagination.limit"
              :page-sizes="[10, 20, 50, 100]"
              :current-page="pagination.page"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            ></el-pagination>
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="汇总统计" name="summary">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card class="summary-card">
              <div class="summary-title">币种手续费统计</div>
              <el-table :data="summaryData.byCurrency" border style="width: 100%" v-loading="summaryLoading">
                <el-table-column prop="_id" label="币种"></el-table-column>
                <el-table-column prop="totalFee" label="总手续费数量"></el-table-column>
                <el-table-column prop="totalFeeUSDT" label="总手续费(USDT)">
                  <template #default="scope">
                    {{ formatUsdtValue(scope.row.totalFeeUSDT) }}
                  </template>
                </el-table-column>
                <el-table-column prop="count" label="订单数"></el-table-column>
              </el-table>
            </el-card>
          </el-col>
          
          <el-col :span="12">
            <el-card class="summary-card">
              <div class="summary-title">交易对手续费统计</div>
              <el-table :data="summaryData.bySymbol" border style="width: 100%" v-loading="summaryLoading">
                <el-table-column prop="_id" label="交易对"></el-table-column>
                <el-table-column prop="totalFeeUSDT" label="总手续费(USDT)">
                  <template #default="scope">
                    {{ formatUsdtValue(scope.row.totalFeeUSDT) }}
                  </template>
                </el-table-column>
                <el-table-column prop="count" label="订单数"></el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import axios from 'axios';
import { calculateOrderFee, FEE_RATES, calculateTotalFees } from '../utils/feeCalculator';
import { getCurrentUser } from '../services/auth';

export default {
  setup() {
    // 当前激活的标签页
    const activeTab = ref('details');

    // 过滤表单
    const filterForm = reactive({
      email: '',
      symbol: '',
      dateRange: []
    });

    // 列表数据
    const feeList = ref([]);
    const loading = ref(false);
    const pagination = reactive({
      page: 1,
      limit: 20,
      total: 0,
      pages: 0
    });

    // 统计数据
    const stats = reactive({
      totalFeeUSDT: 0,
      totalCount: 0
    });

    // 汇总数据
    const summaryData = reactive({
      byCurrency: [],
      bySymbol: []
    });
    const summaryLoading = ref(false);

    // 页面加载时获取数据
    onMounted(() => {
      searchFees();
      getSummary();
    });

    // 搜索手续费记录
    const searchFees = async () => {
      loading.value = true;
      try {
        const user = getCurrentUser();
        const token = user?.token;
        
        // 构建查询参数
        const params = {
          page: pagination.page,
          pageSize: pagination.limit
        };
        
        // 必须提供email参数
        if (filterForm.email) {
          params.email = filterForm.email;
        } else {
          ElMessage.warning('请输入账户邮箱');
          loading.value = false;
          return;
        }
        
        if (filterForm.symbol) {
          params.symbol = filterForm.symbol;
        }
        
        if (filterForm.dateRange && filterForm.dateRange.length === 2) {
          params.startDate = filterForm.dateRange[0];
          params.endDate = filterForm.dateRange[1];
        }
        
        const response = await axios.get('/api/statistics/fee-trend', { 
          params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.data.success) {
          // 转换记录为订单格式以便计算手续费
          const orders = (response.data.data.records || []).map(record => ({
            symbol: record.symbol,
            orderType: record.type || (record.orderType === 'MARKET' ? 'MARKET' : 'LIMIT'),
            productType: record.symbol && record.symbol.endsWith('USDT') ? 'USDT_FUTURE' : 'SPOT',
            amount: parseFloat(record.amount) || 0,
            price: parseFloat(record.price) || 0,
            status: 'FILLED', // 假设所有记录都是已成交的
            feeCurrency: record.feeCurrency,
            fee: record.fee,
            feeUSDT: record.feeUSDT
          }));
          
          feeList.value = response.data.data.records || [];
          pagination.total = response.data.data.total || 0;
          pagination.page = response.data.data.page || 1;
          pagination.limit = response.data.data.pageSize || 20;
          pagination.pages = Math.ceil(pagination.total / pagination.limit);
          
          // 计算统计数据
          stats.totalCount = pagination.total;
          
          // 如果记录中有feeUSDT字段，直接使用；否则使用计算工具计算
          if (orders.length > 0 && orders[0].feeUSDT) {
            stats.totalFeeUSDT = orders.reduce((sum, order) => sum + parseFloat(order.feeUSDT || 0), 0);
          } else {
            const { totalFeeUSDT } = calculateTotalFees(orders);
            stats.totalFeeUSDT = totalFeeUSDT;
          }
        } else {
          ElMessage.error(response.data.message || '获取手续费记录失败');
        }
      } catch (error) {
        console.error('获取手续费记录失败:', error);
        ElMessage.error('获取手续费记录失败: ' + (error.response?.data?.message || error.message));
      } finally {
        loading.value = false;
      }
    };

    // 获取汇总统计
    const getSummary = async () => {
      summaryLoading.value = true;
      try {
        const user = getCurrentUser();
        const token = user?.token;
        
        // 构建查询参数
        const params = {};
        
        // 必须提供email参数
        if (filterForm.email) {
          params.email = filterForm.email;
        } else {
          ElMessage.warning('请输入账户邮箱');
          summaryLoading.value = false;
          return;
        }
        
        if (filterForm.dateRange && filterForm.dateRange.length === 2) {
          params.startDate = filterForm.dateRange[0];
          params.endDate = filterForm.dateRange[1];
        }
        
        const response = await axios.get('/api/statistics/fee-summary', { 
          params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (response.data.success) {
          summaryData.byCurrency = response.data.data.byCurrency;
          summaryData.bySymbol = response.data.data.bySymbol;
          
          // 更新总计数据
          if (response.data.data.total) {
            stats.totalFeeUSDT = response.data.data.total.totalFeeUSDT;
            stats.totalCount = response.data.data.total.totalCount;
          }
        } else {
          ElMessage.error(response.data.message || '获取手续费汇总统计失败');
        }
      } catch (error) {
        console.error('获取手续费汇总统计失败:', error);
        ElMessage.error('获取手续费汇总统计失败: ' + (error.response?.data?.message || error.message));
      } finally {
        summaryLoading.value = false;
      }
    };

    // 重置过滤条件
    const resetFilters = () => {
      filterForm.email = '';
      filterForm.symbol = '';
      filterForm.dateRange = [];
      pagination.page = 1;
      searchFees();
      getSummary();
    };

    // 分页处理
    const handleSizeChange = (val) => {
      pagination.limit = val;
      pagination.page = 1;
      searchFees();
    };

    const handleCurrentChange = (val) => {
      pagination.page = val;
      searchFees();
    };

    // 格式化函数
    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleString();
    };

    const formatOrderType = (type) => {
      const typeMap = {
        'MARKET': '市价单',
        'LIMIT': '限价单',
        'STOP': '止损单',
        'STOP_MARKET': '止损市价单',
        'TAKE_PROFIT': '止盈单',
        'TAKE_PROFIT_MARKET': '止盈市价单'
      };
      return typeMap[type] || type;
    };

    const formatUsdtValue = (value) => {
      if (value === undefined || value === null) return '0.00';
      return Number(value).toFixed(2);
    };

    // 计算平均每单手续费
    const calculateAvgFee = () => {
      if (!stats.totalCount || stats.totalCount === 0) {
        return '0.00';
      }
      return formatUsdtValue(stats.totalFeeUSDT / stats.totalCount);
    };

    // 计算订单手续费
    const calculateOrderFeeDisplay = (order) => {
      // 如果已经有feeUSDT，直接使用
      if (order.feeUSDT) {
        return formatUsdtValue(order.feeUSDT);
      }
      
      // 否则使用计算工具计算
      const orderData = {
        symbol: order.symbol,
        orderType: order.orderType || 'LIMIT',
        productType: order.symbol && order.symbol.includes('USDT') ? 'USDT_FUTURE' : 'SPOT',
        amount: parseFloat(order.amount) || 0,
        price: parseFloat(order.price) || 0,
        status: 'FILLED', // 假设所有显示的订单都是已成交的
        feeCurrency: order.feeCurrency || 'USDT'
      };
      
      const { feeUSDT } = calculateOrderFee(orderData);
      return formatUsdtValue(feeUSDT);
    };

    // 费率数据
    const feeRatesData = computed(() => [
      { type: '现货及杠杆', taker: (FEE_RATES.SPOT.TAKER * 100) + '%', maker: (FEE_RATES.SPOT.MAKER * 100) + '%' },
      { type: 'U本位合约(USDT)', taker: (FEE_RATES.USDT_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.USDT_FUTURE.MAKER * 100) + '%' },
      { type: 'U本位合约(USDC)', taker: (FEE_RATES.USDC_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.USDC_FUTURE.MAKER * 100) + '%' },
      { type: '币本位合约', taker: (FEE_RATES.COIN_FUTURE.TAKER * 100) + '%', maker: (FEE_RATES.COIN_FUTURE.MAKER * 100) + '%' }
    ]);

    return {
      activeTab,
      filterForm,
      feeList,
      loading,
      pagination,
      stats,
      summaryData,
      summaryLoading,
      searchFees,
      getSummary,
      resetFilters,
      handleSizeChange,
      handleCurrentChange,
      formatDate,
      formatOrderType,
      formatUsdtValue,
      calculateAvgFee,
      calculateOrderFeeDisplay,
      feeRatesData
    };
  }
};
</script>

<style scoped>
.fee-statistics-container {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.statistics-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  height: 120px;
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

.fee-usdt {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

.summary-card {
  margin-bottom: 20px;
}

.summary-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
  color: #303133;
}
</style> 