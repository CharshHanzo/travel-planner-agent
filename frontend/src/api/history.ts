import { API_ENDPOINTS } from './config'
import { getDeviceId } from '@/utils/device'
import { useAuthStore } from '@/stores/auth'

export interface TripItem {
  id: string
  city: string
  travel_date: string
  people_count: number
  budget: number
  taste: string | null
  rating: number | null
  mode: string
  created_at: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  agent_calls?: string[]
  timestamp: number
}

export interface TripDetail extends TripItem {
  plan_markdown: string
  session_id: string
  messages: Message[]
}

// 防重入锁
let isLoadingTrips = false
let lastPromise: Promise<{ trips: TripItem[]; total: number }> | null = null

export function fetchTrips(params: {
  city?: string
  rating_min?: number
  offset?: number
  limit?: number
}): Promise<{ trips: TripItem[]; total: number }> {
  // 如果正在加载，返回同一个 Promise
  if (isLoadingTrips && lastPromise) {
    return lastPromise
  }
  
  isLoadingTrips = true
  
  const authStore = useAuthStore()
  const searchParams = new URLSearchParams()
  
  if (!authStore.isLoggedIn) {
    searchParams.set('device_id', getDeviceId())
  }
  
  if (params.city) searchParams.set('city', params.city)
  if (params.rating_min) searchParams.set('rating_min', String(params.rating_min))
  if (params.offset) searchParams.set('offset', String(params.offset))
  if (params.limit) searchParams.set('limit', String(params.limit))
  
  const headers: Record<string, string> = {}
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }
  
  lastPromise = fetch(`${API_ENDPOINTS.historyTrips}?${searchParams}`, { headers })
    .then(r => r.json())
    .finally(() => {
      isLoadingTrips = false
      lastPromise = null
    })
  
  return lastPromise
}

function getAuthHeaders(): Record<string, string> {
  const authStore = useAuthStore()
  const headers: Record<string, string> = {}
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }
  return headers
}

export function fetchTripDetail(tripId: string): Promise<TripDetail> {
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}`, { headers: getAuthHeaders() }).then(r => r.json())
}

export function deleteTrip(tripId: string): Promise<void> {
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}`, { 
    method: 'DELETE',
    headers: getAuthHeaders()
  }).then(r => r.json())
}

export function rateTrip(tripId: string, rating: number): Promise<void> {
  const headers = {
    ...getAuthHeaders(),
    'Content-Type': 'application/json'
  }
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}/rate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ rating }),
  }).then(r => r.json())
}

export interface CreateTripRequest {
  device_id: string
  city: string
  travel_date: string
  people_count: number
  budget: number
  taste?: string | null
  departure?: string | null
  activity_count?: number
  plan_markdown: string
  weather_data?: string | null
  activities_data?: string | null
  food_data?: string | null
  conversation_context?: string | null
  mode?: string
}

export interface CreateTripResponse {
  id: string
  created_at: string
}

export function createTrip(request: CreateTripRequest): Promise<CreateTripResponse> {
  return fetch(API_ENDPOINTS.historyTrips, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }).then(r => r.json())
}