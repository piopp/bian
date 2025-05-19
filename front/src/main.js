// 屏蔽 ResizeObserver loop completed with undelivered notifications 警告
const realConsoleError = window.console.error;
window.console.error = function (...args) {
  if (
    typeof args[0] === 'string' &&
    args[0].includes('ResizeObserver loop completed with undelivered notifications')
  ) {
    return;
  }
  realConsoleError.apply(window.console, args);
};

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'
import { getAuthHeader } from './services/auth'
import { handleResizeObserverErrors, optimizeLayoutDirective } from './utils/performance'
import { initTimeSync, getCorrectedTime } from './services/timeSync'
import './assets/main.css'

// u9884u5148u52a0u8f7dStoresu5e76u521du59cbu5316
import { useUserStore } from './stores/userStore'
import { useSubaccountsStore } from './stores/subaccounts'
import { useMarginTradesStore } from './stores/marginTradesStore'

// u521du59cbu5316u5e76u521bu5efaPiniau5b9eu4f8b
const pinia = createPinia()

// u9884u521du59cbu5316Storesu4ee5u89e3u51b3ESLintu672au4f7fu7528u7684u8b66u544a
const initStores = () => {
  // u6ce8u610fuff1au6211u4eec u521du59cbu5316u5b83u4eec u4f46u5e76u4e0du5b9eu9645u4f7fu7528u5b83u4eecu7684u5f15u7528
  const userStore = useUserStore(pinia);
  const subaccountsStore = useSubaccountsStore(pinia);
  const marginTradesStore = useMarginTradesStore(pinia);
  
  console.log('Storesu9884u521du59cbu5316u5b8cu6210:', { 
    'userStore': !!userStore,
    'subaccountsStore': !!subaccountsStore, 
    'marginTradesStore': !!marginTradesStore 
  });
};

// 初始化时间同步服务
initTimeSync().then(() => {
  console.log('时间同步服务已初始化');
}).catch(error => {
  console.error('时间同步服务初始化失败:', error);
});

// 配置axios拦截器，为每个请求添加认证token和正确的时间戳
axios.interceptors.request.use(
  config => {
    // 获取认证头信息
    const authHeader = getAuthHeader()
    // 如果有认证头，添加到请求中
    if (authHeader.Authorization) {
      config.headers.Authorization = authHeader.Authorization
    }
    
    // 检查是否有params参数，且请求url包含币安API相关端点
    if (config.params && 
        (config.url.includes('/api/subaccounts') || 
         config.url.includes('/api/trading') || 
         config.url.includes('/api/market') ||
         config.url.includes('/api/orders'))) {
      // 如果请求需要timestamp参数，使用校正后的时间戳
      if ('timestamp' in config.params || config.url.includes('signed=true')) {
        config.params.timestamp = getCorrectedTime();
        console.log(`请求使用校正时间戳: ${config.params.timestamp}`);
      }
      
      // 尝试从Pinia store获取主账号ID
      try {
        const userStore = pinia._s.get('user')
        if (userStore && userStore.mainAccountId) {
          // 添加用户ID到请求参数
          if (!config.params.user_id) {
            config.params.user_id = userStore.mainAccountId
            console.log(`请求自动添加主账号ID: ${userStore.mainAccountId}`);
          }
        }
      } catch (error) {
        console.warn('无法从store获取主账号ID:', error);
      }
    }
    
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 全局处理ResizeObserver错误
handleResizeObserverErrors();

// u8c03u7528u521du59cbu5316Stores
initStores();

const app = createApp(App)

// 注册全局优化布局指令
app.directive('optimize-layout', optimizeLayoutDirective);

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
