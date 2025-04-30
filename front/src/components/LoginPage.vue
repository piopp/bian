<template>
  <div class="login-container">
    <div class="login-card">
      <h2>币安管理系统</h2>
      <el-form 
        ref="loginForm" 
        :model="loginForm" 
        :rules="rules" 
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入用户名"
            prefix-icon="el-icon-user"
          ></el-input>
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码"
            prefix-icon="el-icon-lock"
            show-password
          ></el-input>
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="loading" 
            @click="handleSubmit" 
            class="submit-btn"
          >
            登录
          </el-button>
        </el-form-item>
        
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
      </el-form>
    </div>
  </div>
</template>

<script>
import { login } from '../services/auth.js';
import { ElMessage } from 'element-plus';

export default {
  name: 'LoginPage',
  data() {
    return {
      loginForm: {
        username: '',
        password: '',
        remember: false
      },
      loading: false,
      errorMessage: '',
      rules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    async handleSubmit() {
      try {
        const valid = await this.$refs.loginForm.validate();
        
        if (valid) {
          this.loading = true;
          this.errorMessage = '';
          
          try {
            // 使用认证服务登录
            const userData = await login(this.loginForm.username, this.loginForm.password);
            
            ElMessage.success('登录成功');
            
            // 如果记住我被选中，增加token有效期
            if (this.loginForm.remember) {
              const user = JSON.parse(localStorage.getItem('user'));
              if (user) {
                user.exp = Date.now() + 7 * 24 * 3600000; // 7天
                localStorage.setItem('user', JSON.stringify(user));
              }
            }
            
            console.log('登录成功，用户信息:', userData);
            
            // 登录成功后，先触发一个事件，确保全局状态更新
            window.dispatchEvent(new Event('user-login-success'));
            
            // 短暂延迟后再导航，确保状态更新
            setTimeout(() => {
              // 重定向到首页
              this.$router.push('/');
            }, 100);
          } catch (error) {
            this.errorMessage = error.message || '登录失败，请检查用户名和密码';
            ElMessage.error(this.errorMessage);
          } finally {
            this.loading = false;
          }
        }
      } catch (error) {
        // 表单验证失败
        return false;
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: calc(100vh - 120px);
  background-color: #f5f7fa;
}

.login-card {
  width: 400px;
  padding: 40px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.login-card h2 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 30px;
}

.submit-btn {
  width: 100%;
}

.error-message {
  color: #f56c6c;
  font-size: 14px;
  margin-top: 10px;
  text-align: center;
}
</style> 