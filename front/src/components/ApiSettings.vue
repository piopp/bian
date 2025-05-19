<template>
  <div class="api-settings-container">
    <h1 class="page-title">币安API设置</h1>
    
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <h5><el-icon><InfoFilled /></el-icon> 关于API设置</h5>
          <el-button type="info" size="small" @click="syncServerTime">
            <el-icon><Timer /></el-icon> 同步服务器时间
          </el-button>
        </div>
      </template>
      <p>请设置您的币安API密钥以使用所有功能。这些信息将安全地存储在服务器中，不会暴露在代码中或被发送到除币安以外的任何服务器。</p>
      <p><strong>注意：</strong>出于安全考虑，请确保您的API密钥具有适当的权限设置，仅开启必要的操作权限。</p>
    </el-card>

    <!-- 当前配置状态卡片 -->
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <h5><el-icon><InfoFilled /></el-icon> 当前API配置状态</h5>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="API Key">
            <el-input 
              v-model="apiKeyDisplay" 
              readonly 
              placeholder="未设置"
            >
              <template #prefix>
                <el-icon><key /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="API Secret">
            <el-input 
              v-model="apiSecretDisplay" 
              readonly 
              placeholder="未设置"
            >
              <template #prefix>
                <el-icon><lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </el-col>
      </el-row>
      <p class="small-text">出于安全考虑，显示的是部分隐藏的密钥信息。</p>
    </el-card>

    <!-- API设置表单 -->
    <el-card class="form-card">
      <el-form 
        ref="apiFormRef" 
        id="apiForm"
        :model="apiForm" 
        :rules="rules" 
        label-position="top"
      >
        <el-form-item label="API Key" prop="apiKey">
          <el-input 
            v-model="apiForm.apiKey" 
            placeholder="输入币安API Key"
          >
            <template #prefix>
              <el-icon><key /></el-icon>
            </template>
          </el-input>
          <div class="form-hint">您可以在币安官网的API管理中心创建API密钥</div>
        </el-form-item>
        
        <el-form-item label="API Secret" prop="apiSecret">
          <el-input 
            v-model="apiForm.apiSecret" 
            placeholder="输入API Secret" 
            :type="showSecret ? 'text' : 'password'"
          >
            <template #prefix>
              <el-icon><lock /></el-icon>
            </template>
            <template #append>
              <el-button @click="showSecret = !showSecret">
                <el-icon>
                  <View v-if="!showSecret" />
                  <Hide v-else />
                </el-icon>
              </el-button>
            </template>
          </el-input>
          <div class="form-hint">请妥善保管您的API Secret，不要分享给他人</div>
        </el-form-item>
        
        <div class="form-actions">
          <el-button type="primary" @click="saveSettings" :loading="loading">
            <el-icon><Check /></el-icon> 保存设置
          </el-button>
          <el-button type="danger" plain @click="clearSettings" :loading="loading">
            <el-icon><Delete /></el-icon> 清除设置
          </el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 时间同步状态 -->
    <el-card v-if="showTimeStatus" class="time-card">
      <template #header>
        <div class="card-header">
          <h5><el-icon><Timer /></el-icon> 服务器时间状态</h5>
        </div>
      </template>
      <el-table :data="timeData" border style="width: 100%">
        <el-table-column prop="name" label="项目" width="180"></el-table-column>
        <el-table-column prop="value" label="值"></el-table-column>
      </el-table>
      <p class="small-text mt-10">时间同步对于执行API交易非常重要。如果时间偏移过大，可能导致请求被拒绝。</p>
    </el-card>

    <!-- 常见问题 -->
    <el-card class="faq-card">
      <template #header>
        <div class="card-header">
          <h5><el-icon><QuestionFilled /></el-icon> 常见问题</h5>
        </div>
      </template>
      <el-collapse>
        <el-collapse-item title="如何在币安创建API密钥？" name="1">
          <ol>
            <li>登录您的币安账户</li>
            <li>访问 <a href="https://www.binance.com/cn/my/settings/api-management" target="_blank">API管理</a> 页面</li>
            <li>点击"创建API"按钮</li>
            <li>完成安全验证</li>
            <li>设置API权限（建议仅启用"读取"和必要的交易权限，禁用提现权限）</li>
            <li>保存生成的API Key和Secret</li>
          </ol>
        </el-collapse-item>
        <el-collapse-item title="API密钥如何存储？" name="2">
          <p>您的API密钥将安全地存储在服务器的数据库中，这样可以确保：</p>
          <ul>
            <li>API密钥不会直接暴露在代码中</li>
            <li>配置文件已被添加到.gitignore，不会被提交到版本控制系统</li>
            <li>应用程序重启后仍能使用保存的密钥</li>
          </ul>
          <p>尽管如此，仍请注意以下安全建议：</p>
          <ul>
            <li>仅为本应用创建专用API密钥</li>
            <li>限制API权限，禁用提现功能</li>
            <li>设置IP白名单，只允许从固定IP访问</li>
            <li>定期更换API密钥</li>
          </ul>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, QuestionFilled, Check, Delete, Timer, View, Hide, Key as key, Lock as lock } from '@element-plus/icons-vue'
import { getCurrentUser } from '../services/auth'
import { syncWithServer, getSyncStatus, getLastSyncTime, getCorrectedDate } from '../services/timeSync'

// 使用相对路径代替硬编码URL，这样请求会被vue.config.js中的代理配置处理
const API_URL = '/api';

export default {
  name: 'ApiSettingsPage',
  components: {
    InfoFilled,
    QuestionFilled,
    Check,
    Delete,
    Timer,
    View,
    Hide,
    key,
    lock
  },
  setup() {
    const loading = ref(false)
    const showSecret = ref(false)
    const showTimeStatus = ref(false)
    const apiForm = reactive({
      apiKey: '',
      apiSecret: ''
    })
    const apiKeyDisplay = ref('未设置')
    const apiSecretDisplay = ref('未设置')
    const timeData = ref([
      { name: '本地时间', value: '-' },
      { name: '服务器时间', value: '-' },
      { name: '时间偏移', value: '- 毫秒' }
    ])
    const lastSyncTime = ref(null) // 上次同步时间
    const syncInterval = ref(null) // 保存定时器引用
    
    // 表单验证规则
    const rules = {
      apiKey: [
        { required: true, message: '请输入API Key', trigger: 'blur' },
        { min: 10, message: 'API Key长度不正确', trigger: 'blur' }
      ],
      apiSecret: [
        { required: true, message: '请输入API Secret', trigger: 'blur' },
        { min: 10, message: 'API Secret长度不正确', trigger: 'blur' }
      ]
    }
    
    const apiFormRef = ref(null);
    
    // 获取当前API设置
    const fetchApiSettings = async () => {
      try {
        const user = getCurrentUser()
        if (!user) {
          console.log('未登录，无法获取API设置');
          return;
        }
        
        // 使用用户ID而非用户名获取主账号API设置
        const userId = user.id;  // 直接使用id字段
        console.log('正在获取API设置，用户ID:', userId);
        
        if (!userId) {
          console.error('无法获取用户ID');
          ElMessage.error('无法获取用户ID，请重新登录');
          return;
        }
        
        const response = await fetch(`${API_URL}/settings/api-keys/${userId}`, {
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
        
        console.log('API设置获取响应状态:', response.status);
        
        const result = await response.json();
        console.log('API设置获取响应数据:', result);
        
        if (response.ok && result.success) {
          const apiData = result.data;
          if (apiData) {
            console.log('成功获取API设置');
            // 显示部分隐藏的API信息
            apiKeyDisplay.value = maskString(apiData.apiKey);
            apiSecretDisplay.value = apiData.hasApiSecret ? '********' : '未设置';
          } else {
            console.log('API密钥未设置');
            apiKeyDisplay.value = '未设置';
            apiSecretDisplay.value = '未设置';
          }
        } else {
          console.error('获取API设置失败:', result.error);
          ElMessage.error(result.error || '获取API设置失败');
        }
      } catch (error) {
        console.error('获取API设置异常:', error);
        ElMessage.error('获取API设置时发生错误');
      }
    }
    
    // 保存API设置
    const saveSettings = async () => {
      try {
        // 使用ref引用进行表单验证
        if (!apiFormRef.value) {
          console.error('找不到表单引用');
          ElMessage.error('表单验证失败');
          return;
        }
        
        let valid = false;
        try {
          valid = await apiFormRef.value.validate();
        } catch (error) {
          console.error('表单验证错误:', error);
          ElMessage.error('表单验证失败');
          return;
        }
        
        if (!valid) {
          console.log('表单验证未通过');
          return;
        }
        
        console.log('准备提交的表单数据:', apiForm);
        
        loading.value = true;
        const user = getCurrentUser();
        if (!user) {
          ElMessage.error('请先登录');
          return;
        }
        
        // 使用用户ID而非用户名保存API设置
        const userId = user.userId || user.id;
        
        // 发送请求到后端
        const response = await fetch(`${API_URL}/settings/api-keys/${userId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            apiKey: apiForm.apiKey,
            apiSecret: apiForm.apiSecret
          })
        });
        
        const result = await response.json();
        console.log('API响应:', result);
        
        if (response.ok && result.success) {
          ElMessage.success(result.message || 'API设置保存成功');
          // 重新获取显示的API信息
          await fetchApiSettings();
          // 清空表单
          apiForm.apiKey = '';
          apiForm.apiSecret = '';
        } else {
          throw new Error(result.error || '保存失败');
        }
      } catch (error) {
        ElMessage.error(error.message || '保存API设置失败');
      } finally {
        loading.value = false;
      }
    }
    
    // 清除API设置
    const clearSettings = async () => {
      try {
        loading.value = true
        const user = getCurrentUser()
        if (!user) {
          ElMessage.error('请先登录')
          return
        }
        
        // 使用用户ID而非用户名删除API设置
        const userId = user.userId || user.id;
        
        const response = await fetch(`${API_URL}/settings/api-keys/${userId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        })
        
        const result = await response.json()
        
        if (response.ok && result.success) {
          ElMessage.success(result.message || 'API设置已清除')
          apiKeyDisplay.value = '未设置'
          apiSecretDisplay.value = '未设置'
        } else {
          throw new Error(result.error || '清除失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '清除API设置失败')
      } finally {
        loading.value = false
      }
    }
    
    // 同步服务器时间
    const syncServerTime = async () => {
      try {
        showTimeStatus.value = false;
        loading.value = true;
        
        // 使用时间同步服务
        const syncResult = await syncWithServer();
        
        if (!syncResult.success) {
          throw new Error(syncResult.message || '同步币安服务器时间失败');
        }
        
        // 获取同步状态
        // eslint-disable-next-line no-unused-vars
        const status = getSyncStatus();
        const correctedDate = getCorrectedDate();
        const localTime = new Date().toLocaleString();
        const serverTime = correctedDate.toLocaleString();
        
        timeData.value = [
          { name: '本地时间', value: localTime },
          { name: '服务器时间', value: serverTime },
          { name: '时间来源', value: status.source === 'binance' ? '币安服务器' : '服务器(后备)' },
          { name: '时间偏移', value: `${status.offset} 毫秒` },
          { name: '网络延迟', value: `${status.latency || 0} 毫秒` },
          { name: '上次同步', value: status.timestamp.toLocaleString() }
        ];
        
        if (Math.abs(status.offset) > 1000) {
          // 如果时间偏差超过1秒，给出警告
          ElMessage.warning(`本地时间与${status.source === 'binance' ? '币安' : ''}服务器时间偏差较大(${status.offset}毫秒)，系统已自动同步`);
        } else {
          ElMessage.success('时间同步成功');
        }
        
        showTimeStatus.value = true;
      } catch (error) {
        console.error('同步服务器时间失败:', error);
        ElMessage.error('同步服务器时间失败: ' + (error.message || '未知错误'));
        
        // 显示上次成功的同步状态（如果有）
        const lastSync = getLastSyncTime();
        if (lastSync) {
          timeData.value = [
            { name: '本地时间', value: new Date().toLocaleString() },
            { name: '服务器时间', value: '同步失败' },
            { name: '时间来源', value: '未知' },
            { name: '时间偏移', value: '未知' },
            { name: '网络延迟', value: '未知' },
            { name: '上次同步', value: lastSync.toLocaleString() },
            { name: '同步状态', value: '失败 - ' + (error.message || '未知错误') }
          ];
          showTimeStatus.value = true;
        }
      } finally {
        loading.value = false;
      }
    }
    
    // 辅助函数：部分隐藏字符串
    const maskString = (str) => {
      if (!str) return '未设置'
      if (str.length <= 8) return '********'
      return str.substring(0, 4) + '****' + str.substring(str.length - 4)
    }
    
    // 设置自动同步时间的定时器（每30分钟同步一次）
    const setupTimeSyncInterval = () => {
      // 由于在main.js中已经初始化了全局定时器，这里不再重复设置
      // 只更新显示
      const lastSync = getLastSyncTime();
      
      if (getSyncStatus().success && lastSync) {
        const correctedDate = getCorrectedDate();
        const localTime = new Date().toLocaleString();
        const serverTime = correctedDate.toLocaleString();
        
        timeData.value = [
          { name: '本地时间', value: localTime },
          { name: '服务器时间', value: serverTime },
          { name: '时间来源', value: getSyncStatus().source === 'binance' ? '币安服务器' : '服务器(后备)' },
          { name: '时间偏移', value: `${getSyncStatus().offset} 毫秒` },
          { name: '网络延迟', value: `${getSyncStatus().latency || 0} 毫秒` },
          { name: '上次同步', value: lastSync.toLocaleString() }
        ];
        
        showTimeStatus.value = true;
      }
    }
    
    onMounted(async () => {
      // 获取API设置
      await fetchApiSettings()
      
      // 如果已存在同步状态，显示它；否则进行同步
      const lastSync = getLastSyncTime();
      if (lastSync) {
        setupTimeSyncInterval();
      } else {
        await syncServerTime();
      }
    })
    
    // 组件卸载时清除定时器
    onUnmounted(() => {
      if (syncInterval.value) {
        clearInterval(syncInterval.value)
      }
    })
    
    return {
      loading,
      showSecret,
      showTimeStatus,
      apiForm,
      apiKeyDisplay,
      apiSecretDisplay,
      rules,
      timeData,
      saveSettings,
      clearSettings,
      syncServerTime,
      apiFormRef,
      lastSyncTime
    }
  }
}
</script>

<style scoped>
.api-settings-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
  font-size: 1.8rem;
  color: #2c3e50;
}

.info-card, .status-card, .form-card, .time-card, .faq-card {
  margin-bottom: 20px;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h5 {
  margin: 0;
  font-size: 16px;
  display: flex;
  align-items: center;
}

.card-header .el-icon {
  margin-right: 8px;
}

.small-text {
  font-size: 12px;
  color: #909399;
  margin-top: 10px;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.mt-10 {
  margin-top: 10px;
}
</style> 