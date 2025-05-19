<template>
  <el-dialog
    title="账户激活转账"
    v-model="dialogVisible"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="account-info" v-if="account">
      <p><strong>子账号：</strong>{{ account.email }}</p>
      <p><strong>状态：</strong><el-tag :type="getStatusType(account.status)">{{ getStatusText(account.status) }}</el-tag></p>
      <div class="activation-info">
        <el-alert
          type="info"
          :closable="false"
          show-icon
        >
          <p>通过向此子账号转入资产可以激活账户并开通基本功能。</p>
          <p>推荐转入 <strong>USDT</strong> 或 <strong>BTC</strong> 等主流币种。</p>
        </el-alert>
      </div>
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
            v-for="coin in recommendedCoins"
            :key="coin.value"
            :label="coin.label"
            :value="coin.value"
          ></el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="激活金额" prop="amount">
        <el-input v-model="form.amount" type="number" placeholder="请输入转账金额">
          <template #append>{{ form.asset }}</template>
        </el-input>
        <div class="form-tip">
          可用余额: {{ availableBalance }} {{ form.asset }}
          <br>
          <span class="highlight-tip">推荐金额: {{ recommendedAmount }} {{ form.asset }}</span>
        </div>
      </el-form-item>
      
      <el-form-item label="激活后开通" prop="features">
        <el-checkbox-group v-model="form.features">
          <el-checkbox label="MARGIN">杠杆交易</el-checkbox>
          <el-checkbox label="FUTURES">期货交易</el-checkbox>
        </el-checkbox-group>
        <div class="form-tip">选择后将在激活账户后自动开通相应功能</div>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="activateAccount" :loading="loading">激活账户</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentUser } from '../../services/auth'

export default {
  name: 'AccountActivateDialog',
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
  setup(props, { emit }) {
    // 表单引用
    const formRef = ref(null)
    // 加载状态
    const loading = ref(false)
    // 可用余额 (模拟)
    const availableBalance = ref('0.00')
    
    // 计算属性: 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 推荐币种列表
    const recommendedCoins = [
      { label: 'USDT - 泰达币', value: 'USDT' },
      { label: 'BTC - 比特币', value: 'BTC' },
      { label: 'BNB - 币安币', value: 'BNB' },
      { label: 'ETH - 以太坊', value: 'ETH' }
    ]
    
    // 计算推荐金额
    const recommendedAmount = computed(() => {
      if (form.value.asset === 'USDT') return '50';
      if (form.value.asset === 'BTC') return '0.001';
      if (form.value.asset === 'BNB') return '0.1';
      if (form.value.asset === 'ETH') return '0.01';
      return '10';
    });
    
    // 表单数据
    const form = ref({
      asset: 'USDT',
      amount: '',
      features: []
    })
    
    // 监听表单可见性和币种变化
    watch(() => props.visible, (newVal) => {
      if (newVal) {
        // 对话框打开时，设置推荐金额
        form.value.amount = recommendedAmount.value;
        fetchAvailableBalance();
      }
    });
    
    watch(() => form.value.asset, () => {
      form.value.amount = recommendedAmount.value;
      fetchAvailableBalance();
    });
    
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
      ]
    }
    
    // 查询可用余额
    const fetchAvailableBalance = async () => {
      try {
        // 获取当前用户ID
        const currentUser = getCurrentUser();
        const userId = currentUser ? currentUser.userId || currentUser.id : '';
        
        // 实际调用API获取余额
        const response = await fetch(`/api/misc/balance?asset=${form.value.asset}&direction=toSubAccount&id=${userId}`);
        const result = await response.json();
        
        if (result.success) {
          availableBalance.value = result.data?.available || '0.00';
        } else {
          availableBalance.value = '0.00';
          console.error('获取余额失败:', result.error);
        }
      } catch (error) {
        console.error('获取余额失败:', error);
        availableBalance.value = '0.00';
      }
    }
    
    // 获取状态样式和文字
    const getStatusType = (status) => {
      const statusMap = {
        'ACTIVE': 'success',
        'DISABLED': 'danger',
        'PENDING': 'warning'
      }
      return statusMap[status] || 'info'
    }
    
    const getStatusText = (status) => {
      const statusMap = {
        'ACTIVE': '活跃',
        'DISABLED': '已禁用',
        'PENDING': '待激活'
      }
      return statusMap[status] || status
    }
    
    // 激活账户方法
    const activateAccount = () => {
      formRef.value.validate(async (valid) => {
        if (!valid) {
          return false
        }
        
        try {
          // 二次确认
          await ElMessageBox.confirm(
            `确认要向子账号 ${props.account.email} 转入 ${form.value.amount} ${form.value.asset} 用于激活账户${form.value.features.length > 0 ? '并开通选定功能' : ''}?`,
            '激活确认',
            {
              confirmButtonText: '确认激活',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )
          
          loading.value = true
          
          // 步骤1: 转账激活账户
          const transferData = {
            email: props.account.email,
            asset: form.value.asset,
            amount: form.value.amount,
            transferType: 'TO_SUBACCOUNT'
          };
          
          const transferResponse = await fetch('/api/subaccounts/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(transferData)
          });
          
          const transferResult = await transferResponse.json();
          
          if (!transferResult.success) {
            throw new Error(transferResult.error || '转账失败');
          }
          
          // 步骤2: 开通选定功能（如果有）
          const enableResults = [];
          
          if (form.value.features.length > 0) {
            const currentUser = getCurrentUser();
            const authHeader = {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${currentUser.token}`
            };
            
            // 开通杠杆
            if (form.value.features.includes('MARGIN')) {
              const marginResponse = await fetch('/api/subaccounts/margin/enable', {
                method: 'POST',
                headers: authHeader,
                body: JSON.stringify({ email: props.account.email })
              });
              
              const marginResult = await marginResponse.json();
              enableResults.push({
                feature: 'MARGIN',
                success: marginResult.success,
                message: marginResult.success ? '杠杆交易已开通' : marginResult.error
              });
            }
            
            // 开通期货
            if (form.value.features.includes('FUTURES')) {
              const futuresResponse = await fetch('/api/subaccounts/futures/enable', {
                method: 'POST',
                headers: authHeader,
                body: JSON.stringify({ email: props.account.email })
              });
              
              const futuresResult = await futuresResponse.json();
              enableResults.push({
                feature: 'FUTURES',
                success: futuresResult.success,
                message: futuresResult.success ? '期货交易已开通' : futuresResult.error
              });
            }
          }
          
          // 关闭对话框并清空表单
          dialogVisible.value = false;
          formRef.value.resetFields();
          
          // 触发成功事件
          emit('success', {
            email: props.account.email,
            asset: form.value.asset,
            amount: form.value.amount,
            features: form.value.features,
            enableResults
          });
          
          // 显示成功消息
          let successMsg = `已成功向账户 ${props.account.email} 转入 ${form.value.amount} ${form.value.asset}`;
          if (enableResults.some(r => r.success)) {
            successMsg += '，并开通了以下功能：';
            enableResults.forEach(r => {
              if (r.success) {
                successMsg += r.feature === 'MARGIN' ? ' 杠杆交易' : ' 期货交易';
              }
            });
          }
          ElMessage.success(successMsg);
          
        } catch (error) {
          if (error === 'cancel') return;
          console.error('账户激活失败:', error);
          ElMessage.error(error.message || '账户激活失败，请检查网络连接');
        } finally {
          loading.value = false;
        }
      });
    }
    
    return {
      formRef,
      loading,
      dialogVisible,
      form,
      rules,
      recommendedCoins,
      availableBalance,
      recommendedAmount,
      getStatusType,
      getStatusText,
      activateAccount
    }
  }
}
</script>

<style scoped>
.account-info {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 15px;
}

.account-info p {
  margin: 5px 0;
}

.activation-info {
  margin-top: 15px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.2;
  margin-top: 4px;
}

.highlight-tip {
  color: #67c23a;
  font-weight: bold;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 