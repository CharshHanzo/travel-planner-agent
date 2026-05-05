// API 基础配置
const API_BASE = '/api/v1'

export const API_ENDPOINTS = {
  // 快速规划
  travelPlan: `${API_BASE}/travel/plan`,
  // 对话规划
  planChat: `${API_BASE}/travel/plan-chat`,
  // 健康检查
  health: `${API_BASE}/health/check`,
  // 历史记录
  historyTrips: `${API_BASE}/travel/history/trips`,
}

export default API_BASE