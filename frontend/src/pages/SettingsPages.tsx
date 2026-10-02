import { AlertTriangle, ShieldCheck } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { orgApi } from '../api/client'
import { Button, LoadingState, Notice } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import type { Organization, OrganizationMember } from '../types/organizations'

const roleOptions = ['OWNER', 'ADMIN', 'SECURITY_ANALYST', 'MEMBER'] as const
const statusOptions = ['ACTIVE', 'INVITED', 'SUSPENDED', 'DISABLED'] as const

function label(value: string) {
  return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, match => match.toUpperCase())
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function canManageOrganization(role?: string) {
  return role === 'OWNER' || role === 'ADMIN'
}

export function OrganizationSettingsPage() {
  const { user } = useAuth()
  const [organization, setOrganization] = useState<Organization | null>(null)
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const result = await orgApi.getCurrent()
        setOrganization(result)
        setName(result.name)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load organization settings.')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!user || !canManageOrganization(user.role) || !organization) return
    setSaving(true)
    setError('')
    try {
      const updated = await orgApi.updateCurrent({ name })
      setOrganization(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update the organization name.')
    } finally {
      setSaving(false)
    }
  }

  if (!user) {
    return <div className="center-state"><ShieldCheck size={22} /><h1>Access restricted</h1><p>You must be signed in to view tenant settings.</p><Link to="/login"><Button>Sign in</Button></Link></div>
  }

  if (loading) return <LoadingState label="Loading organization settings" />

  return <div className="page-stack"><div className="page-heading"><div><p className="eyebrow">Organization settings</p><h1>Tenant security settings</h1><p className="page-description">Manage the core tenant identity and the member roster for this workspace.</p></div></div>
    <section className="surface-card form-panel">
      <div className="section-heading"><div><p className="card-kicker">Identity</p><h2>{organization?.name || 'Organization'}</h2></div></div>
      <form onSubmit={submit} className="form-grid">
        <div className="field"><label htmlFor="organization-name">Organization name</label><input id="organization-name" value={name} onChange={(event: ChangeEvent<HTMLInputElement>) => setName(event.target.value)} disabled={!canManageOrganization(user.role)} /></div>
        <div className="field"><label>Tenant handle</label><div className="read-only-value">{organization?.slug || ''}</div></div>
        <div className="field"><label htmlFor="organization-status">Status</label><input id="organization-status" value={organization?.status || 'ACTIVE'} readOnly /></div>
        {error && <Notice tone="error">{error}</Notice>}
        {canManageOrganization(user.role) && <div className="form-actions"><Button type="submit" loading={saving}>Save changes</Button></div>}
      </form>
    </section>
  </div>
}

export function MemberDirectoryPage() {
  const { user } = useAuth()
  const [members, setMembers] = useState<OrganizationMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function reload() {
    setLoading(true)
    setError('')
    try {
      const result = await orgApi.listMembers({ limit: 50 })
      setMembers(result.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load members.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void reload() }, [])

  if (!user || !canManageOrganization(user.role)) {
    return <div className="center-state"><AlertTriangle size={22} /><h1>Access restricted</h1><p>Your role does not include member administration access.</p><Link to="/"><Button>Back to overview</Button></Link></div>
  }

  async function updateRole(memberId: string, role: string) {
    try {
      await orgApi.updateMemberRole(memberId, { role })
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update the member role.')
    }
  }

  async function updateStatus(memberId: string, status: string) {
    try {
      await orgApi.updateMemberStatus(memberId, { status })
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update the member status.')
    }
  }

  return <div className="page-stack"><div className="page-heading"><div><p className="eyebrow">Member directory</p><h1>Tenant member roster</h1><p className="page-description">Review current access, elevate trusted users, and manage account status within this tenant.</p></div></div>
    <section className="surface-card inventory-section">
      <div className="section-heading"><div><p className="card-kicker">Members</p><h2>{members.length} account{members.length === 1 ? '' : 's'}</h2></div></div>
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading members" /> : <div className="table-wrap"><table className="audit-table"><thead><tr><th>Member</th><th>Email</th><th>Role</th><th>Status</th><th>Last updated</th></tr></thead><tbody>{members.map(member => <tr key={member.id}><td>{member.full_name || 'Unnamed member'}</td><td>{member.email}</td><td><select value={member.role} onChange={event => void updateRole(member.id, event.target.value)} disabled={member.id === user.id || member.role === 'OWNER'}>{roleOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></td><td><select value={member.status} onChange={event => void updateStatus(member.id, event.target.value)} disabled={member.id === user.id || member.role === 'OWNER'}>{statusOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></td><td>{formatDate(member.updated_at)}</td></tr>)}</tbody></table></div>}
    </section>
  </div>
}
