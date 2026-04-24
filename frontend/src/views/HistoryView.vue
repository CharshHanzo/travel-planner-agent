<template>
  <div class="history-view">
    <h2>历史记录</h2>
    <div class="placeholder-container">
      <el-empty 
        description="功能开发中，敬请期待"
        :image-size="200"
      >
        <el-button type="primary" @click="$router.push('/planner')">去规划旅行</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style lang="scss">
.history-view {
  h2 {
    margin-bottom: $spacing-lg;
    color: #303133;
  }

  .placeholder-container {
    background-color: white;
    padding: $spacing-xl;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
  }
}
</style>