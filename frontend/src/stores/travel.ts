import { defineStore } from 'pinia'
import { TravelRequest, TravelResponse } from '../types/travel'

export const useTravelStore = defineStore('travel', {
  state: () => ({
    currentRequest: null as TravelRequest | null,
    currentResponse: null as TravelResponse | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    setRequest(request: TravelRequest) {
      this.currentRequest = request
    },
    setResponse(response: TravelResponse) {
      this.currentResponse = response
    },
    setLoading(loading: boolean) {
      this.loading = loading
    },
    setError(error: string | null) {
      this.error = error
    },
    reset() {
      this.currentRequest = null
      this.currentResponse = null
      this.loading = false
      this.error = null
    }
  }
})