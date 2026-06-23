import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi } from '@/api/auth'
import type { LoginParams, RegisterParams } from '@/api/auth'
import { getDeviceId } from '@/utils/device'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ id: number; email: string; username: string } | null>(null)
  const token = ref<string | null>(null)
  const refreshTokenValue = ref<string | null>(null)
  
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  
  function initFromStorage() {
    const stored = localStorage.getItem('auth')
    if (stored) {
      try {
        const data = JSON.parse(stored)
        user.value = data.user
        token.value = data.token
        refreshTokenValue.value = data.refreshToken
      } catch {}
    }
  }
  
  function saveToStorage() {
    localStorage.setItem('auth', JSON.stringify({
      user: user.value,
      token: token.value,
      refreshToken: refreshTokenValue.value,
    }))
  }
  
  function setAuth(authData: any) {
    user.value = authData.user
    token.value = authData.access_token
    refreshTokenValue.value = authData.refresh_token
    saveToStorage()
  }
  
  function setToken(newToken: string) {
    token.value = newToken
    saveToStorage()
  }
  
  async function logout() {
    const deviceId = getDeviceId()
    const tokenValue = token.value

    // 先解绑设备
    if (tokenValue) {
      try {
        await fetch(`/api/v1/auth/device?device_id=${deviceId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${tokenValue}` },
        })
      } catch {}
    }

    user.value = null
    token.value = null
    refreshTokenValue.value = null
    localStorage.removeItem('auth')
  }
  
  async function login(params: LoginParams) {
    const result = await loginApi(params)
    if (result.code === 200) {
      setAuth(result.data)
    }
    return result
  }
  
  async function register(params: RegisterParams) {
    const result = await registerApi(params)
    if (result.code === 200) {
      setAuth(result.data)
    }
    return result
  }
  
  return {
    user, token, refreshTokenValue, isLoggedIn,
    initFromStorage, login, register, logout, setToken,
  }
})