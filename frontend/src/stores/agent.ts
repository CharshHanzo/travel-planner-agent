import { defineStore } from 'pinia'
import { AgentStatusEvent } from '../types/agent'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    visitedAgents: new Set<string>(),
    currentAgent: null as string | null,
    statusEvents: [] as AgentStatusEvent[]
  }),
  actions: {
    addVisitedAgent(agentName: string) {
      this.visitedAgents.add(agentName)
    },
    setCurrentAgent(agentName: string | null) {
      this.currentAgent = agentName
    },
    addStatusEvent(event: AgentStatusEvent) {
      this.statusEvents.push(event)
    },
    reset() {
      this.visitedAgents.clear()
      this.currentAgent = null
      this.statusEvents = []
    }
  }
})