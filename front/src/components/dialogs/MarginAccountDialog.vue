<template>
  <el-dialog
    title="杠杆账户详情"
    v-model="dialogVisible"
    width="80%"
    :before-close="handleClose"
  >
    <el-tabs v-model="activeTab" type="card">
      <el-tab-pane label="基本信息" name="basic">
        <div v-if="loading" class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>
        <div v-else-if="error" class="error-container">
          <el-alert
            :title="error"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
        <div v-else>
          <el-descriptions title="账户总览" :column="3" border>
            <el-descriptions-item label="借贷率">
              {{ parseFloat(marginAccount.marginLevel || 0).toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="总资产(BTC)">
              {{ parseFloat(marginAccount.totalAssetOfBtc || 0).toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item label="总负债(BTC)">
              {{ parseFloat(marginAccount.totalLiabilityOfBtc || 0).toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item label="净资产(BTC)">
              {{ parseFloat(marginAccount.totalNetAssetOfBtc || 0).toFixed(8) }}
            </el-descriptions-item>
            <el-descriptions-item label="是否通过风控">
              <el-tag :type="marginAccount.tradeEnabled ? 'success' : 'danger'">
                {{ marginAccount.tradeEnabled ? '通过' : '未通过' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="转账是否启用">
              <el-tag :type="marginAccount.transferEnabled ? 'success' : 'danger'">
                {{ marginAccount.transferEnabled ? '启用' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="资产详情" name="assets">
        <div v-if="loading" class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>
        <div v-else-if="error" class="error-container">
          <el-alert
            :title="error"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
        <div v-else>
          <div style="display: flex; justify-content: space-between; margin-bottom: 15px">
          <el-input
            v-model="assetSearch"
            placeholder="搜索资产"
            clearable
              style="width: 200px"
            />
            
            <el-switch
              v-model="hideZeroAssets"
              active-text="隐藏零资产"
              inactive-text="显示所有资产"
          />
          </div>
          
          <el-table
            :data="filteredAssets"
            style="width: 100%"
            max-height="500px"
            border
          >
            <el-table-column prop="asset" label="资产" width="100" />
            <el-table-column label="可用数量" min-width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.free).toFixed(8) }}
              </template>
            </el-table-column>
            <el-table-column label="冻结数量" min-width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.locked).toFixed(8) }}
              </template>
            </el-table-column>
            <el-table-column label="已借数量" min-width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.borrowed || '0').toFixed(8) }}
              </template>
            </el-table-column>
            <el-table-column label="利息" min-width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.interest || '0').toFixed(8) }}
              </template>
            </el-table-column>
            <el-table-column label="净资产" min-width="120">
              <template #default="scope">
                {{ parseFloat(scope.row.netAsset || '0').toFixed(8) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button type="primary" @click="refreshData">
          刷新数据
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, watch, computed } from 'vue';
import axios from 'axios';
import { getCurrentUser } from '@/services/auth';

export default {
  name: 'MarginAccountDialog',
  props: {
    modelValue: {
      type: Boolean,
      required: true
    },
    account: {
      type: Object,
      default: null
    },
    selectedAccounts: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const dialogVisible = ref(false);
    const activeTab = ref('basic');
    const loading = ref(false);
    const error = ref('');
    const marginAccount = ref({});
    const assetSearch = ref('');
    const hideZeroAssets = ref(true);
    
    const filteredAssets = computed(() => {
      if (!marginAccount.value.userAssets) return [];
      
      let assets = marginAccount.value.userAssets || [];
      
      // 如果勾选了隐藏零资产，则过滤掉数量为0的资产
      if (hideZeroAssets.value) {
        assets = assets.filter(asset => {
          const free = parseFloat(asset.free || 0);
          const locked = parseFloat(asset.locked || 0);
          const borrowed = parseFloat(asset.borrowed || 0);
          const netAsset = parseFloat(asset.netAsset || 0);
          
          // 只要有一个数值不为0，就保留该资产
          return free > 0 || locked > 0 || borrowed > 0 || netAsset > 0;
        });
      }
      
      // 如果有搜索关键词，继续按资产名称过滤
      if (assetSearch.value) {
        assets = assets.filter(asset => 
        asset.asset.toLowerCase().includes(assetSearch.value.toLowerCase())
      );
      }
      
      return assets;
    });
    
    // 监听对话框显示状态
    watch(() => props.modelValue, (val) => {
      dialogVisible.value = val;
      if (val && props.account) {
        loadMarginAccount();
      }
    });
    
    // 监听对话框内部状态变化，同步到父组件
    watch(() => dialogVisible.value, (val) => {
      emit('update:modelValue', val);
    });
    
    // 加载杠杆账户信息
    const loadMarginAccount = async () => {
      // 检查是否有账户信息，优先使用直接传入的account，其次使用selectedAccounts中的第一个账户
      const accountToUse = props.account || (props.selectedAccounts.length > 0 ? props.selectedAccounts[0] : null);
      
      if (!accountToUse || !accountToUse.email) {
        error.value = '账户信息无效，请确保选择了有效的子账号';
        return;
      }
      
      loading.value = true;
      error.value = '';
      
      try {
        const user = getCurrentUser();
        if (!user || !user.token) {
          error.value = '用户未登录';
          return;
        }
        
        const response = await axios.post('/api/subaccounts/margin-account', {
          email: accountToUse.email
        }, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        });
        
        if (response.data.success && response.data.data && response.data.data.length > 0) {
          marginAccount.value = response.data.data[0];
        } else {
          error.value = response.data.error || '获取杠杆账户信息失败';
        }
      } catch (err) {
        console.error('获取杠杆账户信息失败:', err);
        error.value = '网络错误，无法获取杠杆账户信息';
      } finally {
        loading.value = false;
      }
    };
    
    // 刷新数据
    const refreshData = () => {
      loadMarginAccount();
    };
    
    // 关闭对话框
    const handleClose = () => {
      dialogVisible.value = false;
    };
    
    return {
      dialogVisible,
      activeTab,
      loading,
      error,
      marginAccount,
      assetSearch,
      hideZeroAssets,
      filteredAssets,
      refreshData,
      handleClose
    };
  }
};
</script>

<style scoped>
.loading-container,
.error-container {
  padding: 20px;
  min-height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.error-container {
  width: 100%;
}
</style> 