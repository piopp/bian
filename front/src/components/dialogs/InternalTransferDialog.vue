<template>
  <el-dialog
    title="主账户内部转账"
    v-model="dialogVisible"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <p>在主账户的不同账户类型之间转移资产（如现货、期货、杠杆等）。</p>
    </el-alert>
    
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item label="转出账户" prop="fromType">
        <el-select v-model="form.fromType" placeholder="请选择转出账户类型" style="width: 100%">
          <el-option
            v-for="type in accountTypes"
            :key="type.value"
            :label="type.label"
            :value="type.value"
          ></el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item label="转入账户" prop="toType">
        <el-select v-model="form.toType" placeholder="请选择转入账户类型" style="width: 100%">
          <el-option
            v-for="type in accountTypes"
            :key="type.value"
            :label="type.label"
            :value="type.value"
            :disabled="type.value === form.fromType"
          ></el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item 
        label="交易对" 
        prop="symbol"
        v-if="needsSymbol"
      >
        <el-input v-model="form.symbol" placeholder="请输入交易对，如BTCUSDT"></el-input>
        <div class="form-tip">逐仓保证金账户转账必须指定交易对</div>
      </el-form-item>
      
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
          <template #append>{{ form.asset }}</template>
        </el-input>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTransfer" :loading="loading">
          确认转账
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentUser, getAuthHeader } from '@/services/auth'

export default {
  name: 'InternalTransferDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
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
    
    // 账户类型列表
    const accountTypes = [
      { label: '现货账户', value: 'SPOT' },
      { label: '杠杆账户', value: 'MARGIN' },
      { label: '逐仓杠杆账户', value: 'ISOLATED_MARGIN' },
      { label: '期货账户(U本位)', value: 'FUTURES' },
      { label: '期货账户(币本位)', value: 'COIN_FUTURES' },
      { label: '资金账户', value: 'FUNDING' }
    ]
    
    // 常用币种列表
    const commonCoins = [
      { label: 'USDT - 泰达币', value: 'USDT' },
      { label: 'BTC - 比特币', value: 'BTC' },
      { label: 'BNB - 币安币', value: 'BNB' },
      { label: 'ETH - 以太坊', value: 'ETH' },
      { label: 'SOL - 索拉纳', value: 'SOL' },
      { label: 'ADA - 艾达币', value: 'ADA' },
      { label: 'XRP - 瑞波币', value: 'XRP' },
      { label: 'DOGE - 狗狗币', value: 'DOGE' }
    ]
    
    // 表单数据
    const form = ref({
      fromType: 'SPOT',
      toType: 'FUTURES',
      asset: 'USDT',
      amount: '',
      symbol: ''
    })
    
    // 监视转账类型变化，如果涉及逐仓保证金账户，则清空symbol字段
    watch([() => form.value.fromType, () => form.value.toType], () => {
      if (form.value.fromType !== 'ISOLATED_MARGIN' && form.value.toType !== 'ISOLATED_MARGIN') {
        form.value.symbol = '';
      }
    });
    
    // 计算属性: 是否需要symbol参数
    const needsSymbol = computed(() => {
      return form.value.fromType === 'ISOLATED_MARGIN' || form.value.toType === 'ISOLATED_MARGIN';
    });
    
    // 表单验证规则
    const rules = {
      fromType: [
        { required: true, message: '请选择转出账户类型', trigger: 'change' }
      ],
      toType: [
        { required: true, message: '请选择转入账户类型', trigger: 'change' },
        { validator: (rule, value, callback) => {
            if (value === form.value.fromType) {
              callback(new Error('转入账户不能与转出账户相同'))
            } else {
              callback()
            }
          }, trigger: 'change' 
        }
      ],
      symbol: [
        { required: computed(() => needsSymbol.value), message: '使用逐仓保证金账户时必须提供交易对', trigger: 'blur' }
      ],
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
      ]
    }
    
    // 处理转账
    const handleTransfer = () => {
      formRef.value.validate(async (valid) => {
        if (!valid) {
          return false
        }
        
        try {
          // 二次确认
          await ElMessageBox.confirm(
            `确认要从${getAccountTypeLabel(form.value.fromType)}转出 ${form.value.amount} ${form.value.asset} 到${getAccountTypeLabel(form.value.toType)}?`,
            '转账确认',
            {
              confirmButtonText: '确认转账',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )
          
          loading.value = true
          
          // 准备转账参数
          const transferData = {
            asset: form.value.asset,
            amount: form.value.amount,
            from_type: form.value.fromType,
            to_type: form.value.toType
          };
          
          // 如果需要交易对参数，则添加
          if (needsSymbol.value) {
            transferData.symbol = form.value.symbol;
          }
          
          // 调用API
          const response = await fetch('/api/subaccounts/internal-transfer', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              ...getAuthHeader()
            },
            body: JSON.stringify(transferData)
          });
          
          const result = await response.json();
          
          if (result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false;
            formRef.value.resetFields();
            
            // 触发成功事件
            emit('success', {
              from: form.value.fromType,
              to: form.value.toType,
              asset: form.value.asset,
              amount: form.value.amount
            });
            
            ElMessage.success(`转账成功！已将 ${form.value.amount} ${form.value.asset} 从${getAccountTypeLabel(form.value.fromType)}转入${getAccountTypeLabel(form.value.toType)}`);
          } else {
            ElMessage.error(result.error || '转账失败，请重试');
          }
        } catch (error) {
          if (error === 'cancel') return;
          console.error('转账请求失败:', error);
          ElMessage.error('转账操作失败，请检查网络连接');
        } finally {
          loading.value = false;
        }
      })
    }
    
    // 获取账户类型显示名称
    const getAccountTypeLabel = (type) => {
      const found = accountTypes.find(t => t.value === type);
      return found ? found.label : type;
    }
    
    return {
      formRef,
      loading,
      dialogVisible,
      form,
      rules,
      accountTypes,
      commonCoins,
      needsSymbol,
      handleTransfer
    }
  }
}
</script>

<style scoped>
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

.mb-4 {
  margin-bottom: 16px;
}
</style> 