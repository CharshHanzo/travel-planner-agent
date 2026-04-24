import { ref } from 'vue'
import { useAgentStore } from '../stores/agent'
import { useTravelStore } from '../stores/travel'
import { createSSEClient } from '../services/sse'
import { AgentStatusEvent } from '../types/agent'

export function useAgentStream() {
  const agentStore = useAgentStore()
  const travelStore = useTravelStore()
  const sseClient = ref<any>(null)

  function startStream(url: string, request: any) {
    // 重置状态
    agentStore.reset()
    travelStore.setLoading(true)
    travelStore.setError(null)

    sseClient.value = createSSEClient(url)
    sseClient.value.connect(request, {
      onAgentUpdate: (event: AgentStatusEvent) => {
        // 更新agent状态
        agentStore.addStatusEvent(event)
        agentStore.setCurrentAgent(event.agent_name)
        agentStore.addVisitedAgent(event.agent_name)
      },
      onComplete: (data: any) => {
        // 保存结果
        travelStore.setResponse(data)
        travelStore.setLoading(false)
        // 完成后重置当前agent
        agentStore.setCurrentAgent(null)
        // 断开SSE连接
        stopStream()
      },
      onError: (error: Error) => {
        // 设置错误状态
        travelStore.setError(error.message)
        travelStore.setLoading(false)
        // 断开SSE连接
        stopStream()
      }
    })
  }

  function stopStream() {
    if (sseClient.value) {
      sseClient.value.disconnect()
      sseClient.value = null
    }
  }

  function resetStream() {
    stopStream()
    agentStore.reset()
  }

  return {
    startStream,
    stopStream,
    resetStream
  }
}