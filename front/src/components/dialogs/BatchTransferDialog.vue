<template>
  <el-dialog
    title="批量转账"
    v-model="dialogVisible"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="selected-accounts-info">
      <p><strong>已选择账号：</strong>{{ selectedAccounts.length }} 个</p>
      <el-tag
        v-for="(account, index) in displayedAccounts"
        :key="index"
        class="account-tag"
        type="info"
      >
        {{ account.email }}
      </el-tag>
      <el-tag v-if="hasMoreAccounts" class="account-tag" type="info">...</el-tag>
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

      <el-form-item label="转账方式" prop="distributionMethod">
        <el-radio-group v-model="form.distributionMethod">
          <el-radio label="equal">平均分配</el-radio>
          <el-radio label="fixed">固定金额</el-radio>
        </el-radio-group>
        <div class="form-tip">
          平均分配：总金额平均分配给所有账号 / 固定金额：每个账号分配固定金额
        </div>
      </el-form-item>

      <el-form-item 
        :label="form.distributionMethod === 'equal' ? '总金额' : '每账号金额'" 
        prop="amount"
      >
        <el-input v-model="form.amount" type="number" placeholder="请输入转账金额">
          <template #append>{{ form.asset }}</template>
        </el-input>
        <div class="form-tip">
          <template v-if="form.distributionMethod === 'equal'">
            每个账号将收到: {{ perAccountAmount }} {{ form.asset }}
          </template>
          <template v-else>
            总计转出: {{ totalAmount }} {{ form.asset }}
          </template>
        </div>
      </el-form-item>

      <el-form-item label="转账方向" prop="direction">
        <el-radio-group v-model="form.direction">
          <el-radio label="toSubAccounts">主账号 -> 子账号</el-radio>
          <el-radio label="fromSubAccounts">子账号 -> 主账号</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="batchTransfer" :loading="loading">
          批量转账 ({{selectedAccounts.length}}个账号)
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentUser } from '../../services/auth'

export default {
  name: 'BatchTransferDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    selectedAccounts: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:visible', 'success'],
  setup(props, { emit }) {
    // 表单引用
    const formRef = ref(null)
    // 加载状态
    const loading = ref(false)
    
    // 计算属性: 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 显示账号（最多显示5个）
    const displayedAccounts = computed(() => {
      return props.selectedAccounts.slice(0, 5)
    })
    
    // 是否有更多账号
    const hasMoreAccounts = computed(() => {
      return props.selectedAccounts.length > 5
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
      distributionMethod: 'equal',
      amount: '',
      direction: 'toSubAccounts'
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
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ],
      distributionMethod: [
        { required: true, message: '请选择转账方式', trigger: 'change' }
      ],
      direction: [
        { required: true, message: '请选择转账方向', trigger: 'change' }
      ]
    }
    
    // 计算每个账号分配的金额
    const perAccountAmount = computed(() => {
      if (form.value.distributionMethod === 'equal' && form.value.amount && props.selectedAccounts.length > 0) {
        return (Number(form.value.amount) / props.selectedAccounts.length).toFixed(8)
      }
      return form.value.amount || '0'
    })
    
    // 计算总金额
    const totalAmount = computed(() => {
      if (form.value.distributionMethod === 'fixed' && form.value.amount && props.selectedAccounts.length > 0) {
        return (Number(form.value.amount) * props.selectedAccounts.length).toFixed(8)
      }
      return form.value.amount || '0'
    })
    
    // 批量转账方法
    const batchTransfer = () => {
      formRef.value.validate(async (valid) => {
        if (!valid) {
          return false
        }
        
        if (props.selectedAccounts.length === 0) {
          ElMessage.warning('请至少选择一个子账号')
          return false
        }
        
        try {
          // 二次确认
          const confirmMessage = form.value.direction === 'toSubAccounts'
            ? `确认要向 ${props.selectedAccounts.length} 个子账号${form.value.distributionMethod === 'equal' ? '平均' : '每人'}转入 ${form.value.distributionMethod === 'equal' ? form.value.amount : perAccountAmount.value} ${form.value.asset}?`
            : `确认要从 ${props.selectedAccounts.length} 个子账号${form.value.distributionMethod === 'equal' ? '平均' : '每人'}转出 ${form.value.distributionMethod === 'equal' ? form.value.amount : perAccountAmount.value} ${form.value.asset}?`
          
          await ElMessageBox.confirm(
            confirmMessage,
            '批量转账确认',
            {
              confirmButtonText: '确认转账',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )
          
          loading.value = true
          
          // 获取当前用户ID
          const currentUser = getCurrentUser();
          const userId = currentUser ? currentUser.userId || currentUser.id : '';
          
          // 准备转账参数
          const transfers = [];
          const perAccount = form.value.distributionMethod === 'equal' 
            ? Number(form.value.amount) / props.selectedAccounts.length 
            : Number(form.value.amount);
            
          // 为每个子账号创建转账请求
          for (const account of props.selectedAccounts) {
            transfers.push({
              email: account.email,
              asset: form.value.asset,
              amount: perAccount.toString(),
              transferType: form.value.direction === 'toSubAccounts' ? 'TO_SUBACCOUNT' : 'FROM_SUBACCOUNT'
            });
          }
          
          // 调用批量转账API
          const response = await fetch('/api/subaccounts/batch-transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: userId,
              transfers: transfers
            })
          });
          
          const result = await response.json();
          
          if (result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false;
            formRef.value.resetFields();
            
            // 触发成功事件
            emit('success', {
              accounts: props.selectedAccounts.length,
              success: result.success_count,
              failed: result.fail_count
            });
            
            if (result.success_count === props.selectedAccounts.length) {
              ElMessage.success(`已成功向${result.success_count}个子账号完成转账`);
            } else if (result.success_count > 0) {
              ElMessage.warning(`转账部分成功: ${result.success_count}个成功, ${result.fail_count}个失败`);
            } else {
              ElMessage.error(`所有转账都失败了，请检查账号余额和权限`);
            }
          } else {
            ElMessage.error(result.error || '批量转账操作失败，请重试');
          }
        } catch (error) {
          console.error('批量转账请求失败:', error);
          ElMessage.error('批量转账操作失败，请检查网络连接');
        } finally {
          loading.value = false;
        }
      })
    }
    
    return {
      formRef,
      loading,
      dialogVisible,
      form,
      rules,
      commonCoins,
      displayedAccounts,
      hasMoreAccounts,
      perAccountAmount,
      totalAmount,
      batchTransfer
    }
  }
}
</script>

<style scoped>
.selected-accounts-info {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 15px;
}

.account-tag {
  margin: 5px 5px 5px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.2;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 