import apiService from './api'
import { TravelRequest, TravelResponse } from '../types/travel'

export const travelService = {
  // 规划旅行
  async planTravel(request: TravelRequest): Promise<TravelResponse> {
    return apiService.post<TravelResponse>('/v1/travel/plan', request)
  },

  // 获取健康状态
  async getHealth(): Promise<{ status: string }> {
    return apiService.get<{ status: string }>('/health')
  },

  // 获取旅行计划列表
  async getPlans() {
    return apiService.get('/travel/plans')
  },

  // 获取单个旅行计划
  async getPlan(id: number) {
    return apiService.get(`/travel/plans/${id}`)
  },

  // 创建旅行计划
  async createPlan(data: any) {
    return apiService.post('/travel/plans', data)
  },

  // 更新旅行计划
  async updatePlan(id: number, data: any) {
    return apiService.put(`/travel/plans/${id}`, data)
  },

  // 删除旅行计划
  async deletePlan(id: number) {
    return apiService.delete(`/travel/plans/${id}`)
  },

  // 生成旅行计划
  async generatePlan(data: any) {
    return apiService.post('/travel/generate', data)
  }
}