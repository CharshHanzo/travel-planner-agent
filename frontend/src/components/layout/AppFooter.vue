<template>
  <footer class="app-footer">
    <div class="footer-content">
      <div class="footer-info">
        <p>© 2026 Travel Agent. All rights reserved.</p>
        <p>智能旅行规划助手，为您定制完美的旅行体验</p>
      </div>
      <div class="footer-links">
        <a href="#" class="footer-link">关于我们</a>
        <a href="#" class="footer-link">隐私政策</a>
        <a href="#" class="footer-link">使用条款</a>
        <a href="#" class="footer-link">联系我们</a>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
</script>

<style lang="scss">
.app-footer {
  background-color: white;
  border-top: 1px solid $border-color;
  padding: $spacing-lg 0;

  .footer-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 $spacing-lg;

    .footer-info {
      text-align: center;
      margin-bottom: $spacing-md;

      p {
        margin: $spacing-xs 0;
        font-size: $font-size-sm;
        color: $info-color;
      }
    }

    .footer-links {
      display: flex;
      gap: $spacing-lg;

      .footer-link {
        color: #606266;
        font-size: $font-size-sm;
        text-decoration: none;
        transition: color 0.3s ease;

        &:hover {
          color: $primary-color;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .app-footer {
    .footer-content {
      .footer-links {
        flex-wrap: wrap;
        justify-content: center;
        gap: $spacing-md;
      }
    }
  }
}
</style>