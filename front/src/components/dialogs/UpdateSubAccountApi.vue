<template>
  <el-dialog
    v-model="dialogVisible"
    title="修改子账号API设置"
    width="500px"
    destroy-on-close
  >
    <el-form 
      ref="formRef" 
      :model="form" 
      :rules="rules" 
      label-width="100px"
      status-icon
    >
      <el-form-item label="子账号邮箱" prop="email">
        <el-input v-model="form.email" disabled />
      </el-form-item>
      
      <el-form-item label="API Key" prop="apiKey">
        <el-input 
          v-model="form.apiKey" 
          placeholder="输入新的API Key"
        />
      </el-form-item>
      
      <el-form-item label="API Secret" prop="apiSecret">
        <el-input 
          v-model="form.apiSecret" 
          placeholder="输入新的API Secret" 
          :type="showSecret ? 'text' : 'password'"
        >
          <template #suffix>
            <el-icon class="cursor-pointer" @click="showSecret = !showSecret">
              <el-icon-view v-if="!showSecret" />
              <el-icon-hide v-else />
            </el-icon>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item label="权限" prop="permissions">
        <el-select v-model="form.permissions" placeholder="选择API权限" multiple>
          <el-option label="读取信息" value="READ_INFO" />
          <el-option label="启用现货交易" value="ENABLE_SPOT" />
          <el-option label="启用合约交易" value="ENABLE_FUTURES" />
          <el-option label="启用杠杆交易" value="ENABLE_MARGIN" />
        </el-select>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="loading">
          保存修改
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'UpdateSubAccountApi',
  
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    accountData: {
      type: Object,
      default: () => ({})
    }
  },
  
  emits: ['update:visible', 'success'],
  
  setup(props, { emit }) {
    const formRef = ref(null)
    const loading = ref(false)
    const showSecret = ref(false)
    
    const dialogVisible = ref(false)
    
    // 表单数据
    const form = reactive({
      email: '',
      apiKey: '',
      apiSecret: '',
      permissions: []
    })
    
    // 表单验证规则
    const rules = {
      apiKey: [
        { required: true, message: '请输入API Key', trigger: 'blur' },
        { min: 10, message: 'API Key长度不能小于10个字符', trigger: 'blur' }
      ],
      apiSecret: [
        { required: true, message: '请输入API Secret', trigger: 'blur' },
        { min: 10, message: 'API Secret长度不能小于10个字符', trigger: 'blur' }
      ]
    }
    
    // 监听visible属性变化
    watch(() => props.visible, (newVal) => {
      dialogVisible.value = newVal
      if (newVal && props.accountData) {
        // 初始化表单数据
        form.email = props.accountData.email || ''
        form.apiKey = ''
        form.apiSecret = ''
        
        if (props.accountData.permissions) {
          form.permissions = props.accountData.permissions.split(',')
        } else {
          form.permissions = ['READ_INFO', 'ENABLE_SPOT', 'ENABLE_FUTURES']
        }
      }
    })
    
    // 监听对话框状态变化，同步到父组件
    watch(dialogVisible, (newVal) => {
      emit('update:visible', newVal)
    })
    
    // 提交表单
    const submitForm = async () => {
      if (!formRef.value) return
      
      await formRef.value.validate(async (valid) => {
        if (!valid) {
          ElMessage.warning('请完善表单信息')
          return
        }
        
        loading.value = true
        
        try {
          // 将权限数组转为逗号分隔的字符串
          const permissionsStr = form.permissions.join(',')
          
          const response = await axios.put(`/api/subaccounts/api-keys/${form.email}/update`, {
            api_key: form.apiKey,
            api_secret: form.apiSecret,
            permissions: permissionsStr
          })
          
          if (response.data.success) {
            ElMessage.success('子账号API设置修改成功')
            dialogVisible.value = false
            emit('success', response.data.data)
          } else {
            ElMessage.error(`修改失败: ${response.data.error || '未知错误'}`)
          }
        } catch (error) {
          console.error('修改API设置出错:', error)
          const errorMsg = error.response?.data?.error || error.message || '未知错误'
          ElMessage.error(`修改API设置出错: ${errorMsg}`)
        } finally {
          loading.value = false
        }
      })
    }
    
    return {
      formRef,
      dialogVisible,
      form,
      rules,
      loading,
      showSecret,
      submitForm
    }
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.cursor-pointer {
  cursor: pointer;
}
</style> 