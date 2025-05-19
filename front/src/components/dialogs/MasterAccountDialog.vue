<template>
  <el-dialog
    v-model="dialogVisible"
    title="主账号资产查询"
    width="800px"
    destroy-on-close
  >
    <div class="master-account-dialog">
      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-4">
        <el-skeleton :rows="6" animated />
      </div>
      
      <!-- 查询成功且有数据 -->
      <div v-else-if="assets.length > 0">
        <!-- 资产筛选 -->
        <div class="mb-3 filter-row">
          <el-radio-group v-model="filterMode" size="small" @change="filterAssets">
            <el-radio-button label="all">全部资产</el-radio-button>
            <el-radio-button label="nonZero">非零资产</el-radio-button>
          </el-radio-group>
          
          <el-input
            v-model="searchKeyword"
            placeholder="搜索币种"
            clearable
            class="search-input"
            @input="filterAssets"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <!-- 账户概览 -->
        <div class="account-overview mb-3">
          <div class="overview-item">
            <div class="item-label">总估值 (USDT)</div>
            <div class="item-value">{{ totalValue.toFixed(2) }}</div>
          </div>
          <div class="overview-item">
            <div class="item-label">BTC价值</div>
            <div class="item-value">{{ totalBtcValue.toFixed(8) }}</div>
          </div>
          <div class="overview-item">
            <div class="item-label">资产数量</div>
            <div class="item-value">{{ filteredAssets.length }}</div>
          </div>
        </div>
        
        <!-- 资产列表 -->
        <el-table
          :data="filteredAssets"
          style="width: 100%"
          max-height="400px"
          :default-sort="{ prop: 'usdtValue', order: 'descending' }"
          border
        >
          <el-table-column prop="asset" label="币种" width="100" sortable />
          <el-table-column prop="free" label="可用数量" sortable>
            <template #default="scope">
              <span>{{ formatNumber(scope.row.free) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="locked" label="冻结数量" sortable>
            <template #default="scope">
              <span>{{ formatNumber(scope.row.locked) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="total" label="总数量" sortable>
            <template #default="scope">
              <span>{{ formatNumber(scope.row.total) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="usdtValue" label="估值 (USDT)" sortable>
            <template #default="scope">
              <span>{{ formatNumber(scope.row.usdtValue) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="btcValue" label="BTC价值" sortable>
            <template #default="scope">
              <span>{{ formatNumber(scope.row.btcValue, 8) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 查询成功但没有数据 -->
      <div v-else-if="!loading && assets.length === 0" class="text-center py-4">
        <el-empty description="暂无资产数据" />
      </div>
    </div>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button type="primary" @click="fetchMasterAccountAssets" :loading="loading">
          刷新数据
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import axios from 'axios'
import { getCurrentUser } from '../../services/auth'

export default {
  name: 'MasterAccountDialog',
  components: {
    Search
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:visible'],
  setup(props, { emit }) {
    // 响应式数据
    const dialogVisible = ref(false)
    const loading = ref(false)
    const assets = ref([])
    const filteredAssets = ref([])
    const filterMode = ref('nonZero')
    const searchKeyword = ref('')
    const totalValue = ref(0)
    const totalBtcValue = ref(0)
    
    // 监听对话框可见性
    watch(() => props.visible, (newValue) => {
      dialogVisible.value = newValue
      if (newValue) {
        fetchMasterAccountAssets()
      }
    })
    
    // 监听对话框关闭
    watch(dialogVisible, (newValue) => {
      if (!newValue) {
        emit('update:visible', false)
      }
    })
    
    // 格式化数字，保留n位小数
    const formatNumber = (num, digits = 6) => {
      if (num === 0 || num === '0' || !num) return '0'
      
      // 将字符串转换为数字
      const numValue = typeof num === 'string' ? parseFloat(num) : num
      
      // 根据数值大小调整显示精度
      if (numValue >= 1) {
        // 大于1的数字，保留较少位数
        return numValue.toFixed(Math.min(digits, 4))
      } else if (numValue >= 0.0001) {
        // 中等大小的数字
        return numValue.toFixed(Math.min(digits, 6))
      } else {
        // 非常小的数字，显示科学计数法
        return numValue.toExponential(4)
      }
    }
    
    // 计算非零资产
    const filterAssets = () => {
      let filtered = [...assets.value]
      
      // 按关键词过滤
      if (searchKeyword.value) {
        const keyword = searchKeyword.value.toLowerCase()
        filtered = filtered.filter(asset => 
          asset.asset.toLowerCase().includes(keyword)
        )
      }
      
      // 按模式过滤
      if (filterMode.value === 'nonZero') {
        filtered = filtered.filter(asset => parseFloat(asset.total) > 0)
      }
      
      // 更新过滤后的资产
      filteredAssets.value = filtered
    }
    
    // 获取主账号资产
    const fetchMasterAccountAssets = async () => {
      loading.value = true
      
      try {
        const user = getCurrentUser()
        const token = user?.token
        
        // 调用API获取主账号资产
        const response = await axios.get('/api/main-account/assets', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.success) {
          // 处理资产数据
          const assetData = response.data.data
          
          // 更新资产列表，并计算每个资产的总量和USDT价值
          assets.value = assetData.assets.map(asset => ({
            ...asset,
            total: (parseFloat(asset.free) + parseFloat(asset.locked)).toString(),
            usdtValue: parseFloat(asset.usdtValue || 0),
            btcValue: parseFloat(asset.btcValue || 0)
          }))
          
          // 计算总价值
          totalValue.value = assetData.totalValue || 0
          totalBtcValue.value = assetData.btcValue || 0
          
          // 过滤资产
          filterAssets()
        } else {
          ElMessage.error(response.data.error || '获取主账号资产失败')
        }
      } catch (error) {
        console.error('获取主账号资产时出错:', error)
        ElMessage.error('网络错误，获取主账号资产失败')
      } finally {
        loading.value = false
      }
    }
    
    // 关闭对话框
    const handleClose = () => {
      dialogVisible.value = false
    }
    
    return {
      dialogVisible,
      loading,
      assets,
      filteredAssets,
      filterMode,
      searchKeyword,
      totalValue,
      totalBtcValue,
      formatNumber,
      filterAssets,
      fetchMasterAccountAssets,
      handleClose
    }
  }
}
</script>

<style scoped>
.master-account-dialog {
  min-height: 200px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-input {
  max-width: 200px;
}

.account-overview {
  display: flex;
  gap: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 15px;
}

.overview-item {
  flex: 1;
  text-align: center;
}

.item-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.item-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}
</style> 