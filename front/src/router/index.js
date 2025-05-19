import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../services/auth'

import ApiSettings from '../components/ApiSettings.vue'
import LoginPage from '../components/LoginPage.vue'
import SubAccountManage from '../components/SubAccountManage.vue'
import TradingPairsView from '../views/TradingPairsView.vue'
import LeverageMarketView from '../views/LeverageMarketView.vue'
import FeeManagementView from '../views/FeeManagementView.vue'
import TradingCenter from '../views/TradingCenter.vue'

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
    path: '/trading-pairs',
    name: 'TradingPairs',
    component: TradingPairsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/leverage-market',
    name: 'LeverageMarket',
    component: LeverageMarketView,
    meta: { requiresAuth: true, title: '杠杆市场交易' }
  },
  {
    path: '/fee-management',
    name: 'FeeManagement',
    component: FeeManagementView,
    meta: { requiresAuth: true }
  },
  {
    path: '/trading-center',
    name: 'TradingCenter',
    component: TradingCenter,
    meta: { requiresAuth: true, title: '交易中心' }
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