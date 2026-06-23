import { API_ENDPOINTS } from './config'
import { getDeviceId } from '@/utils/device'

export interface RegisterParams {
  email: string
  password: string
  username?: string
}

export interface LoginParams {
  email: string
  password: string
  remember_me?: boolean
}

export interface AuthResult {
  code: number
  message: string
  data: {
    user: {
      id: number
      email: string
      username: string
    }
    access_token: string
    refresh_token: string
    expires_in: number
  }
}

export function register(params: RegisterParams): Promise<AuthResult> {
  return fetch(API_ENDPOINTS.authRegister, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...params,
      device_id: getDeviceId(),
    }),
  }).then(r => r.json())
}

export function login(params: LoginParams): Promise<AuthResult> {
  return fetch(API_ENDPOINTS.authLogin, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...params,
      device_id: getDeviceId(),
    }),
  }).then(r => r.json())
}

export function refreshToken(token: string): Promise<{ access_token: string }> {
  return fetch(`${API_ENDPOINTS.authRefresh}?refresh_token_str=${token}`, {
    method: 'POST',
  }).then(r => r.json())
}