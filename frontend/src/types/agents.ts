export type AgentType = 'GENERAL' | 'CODING' | 'DATA' | 'SECURITY' | 'AUTOMATION' | 'CUSTOM'
export type AgentStatus = 'ACTIVE' | 'DISABLED' | 'SUSPENDED'
export type AgentRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type ActionType = 'READ' | 'WRITE' | 'DELETE' | 'EXECUTE' | 'NETWORK' | 'TRANSFER' | 'ADMIN'
export type Environment = 'DEVELOPMENT' | 'STAGING' | 'PRODUCTION'
export type DataSensitivity = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED'
export type PrivilegeLevel = 'LOW' | 'STANDARD' | 'ELEVATED' | 'ADMIN'
export type SecurityContentType = 'PROMPT' | 'TOOL_INPUT' | 'TOOL_OUTPUT' | 'RESPONSE' | 'TEXT'
export type SecuritySourceContext = 'USER_INPUT' | 'SYSTEM_CONTEXT' | 'TOOL_OUTPUT' | 'AGENT_RESPONSE' | 'OTHER'

export interface Agent { id: string; organization_id: string; name: string; description: string | null; agent_type: AgentType; status: AgentStatus; risk_level: AgentRiskLevel; created_at: string; updated_at: string }
export interface AgentListResponse { items: Agent[]; total: number; offset: number; limit: number }
export interface AgentCreateInput { name: string; description?: string; agent_type: AgentType }
export interface AgentUpdateInput { name?: string; description?: string | null; agent_type?: AgentType; status?: AgentStatus }
export interface RiskEvaluationInput { action_type: ActionType; resource_type: string; operation: string; environment: Environment; data_sensitivity: DataSensitivity; privilege_level: PrivilegeLevel; external_network_access: boolean; write_capability: boolean; destructive_capability: boolean; credential_access: boolean; financial_impact: boolean; requires_human_approval: boolean; metadata?: Record<string, unknown> }
export interface RiskFactor { factor: string; weight: number; reason: string }
export interface RiskAssessment { agent_id: string | null; action: Omit<RiskEvaluationInput, 'metadata'>; score: number; risk_level: AgentRiskLevel; factors: RiskFactor[]; evaluated_at: string }
export interface SecurityScanInput { content: string; content_type: SecurityContentType; source_context?: SecuritySourceContext }
export interface SecurityFinding { finding_type: string; category: string; rule_id: string; severity: string; reason: string; start_offset: number | null; end_offset: number | null }
export interface SecurityScanResult { prompt_injection_detected: boolean; sensitive_data_detected: boolean; finding_count: number; highest_finding_severity: string | null; findings: SecurityFinding[]; scan_version: string }