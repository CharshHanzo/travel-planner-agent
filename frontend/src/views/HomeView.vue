<template>
  <div class="home-view">
    <div class="hero-section">
      <div class="hero-content">
        <h1>智能旅行规划助手</h1>
        <p>为您定制完美的旅行体验，让每一次出行都充满惊喜</p>
        <router-link to="/planner" class="btn btn-primary">开始规划</router-link>
      </div>
    </div>
    <div class="features-section">
      <h2>核心功能</h2>
      <div class="features-grid">
        <div class="feature-card">
          <el-icon class="feature-icon"><Calendar /></el-icon>
          <h3>智能规划</h3>
          <p>基于您的偏好和预算，生成个性化的旅行计划，包括景点、餐厅和活动推荐</p>
        </div>
        <div class="feature-card">
          <el-icon class="feature-icon"><Sunny /></el-icon>
          <h3>天气预测</h3>
          <p>实时获取目的地天气信息，帮助您更好地安排行程</p>
        </div>
        <div class="feature-card">
          <el-icon class="feature-icon"><MapLocation /></el-icon>
          <h3>行程管理</h3>
          <p>智能安排每日行程，优化路线，节省时间和精力</p>
        </div>
        <div class="feature-card">
          <el-icon class="feature-icon"><Coffee /></el-icon>
          <h3>美食推荐</h3>
          <p>根据您的口味偏好，推荐当地特色美食和餐厅</p>
        </div>
        <div class="feature-card">
          <el-icon class="feature-icon"><Clock /></el-icon>
          <h3>历史记录</h3>
          <p>查看和管理您的历史旅行计划，方便下次参考</p>
        </div>
        <div class="feature-card">
          <el-icon class="feature-icon"><Setting /></el-icon>
          <h3>个性化设置</h3>
          <p>根据您的需求，调整规划偏好和设置</p>
        </div>
      </div>
    </div>
    <div class="cta-section">
      <div class="cta-content">
        <h2>准备好开始您的旅行了吗？</h2>
        <p>让我们为您打造一次难忘的旅行体验</p>
        <router-link to="/planner" class="btn btn-primary">立即开始</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Calendar, Sunny, MapLocation, Coffee, Clock, Setting } from '@element-plus/icons-vue'
</script>

<style lang="scss">
.home-view {
  .hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: $spacing-xl * 2 0;
    text-align: center;

    .hero-content {
      max-width: 800px;
      margin: 0 auto;
      padding: 0 $spacing-lg;

      h1 {
        font-size: 48px;
        margin-bottom: $spacing-md;
        font-weight: 600;
      }

      p {
        font-size: 20px;
        margin-bottom: $spacing-xl;
        opacity: 0.9;
      }

      .btn {
        font-size: 18px;
        padding: $spacing-md $spacing-xl;
        border-radius: $border-radius;
        background-color: white;
        color: #667eea;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.3s ease;

        &:hover {
          background-color: rgba(255, 255, 255, 0.9);
          transform: translateY(-2px);
        }
      }
    }
  }

  .features-section {
    padding: $spacing-xl 0;
    background-color: white;

    h2 {
      text-align: center;
      font-size: 32px;
      margin-bottom: $spacing-xl;
      color: #303133;
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: $spacing-lg;
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 $spacing-lg;

      .feature-card {
        padding: $spacing-lg;
        background-color: #f5f7fa;
        border-radius: $border-radius;
        box-shadow: $box-shadow-light;
        text-align: center;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-5px);
          box-shadow: $box-shadow;
        }

        .feature-icon {
          font-size: 48px;
          color: $primary-color;
          margin-bottom: $spacing-md;
        }

        h3 {
          font-size: 18px;
          margin-bottom: $spacing-sm;
          color: #303133;
        }

        p {
          color: #606266;
          line-height: 1.6;
        }
      }
    }
  }

  .cta-section {
    background-color: #f5f7fa;
    padding: $spacing-xl 0;
    text-align: center;

    .cta-content {
      max-width: 600px;
      margin: 0 auto;
      padding: 0 $spacing-lg;

      h2 {
        font-size: 32px;
        margin-bottom: $spacing-md;
        color: #303133;
      }

      p {
        font-size: 18px;
        margin-bottom: $spacing-lg;
        color: #606266;
      }

      .btn {
        font-size: 16px;
        padding: $spacing-md $spacing-xl;
        border-radius: $border-radius;
        background-color: $primary-color;
        color: white;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.3s ease;

        &:hover {
          background-color: darken($primary-color, 10%);
          transform: translateY(-2px);
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .home-view {
    .hero-section {
      padding: $spacing-xl 0;

      .hero-content {
        h1 {
          font-size: 36px;
        }

        p {
          font-size: 18px;
        }
      }
    }

    .features-section {
      h2 {
        font-size: 24px;
      }
    }

    .cta-section {
      .cta-content {
        h2 {
          font-size: 24px;
        }

        p {
          font-size: 16px;
        }
      }
    }
  }
}
</style>