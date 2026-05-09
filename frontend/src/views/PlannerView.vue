<template>
  <div class="planner-view">
    <div class="planner-form" v-if="!loading">
      <h2>旅行规划</h2>
      <el-form class="planner-form-content" :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="城市" prop="city">
          <el-input v-model="form.city" placeholder="请输入目的地城市" />
        </el-form-item>
        <el-form-item label="出发日期" prop="travel_date">
          <el-date-picker 
            v-model="form.travel_date" 
            type="date" 
            placeholder="选择出发日期" 
            :min-date="new Date()"
          />
        </el-form-item>
        <el-form-item  label="人数" prop="people_count">
          <el-input-number 
            v-model="form.people_count" 
            :min="1" 
            :max="20" 
            placeholder="请输入人数" 
          />
        </el-form-item>
        <el-form-item label="预算" prop="budget">
          <el-input-number 
            v-model="form.budget" 
            :min="1" 
            placeholder="请输入预算" 
          />
        </el-form-item>
        <el-form-item label="口味偏好" prop="taste">
          <el-select v-model="form.taste" placeholder="选择口味偏好">
            <el-option label="辣" value="辣" />
            <el-option label="清淡" value="清淡" />
            <el-option label="不挑" value="不挑" />
          </el-select>
        </el-form-item>
        <el-form-item label="出发地点">
          <el-input v-model="form.departure" placeholder="请输入出发地点（可选）" />
        </el-form-item>
        <el-form-item label="活动数量" prop="activity_count">
          <el-slider 
            v-model="form.activity_count" 
            :min="1" 
            :max="5" 
            :marks="{ 1: '1', 5: '5' }" 
          />
          <span class="slider-value">{{ form.activity_count }} 个活动</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="loading">生成建议</el-button>
          <el-button @click="resetForm">重置</el-button>
          <el-button type="info" @click="mockTravelPlan">Mock测试</el-button>
        </el-form-item>
      </el-form>
    </div>
    <div v-else class="loading-container">
      <LoadingSpinner :visible="true" tip="正在生成旅行建议..." />
    </div>
    <ErrorAlert 
      v-if="error" 
      :message="error" 
      type="error" 
      @close="error = null" 
    />
    <div v-if="loading" class="status-container">
      <StatusFlow :visited-agents="visitedAgents" :current-agent="currentAgent || undefined" />
    </div>
    <div v-if="result" class="result-container" ref="resultContainer">
      <AmapView 
        v-if="coordinates && coordinates.points && coordinates.points.length > 0"
        :points="coordinates.points"
        :route="coordinates.route"
      />
      <MarkdownRenderer :content="result.result_markdown" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import LoadingSpinner from '../components/common/LoadingSpinner.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import StatusFlow from '../components/common/StatusFlow.vue'
import ErrorAlert from '../components/common/ErrorAlert.vue'
import AmapView from '../components/map/AmapView.vue'
import { useTravelPlanner } from '../composables/useTravelPlanner'
import { useTravelStore } from '../stores/travel'
import { TasteType, TravelRequest } from '../types/travel'
import { createTrip } from '../api/history'
import { getDeviceId } from '../utils/device'
import { extractCoordinatesFromText } from '../utils/coordinates'

const formRef = ref<any>(null)
const resultContainer = ref<HTMLElement | null>(null)

const form = ref({
  city: '广州',
  travel_date: '',
  people_count: 1,
  budget: 0,
  taste: '' as TasteType,
  departure: '',
  activity_count: 1
})

const rules = {
  city: [
    { required: true, message: '请输入目的地城市', trigger: 'blur' }
  ],
  travel_date: [
    { required: true, message: '请选择出发日期', trigger: 'change' }
  ],
  budget: [
    { required: true, message: '请输入预算', trigger: 'blur' },
    { type: 'number', min: 1, message: '预算必须大于0', trigger: 'blur' }
  ],
  people_count: [
    { required: true, message: '请输入人数', trigger: 'blur' },
    { type: 'number', min: 1, max: 20, message: '人数必须在1-20之间', trigger: 'blur' }
  ],
  taste: [
    { required: true, message: '请选择口味偏好', trigger: 'change' }
  ],
  activity_count: [
    { required: true, message: '请选择活动数量', trigger: 'change' },
    { type: 'number', min: 1, max: 5, message: '活动数量必须在1-5之间', trigger: 'change' }
  ]
}

const { loading, error, result, visitedAgents, currentAgent, planTravel, reset } = useTravelPlanner()
const travelStore = useTravelStore()

// 解析坐标数据（优先使用接口返回的坐标，其次从Markdown中解析）
const coordinates = computed(() => {
  if (!result.value) return null
  
  // 优先使用后端接口直接返回的坐标
  if (result.value.coordinates && result.value.coordinates.points && result.value.coordinates.points.length > 0) {
    return result.value.coordinates
  }
  
  // 备用方案：从Markdown中解析坐标
  if (result.value.result_markdown) {
    const parsedCoords = extractCoordinatesFromText(result.value.result_markdown)
    if (parsedCoords && parsedCoords.points.length > 0) {
      return parsedCoords
    }
  }
  
  return null
})

// 添加console.log检查result
console.log('PlannerView result:', result.value)

// 添加watch监听result变化
watch(result, async (newVal) => {
  console.log('PlannerView result changed:', newVal)
  if (newVal && newVal.result_markdown) {
    try {
      await createTrip({
        device_id: getDeviceId(),
        city: form.value.city,
        travel_date: form.value.travel_date ? new Date(form.value.travel_date).toISOString().split('T')[0] : '',
        people_count: form.value.people_count,
        budget: form.value.budget,
        taste: form.value.taste || null,
        departure: form.value.departure || null,
        activity_count: form.value.activity_count,
        plan_markdown: newVal.result_markdown,
        mode: 'quick',
      })
      console.log('快速规划行程已保存')
    } catch (error) {
      console.error('保存行程失败:', error)
    }
  }
})

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      // 格式化日期为 YYYY-MM-DD 字符串（使用本地时间）
      const formattedForm = {
        ...form.value,
        travel_date: form.value.travel_date ? formatDate(new Date(form.value.travel_date)) : ''
      } as TravelRequest
      
      // 提交表单
      await planTravel(formattedForm)
      
      // 监听结果，完成后滚动到结果区域
      if (result.value) {
        await nextTick()
        if (resultContainer.value) {
          resultContainer.value.scrollIntoView({ behavior: 'smooth' })
        }
      }
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  reset()
}

const mockTravelPlan = async () => {
  // 生成mock markdown文案
  const mockMarkdown = `# Mock 行程建议

## 天气与出行提醒
- **日期**：2026年5月1日（劳动节）
- **天气**：晴天 ☀️
- **气温**：约 25°C，体感舒适
- **建议**：
  - 携带防晒霜和太阳镜
  - 穿着轻便透气的衣物
  - 注意补充水分

---

## 活动建议
### 推荐景点（共2个，已优化路线）

#### 1. 广州塔
- **类型**：地标建筑 / 观景台
- **地址**：广州市海珠区阅江西路222号
- **特色**：
  - 中国第一高、世界第三高的旅游观光塔
  - 拥有摩天轮、极速云霄等游乐设施
  - 俯瞰广州全景的最佳地点
- **建议停留时间**：2 小时
- **门票**：约150元

#### 2. 珠江夜游
- **类型**：水上观光 / 夜景游览
- **地址**：广州市越秀区沿江西路
- **特色**：
  - 欣赏珠江两岸夜景的绝佳方式
  - 途经广州塔、海心沙、猎德大桥等景点
  - 船上提供餐饮和表演
- **建议停留时间**：1.5 小时
- **门票**：约80元

> ✅ **路线说明**：从广州塔出发，步行至珠江夜游码头约15分钟；也可乘坐地铁或公交接驳。

---

## 餐饮建议
### 总预算控制：300元（2人），实际餐饮支出建议为 **≤100元**

| 时间 | 餐厅 | 地点 | 人均 | 总价 | 特色 |
|------|------|------|------|------|------|
| 午餐<br>12:00–13:30 | 点都德（广州塔店） | 广州塔附近 | ¥50 | ¥100 | 广式早茶，经典点心 |
| 晚餐<br>18:00–19:30 | 广州酒家（总店） | 上下九步行街 | ¥60 | ¥120 | 传统粤菜，老字号 |

> 💡 **替代建议**：若不顺路，可选择路边小吃摊（如肠粉、云吞面，人均15–30元），经济实惠。

---

## 推荐行程（时间线）
| 时间 | 安排 | 提示 |
|------|------|------|
| 09:30–11:30 | 游览广州塔 | 登塔观景，体验游乐设施 |
| 11:30–12:00 | 前往餐厅 | 步行至点都德（广州塔店） |
| 12:00–13:30 | 午餐 @ 点都德 | 品尝广式早茶 |
| 14:00–16:00 | 自由活动 | 可前往附近的广州博物馆 |
| 16:00–17:30 | 前往珠江夜游码头 | 乘坐地铁或公交 |
| 18:00–19:30 | 珠江夜游 | 欣赏珠江夜景 |

---

## 预算建议
| 项目 | 明细 | 小计（元） |
|------|------|------------|
| 交通 | 打车/地铁往返（估算） | ¥30 |
| 餐饮 | 午餐+晚餐（推荐组合） | ¥220 |
| 景点 | 广州塔门票+珠江夜游门票 | ¥460 |
| 应急预留 | 饮水、临时消费 | ¥90 |
| **总计** | —— | **¥800** |

✅ **行程紧凑但不过满**，全天以观光+美食为主线，适合两人轻松出游。`
  
  // 构建mock响应（包含坐标数据）
  const mockResponse = {
    session_id: `session-${Date.now()}`,
    status: 'completed',
    result_markdown: mockMarkdown,
    created_at: new Date().toISOString(),
    coordinates: {
      points: [
        {
          name: '广州塔',
          lng: 113.3234,
          lat: 23.1063,
          type: 'activity' as const,
          description: '中国第一高、世界第三高的旅游观光塔',
          duration: '120分钟'
        },
        {
          name: '珠江夜游',
          lng: 113.3097,
          lat: 23.1105,
          type: 'activity' as const,
          description: '欣赏珠江两岸夜景的绝佳方式',
          duration: '90分钟'
        },
        {
          name: '点都德（广州塔店）',
          lng: 113.3225,
          lat: 23.1058,
          type: 'restaurant' as const,
          cuisine: '粤菜',
          price_per_person: 50,
          rating: 4.5
        },
        {
          name: '广州酒家（总店）',
          lng: 113.2643,
          lat: 23.1302,
          type: 'restaurant' as const,
          cuisine: '粤菜',
          price_per_person: 60,
          rating: 4.7
        }
      ],
      route: {
        segments: [
          {
            from: '广州塔',
            to: '珠江夜游',
            path: [
              [113.3234, 23.1063],
              [113.3180, 23.1080],
              [113.3120, 23.1095],
              [113.3100, 23.1102],
              [113.3097, 23.1105]
            ],
            distance: '1500米',
            duration: '20分钟'
          }
        ]
      }
    }
  }
  
  // 重置之前的响应
  travelStore.reset()
  
  // 设置到store中
  travelStore.setResponse(mockResponse)
  
  // 检查result是否更新
  console.log('PlannerView result after mock:', result.value)
  
  // 滚动到结果区域
  await nextTick()
  if (resultContainer.value) {
    resultContainer.value.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

<style lang="scss">
.planner-view {
  h2 {
    margin-bottom: $spacing-lg;
    color: #303133;
  }

  .planner-form {
    background-color: white;
    padding: $spacing-lg;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    margin-bottom: $spacing-lg;
  }

  .planner-form-content {
    margin-left: -40px;
  }

  .loading-container {
    display: flex;
    justify-content: center;
    padding: $spacing-xl;
  }

  .status-container {
    background-color: white;
    padding: $spacing-lg;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    margin-bottom: $spacing-lg;
  }

  .result-container {
    background-color: white;
    padding: $spacing-lg;
    border-radius: $border-radius;
    box-shadow: $box-shadow-light;
    margin-top: $spacing-lg;

    h3 {
      margin-bottom: $spacing-md;
      color: #303133;
    }
  }

  .slider-value {
    margin-left: $spacing-md;
    font-size: $font-size-sm;
    color: #606266;
  }
}

@media (max-width: 768px) {
  .planner-view {
    .planner-form {
      padding: $spacing-md;
    }

    .status-container,
    .result-container {
      padding: $spacing-md;
    }
  }
}
</style>