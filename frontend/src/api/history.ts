import { API_ENDPOINTS } from './config'
import { getDeviceId } from '@/utils/device'

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
  messages: Message[]
}

export function fetchTrips(params: {
  city?: string
  rating_min?: number
  offset?: number
  limit?: number
}): Promise<{ trips: TripItem[]; total: number }> {
  const searchParams = new URLSearchParams()
  searchParams.set('device_id', getDeviceId())
  if (params.city) searchParams.set('city', params.city)
  if (params.rating_min) searchParams.set('rating_min', String(params.rating_min))
  if (params.offset) searchParams.set('offset', String(params.offset))
  if (params.limit) searchParams.set('limit', String(params.limit))
  
  return fetch(`${API_ENDPOINTS.historyTrips}?${searchParams}`).then(r => r.json())
}

export function fetchTripDetail(tripId: string): Promise<TripDetail> {
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}`).then(r => r.json())
}

export function deleteTrip(tripId: string): Promise<void> {
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}`, { method: 'DELETE' }).then(r => r.json())
}

export function rateTrip(tripId: string, rating: number): Promise<void> {
  return fetch(`${API_ENDPOINTS.historyTrips}/${tripId}/rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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