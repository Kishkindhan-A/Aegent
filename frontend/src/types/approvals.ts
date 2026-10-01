import type { AgentRiskLevel } from './agents'

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED'

export interface ApprovalRequest {
  id: string
  organization_id: string
  agent_id: string
  requested_by_user_id: string | null
  policy_id: string | null
  status: ApprovalStatus
  risk_score: number
  risk_level: AgentRiskLevel
  request_fingerprint: string
  normalized_action_snapshot: Record<string, unknown>
  created_at: string
  expires_at: string
  resolved_at: string | null
  resolved_by_user_id: string | null
  resolution_reason: string | null
}

export interface ApprovalListResponse {
  items: ApprovalRequest[]
  total: number
  offset: number
  limit: number
}

export interface ApprovalResolutionRequest {
  resolution_reason?: string
}
