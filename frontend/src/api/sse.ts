interface SSECallbacks {
  onThinking?: () => void
  onAgentStart?: (agentName: string) => void
  onAgentEnd?: (agentName: string) => void
  onMessage?: (text: string) => void
  onPlan?: (markdown: string) => void
  onSession?: (sessionId: string) => void
  onError?: (message: string) => void
  onDone?: () => void
}

export async function sseRequest(
  endpoint: string,
  body: any,
  callbacks: SSECallbacks
): Promise<void> {
  // 根据环境变量构建URL
  const baseUrl = import.meta.env.VITE_SSE_BASE_URL
  const url = baseUrl && baseUrl.trim() !== '' ? 
    `${baseUrl}${endpoint}` : 
    endpoint
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')

  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        // 记录当前事件类型
        currentEvent = line.slice(7).trim()
        continue
      }
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        // 处理数据...
        if (data) {
          try {
            const parsedData = JSON.parse(data)
            // 根据 SSE event 字段判断事件类型
            switch (currentEvent) {
              case 'thinking':
                callbacks.onThinking?.()
                break
              case 'agent_start':
                callbacks.onAgentStart?.(parsedData.agentName || '')
                break
              case 'agent_end':
                callbacks.onAgentEnd?.(parsedData.agentName || '')
                break
              case 'message':
                callbacks.onMessage?.(parsedData.text || '')
                break
              case 'plan':
                callbacks.onPlan?.(parsedData.markdown || '')
                break
              case 'session':
                callbacks.onSession?.(parsedData.session_id || '')
                break
              case 'error':
                callbacks.onError?.(parsedData.message || '')
                break
              case 'done':
                callbacks.onDone?.()
                break
            }
          } catch (error) {
            console.error('解析 SSE 数据失败:', error)
          }
        }
      }
    }
  }
}