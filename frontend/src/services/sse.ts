import { AgentStatusEvent } from '../types/agent'

export interface SSECallbacks {
  onAgentUpdate: (event: AgentStatusEvent) => void
  onComplete: (data: any) => void
  onError: (error: Error) => void
}

export class SSEClient {
  private url: string
  private callbacks: SSECallbacks | null = null
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectDelay: number = 1000
  private controller: AbortController | null = null
  private requestData: any = null

  constructor(url?: string) {
    // 使用环境变量作为默认值，允许传入自定义URL
    // 如果环境变量为空，则使用传入的URL或默认路径
    const baseUrl = import.meta.env.VITE_SSE_BASE_URL
    if (baseUrl && baseUrl.trim() !== '') {
      this.url = url || `${baseUrl}/api/v1/travel/plan-chat`
    } else {
      // 开发环境：使用传入的URL或默认代理路径
      this.url = url || '/api/v1/travel/plan-chat'
    }
  }

  connect(request: any, callbacks: SSECallbacks) {
    this.callbacks = callbacks
    this.requestData = request
    
    this.controller = new AbortController()
    
    this.fetchSSE()
  }

  private async fetchSSE() {
    if (!this.requestData || !this.callbacks) return

    try {
      const response = await fetch(this.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(this.requestData),
        signal: this.controller?.signal
      })

      if (!response.ok) {
        throw new Error(`SSE request failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      this.reconnectAttempts = 0
      console.log('SSE Connection established')

      await this.readStream(reader)
    } catch (error) {
      console.error('SSE Error:', error)
      if (this.callbacks?.onError) {
        this.callbacks.onError(error instanceof Error ? error : new Error('SSE connection error'))
      }
      this.attemptReconnect()
    }
  }

  private async readStream(reader: ReadableStreamDefaultReader<Uint8Array>) {
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      this.processBuffer(buffer)
    }

    // 处理剩余的buffer
    if (buffer) {
      this.processBuffer(buffer)
    }
  }

  private processBuffer(buffer: string) {
    const lines = buffer.split('\n')
    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = line.substring(5).trim()
        if (data) {
          this.handleMessage(data)
        }
      }
    }
  }

  private handleMessage(data: string) {
    try {
      const parsedData = JSON.parse(data)
      
      if (parsedData.type === 'agent_update' && this.callbacks?.onAgentUpdate) {
        this.callbacks.onAgentUpdate(parsedData.data as AgentStatusEvent)
      } else if (parsedData.type === 'complete' && this.callbacks?.onComplete) {
        this.callbacks.onComplete(parsedData.data)
      }
    } catch (error) {
      console.error('Error parsing SSE message:', error)
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
        this.fetchSSE()
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1))
    } else {
      console.error('Max reconnection attempts reached')
    }
  }

  disconnect() {
    if (this.controller) {
      this.controller.abort()
      this.controller = null
    }
    this.callbacks = null
    this.requestData = null
    this.reconnectAttempts = 0
  }

  isConnected() {
    return this.controller !== null
  }
}

export const createSSEClient = (url: string) => {
  return new SSEClient(url)
}