export type UserRole = 'OWNER' | 'ADMIN' | 'SECURITY_ANALYST' | 'MEMBER'
export type UserStatus = 'ACTIVE' | 'DISABLED' | 'SUSPENDED'

export interface CurrentUser {
  id: string
  organization_id: string
  email: string
  full_name: string | null
  role: UserRole
  status: UserStatus
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: CurrentUser
}

export interface ApiError extends Error {
  status: number
  details?: unknown
}