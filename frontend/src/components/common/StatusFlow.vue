<template>
  <div class="status-flow">
    <el-steps :active="activeStep" direction="vertical" :space="20">
      <el-step 
        v-for="agent in agents" 
        :key="agent.name"
        :title="agent.title"
        :description="agent.description"
        :status="getAgentStatus(agent.name)"
      >
        <template #icon>
          <div class="agent-icon" :class="getAgentStatusClass(agent.name)">
            {{ getAgentIcon(agent.name) }}
          </div>
        </template>
      </el-step>
    </el-steps>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  visitedAgents: {
    type: Set<string>,
    required: true
  },
  currentAgent: {
    type: String,
    default: null
  }
})

const agents = [
  {
    name: 'TravelSupervisor',
    title: 'TravelSupervisor',
    description: '主管正在分派任务...'
  },
  {
    name: 'WeatherAgent',
    title: 'WeatherAgent',
    description: 'WeatherAgent 正在获取天气信息...'
  },
  {
    name: 'ActivityAgent',
    title: 'ActivityAgent',
    description: 'ActivityAgent 正在搜索活动...'
  },
  {
    name: 'FoodAgent',
    title: 'FoodAgent',
    description: 'FoodAgent 正在推荐餐厅...'
  }
]

const activeStep = computed(() => {
  if (!props.currentAgent) return 0
  const index = agents.findIndex(agent => agent.name === props.currentAgent)
  return index !== -1 ? index : 0
})

const getAgentStatus = (agentName: string) => {
  if (props.currentAgent === agentName) {
    return 'process'
  } else if (props.visitedAgents.has(agentName)) {
    return 'success'
  } else {
    return 'wait'
  }
}

const getAgentStatusClass = (agentName: string) => {
  if (props.currentAgent === agentName) {
    return 'active'
  } else if (props.visitedAgents.has(agentName)) {
    return 'completed'
  } else {
    return 'waiting'
  }
}

const getAgentIcon = (agentName: string) => {
  if (props.currentAgent === agentName) {
    return '🔄'
  } else if (props.visitedAgents.has(agentName)) {
    return '✅'
  } else {
    return '⏳'
  }
}
</script>

<style lang="scss">
.status-flow {
  margin: $spacing-lg 0;

  .agent-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    transition: all 0.3s ease;

    &.waiting {
      background-color: #e4e7ed;
      color: #909399;
    }

    &.active {
      background-color: $primary-color;
      color: white;
    }

    &.completed {
      background-color: $success-color;
      color: white;
    }
  }

  :deep(.el-step__title) {
    font-size: $font-size-base;
    font-weight: 500;
  }

  :deep(.el-step__description) {
    font-size: $font-size-sm;
    color: #606266;
  }
}

@media (max-width: 768px) {
  .status-flow {
    :deep(.el-steps) {
      padding-left: 10px;
    }
  }
}
</style>