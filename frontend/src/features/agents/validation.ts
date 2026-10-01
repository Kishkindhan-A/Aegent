import type { UserRole } from '../../types/auth'

export const MAX_SCAN_CONTENT_LENGTH = 20000
export const AGENT_MANAGEMENT_ROLES: UserRole[] = ['OWNER', 'ADMIN', 'SECURITY_ANALYST']

export function canManageAgents(role?: UserRole) {
  return Boolean(role && AGENT_MANAGEMENT_ROLES.includes(role))
}

export function validateScanContent(content: string) {
  if (!content.trim()) return 'Content is required.'
  if (content.length > MAX_SCAN_CONTENT_LENGTH) return `Scan content must be ${MAX_SCAN_CONTENT_LENGTH.toLocaleString()} characters or fewer.`
  return ''
}