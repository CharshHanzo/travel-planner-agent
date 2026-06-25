<template>
  <div class="planner-view">
    <div class="planner-form" v-if="!hasStarted && !result">
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
        <el-form-item label="人数" prop="people_count">
          <el-input-number v-model="form.people_count" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="预算" prop="budget">
          <el-input-number v-model="form.budget" :min="1" />
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
          <el-slider v-model="form.activity_count" :min="1" :max="5" :marks="{ 1: '1', 5: '5' }" />
        </el-form-item>
        <el-form-item label="出行方式">
          <el-select v-model="form.transport_mode" placeholder="选择出行方式">
            <el-option label="步行（≤2km）" value="walking" />
            <el-option label="公共交通（≤5km）" value="transit" />
            <el-option label="自驾/打车" value="driving" />
            <el-option label="不限" value="any" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitForm">生成建议</el-button>
          <el-button @click="resetForm">重置</el-button>
          <el-button type="info" @click="mockTravelPlan">Mock测试</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="hasStarted && !result" class="plan-progress">
      <div class="progress-title">正在生成旅行计划...</div>
      <div v-for="(status, step) in steps" :key="step" :class="['progress-step', status]">
        <span class="step-icon">
          {{ status === 'done' ? '✅' : status === 'running' ? '⏳' : status === 'error' ? '❌' : '⬜' }}
        </span>
        <span class="step-label">{{ stepLabel[step as keyof typeof stepLabel] }}</span>
      </div>
    </div>

    <ErrorAlert v-if="error" :message="error" type="error" @close="error = ''" />

    <div v-if="result" class="result-container" ref="resultContainer">
      <AmapView 
        v-if="coordinates && coordinates.points && coordinates.points.length > 0"
        :points="coordinates.points"
        :route="coordinates.route"
      />
      <MarkdownRenderer :content="result.result_markdown" />
      <div class="result-actions">
        <el-button type="primary" @click="resetForm">继续规划</el-button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, nextTick, computed, onMounted } from 'vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import ErrorAlert from '../components/common/ErrorAlert.vue'
import AmapView from '../components/map/AmapView.vue'
import { fetchUserPreferences } from '../api/user'
import { getDeviceId } from '../utils/device'
import { extractCoordinatesFromText } from '../utils/coordinates'
import { ElMessage } from 'element-plus'

// 定义步骤类型
type StepStatus = 'waiting' | 'running' | 'done' | 'error'
type StepKey = 'weather' | 'activities' | 'food' | 'route' | 'plan'

const formRef = ref<any>(null)
const resultContainer = ref<HTMLElement | null>(null)

// 进度步骤状态 - 使用 StepKey 类型
const steps = ref<Record<StepKey, StepStatus>>({
  weather: 'waiting',
  activities: 'waiting',
  food: 'waiting',
  route: 'waiting',
  plan: 'waiting',
})

const stepLabel: Record<StepKey, string> = {
  weather: '查询天气',
  activities: '搜索活动',
  food: '推荐美食',
  route: '规划路线',
  plan: '生成计划',
}

const isPlanning = computed(() => {
  return Object.values(steps.value).some(s => s === 'running' || s === 'done')
})

const form = ref({
  city: '广州',
  travel_date: '',
  people_count: 1,
  budget: 0,
  taste: '' as string,
  departure: '',
  activity_count: 1,
  activity_source: 'xiaohongshu',
  food_source: 'meituan',
  transport_mode: 'any'
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
    { type: 'number' as const, min: 1, message: '预算必须大于0', trigger: 'blur' }
  ],
  people_count: [
    { required: true, message: '请输入人数', trigger: 'blur' },
    { type: 'number' as const, min: 1, max: 20, message: '人数必须在1-20之间', trigger: 'blur' }
  ],
  taste: [
    { required: true, message: '请选择口味偏好', trigger: 'change' }
  ],
  activity_count: [
    { required: true, message: '请选择活动数量', trigger: 'change' },
    { type: 'number' as const, min: 1, max: 5, message: '活动数量必须在1-5之间', trigger: 'change' }
  ]
}

const error = ref<string | null>('')
const result = ref<{ result_markdown: string; coordinates: any } | null>(null)
const hasStarted = ref(false)

onMounted(async () => {
  try {
    const pref = await fetchUserPreferences()
    if (pref.sufficient && pref.preferences) {
      if (pref.preferences.taste) {
        form.value.taste = pref.preferences.taste.value as string
      }
      if (pref.preferences.budget) {
        form.value.budget = pref.preferences.budget.value
      }
      if (pref.preferences.departure) {
        form.value.departure = pref.preferences.departure.value
      }
      if (pref.preferences.people_count) {
        form.value.people_count = pref.preferences.people_count.value
      }
      ElMessage.success({ message: '已根据您的历史偏好自动填充表单', duration: 1900 })
    }
  } catch (error) {
    console.error('获取偏好失败:', error)
  }
})

const coordinates = computed(() => {
  if (!result.value) return null
  
  if (result.value.coordinates && result.value.coordinates.points && result.value.coordinates.points.length > 0) {
    return result.value.coordinates
  }
  
  if (result.value.result_markdown) {
    const parsedCoords = extractCoordinatesFromText(result.value.result_markdown)
    if (parsedCoords && parsedCoords.points.length > 0) {
      return parsedCoords
    }
  }
  
  return null
})

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await (formRef.value as any).validate()
  } catch {
    return
  }
  
  hasStarted.value = true
  
  // 重置状态 - 使用类型安全的遍历
  const stepKeys: StepKey[] = ['weather', 'activities', 'food', 'route', 'plan']
  stepKeys.forEach(k => {
    steps.value[k] = 'waiting'
  })
  error.value = ''
  result.value = null
  
  const formattedForm = {
    ...form.value,
    travel_date: form.value.travel_date ? formatDate(new Date(form.value.travel_date)) : '',
    device_id: getDeviceId(),
  }
  
  try {
    const response = await fetch('/api/v1/travel/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formattedForm),
    })
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('无法读取响应')
    
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
          currentEvent = line.slice(7).trim()
          continue
        }
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (currentEvent === 'agent_start') {
              const agent = data.agent as StepKey
              if (agent in steps.value) {
                steps.value[agent] = 'running'
              }
            } else if (currentEvent === 'agent_end') {
              const agent = data.agent as StepKey
              if (agent in steps.value) {
                steps.value[agent] = 'done'
              }
            } else if (currentEvent === 'plan') {
              steps.value.plan = 'done'
              result.value = {
                result_markdown: data.markdown,
                coordinates: data.coordinates,
              }
            } else if (currentEvent === 'error') {
              steps.value.plan = 'error'
              error.value = data.message
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  } catch (e) {
    error.value = '请求失败，请重试'
  }
  
  // 滚动到结果区域
  if (result.value) {
    await nextTick()
    if (resultContainer.value) {
      resultContainer.value.scrollIntoView({ behavior: 'smooth' })
    }
  }
}

const resetForm = () => {
  if (formRef.value) {
    ;(formRef.value as any).resetFields()
  }
  result.value = null
  error.value = ''
  hasStarted.value = false
  const stepKeys: StepKey[] = ['weather', 'activities', 'food', 'route', 'plan']
  stepKeys.forEach(k => {
    steps.value[k] = 'waiting'
  })
}

const mockTravelPlan = async () => {
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
  
  const mockResponse = {
    result_markdown: mockMarkdown,
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
  
  // 模拟进度
  const agents: StepKey[] = ['weather', 'activities', 'food', 'route', 'plan']
  for (const agent of agents) {
    steps.value[agent] = 'running'
    await new Promise(resolve => setTimeout(resolve, 300))
    steps.value[agent] = 'done'
  }
  
  result.value = mockResponse
  
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

  .plan-progress {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 16px;
    
    .progress-title {
      font-size: 16px;
      font-weight: 500;
      color: #303133;
      margin-bottom: 16px;
    }
    
    .progress-step {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 0;
      font-size: 15px;
      color: #909399;
      
      &.running {
        color: #409eff;
        font-weight: 500;
      }
      
      &.done {
        color: #67c23a;
      }
      
      &.error {
        color: #f56c6c;
      }
      
      .step-icon {
        font-size: 18px;
        width: 24px;
        text-align: center;
      }
    }
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
    
    .result-actions {
      margin-top: $spacing-lg;
      text-align: center;
    }
  }
}

@media (max-width: 768px) {
  .planner-view {
    .planner-form {
      padding: $spacing-md;
    }

    .plan-progress,
    .result-container {
      padding: $spacing-md;
    }
  }
}
</style>