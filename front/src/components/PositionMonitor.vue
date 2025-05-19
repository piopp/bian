<template>
  <div class="position-monitor mb-3">
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">持仓盈亏监控</h5>
        <div>
          <el-switch
            v-model="autoRefresh"
            class="me-2"
            :active-text="'自动刷新'"
            @change="handleAutoRefreshChange"
          />
          <el-select v-model="currentSymbol" placeholder="选择U本位币种" style="width: 150px;" @change="fetchData">
            <el-option 
              v-for="pair in favoriteSymbols" 
              :key="pair.symbol" 
              :label="`${pair.symbol}/USDT`" 
              :value="`${pair.symbol}USDT`"
            />
          </el-select>
          <el-button 
            type="primary" 
            size="small" 
            @click="fetchData" 
            :loading="loading"
            icon="Refresh"
            style="margin-left: 10px;"
          >
            刷新
          </el-button>
        </div>
      </div>
      <div class="card-body">
        <div v-if="loading" class="text-center py-3">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
        </div>
        <div v-else>
          <!-- 价格监控面板 -->
          <div class="row mb-3">
            <!-- 标记价格 -->
            <div class="col-md-4 mb-2">
              <div class="price-card">
                <div class="price-label">标记价格</div>
                <div class="price-value">
                  {{ monitorData.mark_price ? monitorData.mark_price.toFixed(6) : '暂无数据' }}
                </div>
              </div>
            </div>
            
            <!-- 空仓最低价 -->
            <div class="col-md-4 mb-2">
              <div class="price-card">
                <div class="price-label">空仓最低建仓价</div>
                <div class="price-value">
                  <span>{{ monitorData.short.lowest_entry ? monitorData.short.lowest_entry.toFixed(6) : '暂无数据' }}</span>
                  <el-tag 
                    v-if="monitorData.short.lowest_entry"
                    :type="monitorData.short.all_profit ? 'success' : 'danger'"
                    class="ms-2"
                  >
                    {{ monitorData.short.all_profit ? '全部盈利' : '部分亏损' }}
                  </el-tag>
                </div>
              </div>
            </div>
            
            <!-- 多仓最高价 -->
            <div class="col-md-4 mb-2">
              <div class="price-card">
                <div class="price-label">多仓最高建仓价</div>
                <div class="price-value">
                  <span>{{ monitorData.long.highest_entry ? monitorData.long.highest_entry.toFixed(6) : '暂无数据' }}</span>
                  <el-tag 
                    v-if="monitorData.long.highest_entry"
                    :type="monitorData.long.all_profit ? 'success' : 'danger'"
                    class="ms-2"
                  >
                    {{ monitorData.long.all_profit ? '全部盈利' : '部分亏损' }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 子账号持仓盈亏状态表格 -->
          <div v-if="monitorData.accounts && monitorData.accounts.length > 0">
            <h6 class="mb-2">子账号状态</h6>
            <el-table 
              :data="monitorData.accounts" 
              style="width: 100%"
              size="small"
              border
              max-height="300px"
            >
              <el-table-column prop="email" label="子账号" width="180" sortable>
                <template #default="scope">
                  <el-tooltip :content="scope.row.email" placement="top">
                    <span>{{ getShortEmail(scope.row.email) }}</span>
                  </el-tooltip>
                </template>
              </el-table-column>
              <el-table-column label="空仓状态" width="120">
                <template #default="scope">
                  <template v-if="scope.row.success">
                    <el-tag 
                      :type="scope.row.short_all_profit ? 'success' : 'danger'"
                      size="small"
                      v-if="scope.row.short_positions.length > 0"
                    >
                      {{ scope.row.short_all_profit ? '全部盈利' : '部分亏损' }}
                    </el-tag>
                    <span v-else>无空仓</span>
                  </template>
                  <el-tag type="warning" size="small" v-else>查询失败</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="多仓状态" width="120">
                <template #default="scope">
                  <template v-if="scope.row.success">
                    <el-tag 
                      :type="scope.row.long_all_profit ? 'success' : 'danger'"
                      size="small"
                      v-if="scope.row.long_positions.length > 0"
                    >
                      {{ scope.row.long_all_profit ? '全部盈利' : '部分亏损' }}
                    </el-tag>
                    <span v-else>无多仓</span>
                  </template>
                  <el-tag type="warning" size="small" v-else>查询失败</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="强平阈值" width="140">
                <template #default="scope">
                  <template v-if="scope.row.success && scope.row.uniMMR">
                    <el-tooltip :content="`维持保证金率: ${scope.row.uniMMR.maintMarginRatio}%, 总保证金余额: ${scope.row.uniMMR.totalMarginBalance || 0} USDT`" placement="top">
                      <div>
                        <el-progress 
                          :percentage="scope.row.uniMMR.riskRatio || 0" 
                          :status="getUniMMRStatus(scope.row.uniMMR.riskRatio)"
                          :stroke-width="8"
                          :format="formatRiskRatio"
                        ></el-progress>
                      </div>
                    </el-tooltip>
                  </template>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="已付手续费" width="120">
                <template #default="scope">
                  <span v-if="scope.row.success">
                    {{ scope.row.fees_total ? scope.row.fees_total.toFixed(4) : '0.0000' }}
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="持仓数量" width="120">
                <template #default="scope">
                  <span v-if="scope.row.success">
                    {{ scope.row.short_positions.length + scope.row.long_positions.length }}
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="text-center py-3 text-muted">
            <span>暂无子账号持仓数据，请选择币种并点击刷新</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getCurrentUser } from '@/services/auth'

export default {
  name: 'PositionMonitor',
  props: {
    subaccounts: {
      type: Array,
      required: true,
      default: () => []
    },
    activeTab: {
      type: String,
      default: ''
    }
  },
  emits: ['update:loading'],
  setup(props, { emit }) {
    // 响应式数据
    const loading = ref(false);
    const currentSymbol = ref(''); // 默认不选择任何币种
    const autoRefresh = ref(false);
    const refreshInterval = ref(null);
    const favoriteSymbols = ref([]); // 收藏的币种列表
    
    // 监控数据结构
    const monitorData = reactive({
      mark_price: 0,
      short: {
        lowest_entry: 0,
        all_profit: false
      },
      long: {
        highest_entry: 0,
        all_profit: false
      },
      accounts: []
    });
    
    // 获取收藏的交易对列表
    const loadFavoriteSymbols = async () => {
      try {
        // 默认收藏的币种
        favoriteSymbols.value = [
          { symbol: 'BTC', name: '比特币' },
          { symbol: 'ETH', name: '以太坊' },
          { symbol: 'BNB', name: '币安币' },
          { symbol: 'SOL', name: '索拉纳' },
          { symbol: 'ADA', name: '艾达币' },
          { symbol: 'XRP', name: '瑞波币' }
        ];
        
        // 获取API上的热门交易对
        const user = getCurrentUser();
        if (user && user.token) {
          try {
            const response = await axios.get('/api/markets/symbols', {
              headers: { 'Authorization': `Bearer ${user.token}` }
            });
        
            if (response.data.success && Array.isArray(response.data.data)) {
              // 将API返回的数据与默认数据合并
              const apiSymbols = response.data.data.filter(s => s.quoteAsset === 'USDT')
                .map(s => ({
                  symbol: s.baseAsset,
                  name: s.baseAssetName || s.baseAsset
                }));
              
              // 合并并去重
              const mergedSymbols = [...favoriteSymbols.value];
              apiSymbols.forEach(s => {
                if (!mergedSymbols.some(existing => existing.symbol === s.symbol)) {
                  mergedSymbols.push(s);
                }
              });
              
              favoriteSymbols.value = mergedSymbols;
            }
          } catch (error) {
            console.warn('获取热门交易对失败:', error);
          }
        }
      } catch (error) {
        console.error('加载收藏币种失败:', error);
      }
    };
    
    // 获取持仓汇总信息
    const fetchData = async () => {
      if (!currentSymbol.value) {
        ElMessage.warning('请先选择交易对');
        return;
      }
      
      if (props.subaccounts.length === 0) {
        ElMessage.warning('没有可用的子账号');
        return;
      }
      
      loading.value = true;
      emit('update:loading', true);
      
      try {
        const user = getCurrentUser();
        const token = user?.token;
        
        // 获取所有子账号邮箱
        const accounts = props.subaccounts.map(account => account.email);
        
        // 提取币种（去掉后缀USDT）
        const symbol = currentSymbol.value.replace('USDT', '');
        
        // 调用获取持仓API
        const response = await axios.get('/api/market/positions', {
          params: {
            symbol: symbol,
            accounts: accounts.join(',')
          },
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data.success) {
          // 更新监控数据
          const data = response.data.data;
          
          // 更新各个属性
          monitorData.mark_price = data.mark_price || 0;
          monitorData.short.lowest_entry = data.summary?.short?.lowest_entry || 0;
          monitorData.short.all_profit = data.summary?.short?.all_profit || false;
          monitorData.long.highest_entry = data.summary?.long?.highest_entry || 0;
          monitorData.long.all_profit = data.summary?.long?.all_profit || false;
          monitorData.accounts = data.accounts || [];
        } else {
          ElMessage.error(response.data.error || '获取持仓数据失败');
        }
      } catch (error) {
        console.error('获取持仓汇总信息失败:', error);
        ElMessage.error('网络错误，获取持仓汇总信息失败');
      } finally {
        loading.value = false;
        emit('update:loading', false);
      }
    };
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      stopAutoRefresh();
      refreshInterval.value = setInterval(() => {
        if (currentSymbol.value) {
          fetchData();
        }
      }, 30000); // 30秒刷新一次
    };
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value);
        refreshInterval.value = null;
      }
    };
    
    // 处理自动刷新状态变化
    const handleAutoRefreshChange = (val) => {
      if (val) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
      }
    };
    
    // 监听activeTab变化
    watch(() => props.activeTab, (newTab) => {
      if (newTab === 'positions') {
        // 切换到持仓标签页时，先获取收藏交易对
        loadFavoriteSymbols();
      }
    });
    
    // 组件挂载和卸载时的处理
    onMounted(() => {
      if (props.activeTab === 'positions') {
        // 先获取收藏的交易对
        loadFavoriteSymbols();
      }
    });
    
    onUnmounted(() => {
      stopAutoRefresh();
    });
    
    // 缩短邮箱显示
    const getShortEmail = (email) => {
      if (!email) return '';
      const parts = email.split('@');
      if (parts.length !== 2) return email;
      
      const name = parts[0];
      return name.length > 10 ? `${name.substring(0, 8)}...` : name;
    };
    
    // 获取uniMMR风险率状态
    const getUniMMRStatus = (riskRatio) => {
      if (!riskRatio || riskRatio < 0) return '';
      if (riskRatio >= 80) return 'exception'; // 危险
      if (riskRatio >= 50) return 'warning'; // 警告
      return 'success'; // 安全
    };
    
    // 格式化风险率显示
    const formatRiskRatio = (percentage) => {
      return percentage ? `${percentage}%` : '0%';
    };
    
    return {
      loading,
      currentSymbol,
      autoRefresh,
      favoriteSymbols,
      monitorData,
      fetchData,
      getShortEmail,
      getUniMMRStatus,
      formatRiskRatio,
      handleAutoRefreshChange
    };
  }
}
</script>

<style scoped>
/* 持仓监控面板样式 */
.position-monitor {
  margin-bottom: 15px;
}

.price-card {
  padding: 12px;
  border-radius: 6px;
  background-color: #f5f7fa;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  height: 100%;
}

.price-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.price-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  display: flex;
  align-items: center;
}

.text-success {
  color: #67c23a !important;
}

.text-danger {
  color: #f56c6c !important;
}
</style> 