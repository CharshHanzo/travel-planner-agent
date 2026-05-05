<template>
  <div class="app-container">
    <AppHeader />
    <main class="app-main">
      <router-view />
    </main>
    <!-- <AppFooter /> -->
  </div>
</template>

<script setup lang="ts">
import AppHeader from './components/layout/AppHeader.vue'
// import AppFooter from './components/layout/AppFooter.vue'
</script>

<style lang="scss">
@import './assets/styles/variables.scss';

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.app-main {
  flex: 1;
  padding: 24px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .app-main {
    padding: 16px;
  }
}
</style>