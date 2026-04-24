<template>
  <div v-if="visible" class="loading-spinner" :class="{ 'fullscreen': fullscreen }">
    <div class="spinner-container">
      <div class="spinner"></div>
      <span v-if="tip" class="loading-text">{{ tip }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  tip: {
    type: String,
    default: ''
  },
  fullscreen: {
    type: Boolean,
    default: false
  }
})
</script>

<style lang="scss">
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-lg;

  &.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    z-index: 9999;
  }

  .spinner-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: white;
    padding: $spacing-lg;
    border-radius: $border-radius;
    box-shadow: $box-shadow;

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid rgba($primary-color, 0.2);
      border-radius: 50%;
      border-top-color: $primary-color;
      animation: spin 1s ease-in-out infinite;
    }

    .loading-text {
      margin-top: $spacing-md;
      color: $info-color;
      font-size: $font-size-base;
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>