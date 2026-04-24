import { computed } from 'vue'
import { useTravelStore } from '../stores/travel'
import { useAgentStore } from '../stores/agent'
import { TravelRequest } from '../types/travel'

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
      
      // 直接调用API接口获取结果
      const response = await fetch('/api/v1/travel/plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })
      
      if (!response.ok) {
        throw new Error('网络请求失败')
      }
      
      const data = await response.json()
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