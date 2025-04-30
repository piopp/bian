<template>
  <div class="position-container">
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
            <el-button type="primary" @click="fetchPositions" :loading="loading">刷新</el-button>
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
            {{ parseFloat(scope.row.entryPrice).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="markPrice" label="标记价" width="100" sortable>
          <template #default="scope">
            {{ parseFloat(scope.row.markPrice).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="unrealizedProfit" label="未实现盈亏" width="120" sortable>
          <template #default="scope">
            <span :class="parseFloat(scope.row.unrealizedProfit) >= 0 ? 'text-success' : 'text-danger'">
              {{ parseFloat(scope.row.unrealizedProfit).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="pnlPercentage" label="收益率" width="100" sortable>
          <template #default="scope">
            <span :class="parseFloat(scope.row.pnlPercentage) >= 0 ? 'text-success' : 'text-danger'">
              {{ parseFloat(scope.row.pnlPercentage).toFixed(2) }}%
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
import { parseApiResult } from '@/utils/apiHelper';
import { getCurrentUser } from '@/services/auth';

export default {
  name: 'PositionList',
  props: {
    subaccounts: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const loading = ref(false);
    const positionsData = ref([]);
    const selectedSymbol = ref('');
    const autoRefresh = ref(false);
    const refreshTimer = ref(null);
    
    // 根据筛选条件过滤持仓
    const filteredPositionsData = computed(() => {
      if (!selectedSymbol.value) {
        return positionsData.value;
      }
      
      return positionsData.value.filter(position => position.symbol === selectedSymbol.value);
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
    
    const fetchPositions = async () => {
      loading.value = true;
      
      try {
        // 获取当前用户和token
        const user = getCurrentUser();
        const token = user?.token;
        const userIdValue = user?.id;
        
        // 使用传递进来的子账号列表
        const emails = props.subaccounts.map(account => account.email);
        
        if (emails.length === 0) {
          ElMessage.warning('没有可用的子账号');
          loading.value = false;
          return;
        }
        
        console.log("发送请求参数：", { emails, userId: userIdValue });
        
        // 批量查询所有选中子账号的持仓信息
        const response = await axios.post('/api/subaccounts/futures-positions', {
          emails: emails,
          userId: userIdValue
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        const positionsResult = parseApiResult(response);
        
        if (!positionsResult.success) {
          ElMessage.error('获取持仓列表失败');
          loading.value = false;
          return;
        }
        
        // 合并所有子账号的持仓
        const allPositions = [];
        
        if (positionsResult.data) {
          positionsResult.data.forEach(accountPositions => {
            if (accountPositions.success && accountPositions.positions && accountPositions.positions.length > 0) {
              // 为每个持仓添加子账号信息
              const positionsWithEmail = accountPositions.positions.map(position => ({
                ...position,
                email: accountPositions.email
              }));
              allPositions.push(...positionsWithEmail);
            }
          });
        }
        
        // 更新数据
        positionsData.value = allPositions;
        
        if (allPositions.length === 0) {
          ElMessage.info('所有子账号暂无持仓');
        }
      } catch (error) {
        console.error('获取持仓失败:', error);
        ElMessage.error('网络错误，获取持仓失败');
      } finally {
        loading.value = false;
      }
    };
    
    const closePosition = async (position) => {
      try {
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
        
        // 发送平仓请求
        const response = await axios.post('/api/subaccounts/batch-close', {
          emails: [position.email],
          symbol: position.symbol,
          closeType: 'ALL'  // 全部平仓
        });
        
        const result = parseApiResult(response);
        
        // 检查响应数据格式，确保正确处理数组结果
        if (response.data && Array.isArray(response.data)) {
          // 直接使用数组中第一个元素（因为只请求了一个账号）
          const closeResult = response.data[0];
          if (closeResult && closeResult.success) {
            ElMessage.success('平仓成功');
            // 延迟500ms后重新获取持仓列表，确保后端数据已更新
            setTimeout(() => {
              fetchPositions();
            }, 500);
          } else {
            // 虽然API返回失败，但仍尝试刷新持仓列表
            // 可能服务端平仓成功但响应错误
            ElMessage.warning(closeResult?.message || '平仓操作可能已成功，正在刷新数据...');
            setTimeout(() => {
              fetchPositions();
            }, 1000);
          }
        } else if (result.success) {
          ElMessage.success('平仓成功');
          // 延迟500ms后重新获取持仓列表
          setTimeout(() => {
            fetchPositions();
          }, 500);
        } else {
          // 即使提示失败，也尝试刷新持仓状态
          ElMessage.warning(result.error || '平仓结果未知，正在刷新数据...');
          setTimeout(() => {
            fetchPositions();
          }, 1000);
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('平仓失败:', error);
          ElMessage.error('平仓请求失败');
          // 即使请求失败，也刷新一次持仓数据
          setTimeout(() => {
            fetchPositions();
          }, 1000);
        }
      } finally {
        loading.value = false;
      }
    };
    
    // 启动自动刷新
    const startAutoRefresh = () => {
      if (!refreshTimer.value) {
        // 立即执行一次查询
        fetchPositions();
        
        // 设置定时器，每3秒查询一次
        refreshTimer.value = setInterval(() => {
          if (!loading.value) {
            fetchPositions();
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
      fetchPositions();
    });
    
    // 组件销毁时清除定时器
    onUnmounted(() => {
      stopAutoRefresh();
    });
    
    return {
      loading,
      positionsData,
      filteredPositionsData,
      selectedSymbol,
      commonSymbols,
      autoRefresh,
      getShortEmail,
      fetchPositions,
      closePosition
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
</style> 