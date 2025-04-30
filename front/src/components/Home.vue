<template>
  <div class="home-container">
    <main class="main-content">
      <div class="welcome-section">
        <h2>欢迎使用</h2>
        <p>这是一个自动化币安提现的工具，帮助您轻松管理加密货币资产。</p>
      </div>
      <div class="features-section">
        <div class="feature-card">
          <h3>自动提现</h3>
          <p>设置提现规则，系统将按照您的要求自动执行提现操作。</p>
        </div>
        <div class="feature-card">
          <h3>安全可靠</h3>
          <p>采用加密技术保护您的API密钥和资产安全。</p>
        </div>
        <div class="feature-card">
          <h3>实时监控</h3>
          <p>随时查看资产状态和提现历史记录。</p>
        </div>
      </div>
      <div class="action-section">
        <el-button type="primary" size="large">开始设置</el-button>
        <el-button type="info" size="large" plain>查看文档</el-button>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'HomePage',
  data() {
    return {
      // 这里可以添加首页需要的数据
    }
  },
  methods: {
    // 这里可以添加首页需要的方法
  }
}
</script>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.welcome-section {
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
}

.welcome-section h2 {
  color: #2c3e50;
  font-size: 2rem;
  margin-bottom: 15px;
}

.welcome-section p {
  color: #666;
  font-size: 1.1rem;
  line-height: 1.6;
}

.features-section {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
}

.feature-card {
  flex: 1;
  min-width: 250px;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.feature-card h3 {
  color: #2c3e50;
  font-size: 1.4rem;
  margin-bottom: 10px;
}

.feature-card p {
  color: #666;
  font-size: 1rem;
  line-height: 1.5;
}

.action-section {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}
</style> 