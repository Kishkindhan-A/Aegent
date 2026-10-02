export type AuditEventType =
  | 'AUTH_LOGIN_SUCCESS'
  | 'AUTH_LOGOUT'
  | 'AGENT_CREATED'
  | 'AGENT_UPDATED'
  | 'AGENT_DISABLED'
  | 'RISK_EVALUATED'
  | 'POLICY_CREATED'
  | 'POLICY_UPDATED'
  | 'POLICY_DISABLED'
  | 'AUTHORIZATION_EVALUATED'
  | 'APPROVAL_REQUESTED'
  | 'APPROVAL_APPROVED'
  | 'APPROVAL_REJECTED'
  | 'APPROVAL_EXPIRED'
  | 'PROMPT_INJECTION_DETECTED'
  | 'SENSITIVE_DATA_DETECTED'
  | 'POLICY_VIOLATION'
  | 'ANOMALOUS_AGENT_BEHAVIOR'

export type AuditEventCategory = 'AUTHENTICATION' | 'AGENT' | 'RISK' | 'POLICY' | 'AUTHORIZATION' | 'APPROVAL' | 'SECURITY'
export type EventSeverity = 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL'
export type ActorType = 'USER' | 'AGENT' | 'SYSTEM'

export interface AuditEvent {
  id: string
  organization_id: string
  event_type: AuditEventType
  category: AuditEventCategory
  severity: EventSeverity
  actor_type: ActorType
  actor_user_id: string | null
  agent_id: string | null
  policy_id: string | null
  approval_request_id: string | null
  correlation_id: string | null
  request_id: string | null
  source: string
  summary: string
  details: Record<string, unknown>
  created_at: string
}

export interface AuditEventListResponse {
  items: AuditEvent[]
  total: number
  offset: number
  limit: number
}
