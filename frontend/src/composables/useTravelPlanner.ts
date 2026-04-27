import { computed } from 'vue'
import { useTravelStore } from '../stores/travel'
import { useAgentStore } from '../stores/agent'
import { TravelRequest } from '../types/travel'
import { submitTravelPlan } from '../api'

export function useTravelPlanner() {
  const travelStore = useTravelStore()
  const agentStore = useAgentStore()

  const loading = computed(() => travelStore.loading)
  const error = computed(() => travelStore.error)
  const result = computed(() => travelStore.currentResponse)
  const visitedAgents = computed(() => agentStore.visitedAgents)
  const currentAgent = computed(() => agentStore.currentAgent)

  async function planTravel(request: TravelRequest) {
    // 保存请求
    travelStore.setRequest(request)
    
    try {
      travelStore.setLoading(true)
      
      // 使用新的 submitTravelPlan 方法
      const data = await submitTravelPlan({
        city: request.city,
        date: request.travel_date,
        people: request.people_count,
        budget: request.budget,
        taste: request.taste,
        departure: request.departure,
        activity_count: request.activity_count
      })
      travelStore.setResponse(data)
    } catch (err) {
      travelStore.setError(err instanceof Error ? err.message : '请求失败')
    } finally {
      travelStore.setLoading(false)
    }
  }

  function cancelPlan() {
    travelStore.setLoading(false)
  }

  function reset() {
    travelStore.reset()
  }

  return {
    loading,
    error,
    result,
    visitedAgents,
    currentAgent,
    planTravel,
    cancelPlan,
    reset
  }
}