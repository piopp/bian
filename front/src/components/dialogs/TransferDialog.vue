<template>
  <el-dialog
    title="子账号转账"
    v-model="dialogVisible"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="account-info" v-if="account">
      <p><strong>子账号：</strong>{{ account.email }}</p>
      <p><strong>状态：</strong><el-tag :type="getStatusType(account.status)">{{ getStatusText(account.status) }}</el-tag></p>
    </div>

    <el-divider></el-divider>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item label="币种" prop="asset">
        <el-select v-model="form.asset" placeholder="请选择币种" style="width: 100%">
          <el-option
            v-for="coin in commonCoins"
            :key="coin.value"
            :label="coin.label"
            :value="coin.value"
          ></el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="转账金额" prop="amount">
        <el-input v-model="form.amount" type="number" placeholder="请输入转账金额">
          <template #append>
            <el-select v-model="form.asset" style="width: 90px">
              <el-option
                v-for="coin in commonCoins"
                :key="coin.value"
                :label="coin.value"
                :value="coin.value"
              ></el-option>
            </el-select>
          </template>
        </el-input>
        <div class="form-tip">可用余额: {{ availableBalance }} {{ form.asset }}</div>
      </el-form-item>

      <el-form-item label="转账方向" prop="direction">
        <el-radio-group v-model="form.direction">
          <el-radio label="toSubAccount">主账号 -> 子账号</el-radio>
          <el-radio label="fromSubAccount">子账号 -> 主账号</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="transferAsset" :loading="loading">确认转账</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'TransferDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    account: {
      type: Object,
      default: null
    }
  },
  emits: ['update:visible', 'success'],
  setup(props, { emit }) {
    // 表单引用
    const formRef = ref(null)
    // 加载状态
    const loading = ref(false)
    // 可用余额
    const availableBalance = ref('0.00')
    
    // 计算属性: 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 常用币种列表
    const commonCoins = [
      { label: 'BTC - 比特币', value: 'BTC' },
      { label: 'ETH - 以太坊', value: 'ETH' },
      { label: 'USDT - 泰达币', value: 'USDT' },
      { label: 'BNB - 币安币', value: 'BNB' },
      { label: 'SOL - 索拉纳', value: 'SOL' },
      { label: 'ADA - 艾达币', value: 'ADA' },
      { label: 'XRP - 瑞波币', value: 'XRP' },
      { label: 'DOGE - 狗狗币', value: 'DOGE' }
    ]
    
    // 表单数据
    const form = ref({
      asset: 'USDT',
      amount: '',
      direction: 'toSubAccount'
    })
    
    // 表单验证规则
    const rules = {
      asset: [
        { required: true, message: '请选择币种', trigger: 'change' }
      ],
      amount: [
        { required: true, message: '请输入转账金额', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value === '') {
              callback(new Error('转账金额不能为空'))
            } else if (isNaN(Number(value)) || Number(value) <= 0) {
              callback(new Error('请输入大于0的有效金额'))
            } else if (Number(value) > Number(availableBalance.value)) {
              callback(new Error('余额不足'))
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ],
      direction: [
        { required: true, message: '请选择转账方向', trigger: 'change' }
      ]
    }
    
    // 监听对话框打开
    watch(() => props.visible, (newVal) => {
      if (newVal && props.account) {
        // 清空表单
        if (formRef.value) {
          formRef.value.resetFields()
        }
        // 查询余额
        fetchAvailableBalance()
      }
    })
    
    // 监听币种变化，更新可用余额
    watch(() => form.value.asset, () => {
      fetchAvailableBalance()
    })
    
    // 监听转账方向变化，更新可用余额
    watch(() => form.value.direction, () => {
      fetchAvailableBalance()
    })
    
    // 查询可用余额
    const fetchAvailableBalance = async () => {
      if (!props.account) return
      
      try {
        // 构建查询参数
        const params = new URLSearchParams({
          asset: form.value.asset,
          direction: form.value.direction,
          email: props.account.email
        })
        
        // 请求API获取余额
        const response = await fetch(`/api/misc/balance?${params.toString()}`)
        const result = await response.json()
        
        if (result.success) {
          availableBalance.value = result.data?.available || '0.00'
        } else {
          availableBalance.value = '0.00'
          console.error('获取余额失败:', result.error)
        }
      } catch (error) {
        console.error('获取余额请求异常:', error)
        availableBalance.value = '0.00'
      }
    }
    
    // 获取状态样式
    const getStatusType = (status) => {
      if (!status) return 'info'
      
      const statusMap = {
        'ACTIVE': 'success',
        'active': 'success',
        'DISABLED': 'danger',
        'disabled': 'danger',
        'PENDING': 'warning',
        'pending': 'warning'
      }
      return statusMap[status] || 'info'
    }
    
    // 获取状态文本
    const getStatusText = (status) => {
      if (!status) return '未知'
      
      const statusMap = {
        'ACTIVE': '活跃',
        'active': '活跃',
        'DISABLED': '已禁用',
        'disabled': '已禁用',
        'PENDING': '待激活',
        'pending': '待激活'
      }
      return statusMap[status] || status
    }
    
    // 转账方法
    const transferAsset = () => {
      formRef.value.validate(async (valid) => {
        if (!valid) return
        
        try {
          // 二次确认
          await ElMessageBox.confirm(
            `确认要${form.value.direction === 'toSubAccount' ? '向' : '从'}子账号 ${props.account.email} ${form.value.direction === 'toSubAccount' ? '转入' : '转出'} ${form.value.amount} ${form.value.asset}?`,
            '转账确认',
            {
              confirmButtonText: '确认转账',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )
          
          loading.value = true
          
          // 构建请求数据
          const requestData = {
            transfers: [
              {
                email: props.account.email,
                asset: form.value.asset,
                amount: form.value.amount,
                transferType: form.value.direction === 'toSubAccount' ? 'TO_SUBACCOUNT' : 'FROM_SUBACCOUNT'
              }
            ]
          }
          
          // 调用API执行转账
          const response = await fetch('/api/subaccounts/batch-transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
          })
          
          const result = await response.json()
          
          if (result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false
            formRef.value.resetFields()
            
            // 触发成功事件
            emit('success', {
              email: props.account.email,
              asset: form.value.asset,
              amount: form.value.amount,
              direction: form.value.direction
            })
            
            ElMessage.success('转账成功')
          } else {
            ElMessage.error(result.error || '转账失败，请重试')
          }
        } catch (error) {
          if (error === 'cancel') return
          
          console.error('转账请求异常:', error)
          ElMessage.error('转账异常: ' + (error.message || '未知错误'))
        } finally {
          loading.value = false
        }
      })
    }
    
    // 组件挂载时执行
    onMounted(() => {
      if (props.visible && props.account) {
        fetchAvailableBalance()
      }
    })
    
    return {
      formRef,
      dialogVisible,
      form,
      rules,
      loading,
      availableBalance,
      commonCoins,
      getStatusType,
      getStatusText,
      transferAsset
    }
  }
}
</script>

<style scoped>
.account-info {
  margin-bottom: 20px;
}

.account-info p {
  margin: 8px 0;
  display: flex;
  align-items: center;
}

.account-info strong {
  display: inline-block;
  width: 80px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
  text-align: right;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 