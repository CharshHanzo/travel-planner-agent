<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo">
        <router-link to="/" class="logo-link">
          <h1>Travel Agent</h1>
        </router-link>
      </div>
      <nav class="main-nav" v-if="!isMobile">
        <router-link to="/" class="nav-item" active-class="active">
          <el-icon><House /></el-icon>
          <span>首页</span>
        </router-link>
        <router-link to="/planner" class="nav-item" active-class="active">
          <el-icon><Calendar /></el-icon>
          <span>快速规划</span>
        </router-link>
        <router-link to="/plan-chat" class="nav-item" active-class="active">
          <el-icon><ChatDotSquare /></el-icon>
          <span>对话规划</span>
        </router-link>
        <router-link to="/history" class="nav-item" active-class="active">
          <el-icon><Clock /></el-icon>
          <span>历史</span>
        </router-link>
        <router-link to="/settings" class="nav-item" active-class="active">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </router-link>
      </nav>
    </div>
    <div class="header-right">
      <el-dropdown>
        <span class="user-info">
          <el-avatar size="small">U</el-avatar>
          <span class="username" v-if="!isMobile">User</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>个人中心</el-dropdown-item>
            <el-dropdown-item>设置</el-dropdown-item>
            <el-dropdown-item divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button 
        type="text" 
        class="mobile-menu-btn" 
        @click="toggleMobileMenu"
        v-if="isMobile"
      >
        <el-icon><Menu /></el-icon>
      </el-button>
    </div>
    <!-- 移动端菜单 -->
    <div class="mobile-menu" v-if="isMobile && showMobileMenu">
      <router-link to="/" class="mobile-nav-item" active-class="active" @click="toggleMobileMenu">
        <el-icon><House /></el-icon>
        <span>首页</span>
      </router-link>
      <router-link to="/planner" class="mobile-nav-item" active-class="active" @click="toggleMobileMenu">
        <el-icon><Calendar /></el-icon>
        <span>快速规划</span>
      </router-link>
      <router-link to="/plan-chat" class="mobile-nav-item" active-class="active" @click="toggleMobileMenu">
        <el-icon><ChatDotSquare /></el-icon>
        <span>对话规划</span>
      </router-link>
      <router-link to="/history" class="mobile-nav-item" active-class="active" @click="toggleMobileMenu">
        <el-icon><Clock /></el-icon>
        <span>历史</span>
      </router-link>
      <router-link to="/settings" class="mobile-nav-item" active-class="active" @click="toggleMobileMenu">
        <el-icon><Setting /></el-icon>
        <span>设置</span>
      </router-link>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ArrowDown, House, Calendar, Clock, Setting, Menu, ChatDotSquare } from '@element-plus/icons-vue'

const isMobile = ref(false)
const showMobileMenu = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 $spacing-lg;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;

  .header-left {
    display: flex;
    align-items: center;

    .logo {
      .logo-link {
        text-decoration: none;

        h1 {
          font-size: $font-size-lg;
          font-weight: 600;
          color: $primary-color;
          margin: 0;
        }
      }
    }

    .main-nav {
      display: flex;
      margin-left: $spacing-xl;

      .nav-item {
        display: flex;
        align-items: center;
        padding: $spacing-sm $spacing-md;
        color: #606266;
        text-decoration: none;
        transition: all 0.3s ease;

        el-icon {
          margin-right: $spacing-xs;
        }

        &:hover {
          color: $primary-color;
        }

        &.active {
          color: $primary-color;
          font-weight: 500;
        }
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;

    .user-info {
      display: flex;
      align-items: center;
      cursor: pointer;
      padding: $spacing-xs $spacing-sm;
      border-radius: $border-radius;
      transition: all 0.3s ease;

      &:hover {
        background-color: rgba($primary-color, 0.1);
      }

      .username {
        margin: 0 $spacing-sm;
        font-size: $font-size-base;
        color: #303133;
      }
    }

    .mobile-menu-btn {
      margin-left: $spacing-md;
    }
  }

  .mobile-menu {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background-color: white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: $spacing-sm 0;
    z-index: 1000;

    .mobile-nav-item {
      display: flex;
      align-items: center;
      padding: $spacing-sm $spacing-lg;
      color: #606266;
      text-decoration: none;
      transition: all 0.3s ease;

      el-icon {
        margin-right: $spacing-sm;
      }

      &:hover {
        background-color: rgba($primary-color, 0.1);
        color: $primary-color;
      }

      &.active {
        background-color: rgba($primary-color, 0.1);
        color: $primary-color;
        font-weight: 500;
      }
    }
  }
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 $spacing-md;
  }
}
</style>