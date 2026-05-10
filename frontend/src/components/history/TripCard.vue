<template>
  <div class="trip-card">
    <div class="card-header">
      <h3 class="city-name">{{ trip.city || '未命名行程' }}</h3>
      <span :class="['mode-tag', trip.mode === 'quick' ? 'mode-quick' : 'mode-chat']">
        {{ trip.mode === 'quick' ? '快速规划' : '对话规划' }}
      </span>
    </div>
    
    <div class="card-info">
      <div class="info-row">
        <span class="info-tag">
          <el-icon><Calendar /></el-icon>
          {{ formatDate(trip.travel_date) }}
        </span>
        <span class="info-tag">
          <el-icon><User /></el-icon>
          {{ trip.people_count }}人
        </span>
        <span class="info-tag">
          <el-icon><Wallet /></el-icon>
          {{ trip.budget }}元
        </span>
      </div>
      
      <div v-if="trip.taste && trip.taste !== '不挑'" class="info-row">
        <span class="info-tag">
          <el-icon><KnifeFork /></el-icon>
          {{ trip.taste }}口味
        </span>
      </div>
    </div>
    
    <div class="card-rating">
      <el-rate 
        :value="trip.rating || 0" 
        disabled 
        show-score 
        text-color="#ff9900"
        score-template="{value}"
        class="rating"
      />
    </div>
    
    <div class="card-footer">
      <span class="create-time">{{ formatTime(trip.created_at) }}</span>
      <div class="actions">
        <el-button size="small" type="primary" @click="$emit('view', trip.id)">
          <el-icon><View /></el-icon>
          查看详情
        </el-button>
        <el-button size="small" type="danger" @click="$emit('delete', trip.id)">
          <el-icon><Delete /></el-icon>
          删除
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Calendar, User, Wallet, KnifeFork, View, Delete } from '@element-plus/icons-vue'
import type { TripItem } from '@/api/history'

defineProps<{
  trip: TripItem
}>()

defineEmits<{
  view: [tripId: string]
  delete: [tripId: string]
}>()

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(timeStr: string): string {
  if (!timeStr) return ''
  const now = new Date()
  const created = new Date(timeStr)
  const diff = now.getTime() - created.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return created.toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.trip-card {
  background: white;
  border-radius: $border-radius;
  padding: $spacing-md;
  box-shadow: $box-shadow-light;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: $box-shadow;
    transform: translateY(-2px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-md;

    .city-name {
      font-size: $font-size-lg;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }

    .mode-tag {
      padding: 2px 8px;
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

  .card-info {
    margin-bottom: $spacing-md;

    .info-row {
      display: flex;
      flex-wrap: wrap;
      gap: $spacing-xs;
      margin-bottom: $spacing-xs;

      .info-tag {
        display: flex;
        align-items: center;
        padding: 4px 8px;
        background-color: #f5f7fa;
        border-radius: $border-radius-sm;
        font-size: $font-size-xs;
        color: #606266;

        el-icon {
          margin-right: 4px;
          font-size: 12px;
        }
      }
    }
  }

  .card-rating {
    margin-bottom: $spacing-md;

    .rating {
      font-size: 14px;
    }
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: $spacing-sm;
    border-top: 1px solid $border-color;

    .create-time {
      font-size: $font-size-xs;
      color: #909399;
    }

    .actions {
      display: flex;
      gap: $spacing-xs;
    }
  }
}
</style>