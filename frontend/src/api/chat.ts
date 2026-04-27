import { API_ENDPOINTS } from './config'
import { sseRequest } from './sse'

export interface ChatRequest {
  message: string
  session_id?: string | null
  context?: Record<string, any>
}

export interface ChatCallbacks {
  onThinking?: () => void
  onAgentStart?: (agentName: string) => void
  onAgentEnd?: (agentName: string) => void
  onMessage?: (text: string) => void
  onPlan?: (markdown: string) => void
  onSession?: (sessionId: string) => void
  onError?: (message: string) => void
  onDone?: () => void
}

export function sendChatMessage(
  request: ChatRequest,
  callbacks: ChatCallbacks
): Promise<void> {
  return sseRequest(API_ENDPOINTS.planChat, request, callbacks)
}