<template>
  <div class="settings-view">
    <h2>设置</h2>
    <div class="settings-card">
      <h3>API 配置</h3>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="API 基础地址">
          <span>{{ apiBaseUrl }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="SSE 基础地址">
          <span>{{ sseBaseUrl }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="success">已配置</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>
    <div class="settings-card">
      <h3>系统设置</h3>
      <el-form :model="settings" label-width="120px">
        <el-form-item label="语言">
          <el-select v-model="settings.language" placeholder="选择语言">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题">
          <el-select v-model="settings.theme" placeholder="选择主题">
            <el-option label="亮色" value="light" />
            <el-option label="暗色" value="dark" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知">
          <el-switch v-model="settings.notifications" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const apiBaseUrl = computed(() => import.meta.env.VITE_API_BASE_URL)
const sseBaseUrl = computed(() => import.meta.env.VITE_SSE_BASE_URL)

const settings = ref({
  language: 'zh-CN',
  theme: 'light',
  notifications: true
})

const saveSettings = () => {
  console.log('保存设置:', settings.value)
  // 实现保存设置的逻辑
  // 这里可以调用API保存设置到后端，或者保存到localStorage
  localStorage.setItem('settings', JSON.stringify(settings.value))
  // 显示保存成功的提示
  alert('设置已保存')
}
</script>

<style lang="scss">
.settings-view {
  h2 {
    margin-bottom: $spacing-lg;
    color: #303133;
  }

  .settings-card {
    background-color: white;
    padding: $spacing-lg;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    margin-bottom: $spacing-lg;

    h3 {
      margin-bottom: $spacing-md;
      color: #303133;
      font-size: $font-size-lg;
    }
  }
}

@media (max-width: 768px) {
  .settings-view {
    .settings-card {
      padding: $spacing-md;
    }
  }
}
</style>