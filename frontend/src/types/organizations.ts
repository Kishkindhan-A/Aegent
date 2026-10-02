export type OrganizationStatus = 'ACTIVE' | 'SUSPENDED' | 'DISABLED'
export type OrganizationRole = 'OWNER' | 'ADMIN' | 'SECURITY_ANALYST' | 'MEMBER'
export type OrganizationUserStatus = 'ACTIVE' | 'INVITED' | 'SUSPENDED' | 'DISABLED'

export interface Organization {
  id: string
  name: string
  slug: string
  status: OrganizationStatus
  created_at: string
  updated_at: string
}

export interface OrganizationMember {
  id: string
  email: string
  full_name: string | null
  role: OrganizationRole
  status: OrganizationUserStatus
  created_at: string
  updated_at: string
}

export interface OrganizationMembersResponse {
  items: OrganizationMember[]
  total: number
  offset: number
  limit: number
}
