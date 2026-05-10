<template>
  <div class="sidebar-wrapper" :class="{ collapsed: isCollapsed }">
    <!-- 折叠按钮 -->
    <button 
      class="collapse-btn" 
      @click="toggleCollapse"
      title="折叠侧边栏"
    >
      <el-icon><component :is="isCollapsed ? ArrowRight : ArrowLeft" /></el-icon>
    </button>
    
    <!-- 侧边栏 -->
    <div 
      class="chat-sidebar" 
      :class="{ collapsed: isCollapsed }"
    >
      <!-- 侧边栏内容 -->
      <div class="sidebar-content">
      <!-- 新建对话按钮 -->
      <button class="new-chat-btn" @click="handleNewChat">
        <el-icon><ChatDotSquare /></el-icon>
        <span v-if="!isCollapsed">新建对话</span>
      </button>
      
      <!-- 分割线 -->
      <div class="divider" v-if="!isCollapsed"></div>
      
      <!-- 历史记录列表 -->
      <div class="history-list">
        <div v-if="trips.length === 0" class="empty-state">
          <el-icon><Box /></el-icon>
          <span v-if="!isCollapsed">暂无对话记录</span>
        </div>
        
        <div 
          v-for="trip in trips" 
          :key="trip.id"
          class="history-item"
          :class="{ active: trip.id === currentSessionId }"
          @click="handleSelectChat(trip.id)"
        >
          <div class="item-content">
            <el-icon class="location-icon"><MapLocation /></el-icon>
            <div class="item-info" v-if="!isCollapsed">
              <div class="item-title">{{ trip.city || '未命名行程' }}</div>
              <div class="item-time">{{ formatTime(trip.created_at) }}</div>
            </div>
          </div>
          
          <!-- 删除按钮 -->
          <button 
            v-if="!isCollapsed"
            class="delete-btn" 
            @click.stop="handleDeleteChat(trip.id)"
            title="删除对话"
          >
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </div>
      </div>
      
      <!-- 底部查看全部历史 -->
      <div class="sidebar-footer">
        <div class="divider" v-if="!isCollapsed"></div>
        <router-link 
          to="/history" 
          class="view-all-link"
          title="查看全部历史"
        >
          <el-icon><List /></el-icon>
          <span class="text-content">查看全部历史</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeft, 
  ArrowRight, 
  ChatDotSquare, 
  MapLocation, 
  Delete, 
  List,
  Box 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchTrips, deleteTrip } from '@/api/history'
import type { TripItem } from '@/api/history'

const router = useRouter()

defineProps<{
  currentSessionId: string
}>()

const emit = defineEmits<{
  (e: 'new-chat'): void
  (e: 'select-chat', sessionId: string): void
  (e: 'delete-chat', sessionId: string): void
}>()

const isCollapsed = ref(false)
const trips = ref<TripItem[]>([])

// 从 localStorage 读取折叠状态
const loadCollapseState = () => {
  const saved = localStorage.getItem('sidebarCollapsed')
  isCollapsed.value = saved === 'true'
}

// 保存折叠状态到 localStorage
const saveCollapseState = () => {
  localStorage.setItem('sidebarCollapsed', String(isCollapsed.value))
}

// 切换折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  saveCollapseState()
}

// 获取历史记录
const loadHistory = async () => {
  try {
    const data = await fetchTrips({ limit: 10 })
    trips.value = data.trips || []
  } catch (error) {
    console.error('加载历史记录失败:', error)
  }
}

// 格式化时间
const formatTime = (dateString?: string) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

// 处理新建对话
const handleNewChat = () => {
  emit('new-chat')
}

// 处理选择对话
const handleSelectChat = (sessionId: string) => {
  emit('select-chat', sessionId)
}

// 处理删除对话
const handleDeleteChat = (tripId: string) => {
  emit('delete-chat', tripId)
}

// 刷新历史列表
const refreshHistory = () => {
  loadHistory()
}

// 监听路由变化刷新列表
const handleRouteChange = () => {
  loadHistory()
}

onMounted(() => {
  loadCollapseState()
  loadHistory()
  
  // 监听路由变化
  router.afterEach(handleRouteChange)
})

onUnmounted(() => {
  router.afterEach(handleRouteChange)
})

// 监听折叠状态变化
watch(isCollapsed, saveCollapseState)

// 暴露 refresh 方法
defineExpose({
  refresh: refreshHistory,
})
</script>

<style lang="scss" scoped>
.sidebar-wrapper {
  position: relative;
  width: 260px;
  transition: width 0.2s ease;
  
  &.collapsed {
    width: 60px;
  }
  
  .collapse-btn {
    position: absolute;
    right: -12px;
    top: 26px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 1px solid #e5e7eb;
    background-color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 10;
    transition: all 0.2s ease;
    
    .dark & {
      background-color: #2d2d3f;
      border-color: #3d3d4f;
      
      .el-icon {
        color: #9ca3af;
      }
    }
    
    &:hover {
      background-color: #f0f0f0;
      transform: scale(1.1);
      
      .dark & {
        background-color: #3d3d4f;
      }
    }
    
    .el-icon {
      font-size: 14px;
      color: #6b7280;
    }
  }
}

.chat-sidebar {
  width: 100%;
  background-color: #f9fafb;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid #e5e7eb;
  overflow: hidden;
  
  .dark & {
    background-color: #1a1a2e;
    border-right-color: #2d2d3f;
  }
  
  .sidebar-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 16px;
    overflow: hidden;
    align-items: stretch;
  }
  
  .collapsed & {
    .sidebar-content {
      align-items: center;
    }
  }
  
  .new-chat-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 12px 16px;
    background-color: #409eff;
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    overflow: hidden;
    
    &:hover {
      background-color: #3089e6;
      transform: translateY(-1px);
    }
    
    &:active {
      transform: translateY(0);
    }
    
    .el-icon {
      font-size: 18px;
    }
  }
  
  .divider {
    height: 1px;
    background-color: #e5e7eb;
    margin: 16px 0;
    
    .dark & {
      background-color: #2d2d3f;
    }
  }
  
  .history-list {
    flex: 1;
    overflow-y: auto;
    padding-right: 4px;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-track {
      background: transparent;
    }
    
    &::-webkit-scrollbar-thumb {
      background-color: #d1d5db;
      border-radius: 3px;
      
      .dark & {
        background-color: #3d3d4f;
      }
    }
    
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 16px;
      color: #9ca3af;
      
      .el-icon {
        font-size: 32px;
        margin-bottom: 8px;
      }
      
      span {
        font-size: 14px;
      }
    }
    
    .history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      margin-bottom: 4px;
      
      &:hover {
        background-color: #f3f4f6;
        
        .dark & {
          background-color: #2d2d3f;
        }
        
        .delete-btn {
          opacity: 1;
        }
      }
      
      &.active {
        background-color: #e0f2fe;
        
        .dark & {
          background-color: #2563eb;
        }
        
        .item-title {
          color: #0ea5e9;
          
          .dark & {
            color: #bfdbfe;
          }
        }
      }
      
      .item-content {
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1;
        min-width: 0;
        
        .location-icon {
          flex-shrink: 0;
          font-size: 18px;
          color: #f59e0b;
        }
        
        .item-info {
          flex: 1;
          min-width: 0;
          
          .item-title {
            font-size: 14px;
            font-weight: 500;
            color: #374151;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            
            .dark & {
              color: #e5e7eb;
            }
          }
          
          .item-time {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 2px;
          }
        }
      }
      
      .delete-btn {
        opacity: 0;
        padding: 6px;
        border: none;
        background: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
        
        &:hover {
          background-color: #fee2e2;
          
          .dark & {
            background-color: #450a0a;
          }
          
          .el-icon {
            color: #dc2626;
          }
        }
        
        .el-icon {
          font-size: 16px;
          color: #9ca3af;
        }
      }
    }
  }
  
  .sidebar-footer {
    flex-shrink: 0;
    
    .view-all-link {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px;
      color: #6b7280;
      text-decoration: none;
      font-size: 14px;
      border-radius: 10px;
      transition: all 0.2s ease;
      white-space: nowrap;
      overflow: hidden;
      
      .dark & {
        color: #9ca3af;
      }
      
      &:hover {
        background-color: #f3f4f6;
        color: #374151;
        
        .dark & {
          background-color: #2d2d3f;
          color: #e5e7eb;
        }
      }
      
      .el-icon {
        font-size: 16px;
      }
      
      .text-content {
        opacity: 1;
        transition: opacity 0.1s ease 0.1s;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
  
}

.sidebar-wrapper.collapsed {
  .chat-sidebar {
    .sidebar-footer {
      .view-all-link {
        .text-content {
          opacity: 0;
          transition: opacity 0.05s ease 0s;
        }
      }
    }
  }
}

// 深色模式
.dark {
  .chat-sidebar {
    background-color: #1a1a2e;
    border-right-color: #2d2d3f;
  }
}
</style>