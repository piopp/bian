<template>
  <div id="app">
    <NavBar />
    <div class="content-container">
      <router-view @open-arbitrage="openArbitrageDialog"/>
    </div>
    <!-- 自动化套利对话框 -->
    <auto-arbitrage-dialog
      v-model="arbitrageDialogVisible"
      :account="arbitrageAccount"
      :selectedAccounts="arbitrageSelectedAccounts"
      @success="handleArbitrageSuccess"
    />
    
    <!-- 调试信息浮动按钮 -->
    <div class="debug-floating-button" @click="toggleDebugInfo" v-if="showDebugButton">
      <span>调试信息</span>
    </div>
    
    <!-- 调试信息面板 -->
    <div class="debug-floating-panel" v-if="showDebugInfo">
      <div class="debug-panel-header">
        <h3>系统调试信息</h3>
        <button @click="showDebugInfo = false">关闭</button>
      </div>
      <div class="debug-panel-content">
        <div><strong>应用版本:</strong> v1.0.0</div>
        <div><strong>子账号加载状态:</strong> {{ isSubaccountsLoaded ? '已加载' : '未加载' }}</div>
        <div><strong>子账号总数:</strong> {{ totalSubaccounts }}</div>
        <div><strong>带API子账号:</strong> {{ withApiSubaccounts }}</div>
        <div><strong>主账号信息:</strong> {{ mainAccountInfo }}</div>
        <div class="debug-actions">
          <button @click="forceRefreshSubaccounts">强制刷新子账号</button>
          <button @click="refreshMainAccountInfo">刷新主账号</button>
          <button @click="addTestAccounts">添加测试账号</button>
          <button @click="clearLocalStorage">清除本地存储</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import NavBar from './components/NavBar.vue'
import AutoArbitrageDialog from './components/dialogs/AutoArbitrageDialog.vue'
import eventBus from './services/eventBus.js'
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useSubaccountsStore } from './stores/subaccounts'
import { useUserStore } from './stores/userStore'

export default {
  name: 'App',
  components: {
    NavBar,
    AutoArbitrageDialog,
  },
  setup() {
    // 添加控制台问候语
    console.log('=== 币安提现系统启动 ===')
    console.log('如遇问题，请使用F12打开控制台查看详细日志')
    
    const arbitrageDialogVisible = ref(false);
    const arbitrageAccount = ref(null);
    const arbitrageSelectedAccounts = ref([]);
    
    // 调试相关
    const showDebugButton = ref(true);
    const showDebugInfo = ref(false);
    
    // 获取子账号Store
    const subaccountsStore = useSubaccountsStore();
    
    // 获取主账号Store
    const userStore = useUserStore();
    
    // 计算属性
    const isSubaccountsLoaded = computed(() => 
      subaccountsStore.subaccounts && subaccountsStore.subaccounts.length > 0);
    const totalSubaccounts = computed(() => 
      Array.isArray(subaccountsStore.subaccounts) ? subaccountsStore.subaccounts.length : 0);
    const withApiSubaccounts = computed(() => {
      if (!Array.isArray(subaccountsStore.subaccounts)) return 0;
      return subaccountsStore.subaccounts.filter(a => a && a.apiKey && a.apiKey.trim() !== '').length;
    });
    
    // 主账号信息
    const mainAccountInfo = computed(() => {
      if (userStore.hasMainAccount) {
        return `ID: ${userStore.mainAccountId}, 邮箱: ${userStore.mainAccountEmail || '未知'}`;
      }
      return '未设置主账号信息';
    });

    const openArbitrageDialog = (params) => {
      arbitrageAccount.value = params.account || null;
      arbitrageSelectedAccounts.value = params.selectedAccounts || [];
      arbitrageDialogVisible.value = true;
    };

    const handleArbitrageSuccess = (result) => {
      console.log('自动化套利完成', result);
      // 如果需要可以添加全局通知
    };
    
    // 调试功能
    const toggleDebugInfo = () => {
      showDebugInfo.value = !showDebugInfo.value;
      console.log('调试面板:', showDebugInfo.value ? '已打开' : '已关闭');
    };
    
    const forceRefreshSubaccounts = async () => {
      console.log('强制刷新子账号数据');
      try {
        await subaccountsStore.fetchSubaccounts(true);
        console.log('子账号数据已刷新:', subaccountsStore.subaccounts);
      } catch (error) {
        console.error('刷新子账号失败:', error);
      }
    };
    
    // 刷新主账号信息
    const refreshMainAccountInfo = async () => {
      console.log('刷新主账号信息');
      try {
        await userStore.fetchMainAccountInfo();
        console.log('主账号信息已刷新:', {
          id: userStore.mainAccountId,
          email: userStore.mainAccountEmail
        });
      } catch (error) {
        console.error('刷新主账号信息失败:', error);
      }
    };
    
    const addTestAccounts = () => {
      const testAccounts = [
        {
          email: "testsubaccount123_virtual@1b7cc6hsnoemail.com",
          apiKey: "KdjFLprXQLbLzUnSqyU5uwMGOHIMlF87tEp6fDzpcEGwSVW4V2cuXdpZukL0p2bM",
          apiSecret: "",
          name: "testsubaccount123_virtual@1b7cc6hsnoemail.com",
          status: "ACTIVE",
          accountType: "VIRTUAL",
          features: [],
          hasApiKey: true
        },
        {
          email: "userup9fhme2yh_virtual@yxjgp18dnoemail.com",
          apiKey: "AwKmyvyfmEkR5VqCPeMB7R1JCAST2RkME9OZh00MSQs7NITGoKgtcW9jrJ5JWrCk",
          apiSecret: "",
          name: "userup9fhme2yh_virtual@yxjgp18dnoemail.com",
          status: "ACTIVE",
          accountType: "VIRTUAL",
          features: [],
          hasApiKey: true
        }
      ];
      
      console.log('添加测试子账号:', testAccounts.length);
      subaccountsStore.subaccounts.value = testAccounts;
    };
    
    const clearLocalStorage = () => {
      console.log('清除本地存储');
      localStorage.clear();
      sessionStorage.clear();
      console.log('已清除所有本地存储');
    };

    // 主数据刷新相关设置
    const globalAutoRefresh = ref(true); // 默认开启自动刷新
    const refreshInterval = ref(500); // 默认刷新间隔500ms，提高响应速度

    // 使用Vue 3的生命周期钩子
    onMounted(() => {
      console.log('App组件已挂载');
      // 使用事件总线监听自动化套利事件
      eventBus.on('open-arbitrage', openArbitrageDialog);
      
      // 初始化主账号信息
      refreshMainAccountInfo().catch(err => {
        console.warn('初始化主账号信息失败:', err);
      });
      
      // 预加载子账号数据
      setTimeout(() => {
        console.log('预加载子账号数据');
        forceRefreshSubaccounts();
      }, 1000);
    });

    onBeforeUnmount(() => {
      // 清除事件监听
      eventBus.off('open-arbitrage', openArbitrageDialog);
    });

    return {
      arbitrageDialogVisible,
      arbitrageAccount,
      arbitrageSelectedAccounts,
      openArbitrageDialog,
      handleArbitrageSuccess,
      // 调试相关
      showDebugButton,
      showDebugInfo,
      toggleDebugInfo,
      isSubaccountsLoaded,
      totalSubaccounts,
      withApiSubaccounts,
      mainAccountInfo,
      forceRefreshSubaccounts,
      refreshMainAccountInfo,
      addTestAccounts,
      clearLocalStorage,
      // 添加全局配置变量
      globalAutoRefresh,
      refreshInterval
    };
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0;
  padding: 0;
}

body {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.content-container {
  padding: 20px;
}

/* 调试按钮和面板样式 */
.debug-floating-button {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: rgba(52, 152, 219, 0.8);
  color: white;
  padding: 10px 15px;
  border-radius: 4px;
  cursor: pointer;
  z-index: 1000;
  font-size: 14px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.debug-floating-button:hover {
  background-color: rgba(52, 152, 219, 1);
}

.debug-floating-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 3px 10px rgba(0,0,0,0.2);
  z-index: 1001;
  width: 400px;
  max-width: 90vw;
}

.debug-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding: 10px 15px;
}

.debug-panel-header h3 {
  margin: 0;
  font-size: 18px;
}

.debug-panel-header button {
  background: none;
  border: none;
  font-size: 14px;
  color: #666;
  cursor: pointer;
}

.debug-panel-content {
  padding: 15px;
}

.debug-panel-content div {
  margin-bottom: 8px;
}

.debug-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
}

.debug-actions button {
  background-color: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 5px 10px;
  font-size: 14px;
  cursor: pointer;
}

.debug-actions button:hover {
  background-color: #e9ecef;
}
</style>
