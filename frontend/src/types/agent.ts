export type AgentStatus = 'pending' | 'running' | 'completed' | 'error'

export type AgentName = 'TravelSupervisor' | 'WeatherAgent' | 'ActivityAgent' | 'FoodAgent'

export interface AgentStatusEvent {
  agent_name: AgentName
  status: AgentStatus
  message: string
  timestamp: string
}

export interface AgentResponse {
  id: string
  response: string
  status: AgentStatus
  createdAt: string
  updatedAt: string
}

export interface StreamEvent {
  type: 'message' | 'error' | 'end'
  data: string
}

export interface AgentConfig {
  model: string
  temperature: number
  maxTokens: number
  topP: number
}
