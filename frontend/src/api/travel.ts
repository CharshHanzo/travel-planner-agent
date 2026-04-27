import { API_ENDPOINTS } from './config'

export interface TravelPlanRequest {
  city: string
  date: string
  people: number
  budget: number
  taste: string
  departure?: string
  activity_count?: number
}

export function submitTravelPlan(data: TravelPlanRequest) {
  return fetch(API_ENDPOINTS.travelPlan, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => res.json())
}