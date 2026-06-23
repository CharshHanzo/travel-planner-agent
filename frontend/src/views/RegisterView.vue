<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>注册</h2>
      <el-form @submit.prevent="handleRegister">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名（可选）" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6位）" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" block>
          注册
        </el-button>
      </el-form>
      <p class="switch-link">
        已有账号？<router-link to="/login">立即登录</router-link>
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
  username: '',
  password: '',
  confirmPassword: '',
})
const loading = ref(false)

async function handleRegister() {
  if (!form.email) {
    ElMessage.warning('请填写邮箱')
    return
  }
  if (!form.password) {
    ElMessage.warning('请填写密码')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少需要6位')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    const result = await authStore.register({
      email: form.email,
      password: form.password,
      username: form.username || undefined,
    })
    if (result.code === 200) {
      ElMessage.success('注册成功')
      router.push('/')
    } else {
      ElMessage.error(result.message || '注册失败')
    }
  } catch {
    ElMessage.error('注册失败，请重试')
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