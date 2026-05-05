<template>
  <div class="history-view">
    <div class="search-bar">
      <el-input 
        v-model="searchCity" 
        placeholder="搜索城市" 
        class="search-input"
        clearable
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select 
        v-model="ratingFilter" 
        placeholder="评分筛选" 
        class="rating-select"
        @change="handleSearch"
      >
        <el-option label="全部" :value="''" />
        <el-option label="3分及以上" :value="3" />
        <el-option label="4分及以上" :value="4" />
        <el-option label="5分" :value="5" />
      </el-select>
    </div>
    
    <div v-if="loading" class="loading-container">
      <div class="loading-content">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
    </div>
    
    <div v-else-if="trips.length === 0" class="empty-container">
      <el-empty 
        description="暂无历史记录"
        :image-size="200"
      >
        <el-button type="primary" @click="$router.push('/planner')">去规划旅行</el-button>
      </el-empty>
    </div>
    
    <div v-else class="trip-grid">
      <div 
        v-for="trip in trips" 
        :key="trip.id" 
        class="trip-item"
      >
        <TripCard 
          :trip="trip" 
          @view="handleViewDetail" 
          @delete="handleDelete"
        />
      </div>
    </div>
    
    <TripDetail 
      :visible="showDetail" 
      :trip-id="selectedTripId" 
      @update:visible="showDetail = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, Loading } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import TripCard from '@/components/history/TripCard.vue'
import TripDetail from '@/components/history/TripDetail.vue'
import { fetchTrips, deleteTrip } from '@/api/history'
import type { TripItem } from '@/api/history'

const loading = ref(false)
const trips = ref<TripItem[]>([])
const searchCity = ref('')
const ratingFilter = ref<number | string>('')
const showDetail = ref(false)
const selectedTripId = ref<string | null>(null)

async function loadTrips() {
  loading.value = true
  try {
    const result = await fetchTrips({
      city: searchCity.value || undefined,
      rating_min: ratingFilter.value ? Number(ratingFilter.value) : undefined,
      limit: 50,
    })
    trips.value = result.trips
  } catch (error) {
    console.error('加载行程列表失败:', error)
    trips.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadTrips()
}

function handleViewDetail(tripId: string) {
  selectedTripId.value = tripId
  showDetail.value = true
}

async function handleDelete(tripId: string) {
  await ElMessageBox.confirm(
    '确定要删除这条行程记录吗？',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
  
  try {
    await deleteTrip(tripId)
    ElMessage.success('删除成功')
    loadTrips()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadTrips()
})
</script>

<style lang="scss">
.history-view {
  .search-bar {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-lg;
    padding: $spacing-md;
    background-color: white;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;

    .search-input {
      flex: 1;
      max-width: 300px;
    }

    .rating-select {
      width: 150px;
    }
  }

  .loading-container {
    padding: $spacing-xl;
    display: flex;
    justify-content: center;
    align-items: center;

    .loading-content {
      display: flex;
      align-items: center;
      gap: $spacing-sm;

      .loading-icon {
        animation: spin 1s linear infinite;
        font-size: 24px;
        color: $primary-color;
      }
    }
  }

  .empty-container {
    background-color: white;
    padding: $spacing-xl;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
  }

  .trip-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-md;

    .trip-item {
      break-inside: avoid;
    }
  }
}

@media (max-width: 992px) {
  .history-view {
    .trip-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}

@media (max-width: 768px) {
  .history-view {
    .search-bar {
      flex-direction: column;

      .search-input {
        max-width: none;
      }

      .rating-select {
        width: 100%;
      }
    }

    .trip-grid {
      grid-template-columns: 1fr;
    }
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>