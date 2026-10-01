import type { ActionType, AgentRiskLevel, AgentType, DataSensitivity, Environment, PrivilegeLevel } from './agents'

export type PolicyEffect = 'ALLOW' | 'DENY' | 'REQUIRE_APPROVAL'

export interface PolicyConditions {
  agent_id?: string
  agent_type?: AgentType
  action_type?: ActionType
  environment?: Environment
  data_sensitivity?: DataSensitivity
  privilege_level?: PrivilegeLevel
  minimum_risk_score?: number
  minimum_risk_level?: AgentRiskLevel
  external_network_access?: boolean
  destructive_capability?: boolean
  credential_access?: boolean
  financial_impact?: boolean
}

export interface Policy {
  id: string
  organization_id: string
  name: string
  description: string | null
  effect: PolicyEffect
  enabled: boolean
  priority: number
  conditions: PolicyConditions
  created_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface PolicyCreateInput {
  name: string
  description?: string | null
  effect: PolicyEffect
  enabled?: boolean
  priority: number
  conditions: PolicyConditions
}

export interface PolicyUpdateInput {
  name?: string
  description?: string | null
  effect?: PolicyEffect
  enabled?: boolean
  priority?: number
  conditions?: PolicyConditions
}

export interface PolicyListResponse {
  items: Policy[]
  total: number
  offset: number
  limit: number
}
