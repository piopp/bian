<template>
  <div class="trading-pairs-container">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>交易对管理</h2>
          <div class="header-actions">
            <el-button type="primary" @click="showAddDialog" size="small">
              添加交易对
            </el-button>
            <el-button type="success" @click="initializeCommonPairs" size="small">
              初始化常用交易对
            </el-button>
            <el-button type="warning" @click="showImportDialog" size="small">
              批量导入
            </el-button>
            <el-button type="danger" @click="confirmClearAll" size="small">
              清空交易对
            </el-button>
          </div>
        </div>
      </template>

      <!-- 过滤器 -->
      <div class="filter-section">
        <el-input
          v-model="searchQuery"
          placeholder="搜索交易对"
          prefix-icon="el-icon-search"
          clearable
          class="search-input"
        ></el-input>
        <el-switch
          v-model="showFavoritesOnly"
          active-text="仅显示收藏"
          inactive-text="显示全部"
          class="favorite-switch"
        ></el-switch>
      </div>

      <!-- 交易对表格 -->
      <el-table
        :data="filteredTradingPairs"
        style="width: 100%"
        v-loading="isLoading"
        stripe
        border
      >
        <el-table-column label="ID" prop="id" width="70"></el-table-column>
        <el-table-column label="交易对" prop="symbol" width="120"></el-table-column>
        <el-table-column label="基础资产" prop="base_asset" width="100"></el-table-column>
        <el-table-column label="计价资产" prop="quote_asset" width="100"></el-table-column>
        <el-table-column label="描述" prop="description"></el-table-column>
        <el-table-column label="收藏" width="80">
          <template #default="scope">
            <el-button
              :type="scope.row.is_favorite ? 'warning' : 'info'"
              @click="toggleFavorite(scope.row)"
              circle
              size="small"
              :icon="scope.row.is_favorite ? 'Star' : 'StarFilled'"
            ></el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button
              type="primary"
              @click="showEditDialog(scope.row)"
              size="small"
              icon="Edit"
              circle
            ></el-button>
            <el-button
              type="danger"
              @click="confirmDelete(scope.row)"
              size="small"
              icon="Delete"
              circle
            ></el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑交易对对话框 -->
    <el-dialog
      :title="isEditMode ? '编辑交易对' : '添加交易对'"
      v-model="dialogVisible"
      width="500px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="pairForm">
        <el-form-item label="交易对符号" prop="symbol">
          <el-input v-model="form.symbol" :disabled="isEditMode"></el-input>
          <div class="form-hint" v-if="!isEditMode">例如: BTCUSDT, ETHBUSD</div>
        </el-form-item>
        <el-form-item label="基础资产" prop="base_asset" v-if="!isEditMode">
          <el-input v-model="form.base_asset"></el-input>
          <div class="form-hint">例如: BTC, ETH (留空将自动识别)</div>
        </el-form-item>
        <el-form-item label="计价资产" prop="quote_asset" v-if="!isEditMode">
          <el-input v-model="form.quote_asset"></el-input>
          <div class="form-hint">例如: USDT, BUSD (留空将自动识别)</div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description"></el-input>
          <div class="form-hint">例如: 比特币/USDT</div>
        </el-form-item>
        <el-form-item label="是否收藏">
          <el-switch v-model="form.is_favorite"></el-switch>
        </el-form-item>
        <el-form-item label="显示顺序" prop="order">
          <el-input-number v-model="form.order" :min="0"></el-input-number>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveTradingPair" :loading="isSaving">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog title="批量导入交易对" v-model="importDialogVisible" width="600px">
      <el-form label-width="100px">
        <el-form-item label="导入格式">
          <div class="import-format-info">
            <p>请输入要导入的交易对，每行一个，格式如下：</p>
            <pre>BTCUSDT,比特币/USDT,1
ETHUSDT,以太坊/USDT,0
BNBUSDT</pre>
            <p>格式说明：交易对符号,描述,是否收藏(1表示收藏,0表示不收藏)</p>
            <p>注意：描述和收藏状态可选，如不提供则使用默认值</p>
          </div>
        </el-form-item>
        <el-form-item label="交易对列表">
          <el-input
            type="textarea"
            v-model="importText"
            :rows="8"
            placeholder="请输入交易对列表，每行一个"
          ></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="importTradingPairs" :loading="isImporting">
            导入
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 导入结果对话框 -->
    <el-dialog title="导入结果" v-model="resultDialogVisible" width="600px">
      <div class="import-result-summary">
        <p>总计: {{ importResults.length }} 个交易对</p>
        <p>成功: {{ importResults.filter(r => r.success).length }} 个</p>
        <p>失败: {{ importResults.filter(r => !r.success).length }} 个</p>
      </div>
      <el-table :data="importResults" style="width: 100%" max-height="300px">
        <el-table-column label="交易对" prop="symbol" width="120"></el-table-column>
        <el-table-column label="状态">
          <template #default="scope">
            <el-tag :type="scope.row.success ? 'success' : 'danger'">
              {{ scope.row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="消息" prop="message" show-overflow-tooltip></el-table-column>
        <el-table-column label="错误" prop="error" show-overflow-tooltip></el-table-column>
      </el-table>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="resultDialogVisible = false">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

export default {
  name: 'TradingPairsView',

  setup() {
    // 状态
    const tradingPairs = ref([])
    const isLoading = ref(false)
    const dialogVisible = ref(false)
    const isEditMode = ref(false)
    const isSaving = ref(false)
    const searchQuery = ref('')
    const showFavoritesOnly = ref(false)
    const importDialogVisible = ref(false)
    const importText = ref('')
    const isImporting = ref(false)
    const resultDialogVisible = ref(false)
    const importResults = ref([])
    
    // 表单
    const form = reactive({
      id: null,
      symbol: '',
      base_asset: '',
      quote_asset: '',
      description: '',
      is_favorite: false,
      order: 0
    })
    
    // 表单验证规则
    const rules = {
      symbol: [
        { required: true, message: '请输入交易对符号', trigger: 'blur' },
        { pattern: /^[A-Za-z0-9]+$/, message: '交易对符号只能包含字母和数字', trigger: 'blur' }
      ],
      description: [
        { max: 100, message: '描述不能超过100个字符', trigger: 'blur' }
      ]
    }
    
    // 过滤交易对列表
    const filteredTradingPairs = computed(() => {
      let filtered = tradingPairs.value
      
      // 筛选收藏
      if (showFavoritesOnly.value) {
        filtered = filtered.filter(pair => pair.is_favorite)
      }
      
      // 搜索查询
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filtered = filtered.filter(pair => 
          pair.symbol.toLowerCase().includes(query) || 
          pair.description.toLowerCase().includes(query) ||
          pair.base_asset.toLowerCase().includes(query) ||
          pair.quote_asset.toLowerCase().includes(query)
        )
      }
      
      return filtered
    })
    
    // 加载交易对列表
    const loadTradingPairs = async () => {
      isLoading.value = true
      try {
        const response = await axios.get('/api/trading-pairs')
        if (response.data.success) {
          tradingPairs.value = response.data.data
        } else {
          ElMessage.error('加载交易对列表失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('加载交易对列表失败:', error)
        ElMessage.error('加载交易对列表失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isLoading.value = false
      }
    }
    
    // 显示添加对话框
    const showAddDialog = () => {
      isEditMode.value = false
      resetForm()
      form.is_favorite = true
      dialogVisible.value = true
    }
    
    // 显示编辑对话框
    const showEditDialog = (row) => {
      isEditMode.value = true
      Object.assign(form, row)
      dialogVisible.value = true
    }
    
    // 重置表单
    const resetForm = () => {
      form.id = null
      form.symbol = ''
      form.base_asset = ''
      form.quote_asset = ''
      form.description = ''
      form.is_favorite = false
      form.order = 0
    }
    
    // 保存交易对
    const saveTradingPair = async () => {
      isSaving.value = true
      try {
        // 确保基础字段存在
        const formData = { ...form }
        
        // 如果base_asset或quote_asset为空，尝试从symbol中解析
        if (!isEditMode.value) {
          if (!formData.base_asset || !formData.quote_asset) {
            // 常见的计价资产列表
            const quoteAssets = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB'];
            let found = false;
            
            // 检查symbol是否以已知计价资产结尾
            for (const quote of quoteAssets) {
              if (formData.symbol.endsWith(quote)) {
                const base = formData.symbol.slice(0, -quote.length);
                if (base) {
                  if (!formData.base_asset) formData.base_asset = base;
                  if (!formData.quote_asset) formData.quote_asset = quote;
                  found = true;
                  break;
                }
              }
            }
            
            // 如果没有匹配到任何已知计价资产，使用一个基本的规则
            if (!found) {
              // 假设后4个字符是计价资产，前面的是基础资产
              if (formData.symbol.length > 4) {
                if (!formData.base_asset) formData.base_asset = formData.symbol.slice(0, -4);
                if (!formData.quote_asset) formData.quote_asset = formData.symbol.slice(-4);
              }
            }
          }
        }

        let response;
        if (isEditMode.value) {
          // 更新
          response = await axios.put(`/api/trading-pairs/${form.id}`, formData);
        } else {
          // 新增
          response = await axios.post('/api/trading-pairs/add', formData);
        }
        
        if (response.data.success) {
          ElMessage.success(response.data.message || '保存成功')
          dialogVisible.value = false
          loadTradingPairs()
        } else {
          ElMessage.error('保存失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('保存交易对失败:', error)
        ElMessage.error('保存失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isSaving.value = false
      }
    }
    
    // 删除确认
    const confirmDelete = (row) => {
      ElMessageBox.confirm(
        `确定要删除交易对 ${row.symbol} 吗？`,
        '删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        deleteTradingPair(row.id)
      }).catch(() => {})
    }
    
    // 删除交易对
    const deleteTradingPair = async (id) => {
      try {
        const response = await axios.delete(`/api/trading-pairs/delete/${id}`)
        if (response.data.success) {
          ElMessage.success(response.data.message || '删除成功')
          loadTradingPairs()
        } else {
          ElMessage.error('删除失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('删除交易对失败:', error)
        ElMessage.error('删除失败: ' + (error.response?.data?.error || error.message))
      }
    }
    
    // 确认清空所有交易对
    const confirmClearAll = () => {
      ElMessageBox.confirm(
        '确定要清空所有交易对吗？此操作不可恢复！',
        '危险操作',
        {
          confirmButtonText: '确定清空',
          cancelButtonText: '取消',
          type: 'danger',
          confirmButtonClass: 'el-button--danger',
        }
      ).then(() => {
        clearAllTradingPairs()
      }).catch(() => {})
    }
    
    // 清空所有交易对
    const clearAllTradingPairs = async () => {
      try {
        const response = await axios.delete('/api/trading-pairs/clear-all')
        if (response.data.success) {
          ElMessage.success(response.data.message)
          loadTradingPairs()
        } else {
          ElMessage.error('清空交易对失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('清空交易对失败:', error)
        ElMessage.error('清空交易对失败: ' + (error.response?.data?.error || error.message))
      }
    }
    
    // 切换收藏状态
    const toggleFavorite = async (row) => {
      try {
        const response = await axios.post(`/api/trading-pairs/favorite/${row.id}`, {
          is_favorite: !row.is_favorite
        })
        if (response.data.success) {
          ElMessage.success(response.data.message)
          // 更新本地状态
          const index = tradingPairs.value.findIndex(pair => pair.id === row.id)
          if (index !== -1) {
            tradingPairs.value[index].is_favorite = response.data.is_favorite
          }
        } else {
          ElMessage.error('操作失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('切换收藏状态失败:', error)
        ElMessage.error('操作失败: ' + (error.response?.data?.error || error.message))
      }
    }
    
    // 显示批量导入对话框
    const showImportDialog = () => {
      importText.value = ''
      importDialogVisible.value = true
    }
    
    // 批量导入交易对
    const importTradingPairs = async () => {
      if (!importText.value.trim()) {
        ElMessage.warning('请输入要导入的交易对')
        return
      }
      
      isImporting.value = true
      try {
        // 解析导入文本
        const lines = importText.value.trim().split('\n')
        const pairs = []
        
        for (const line of lines) {
          if (!line.trim()) continue
          
          const parts = line.split(',')
          const symbol = parts[0].trim()
          
          if (!symbol) continue
          
          const pair = { symbol }
          
          if (parts.length > 1 && parts[1].trim()) {
            pair.description = parts[1].trim()
          }
          
          if (parts.length > 2) {
            pair.is_favorite = parts[2].trim() === '1'
          }
          
          pairs.push(pair)
        }
        
        // 发送请求
        const response = await axios.post('/api/trading-pairs/batch-import', { pairs })
        
        if (response.data.success) {
          ElMessage.success(`成功导入${response.data.successCount}个交易对，${response.data.existingCount}个已存在，${response.data.failCount}个失败`)
          importResults.value = response.data.results || []
          importDialogVisible.value = false
          resultDialogVisible.value = true
          loadTradingPairs()
        } else {
          ElMessage.error('批量导入失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('批量导入交易对失败:', error)
        ElMessage.error('批量导入失败: ' + (error.response?.data?.error || error.message))
      } finally {
        isImporting.value = false
      }
    }
    
    // 初始化常用交易对
    const initializeCommonPairs = async () => {
      try {
        const response = await axios.post('/api/trading-pairs/initialize-common')
        if (response.data.success) {
          ElMessage.success(response.data.message)
          loadTradingPairs()
        } else {
          ElMessage.error('初始化常用交易对失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('初始化常用交易对失败:', error)
        ElMessage.error('初始化常用交易对失败: ' + (error.response?.data?.error || error.message))
      }
    }
    
    // 生命周期钩子
    onMounted(() => {
      loadTradingPairs()
    })
    
    return {
      tradingPairs,
      filteredTradingPairs,
      isLoading,
      dialogVisible,
      isEditMode,
      isSaving,
      form,
      rules,
      searchQuery,
      showFavoritesOnly,
      importDialogVisible,
      importText,
      isImporting,
      resultDialogVisible,
      importResults,
      
      showAddDialog,
      showEditDialog,
      saveTradingPair,
      confirmDelete,
      toggleFavorite,
      showImportDialog,
      importTradingPairs,
      initializeCommonPairs,
      confirmClearAll
    }
  }
}
</script>

<style scoped>
.trading-pairs-container {
  padding: 20px;
}

.main-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-input {
  width: 250px;
}

.favorite-switch {
  margin-left: auto;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.import-format-info {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
}

.import-format-info pre {
  background-color: #ebeef5;
  padding: 8px;
  border-radius: 4px;
  margin: 10px 0;
  font-family: monospace;
}

.import-result-summary {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.import-result-summary p {
  margin: 5px 0;
}
</style> 