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
      
      <div class="detail-content">
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
import { ref, computed, watch } from 'vue'
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

const dialogTitle = computed(() => {
  if (!trip.value) return '行程详情'
  return `${trip.value.city} · ${trip.value.travel_date}`
})

watch(() => props.visible, async (val) => {
  if (val && props.tripId) {
    await loadTripDetail(props.tripId)
  }
})

async function loadTripDetail(tripId: string) {
  loading.value = true
  try {
    trip.value = await fetchTripDetail(tripId)
    currentRating.value = trip.value.rating || 0
  } catch (error) {
    console.error('加载行程详情失败:', error)
    emit('update:visible', false)
  } finally {
    loading.value = false
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

  .detail-content {
    max-height: 500px;
    overflow-y: auto;
    padding-right: $spacing-sm;
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