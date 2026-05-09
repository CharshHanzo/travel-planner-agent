import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: {
        title: '首页 - 智能旅行规划助手'
      }
    },
    {
      path: '/planner',
      name: 'planner',
      component: () => import('../views/PlannerView.vue'),
      meta: {
        title: '旅行规划 - 智能旅行规划助手'
      }
    },
    {
      path: '/plan-chat',
      name: 'plan-chat',
      component: () => import('../views/ChatPlan.vue'),
      meta: {
        title: '对话式规划 - 智能旅行规划助手',
        layout: 'fullscreen'
      }
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryView.vue'),
      meta: {
        title: '历史记录 - 智能旅行规划助手'
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: {
        title: '设置 - 智能旅行规划助手'
      }
    }
  ]
})

// 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title as string || '智能旅行规划助手'
  next()
})

export default router