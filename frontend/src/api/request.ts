import { useAuthStore } from '@/stores/auth'
import { getDeviceId } from '@/utils/device'

const BASE_URL = '/api/v1'

export async function request(url: string, options: RequestInit = {}): Promise<Response> {
  const authStore = useAuthStore()
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Device-Id': getDeviceId(),
    ...(options.headers as Record<string, string> || {}),
  }
  
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }
  
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  })
  
  if (response.status === 401 && authStore.refreshTokenValue) {
    try {
      const result = await refreshToken(authStore.refreshTokenValue)
      authStore.setToken(result.access_token)
      headers['Authorization'] = `Bearer ${result.access_token}`
      return fetch(`${BASE_URL}${url}`, { ...options, headers })
    } catch {
      authStore.logout()
    }
  }
  
  return response
}

async function refreshToken(token: string): Promise<{ access_token: string }> {
  const response = await fetch(`${BASE_URL}/auth/refresh?refresh_token_str=${token}`, {
    method: 'POST',
  })
  return response.json()
}