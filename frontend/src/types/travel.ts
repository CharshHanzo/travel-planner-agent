export type TasteType = '辣' | '清淡' | '不挑'

export interface TravelRequest {
  city: string
  travel_date: string
  people_count: number
  budget: number
  taste: TasteType
  departure?: string
  activity_count: number
}

export interface CoordinatesPoint {
  name: string
  lng: number
  lat: number
  type: 'activity' | 'restaurant'
  description?: string
  duration?: string
  cuisine?: string
  price_per_person?: number
  rating?: number
}

export interface RouteSegment {
  from: string
  to: string
  path: number[][]
  distance: string
  duration: string
}

export interface CoordinatesData {
  points: CoordinatesPoint[]
  route?: {
    segments: RouteSegment[]
  } | null
}

export interface TravelResponse {
  session_id: string
  status: string
  result_markdown: string
  created_at: string
  coordinates?: CoordinatesData
}

export interface TravelPlan {
  id: number
  destination: string
  startDate: string
  endDate: string
  budget: number
  preferences: string[]
  createdAt: string
  updatedAt: string
}

export interface PlanRequest {
  destination: string
  startDate: string
  endDate: string
  budget: number
  preferences: string[]
}

export interface PlanResponse {
  id: number
  plan: string
  createdAt: string
}

export interface BudgetAllocation {
  transportation: number
  accommodation: number
  food: number
  activities: number
  other: number
}
