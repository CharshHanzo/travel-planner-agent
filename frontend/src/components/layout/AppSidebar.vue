<template>
  <aside class="app-sidebar">
    <nav class="sidebar-nav">
      <router-link to="/" class="nav-item" active-class="active">
        <el-icon><House /></el-icon>
        <span>首页</span>
      </router-link>
      <router-link to="/planner" class="nav-item" active-class="active">
        <el-icon><Calendar /></el-icon>
        <span>旅行规划</span>
      </router-link>
      <router-link to="/plan-chat" class="nav-item" active-class="active">
        <el-icon><ChatDotSquare /></el-icon>
        <span>对话规划</span>
      </router-link>
      <router-link to="/history" class="nav-item" active-class="active">
        <el-icon><Clock /></el-icon>
        <span>历史记录</span>
      </router-link>
      <router-link to="/settings" class="nav-item" active-class="active">
        <el-icon><Setting /></el-icon>
        <span>设置</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { House, Calendar, Clock, Setting, ChatDotSquare } from '@element-plus/icons-vue'
</script>

<style lang="scss">
.app-sidebar {
  width: 200px;
  background-color: white;
  border-right: 1px solid $border-color;
  height: 100%;

  .sidebar-nav {
    padding: $spacing-md 0;

    .nav-item {
      display: flex;
      align-items: center;
      padding: $spacing-sm $spacing-lg;
      color: #606266;
      text-decoration: none;
      transition: all 0.3s ease;

      el-icon {
        margin-right: $spacing-sm;
        font-size: 18px;
      }

      &:hover {
        background-color: rgba($primary-color, 0.1);
        color: $primary-color;
      }

      &.active {
        background-color: rgba($primary-color, 0.2);
        color: $primary-color;
        font-weight: 500;
      }
    }
  }
}
</style>