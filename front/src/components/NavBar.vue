<template>
  <div class="navbar-container">
    <el-menu
      :default-active="activeIndex"
      class="el-menu-demo"
      mode="horizontal"
      :ellipsis="false"
      background-color="#545c64"
      text-color="#fff"
      active-text-color="#ffd04b"
      @select="handleSelect"
    >
      <el-menu-item index="0">
        <el-icon><house /></el-icon>
        <span>币安管理系统</span>
      </el-menu-item>
      <div class="flex-grow" />
      <template v-if="isLoggedIn">
        <el-menu-item index="4">API设置</el-menu-item>
        <el-menu-item index="6">子账户管理</el-menu-item>
        <el-menu-item index="7">批量子账户</el-menu-item>
        <el-menu-item index="/trading-pairs">
          <el-icon><Money /></el-icon>
          <span>交易对管理</span>
        </el-menu-item>
        <el-sub-menu index="user">
          <template #title>
            <el-icon><user /></el-icon>
            {{ username }}
          </template>
          <el-menu-item index="logout">
            <el-icon><switch-button /></el-icon>
            退出登录
          </el-menu-item>
        </el-sub-menu>
      </template>
      <template v-else>
        <el-menu-item index="login">
          <el-icon><key /></el-icon>
          登录
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { House, User, SwitchButton, Key, Money } from '@element-plus/icons-vue'
import { logout, getCurrentUser, isAuthenticated } from '../services/auth.js'
import { ElMessage } from 'element-plus'

export default {
  name: 'NavBarComponent',
  components: {
    House,
    User,
    SwitchButton,
    Key,
    Money
  },
  setup() {
    const activeIndex = ref('1')
    const router = useRouter()
    const route = useRoute()
    const loginStatus = ref(isAuthenticated())

    // 检查用户是否已登录
    const isLoggedIn = computed(() => {
      return loginStatus.value
    })

    // 监听路由变化
    watch(route, () => {
      // 路由变化时重新检查登录状态
      loginStatus.value = isAuthenticated()
    }, { immediate: true })

    // 组件挂载时也检查一次
    onMounted(() => {
      loginStatus.value = isAuthenticated()
      
      // 监听登录成功事件
      window.addEventListener('user-login-success', () => {
        console.log('检测到登录成功事件，更新导航栏状态');
        loginStatus.value = isAuthenticated()
      })
    })

    // 获取用户名
    const username = computed(() => {
      const user = getCurrentUser()
      return user ? user.username : ''
    })

    const handleSelect = (key) => {
      console.log('选择菜单项:', key);
      
      switch (key) {
        case '0':
          router.push('/');
          break;
        case 'login':
          router.push('/login');
          break;
        case 'logout':
          // 使用认证服务登出
          logout();
          ElMessage.success('已成功登出');
          router.push('/login');
          break;
        case '4':
          // API设置页面
          console.log('正在导航到API设置页面');
          router.push('/');
          break;
        case '6':
          // 子账户管理页面
          console.log('正在导航到子账户管理页面');
          router.push('/sub-accounts');
          break;
        case '7':
          // 批量子账户页面
          console.log('正在导航到批量子账户页面');
          router.push('/batch-subaccount');
          break;
        case '/trading-pairs':
          // 交易对管理页面
          console.log('正在导航到交易对管理页面');
          router.push('/trading-pairs');
          break;
        default:
          console.log('未知的菜单项:', key);
          break;
      }
    }

    return {
      activeIndex,
      handleSelect,
      isLoggedIn,
      username
    }
  }
}
</script>

<style scoped>
.navbar-container {
  width: 100%;
}

.flex-grow {
  flex-grow: 1;
}

.el-menu {
  display: flex;
}
</style> 