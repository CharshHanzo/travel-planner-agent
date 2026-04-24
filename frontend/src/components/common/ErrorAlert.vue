<template>
  <div v-if="message" class="error-alert" :class="type">
    <div class="alert-content">
      <el-icon class="alert-icon">
        <component :is="iconComponent" />
      </el-icon>
      <span class="alert-message">{{ message }}</span>
      <el-icon class="close-icon" @click="onClose"><Close /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Close, CircleClose, Warning, InfoFilled, SuccessFilled } from '@element-plus/icons-vue'

const props = defineProps({
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'error',
    validator: (value: string) => ['error', 'warning', 'info', 'success'].includes(value)
  }
})

const emit = defineEmits(['close'])

const iconComponent = {
  error: CircleClose,
  warning: Warning,
  info: InfoFilled,
  success: SuccessFilled
}[props.type]

const onClose = () => {
  emit('close')
}
</script>

<style lang="scss">
.error-alert {
  margin-bottom: $spacing-md;
  border-radius: $border-radius;
  transition: all 0.3s ease;

  &.error {
    .alert-content {
      background-color: rgba($danger-color, 0.1);
      border-left: 4px solid $danger-color;

      .alert-icon {
        color: $danger-color;
      }
    }
  }

  &.warning {
    .alert-content {
      background-color: rgba($warning-color, 0.1);
      border-left: 4px solid $warning-color;

      .alert-icon {
        color: $warning-color;
      }
    }
  }

  &.info {
    .alert-content {
      background-color: rgba($info-color, 0.1);
      border-left: 4px solid $info-color;

      .alert-icon {
        color: $info-color;
      }
    }
  }

  &.success {
    .alert-content {
      background-color: rgba($success-color, 0.1);
      border-left: 4px solid $success-color;

      .alert-icon {
        color: $success-color;
      }
    }
  }

  .alert-content {
    display: flex;
    align-items: center;
    padding: $spacing-sm $spacing-md;

    .alert-icon {
      margin-right: $spacing-sm;
    }

    .alert-message {
      flex: 1;
      color: #606266;
    }

    .close-icon {
      color: $info-color;
      cursor: pointer;
      font-size: $font-size-lg;

      &:hover {
        color: #606266;
      }
    }
  }
}
</style>