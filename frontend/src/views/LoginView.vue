<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>登录</h2>
      <el-form @submit.prevent="handleLogin">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.remember">记住我（30天免登录）</el-checkbox>
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" block>
          登录
        </el-button>
      </el-form>
      <p class="switch-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const router = useRouter()

const form = reactive({
  email: '',
  password: '',
  remember: false,
})
const loading = ref(false)

async function handleLogin() {
  if (!form.email || !form.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  loading.value = true
  try {
    const result = await authStore.login({
      email: form.email,
      password: form.password,
      remember_me: form.remember,
    })
    if (result.code === 200) {
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.error(result.message || '登录失败')
    }
  } catch {
    ElMessage.error('登录失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  .auth-card {
    width: 400px;
    padding: 40px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    h2 {
      text-align: center;
      margin-bottom: 32px;
      font-size: 24px;
      color: #303133;
    }
    .switch-link { 
      text-align: center; 
      margin-top: 16px; 
      color: #606266;
      a {
        color: #409eff;
        text-decoration: none;
        &:hover { text-decoration: underline; }
      }
    }
  }
}
</style>