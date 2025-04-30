<template>
  <el-dialog
    title="创建子账号"
    v-model="dialogVisible"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item label="子账号前缀" prop="prefix">
        <el-input v-model="form.prefix" placeholder="请输入子账号前缀"></el-input>
        <div class="form-tip">将自动添加随机字符作为邮箱后缀</div>
      </el-form-item>
      
      <el-form-item label="账号类型" prop="accountType">
        <el-select 
          v-model="form.accountType" 
          placeholder="请选择账号类型"
          style="width: 100%;"
        >
          <el-option label="普通子账号" value="standard"></el-option>
          <el-option label="管理子账号" value="manager"></el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item label="开通功能" prop="features">
        <el-checkbox-group v-model="form.features">
          <el-checkbox label="futures">期货</el-checkbox>
          <el-checkbox label="margin">杠杆</el-checkbox>
          <el-checkbox label="options">期权</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createAccount" :loading="loading">创建</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'CreateAccountDialog',
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
    
    // 表单数据
    const form = ref({
      prefix: '',
      accountType: 'standard',
      features: []
    })
    
    // 表单验证规则
    const rules = {
      prefix: [
        { required: true, message: '请输入子账号前缀', trigger: 'blur' },
        { min: 3, max: 15, message: '长度在 3 到 15 个字符', trigger: 'blur' }
      ],
      accountType: [
        { required: true, message: '请选择账号类型', trigger: 'change' }
      ]
    }
    
    // 创建账号方法
    const createAccount = () => {
      formRef.value.validate(async (valid) => {
        if (!valid) {
          return false
        }
        
        try {
          loading.value = true
          
          // 获取服务器时间
          let serverTimestamp = Date.now(); // 默认使用本地时间
          try {
            const response = await fetch('/api/server_time');
            if (response.ok) {
              const data = await response.json();
              if (data && data.server_time) {
                serverTimestamp = data.server_time;
              }
            }
          } catch (error) {
            console.error('获取服务器时间失败，将使用本地时间:', error);
          }
          
          // 构建请求数据
          const requestData = {
            subaccount_name: form.value.prefix, // 子账号名称
            accountType: form.value.accountType, // 账号类型
            features: form.value.features, // 需要开通的功能
            timestamp: serverTimestamp
          };
          
          // 实际调用API创建子账号
          const response = await fetch('/api/subaccounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
          });
          
          const result = await response.json();
          
          if (result.success) {
            // 关闭对话框并清空表单
            dialogVisible.value = false;
            formRef.value.resetFields();
            
            // 触发成功事件
            emit('success', {
              email: result.data?.email || '子账号创建成功',
              success: true
            });
            
            ElMessage.success(`子账号 ${result.data?.email || ''} 创建成功`);
          } else {
            ElMessage.error(result.error || '创建子账号失败，请重试');
          }
        } catch (error) {
          console.error('创建子账号失败:', error);
          ElMessage.error('创建子账号失败，请检查网络连接');
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
      createAccount
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
</style> 