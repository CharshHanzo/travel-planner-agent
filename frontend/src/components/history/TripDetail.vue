<template>
  <el-dialog 
    :title="dialogTitle" 
    :visible.sync="visible" 
    width="80%" 
    max-width="900px"
    :loading="loading"
  >
    <div v-if="trip" class="trip-detail">
      <div class="detail-header">
        <div class="basic-info">
          <span class="info-item">
            <el-icon><User /></el-icon>
            {{ trip.people_count }}人
          </span>
          <span class="info-item">
            <el-icon><Wallet /></el-icon>
            {{ trip.budget }}元
          </span>
          <span v-if="trip.taste && trip.taste !== '不挑'" class="info-item">
            <el-icon><ForkSpoon /></el-icon>
            {{ trip.taste }}口味
          </span>
        </div>
        <span :class="['mode-tag', trip.mode === 'quick' ? 'mode-quick' : 'mode-chat']">
          {{ trip.mode === 'quick' ? '快速规划' : '对话规划' }}
        </span>
      </div>
      
      <!-- 标签页切换（仅对话模式且有消息时显示） -->
      <el-tabs v-model="activeTab" v-if="showTabs" class="detail-tabs">
        <el-tab-pane label="旅行计划" name="plan">
          <div class="detail-content">
            <MarkdownRenderer :content="trip.plan_markdown" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="对话记录" name="chat">
          <div ref="chatContainer" class="chat-content">
            <div v-for="(message, index) in trip.messages" :key="index" :class="['message', message.role]">
              <div class="message-content">
                <div v-if="message.role === 'assistant'" class="ai-message">
                  <MarkdownRenderer :content="message.content" />
                  <!-- Agent 调用标签 -->
                  <div v-if="message.agent_calls && message.agent_calls.length > 0" class="agent-tags">
                    <span v-for="(agent, idx) in message.agent_calls" :key="idx" class="agent-tag">
                      {{ getAgentLabel(agent) }}
                    </span>
                  </div>
                </div>
                <div v-else class="user-message">
                  {{ message.content }}
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
      
      <!-- 快速模式：只显示旅行计划 -->
      <div v-else class="detail-content">
        <MarkdownRenderer :content="trip.plan_markdown" />
      </div>
    </div>
    
    <template #footer>
      <div class="footer-content">
        <div class="rating-section">
          <span class="rating-label">评分：</span>
          <el-rate 
            v-model="currentRating" 
            :max="5" 
            show-score 
            text-color="#ff9900"
            score-template="{value}分"
            @change="handleRating"
          />
        </div>
        <el-button type="primary" @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { User, Wallet, ForkSpoon } from '@element-plus/icons-vue'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'
import type { TripDetail as TripDetailType } from '@/api/history'
import { fetchTripDetail, rateTrip } from '@/api/history'

const props = defineProps<{
  visible: boolean
  tripId: string | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const loading = ref(false)
const trip = ref<TripDetailType | null>(null)
const currentRating = ref(0)
const activeTab = ref('plan')
const chatContainer = ref<HTMLElement | null>(null)

const dialogTitle = computed(() => {
  if (!trip.value) return '行程详情'
  return `${trip.value.city} · ${trip.value.travel_date}`
})

const showTabs = computed(() => {
  return trip.value?.mode === 'chat' && trip.value?.messages.length > 0
})

const agentLabels: Record<string, string> = {
  weather: '天气查询',
  activities: '活动推荐',
  food: '美食推荐',
  modify: '修改建议',
  generate_plan: '生成计划'
}

function getAgentLabel(agent: string): string {
  return agentLabels[agent] || agent
}

watch(() => props.visible, async (val) => {
  if (val && props.tripId) {
    activeTab.value = 'plan'
    await loadTripDetail(props.tripId)
  }
})

watch(activeTab, async (val) => {
  if (val === 'chat') {
    await nextTick()
    scrollToBottom()
  }
})

async function loadTripDetail(tripId: string) {
  loading.value = true
  try {
    trip.value = await fetchTripDetail(tripId)
    currentRating.value = trip.value.rating || 0
    await nextTick()
    if (activeTab.value === 'chat') {
      scrollToBottom()
    }
  } catch (error) {
    console.error('加载行程详情失败:', error)
    emit('update:visible', false)
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function handleRating(rating: number) {
  if (!props.tripId) return
  try {
    await rateTrip(props.tripId, rating)
  } catch (error) {
    console.error('评分失败:', error)
  }
}
</script>

<style lang="scss" scoped>
.trip-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $spacing-md;
    background-color: #f5f7fa;
    border-radius: $border-radius;
    margin-bottom: $spacing-md;

    .basic-info {
      display: flex;
      gap: $spacing-md;

      .info-item {
        display: flex;
        align-items: center;
        font-size: $font-size-sm;
        color: #606266;

        el-icon {
          margin-right: 4px;
        }
      }
    }

    .mode-tag {
      padding: 4px 12px;
      border-radius: $border-radius-sm;
      font-size: $font-size-xs;
      font-weight: 500;

      &.mode-quick {
        background-color: rgba($success-color, 0.1);
        color: $success-color;
      }

      &.mode-chat {
        background-color: rgba($primary-color, 0.1);
        color: $primary-color;
      }
    }
  }

  .detail-tabs {
    margin-top: $spacing-sm;
  }

  .detail-content {
    max-height: 500px;
    overflow-y: auto;
    padding-right: $spacing-sm;
  }

  .chat-content {
    max-height: 500px;
    overflow-y: auto;
    padding: $spacing-md;
    background-color: #f7f7f8;
    border-radius: $border-radius;

    .message {
      margin-bottom: $spacing-md;

      &.user {
        display: flex;
        justify-content: flex-end;

        .message-content {
          max-width: 70%;
          background-color: #409eff;
          color: white;
          border-radius: 18px 18px 4px 18px;
          padding: $spacing-sm $spacing-md;

          .user-message {
            font-size: $font-size-base;
            line-height: 1.6;
          }
        }
      }

      &.assistant {
        display: flex;
        justify-content: flex-start;

        .message-content {
          max-width: 100%;
          background-color: white;
          border-radius: 18px 18px 18px 4px;
          padding: $spacing-sm $spacing-md;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

          .ai-message {
            font-size: $font-size-base;
            line-height: 1.6;

            :deep(h1), :deep(h2), :deep(h3) {
              font-size: $font-size-base;
              margin: $spacing-xs 0;
            }

            :deep(p) {
              margin: $spacing-xs 0;
            }

            :deep(ul), :deep(ol) {
              padding-left: $spacing-md;
              margin: $spacing-xs 0;
            }
          }

          .agent-tags {
            display: flex;
            flex-wrap: wrap;
            gap: $spacing-xs;
            margin-top: $spacing-sm;

            .agent-tag {
              padding: 2px 8px;
              background-color: rgba($primary-color, 0.1);
              color: $primary-color;
              border-radius: $border-radius-sm;
              font-size: $font-size-xs;
            }
          }
        }
      }
    }
  }
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .rating-section {
    display: flex;
    align-items: center;
    gap: $spacing-sm;

    .rating-label {
      font-size: $font-size-sm;
      color: #606266;
    }
  }
}
</style>