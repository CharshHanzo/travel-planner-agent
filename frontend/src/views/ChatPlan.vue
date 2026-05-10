<template>
  <div class="chat-page">
    <!-- 侧边栏 -->
    <ChatSidebar
      ref="chatSidebarRef"
      :current-session-id="sessionId"
      @new-chat="handleNewChat"
      @select-chat="handleSelectChat"
      @delete-chat="handleDeleteChat"
    />
    
    <!-- 主内容区 -->
    <div class="chat-main">
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
                  <div v-if="message.content" class="message-text">
                    <MarkdownRenderer :content="message.content" />
                  </div>
                  <div v-else-if="message.loading" class="message-loading">
                    <el-icon><Loading /></el-icon>
                    <span>{{ message.loading }}</span>
                  </div>
                  <div v-if="message.coordinates && message.coordinates.points && message.coordinates.points.length > 0" class="map-section">
                    <AmapView 
                      :points="message.coordinates.points" 
                      :route="message.coordinates.route" 
                    />
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
              @keydown.enter.exact.prevent="sendMessage()"
              @keydown.enter.shift="handleShiftEnter"
              :disabled="loading"
              class="chat-input"
            />
            <el-button 
              type="primary" 
              @click="sendMessage()" 
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading, ArrowUp } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import ChatSidebar from '../components/chat/ChatSidebar.vue'
import AmapView from '../components/map/AmapView.vue'
import { sendChatMessage } from '@/api'
import { getDeviceId } from '@/utils/device'
import { deleteTrip } from '@/api/history'

const route = useRoute()

interface Message {
  type: 'user' | 'ai'
  content?: string
  loading?: string
  coordinates?: any
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const sessionId = ref<string>('')
const messagesContainer = ref<HTMLElement | null>(null)
const chatSidebarRef = ref<InstanceType<typeof ChatSidebar> | null>(null)

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



// 滚动到最新消息
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 发送消息
const sendMessage = async (overrideMessage?: string) => {
  const message = overrideMessage || inputMessage.value.trim()
  if (!message || loading.value) return
  
  // 添加用户消息
  messages.value.push({ type: 'user', content: message })
  // 只有当不是使用 overrideMessage 时才清空输入框
  if (!overrideMessage) {
    inputMessage.value = ''
  }
  await scrollToBottom()
  
  // 添加 AI 加载消息
  messages.value.push({ type: 'ai', loading: '正在处理...' })
  await scrollToBottom()
  
  loading.value = true
  
  try {
    // 调用新的 sendChatMessage 方法
    await sendChatMessage(
      { message, session_id: sessionId.value, context: {}, device_id: getDeviceId() },
      {
        onThinking: () => {
          // 显示思考状态
        },
        onMessage: (text) => {
          // 追加消息
          messages.value[messages.value.length - 1] = { type: 'ai', content: text }
          scrollToBottom()
        },
        onPlan: async (markdown, coordinates) => {
          console.log('onPlan 回调触发:', { markdown: markdown?.length, coordinates })
          
          messages.value[messages.value.length - 1] = {
            type: 'ai',
            content: markdown || '',
            coordinates: coordinates || null,
          }
          scrollToBottom()
        },
        onSession: (id) => {
          // 保存 session_id
          sessionId.value = id
        },
        onError: (msg) => {
          // 错误处理
          console.error('发送消息失败:', msg)
          messages.value[messages.value.length - 1] = { type: 'ai', content: `抱歉，处理请求时出错了: ${msg}` }
        },
        onDone: () => {
          // 完成
        },
      }
    )
  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value[messages.value.length - 1] = { type: 'ai', content: '抱歉，处理请求时出错了，请重试。' }
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

// 处理 Shift+Enter 换行
const handleShiftEnter = (event: KeyboardEvent) => {
  // 手动在光标位置插入换行
  const textarea = event.target as HTMLTextAreaElement
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  inputMessage.value = inputMessage.value.substring(0, start) + '\n' + inputMessage.value.substring(end)
  // 恢复光标位置
  nextTick(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  })
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
onMounted(async () => {
  const sessionIdFromQuery = route.query.session_id as string
  
  if (sessionIdFromQuery) {
    // 方案：恢复历史对话
    await restoreSession(sessionIdFromQuery)
  } else if (route.query.city) {
    // 方案：用历史参数开始新对话
    await startWithParams({
      city: route.query.city as string,
      date: route.query.date as string,
      people: Number(route.query.people),
      budget: Number(route.query.budget),
      taste: route.query.taste as string,
    })
  } else {
    // 全新对话
    sessionId.value = generateSessionId()
  }
  
  const textarea = document.querySelector('.chat-input textarea') as HTMLTextAreaElement | null
  if (textarea) {
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
    })
  }
  
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
      scrollToBottom()
    })
  }
})

async function restoreSession(identifier: string) {
  try {
    const response = await fetch(`/api/v1/travel/history/sessions/${identifier}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    
    // 恢复消息列表（增加空值保护）
    const historyMessages = data.messages || []
    messages.value = historyMessages.map((msg: any) => ({
      type: msg.role === 'user' ? 'user' : 'ai',
      content: msg.content,
    }))
    
    // 用后端返回的 session_id 更新当前会话
    sessionId.value = data.session_id || identifier
    
    scrollToBottom()
  } catch (error) {
    console.error('恢复会话失败:', error)
    ElMessage.error('恢复会话失败，将开始新对话')
    sessionId.value = generateSessionId()
  }
}

async function startWithParams(params: { city: string; date: string; people: number; budget: number; taste: string }) {
  // 构建首条消息
  let initMessage = `我想去${params.city}玩`
  if (params.date) {
    initMessage += `，${params.date}出发`
  }
  if (params.people) {
    initMessage += `，${params.people}个人`
  }
  if (params.budget) {
    initMessage += `，预算${params.budget}元`
  }
  
  // 初始化 session
  sessionId.value = generateSessionId()
  
  // 自动发送首条消息
  await sendMessage(initMessage)
}

function handleNewChat() {
  // 清空状态，开始新对话
  messages.value = []
  sessionId.value = generateSessionId()
  inputMessage.value = ''
}

async function handleSelectChat(sessionIdFromSidebar: string) {
  // 加载选中的对话
  await restoreSession(sessionIdFromSidebar)
}

async function handleDeleteChat(tripId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条对话记录吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteTrip(tripId)
    ElMessage.success('删除成功')
    
    // 刷新侧边栏列表
    chatSidebarRef.value?.refresh()
    
    // 如果删的是当前对话，开新对话
    if (tripId === sessionId.value) {
      handleNewChat()
    }
  } catch (error) {
    // 用户取消删除
  }
}
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

/* 聊天页面整体布局 */
.chat-page {
  display: flex;
  height: calc(100vh - 60px);
  height: calc(100dvh - 60px);
  overflow: hidden;
  margin: 0;
  padding: 0;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  background-color: #f7f7f8;
  
  .dark & {
    background-color: #1e1e2e;
  }
  
  .chat-container {
    flex: 0 1 auto;
    display: flex;
    flex-direction: column;
    max-width: 800px;
    width: 100%;
    height: calc(100dvh - 60px); // 减去 header 高度
    margin: 0 auto;
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      display: flex;
      flex-direction: column;
      max-height: calc(100dvh - 200px); // 减去 header(60px) + 输入框(120px) + 边距(100px)
      
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
        margin-top: 20px;
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
              
              .map-section {
                margin-top: 16px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
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
      min-height: 120px; /* 确保输入框区域有最小高度 */
      
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
  .chat-main {
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
        min-height: 100px; /* 移动端调整最小高度 */
        
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