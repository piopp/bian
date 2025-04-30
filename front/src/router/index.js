import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../services/auth'

import ApiSettings from '../components/ApiSettings.vue'
import LoginPage from '../components/LoginPage.vue'
import SubAccountManage from '../components/SubAccountManage.vue'
import BatchSubAccount from '../views/BatchSubAccount.vue'
import TradingPairsView from '../views/TradingPairsView.vue'

const routes = [
  {
    path: '/',
    name: 'ApiSettings',
    component: ApiSettings,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'LoginPage',
    component: LoginPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/sub-accounts',
    name: 'SubAccountManage',
    component: SubAccountManage,
    meta: { requiresAuth: true }
  },
  {
    path: '/batch-subaccount',
    component: BatchSubAccount,
    meta: { requiresAuth: true }
  },
  {
    path: '/trading-pairs',
    name: 'TradingPairs',
    component: TradingPairsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/fee-statistics',
    name: 'FeeStatistics',
    component: () => import('../views/FeeStatistics.vue'),
    meta: { requiresAuth: true }
  },
  // 可以在这里添加更多路由
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

// 添加路由守卫
router.beforeEach((to, from, next) => {
  // 如果需要登录但用户未登录，重定向到登录页
  if (to.matched.some(record => record.meta.requiresAuth) && !isAuthenticated()) {
    next({ path: '/login' })
  } else {
    next()
  }
})

export default router 