<template>
  <el-dialog
    title="批量创建子账号"
    v-model="dialogVisible"
    width="600px"
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
      
      <el-form-item label="创建数量" prop="count">
        <el-input-number
          v-model="form.count"
          :min="1"
          :max="100"
          :precision="0"
          style="width: 100%;"
        ></el-input-number>
        <div class="form-tip">单次最多可创建100个子账号</div>
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
      
      <el-divider content-position="left">高级设置</el-divider>
      
      <el-form-item label="导入Excel">
        <el-upload
          action="#"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :file-list="fileList"
        >
          <template #trigger>
            <el-button type="primary">选择文件</el-button>
          </template>
          <template #tip>
            <div class="el-upload__tip">
              批量创建可导入Excel模板，<el-link type="primary" @click="downloadTemplate">下载模板</el-link>
            </div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="batchCreate" :loading="loading">批量创建</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'BatchCreateDialog',
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
    // 上传文件列表
    const fileList = ref([])
    
    // 计算属性: 对话框可见性
    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })
    
    // 表单数据
    const form = ref({
      prefix: '',
      count: 10,
      accountType: 'standard',
      features: ['futures'],
      excelFile: null
    })
    
    // 表单验证规则
    const rules = {
      prefix: [
        { required: true, message: '请输入子账号前缀', trigger: 'blur' },
        { min: 3, max: 15, message: '长度在 3 到 15 个字符', trigger: 'blur' }
      ],
      count: [
        { required: true, message: '请输入创建数量', trigger: 'blur' },
        { type: 'number', min: 1, max: 100, message: '数量范围在 1 到 100 之间', trigger: 'blur' }
      ],
      accountType: [
        { required: true, message: '请选择账号类型', trigger: 'change' }
      ]
    }
    
    // 处理文件变化
    const handleFileChange = (file) => {
      fileList.value = [file]
      form.value.excelFile = file.raw
    }
    
    // 下载模板
    const downloadTemplate = () => {
      // 这里应该实现模板下载逻辑
      ElMessage.success('模板下载中...')
    }
    
    // 批量创建账号
    const batchCreate = () => {
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
            prefix: form.value.prefix, // 子账号前缀
            count: form.value.count, // 创建数量
            accountType: form.value.accountType, // 账号类型
            features: form.value.features, // 需要开通的功能
            timestamp: serverTimestamp
          };
          
          // 如果有Excel文件，需要使用FormData
          if (form.value.excelFile) {
            const formData = new FormData();
            formData.append('excelFile', form.value.excelFile);
            formData.append('data', JSON.stringify(requestData));
            
            // 调用上传Excel的API
            const response = await fetch('/api/subaccounts/import-excel', {
              method: 'POST',
              body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
              dialogVisible.value = false;
              formRef.value.resetFields();
              fileList.value = [];
              
              emit('success', {
                count: result.data?.count || form.value.count,
                accountType: form.value.accountType,
                successCount: result.data?.success_count || 0,
                failCount: result.data?.fail_count || 0
              });
              
              ElMessage.success(`成功批量创建了 ${result.data?.success_count || 0}/${result.data?.count || form.value.count} 个子账号`);
            } else {
              ElMessage.error(result.error || '批量导入Excel创建子账号失败');
            }
          } else {
            // 正常批量创建
            const response = await fetch('/api/subaccounts/batch-create', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(requestData)
            });
            
            const result = await response.json();
            
            if (result.success) {
              dialogVisible.value = false;
              formRef.value.resetFields();
              fileList.value = [];
              
              emit('success', {
                count: form.value.count,
                accountType: form.value.accountType,
                successCount: result.success_count || 0,
                failCount: result.fail_count || 0
              });
              
              ElMessage.success(`成功批量创建了 ${result.success_count || 0}/${result.total || form.value.count} 个子账号`);
            } else {
              ElMessage.error(result.error || '批量创建子账号失败');
            }
          }
        } catch (error) {
          console.error('批量创建子账号失败:', error);
          ElMessage.error('批量创建子账号失败，请检查网络连接');
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
      fileList,
      handleFileChange,
      downloadTemplate,
      batchCreate
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

.el-upload__tip {
  line-height: 1.2;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style> 