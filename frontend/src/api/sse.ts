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
  url: string,
  body: any,
  callbacks: SSECallbacks
): Promise<void> {
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

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7).trim()
        // 等待下一行的 data
        continue
      }
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        // 处理数据...
        if (data) {
          try {
            const parsedData = JSON.parse(data)
            switch (parsedData.type) {
              case 'thinking':
                callbacks.onThinking?.()
                break
              case 'agent_start':
                callbacks.onAgentStart?.(parsedData.data?.agentName || '')
                break
              case 'agent_end':
                callbacks.onAgentEnd?.(parsedData.data?.agentName || '')
                break
              case 'message':
                callbacks.onMessage?.(parsedData.data?.text || '')
                break
              case 'plan':
                callbacks.onPlan?.(parsedData.data?.markdown || '')
                break
              case 'session':
                callbacks.onSession?.(parsedData.data?.sessionId || '')
                break
              case 'error':
                callbacks.onError?.(parsedData.data?.message || '')
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