<template>
  <div class="chat-plan-view">
    <div class="chat-container">
      <!-- 消息列表区域 -->
      <div class="chat-messages" ref="messagesContainer">
        <!-- 欢迎页 -->
        <div v-if="messages.length === 0" class="welcome-panel">
          <div class="welcome-content">
            <div class="welcome-icon">✈️</div>
            <h2 class="welcome-title">Hi，我是你的旅行规划助手</h2>
            <p class="welcome-subtitle">告诉我你想去哪里，我会帮你安排一切</p>
            <div class="welcome-suggestions">
              <div 
                v-for="(suggestion, index) in suggestions" 
                :key="index" 
                class="suggestion-card"
                @click="handleSuggestion(suggestion)"
              >
                {{ suggestion }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- 消息列表 -->
        <div v-else class="messages-wrapper">
          <div v-for="(message, index) in messages" :key="index" :class="['message', message.type]">
            <div class="message-content">
              <div v-if="message.type === 'ai'" class="ai-message">
                <div v-if="message.content" class="message-text" v-html="renderMarkdown(message.content)"></div>
                <div v-else-if="message.loading" class="message-loading">
                  <el-icon><Loading /></el-icon>
                  <span>{{ message.loading }}</span>
                </div>
              </div>
              <div v-else class="user-message">
                <div class="message-text">{{ message.content }}</div>
              </div>
            </div>
            <!-- 计划操作按钮 -->
            <div v-if="message.type === 'ai' && message.content && isPlanMessage(message.content)" class="plan-actions">
              <el-button size="small" plain @click="copyPlan(message.content)">📋 复制</el-button>
              <el-button size="small" plain @click="exportPlan(message.content)">📥 导出</el-button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入框区域 -->
      <div class="chat-input-container">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="1"
            placeholder="输入你的旅行需求..."
            @keyup.enter.exact="sendMessage"
            @keyup.enter.shift="$event.target.value += '\n'"
            :disabled="loading"
            class="chat-input"
          />
          <el-button 
            type="primary" 
            @click="sendMessage" 
            :loading="loading"
            :disabled="!inputMessage.trim()"
            class="send-button"
          >
            <el-icon><ArrowUp /></el-icon>
          </el-button>
        </div>
        <p class="input-hint">提示：可以随时修改需求，我会实时调整方案</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { Loading, ArrowUp } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'

interface Message {
  type: 'user' | 'ai'
  content?: string
  loading?: string
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const sessionId = ref<string>('')
const messagesContainer = ref<HTMLElement | null>(null)

// 建议问题
const suggestions = [
  '🏙️ 推荐几个北京的景点',
  '🌧️ 明天杭州天气如何',
  '🍜 帮我推荐成都的火锅店',
  '📋 帮我生成本次旅行计划'
]

// 生成会话 ID
const generateSessionId = () => {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// 渲染 Markdown
const renderMarkdown = (content: string) => {
  // 这里可以使用简单的 Markdown 渲染，或者使用 MarkdownRenderer 组件
  return content
}

// 滚动到最新消息
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 发送消息
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return
  
  // 添加用户消息
  messages.value.push({ type: 'user', content: message })
  inputMessage.value = ''
  await scrollToBottom()
  
  // 添加 AI 加载消息
  messages.value.push({ type: 'ai', loading: '正在处理...' })
  await scrollToBottom()
  
  loading.value = true
  
  try {
    // 调用 SSE 接口
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/travel/plan-chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        session_id: sessionId.value
      })
    })
    
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无响应体')
    }
    
    const decoder = new TextDecoder()
    let buffer = ''
    let currentMessageIndex = messages.value.length - 1
    let aiResponse = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('event:')) {
          const event = line.substring(6).trim()
          
          // 处理下一行的 data
          const dataLineIndex = lines.indexOf(line) + 1
          if (dataLineIndex < lines.length && lines[dataLineIndex].startsWith('data:')) {
            const data = lines[dataLineIndex].substring(5).trim()
            if (data) {
              try {
                const parsedData = JSON.parse(data)
                
                if (event === 'message' && parsedData.text) {
                  aiResponse = parsedData.text
                  messages.value[currentMessageIndex] = { type: 'ai', content: aiResponse }
                  await scrollToBottom()
                } else if (event === 'session' && parsedData.session_id) {
                  sessionId.value = parsedData.session_id
                } else if (event === 'done') {
                  // 完成
                }
              } catch (error) {
                console.error('解析 SSE 消息失败:', error)
              }
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value[messages.value.length - 1] = { type: 'ai', content: '抱歉，处理请求时出错了，请重试。' }
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

// 处理建议问题
const handleSuggestion = (suggestion: string) => {
  inputMessage.value = suggestion
  sendMessage()
}

// 复制计划
const copyPlan = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('计划已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  }
}

// 导出计划
const exportPlan = (content: string) => {
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `travel-plan-${new Date().toISOString().split('T')[0]}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success('计划已导出')
}

// 判断是否为计划消息
const isPlanMessage = (content: string) => {
  // 简单判断：包含标题、列表等 Markdown 元素的消息视为计划
  return content.includes('#') || content.includes('- ') || content.includes('1. ')
}

// 初始化
onMounted(() => {
  // 生成会话 ID
  sessionId.value = generateSessionId()
  
  // 监听输入框变化，自动调整高度
  const textarea = document.querySelector('.chat-input textarea')
  if (textarea) {
    textarea.addEventListener('input', function() {
      this.style.height = 'auto'
      this.style.height = Math.min(this.scrollHeight, 120) + 'px'
    })
  }
  
  // 监听视觉视口变化，适配移动端
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
      scrollToBottom()
    })
  }
})
</script>

<style lang="scss">
/* 确保根元素高度为 100% */
html, body {
  height: 100%;
  margin: 0;
  padding: 0;
}

#app {
  height: 100%;
}

.chat-plan-view {
  display: flex;
  height: 100vh;
  height: 100dvh; /* 兼容移动端 */
  overflow: hidden;
  margin: 0;
  padding: 0;
  background-color: #f7f7f8;
  
  /* 深色模式 */
  &.dark {
    background-color: #1e1e2e;
  }
  
  .chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
    .chat-messages {
      flex: 1;
      padding: 24px 16px;
      overflow-y: auto;
      min-height: 0;
      display: flex;
      flex-direction: column;
      
      // 欢迎页
      .welcome-panel {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        
        .welcome-content {
          text-align: center;
          max-width: 500px;
          
          .welcome-icon {
            font-size: 48px;
            margin-bottom: 24px;
          }
          
          .welcome-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #303133;
            
            .dark & {
              color: #e5e7eb;
            }
          }
          
          .welcome-subtitle {
            font-size: 16px;
            color: #606266;
            margin-bottom: 32px;
            
            .dark & {
              color: #9ca3af;
            }
          }
          
          .welcome-suggestions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-top: 24px;
            
            .suggestion-card {
              padding: 16px;
              background-color: white;
              border: 1px solid #e5e5e5;
              border-radius: 12px;
              cursor: pointer;
              transition: all 0.2s ease;
              text-align: left;
              font-size: 14px;
              color: #303133;
              
              .dark & {
                background-color: #2d2d3f;
                border-color: #3d3d4f;
                color: #e5e7eb;
              }
              
              &:hover {
                background-color: #f0f0f0;
                transform: translateY(-2px);
                
                .dark & {
                  background-color: #3d3d4f;
                }
              }
            }
          }
        }
      }
      
      // 消息列表
      .messages-wrapper {
        max-width: 720px;
        width: 100%;
        margin: 0 auto;
        
        .message {
          margin-bottom: 24px;
          
          &.user {
            display: flex;
            justify-content: flex-end;
            
            .message-content {
              max-width: 70%;
              background-color: #f0f0f0;
              color: #303133;
              border-radius: 18px 18px 4px 18px;
              padding: 12px 16px;
              
              .dark & {
                background-color: #2d2d3f;
                color: #e5e7eb;
              }
            }
          }
          
          &.ai {
            display: flex;
            justify-content: flex-start;
            
            .message-content {
              max-width: 100%;
              color: #303133;
              padding: 12px 16px;
              
              .dark & {
                color: #e5e7eb;
              }
              
              .message-loading {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #606266;
                
                .dark & {
                  color: #9ca3af;
                }
                
                .el-icon {
                  animation: rotate 1s linear infinite;
                }
              }
            }
          }
          
          .message-text {
            font-size: 15px;
            line-height: 1.6;
            
            // Markdown 样式
            h1, h2, h3, h4, h5, h6 {
              margin: 12px 0 8px 0;
              font-weight: 600;
            }
            
            h1 {
              font-size: 20px;
            }
            
            h2 {
              font-size: 18px;
            }
            
            h3 {
              font-size: 16px;
            }
            
            p {
              margin: 8px 0;
            }
            
            ul, ol {
              margin: 8px 0;
              padding-left: 24px;
            }
            
            li {
              margin: 4px 0;
            }
            
            code {
              background-color: #f5f7fa;
              padding: 2px 4px;
              border-radius: 3px;
              font-family: monospace;
              font-size: 14px;
              
              .dark & {
                background-color: #2d2d3f;
              }
            }
            
            pre {
              background-color: #f5f7fa;
              padding: 12px;
              border-radius: 8px;
              overflow-x: auto;
              margin: 12px 0;
              
              .dark & {
                background-color: #2d2d3f;
              }
              
              code {
                background-color: transparent;
                padding: 0;
              }
            }
            
            table {
              width: 100%;
              border-collapse: collapse;
              margin: 12px 0;
              
              th, td {
                padding: 8px 12px;
                border: 1px solid #e5e5e5;
                text-align: left;
                
                .dark & {
                  border-color: #3d3d4f;
                }
              }
              
              th {
                background-color: #f5f7fa;
                font-weight: 600;
                
                .dark & {
                  background-color: #2d2d3f;
                }
              }
            }
          }
          
          // 计划操作按钮
          .plan-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            justify-content: flex-start;
            
            .el-button {
              font-size: 12px;
              padding: 4px 12px;
              border-radius: 16px;
            }
          }
        }
      }
    }
    
    .chat-input-container {
      flex-shrink: 0;
      padding: 16px;
      background-color: #f7f7f8;
      border-top: 1px solid #e5e5e5;
      
      .dark & {
        background-color: #1e1e2e;
        border-top-color: #3d3d4f;
      }
      
      .input-wrapper {
        max-width: 720px;
        width: 100%;
        margin: 0 auto;
        display: flex;
        gap: 12px;
        align-items: flex-end;
        
        .chat-input {
          flex: 1;
          
          textarea {
            resize: none;
            min-height: 44px;
            max-height: 120px;
            font-size: 15px;
            border-radius: 12px;
            border: 1px solid #d1d5db;
            padding: 12px 16px;
            
            .dark & {
              background-color: #2d2d3f;
              border-color: #3d3d4f;
              color: #e5e7eb;
            }
            
            &:focus {
              border-color: #409eff;
            }
          }
        }
        
        .send-button {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0;
        }
      }
      
      .input-hint {
        max-width: 720px;
        width: 100%;
        margin: 8px auto 0;
        font-size: 12px;
        color: #909399;
        text-align: center;
        
        .dark & {
          color: #6b7280;
        }
      }
    }
  }
}

// 移动端适配
@media (max-width: 768px) {
  .chat-plan-view {
    .chat-container {
      .chat-messages {
        padding: 12px;
        
        .welcome-panel {
          .welcome-content {
            .welcome-suggestions {
              grid-template-columns: 1fr;
            }
          }
        }
        
        .messages-wrapper {
          .message {
            &.user {
              .message-content {
                max-width: 85%;
              }
            }
          }
        }
      }
      
      .chat-input-container {
        padding: 10px;
        
        .input-wrapper {
          gap: 8px;
          
          .send-button {
            width: 36px;
            height: 36px;
          }
        }
      }
    }
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>