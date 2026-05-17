import { API_ENDPOINTS } from './config'
import { getDeviceId } from '@/utils/device'

export interface UserPreferences {
  preferences: Record<string, { value: any; confidence: number }>
  total_trips: number
  sufficient: boolean
}

export function fetchUserPreferences(): Promise<UserPreferences> {
  return fetch(`${API_ENDPOINTS.userPreferences}?device_id=${getDeviceId()}`).then(r => r.json())
}
