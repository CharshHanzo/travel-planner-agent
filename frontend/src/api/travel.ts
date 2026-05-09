import { API_ENDPOINTS } from './config'

export interface TravelPlanRequest {
  city: string
  date: string
  people: number
  budget: number
  taste: string
  departure?: string
  activity_count?: number
  device_id: string
}

export function submitTravelPlan(data: TravelPlanRequest) {
  // 转换字段名以匹配后端API
  const requestData = {
    city: data.city,
    travel_date: data.date,
    people_count: data.people,
    budget: data.budget,
    taste: data.taste,
    departure: data.departure,
    activity_count: data.activity_count,
    device_id: data.device_id
  }
  
  return fetch(API_ENDPOINTS.travelPlan, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData),
  }).then(res => {
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`)
    }
    return res.json()
  })
}