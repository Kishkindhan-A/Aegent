import type { ApiError, TokenResponse } from '../types/auth'
import type { Agent, AgentCreateInput, AgentListResponse, AgentUpdateInput, RiskAssessment, RiskEvaluationInput, SecurityScanInput, SecurityScanResult } from '../types/agents'
import type { ApprovalListResponse, ApprovalRequest, ApprovalResolutionRequest } from '../types/approvals'
import type { AuditEvent, AuditEventListResponse } from '../types/audit'
import type { Policy, PolicyCreateInput, PolicyListResponse, PolicyUpdateInput } from '../types/policies'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
let accessToken: string | null = null
let refreshPromise: Promise<TokenResponse | null> | null = null

export const sessionStore = {
  getRefreshToken: () => sessionStorage.getItem('aegent.refresh_token'),
  setRefreshToken: (token: string) => sessionStorage.setItem('aegent.refresh_token', token),
  clear: () => {
    accessToken = null
    sessionStorage.removeItem('aegent.refresh_token')
  },
}

export function setAccessToken(token: string | null) {
  accessToken = token
}

function messageForStatus(status: number) {
  if (status === 401) return 'Your session is no longer valid. Please sign in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested resource is unavailable.'
  if (status === 422) return 'Please check the highlighted fields and try again.'
  if (status >= 500) return 'Aegent is temporarily unavailable. Please try again.'
  return 'The request could not be completed.'
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok) {
    const error = new Error(typeof body?.detail === 'string' ? body.detail : messageForStatus(response.status)) as ApiError
    error.status = response.status
    error.details = body?.detail
    throw error
  }
  return body
}

async function refreshSession() {
  const refreshToken = sessionStore.getRefreshToken()
  if (!refreshToken) return null
  if (!refreshPromise) {
    refreshPromise = fetch(`${baseUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(parseResponse)
      .then((tokens: TokenResponse) => {
        setAccessToken(tokens.access_token)
        sessionStore.setRefreshToken(tokens.refresh_token)
        return tokens
      })
      .catch(() => {
        sessionStore.clear()
        window.dispatchEvent(new Event('aegent:session-expired'))
        return null
      })
      .finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

export async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, { ...options, headers })
  } catch {
    const error = new Error('Unable to reach Aegent. Check the backend connection and try again.') as ApiError
    error.status = 0
    throw error
  }
  if (response.status === 401 && retry && !path.includes('/auth/')) {
    const refreshed = await refreshSession()
    if (refreshed) return request<T>(path, options, false)
  }
  return parseResponse(response)
}

export const authApi = {
  login: (payload: { email: string; password: string; organization_slug: string }) => request<TokenResponse>('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload: { organization_name: string; organization_slug: string; owner_email: string; owner_full_name: string; password: string }) => request<TokenResponse>('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => request<import('../types/auth').CurrentUser>('/api/v1/auth/me'),
  restore: async () => {
    const tokens = await refreshSession()
    if (!tokens) return null
    try {
      return await authApi.me()
    } catch (error) {
      sessionStore.clear()
      window.dispatchEvent(new Event('aegent:session-expired'))
      throw error
    }
  },
  logout: async () => {
    const token = sessionStore.getRefreshToken()
    try {
      if (token) await request('/api/v1/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: token }) }, false)
    } finally {
      sessionStore.clear()
    }
  },
}

export const agentsApi = {
  list: (params: { offset?: number; limit?: number; status?: string; agent_type?: string; risk_level?: string } = {}) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => { if (value) query.set(key, String(value)) })
    return request<AgentListResponse>(`/api/v1/agents${query.size ? `?${query}` : ''}`)
  },
  get: (agentId: string) => request<Agent>(`/api/v1/agents/${agentId}`),
  create: (payload: AgentCreateInput) => request<Agent>('/api/v1/agents', { method: 'POST', body: JSON.stringify(payload) }),
  update: (agentId: string, payload: AgentUpdateInput) => request<Agent>(`/api/v1/agents/${agentId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  disable: (agentId: string) => request<Agent>(`/api/v1/agents/${agentId}/disable`, { method: 'POST' }),
  evaluateRisk: (agentId: string, payload: RiskEvaluationInput) => request<RiskAssessment>(`/api/v1/agents/${agentId}/risk/evaluate`, { method: 'POST', body: JSON.stringify(payload) }),
  scan: (agentId: string, payload: SecurityScanInput) => request<SecurityScanResult>(`/api/v1/agents/${agentId}/security/scan`, { method: 'POST', body: JSON.stringify(payload) }),
}

export const policiesApi = {
  list: (params: { offset?: number; limit?: number; enabled?: boolean } = {}) => {
    const query = new URLSearchParams()
    if (params.offset !== undefined) query.set('offset', String(params.offset))
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    if (params.enabled !== undefined) query.set('enabled', String(params.enabled))
    return request<PolicyListResponse>(`/api/v1/policies${query.size ? `?${query}` : ''}`)
  },
  get: (policyId: string) => request<Policy>(`/api/v1/policies/${policyId}`),
  create: (payload: PolicyCreateInput) => request<Policy>('/api/v1/policies', { method: 'POST', body: JSON.stringify(payload) }),
  update: (policyId: string, payload: PolicyUpdateInput) => request<Policy>(`/api/v1/policies/${policyId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  disable: (policyId: string) => request<Policy>(`/api/v1/policies/${policyId}/disable`, { method: 'POST' }),
}

export const approvalsApi = {
  list: (params: { offset?: number; limit?: number; status?: string } = {}) => {
    const query = new URLSearchParams()
    if (params.offset !== undefined) query.set('offset', String(params.offset))
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    if (params.status) query.set('status', params.status)
    return request<ApprovalListResponse>(`/api/v1/approvals${query.size ? `?${query}` : ''}`)
  },
  get: (approvalId: string) => request<ApprovalRequest>(`/api/v1/approvals/${approvalId}`),
  approve: (approvalId: string, resolutionReason?: string) => request<ApprovalRequest>(`/api/v1/approvals/${approvalId}/approve`, { method: 'POST', body: JSON.stringify({ resolution_reason: resolutionReason || undefined }) }),
  reject: (approvalId: string, resolutionReason?: string) => request<ApprovalRequest>(`/api/v1/approvals/${approvalId}/reject`, { method: 'POST', body: JSON.stringify({ resolution_reason: resolutionReason || undefined }) }),
}

export const auditsApi = {
  list: (params: {
    event_type?: string
    category?: string
    severity?: string
    actor_user_id?: string
    agent_id?: string
    policy_id?: string
    approval_request_id?: string
    correlation_id?: string
    created_after?: string
    created_before?: string
    offset?: number
    limit?: number
  } = {}) => {
    const query = new URLSearchParams()
    if (params.event_type) query.set('event_type', params.event_type)
    if (params.category) query.set('category', params.category)
    if (params.severity) query.set('severity', params.severity)
    if (params.actor_user_id) query.set('actor_user_id', params.actor_user_id)
    if (params.agent_id) query.set('agent_id', params.agent_id)
    if (params.policy_id) query.set('policy_id', params.policy_id)
    if (params.approval_request_id) query.set('approval_request_id', params.approval_request_id)
    if (params.correlation_id) query.set('correlation_id', params.correlation_id)
    if (params.created_after) query.set('created_after', params.created_after)
    if (params.created_before) query.set('created_before', params.created_before)
    if (params.offset !== undefined) query.set('offset', String(params.offset))
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    return request<AuditEventListResponse>(`/api/v1/audit/events${query.size ? `?${query}` : ''}`)
  },
  get: (eventId: string) => request<AuditEvent>(`/api/v1/audit/events/${eventId}`),
}