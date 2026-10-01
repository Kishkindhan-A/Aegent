import { AlertTriangle, Check, ChevronLeft, ChevronRight, Clock3, ShieldAlert, ShieldCheck, X } from 'lucide-react'
import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { approvalsApi } from '../api/client'
import { Button, LoadingState, Notice } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import type { ApprovalRequest, ApprovalStatus } from '../types/approvals'

const pageSize = 10
const statusOptions: Array<ApprovalStatus | ''> = ['', 'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED']

function label(value: string) {
  return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, char => char.toUpperCase())
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function ApprovalStatusBadge({ status }: { status: ApprovalStatus }) {
  return <span className={`semantic-badge ${status.toLowerCase()}`}><span aria-hidden="true" className="badge-mark">{status === 'APPROVED' ? <Check size={11} /> : status === 'REJECTED' ? <X size={11} /> : status === 'EXPIRED' ? <Clock3 size={11} /> : <ShieldAlert size={11} />}</span>{status}</span>
}

function canReviewApprovals(role?: string) {
  return role === 'OWNER' || role === 'ADMIN' || role === 'SECURITY_ANALYST'
}

export function ApprovalsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const canReview = canReviewApprovals(user?.role)
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [statusFilter, setStatusFilter] = useState<ApprovalStatus | ''>('PENDING')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load(nextOffset = offset) {
    setLoading(true)
    setError('')
    try {
      const result = await approvalsApi.list({ offset: nextOffset, limit: pageSize, status: statusFilter || undefined })
      setApprovals(result.items)
      setTotal(result.total)
      setOffset(result.offset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load approval requests.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(0)
  }, [statusFilter])

  const page = Math.max(1, Math.floor(offset / pageSize) + 1)
  const pages = Math.max(1, Math.ceil(total / pageSize))

  if (!loading && error && approvals.length === 0) {
    return <div className="center-state"><AlertTriangle size={22} /><h1>Unable to load approvals</h1><p>{error}</p></div>
  }

  return <div className="approvals-page"><div className="page-heading"><div><p className="eyebrow">Approval queue</p><h1>Approvals</h1><p className="page-description">Human review for policy-triggered approval requests.</p></div>{!canReview && <span className="status-badge status-badge-info"><ShieldAlert size={14} />Read only</span>}</div><section className="inventory-section"><div className="section-heading"><div><p className="card-kicker">Review queue</p><h2>{statusFilter === 'PENDING' ? 'Pending review' : statusFilter ? `${label(statusFilter)} requests` : 'All approval requests'}</h2></div><button className="icon-button" aria-label="Refresh approval queue" type="button" onClick={() => void load()} disabled={loading}><ShieldCheck size={17} /></button></div><div className="filter-bar" aria-label="Approval filters"><label><span>Status</span><select value={statusFilter} onChange={event => setStatusFilter(event.target.value as ApprovalStatus | '')}><option value="">All states</option>{statusOptions.filter(option => option !== '').map(option => <option key={option} value={option}>{option}</option>)}</select></label></div>{error && <Notice tone="error">{error}</Notice>}{loading ? <LoadingState label="Loading approvals" /> : approvals.length === 0 ? <div className="empty-state"><ShieldAlert size={28} /><h2>No pending approval requests</h2><p>When a policy requires human review, the request appears here until a reviewer resolves it.</p></div> : <div className="table-wrap"><table className="policy-table"><thead><tr><th>ID</th><th>Agent</th><th>Status</th><th>Risk</th><th>Policy</th><th>Requested</th><th>Expires</th></tr></thead><tbody>{approvals.map(approval => <tr key={approval.id} onClick={() => navigate(`/approvals/${approval.id}`)}><td><strong>{approval.id.slice(0, 8)}</strong></td><td>{approval.agent_id.slice(0, 8)}</td><td><ApprovalStatusBadge status={approval.status} /></td><td><span className="risk-pair"><strong>{approval.risk_score}</strong><small>{approval.risk_level}</small></span></td><td>{approval.policy_id ? approval.policy_id.slice(0, 8) : '—'}</td><td>{formatDate(approval.created_at)}</td><td>{formatDate(approval.expires_at)}</td></tr>)}</tbody></table></div>}{total > pageSize && <div className="pagination"><div><button type="button" className="icon-button" aria-label="Previous page" disabled={page <= 1} onClick={() => void load(Math.max(0, offset - pageSize))}><ChevronLeft size={18} /></button><button type="button" className="icon-button" aria-label="Next page" disabled={page >= pages} onClick={() => void load(offset + pageSize)}><ChevronRight size={18} /></button></div><span>Page {page} of {pages}</span></div>}</section></div>
}

export function ApprovalDetailPage() {
  const { approvalId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [approval, setApproval] = useState<ApprovalRequest | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmAction, setConfirmActionState] = useState<'approve' | 'reject' | null>(null)
  const [resolutionReason, setResolutionReason] = useState('')
  const reviewTriggerRef = useRef<HTMLElement | null>(null)

  function setConfirmAction(action: 'approve' | 'reject' | null) {
    if (action) reviewTriggerRef.current = document.activeElement as HTMLElement
    setConfirmActionState(action)
    if (!action) window.requestAnimationFrame(() => {
      if (reviewTriggerRef.current?.isConnected) reviewTriggerRef.current.focus()
    })
  }

  async function loadApproval() {
    if (!approvalId) return
    setLoading(true)
    setError('')
    try {
      const result = await approvalsApi.get(approvalId)
      setApproval(result)
      setConfirmAction(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load approval request.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadApproval()
  }, [approvalId])

  useEffect(() => {
    if (!confirmAction) return
    document.getElementById('resolution-reason')?.focus()
    function handleDialogKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !submitting) {
        event.preventDefault()
        setResolutionReason('')
        setConfirmAction(null)
        return
      }
      if (event.key !== 'Tab') return
      const focusable = document.querySelectorAll<HTMLElement>(
        '[role="dialog"] textarea:not(:disabled), [role="dialog"] button:not(:disabled)',
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', handleDialogKeyDown)
    return () => window.removeEventListener('keydown', handleDialogKeyDown)
  }, [confirmAction, submitting])

  async function resolve(action: 'approve' | 'reject') {
    if (!approvalId) return
    setSubmitting(true)
    try {
      const result = action === 'approve' ? await approvalsApi.approve(approvalId, resolutionReason) : await approvalsApi.reject(approvalId, resolutionReason)
      setApproval(result)
      setConfirmAction(null)
      setResolutionReason('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to complete the review.'
      setError(message)
      if (err && typeof err === 'object' && 'status' in err && (err as { status?: number }).status === 409) {
        await loadApproval()
      }
    } finally {
      setSubmitting(false)
    }
  }

  const canReview = canReviewApprovals(user?.role)
  const selfReview = Boolean(user && approval && user.id === approval.requested_by_user_id)
  const expired = Boolean(approval && new Date(approval.expires_at).getTime() <= Date.now())
  const actionable = canReview && !selfReview && approval?.status === 'PENDING' && !expired

  if (loading) return <LoadingState label="Loading approval" />
  if (error && !approval) return <div className="center-state"><AlertTriangle size={22} /><h1>Unable to load approval</h1><p>{error}</p><Link to="/approvals"><Button>Back to approvals</Button></Link></div>
  if (!approval) return null

  const snapshot = approval.normalized_action_snapshot as Record<string, unknown>

  return <div className="approval-detail"><div className="page-heading"><div><Link className="back-link" to="/approvals"><ChevronLeft size={16} />Approvals</Link><p className="eyebrow">Approval request</p><h1>{approval.id.slice(0, 8)}</h1></div>{approval.status === 'PENDING' && <Button variant="secondary" onClick={() => void loadApproval()}><ShieldCheck size={16} />Refresh</Button>}</div>
    <div className="policy-summary-grid"><div className="surface-card"><p className="card-kicker">Status</p><ApprovalStatusBadge status={approval.status} /></div><div className="surface-card"><p className="card-kicker">Risk</p><strong>{approval.risk_score}</strong><small>{approval.risk_level}</small></div><div className="surface-card"><p className="card-kicker">Decision</p><strong>{String(snapshot.policy_effect ?? '—')}</strong>{typeof snapshot.policy_name === 'string' && <small>{snapshot.policy_name}</small>}</div><div className="surface-card"><p className="card-kicker">Requested</p><strong>{formatDate(approval.created_at)}</strong></div><div className="surface-card"><p className="card-kicker">Expires</p><strong>{formatDate(approval.expires_at)}</strong></div></div>
    {selfReview && <Notice tone="info">You cannot review your own request.</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Decision context</p><h2>Request snapshot</h2></div></div><ul className="condition-list">{Object.entries(snapshot).filter(([key]) => !['policy_id', 'policy_name', 'policy_effect'].includes(key)).map(([key, value]) => <li key={key}><strong>{label(String(key))}</strong><span>{typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value ?? '—')}</span></li>)}</ul></section>
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Review controls</p><h2>Decision</h2></div></div>{approval.status === 'PENDING' ? <div className="decision-actions">{!canReview ? <Notice tone="info">Your role cannot review approvals.</Notice> : actionable ? <><Button onClick={() => setConfirmAction('approve')}><Check size={16} />Approve</Button><Button variant="secondary" onClick={() => setConfirmAction('reject')}><X size={16} />Reject</Button></> : <Notice tone="info">This request is not actionable. {selfReview ? 'You cannot review your own request.' : expired ? 'This request has expired.' : 'The approval has already been resolved.'}</Notice>}</div> : <Notice tone="info">This approval request is {approval.status.toLowerCase()} and is read-only.</Notice>}</section>
    {confirmAction && <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="review-dialog-title"><div className="confirm-dialog"><h2 id="review-dialog-title">{confirmAction === 'approve' ? 'Approve this request?' : 'Reject this request?'}</h2><p>The decision resolves the pending request in the backend. Reviewers cannot approve or reject after the backend marks it resolved or expired.</p><div className="field"><label htmlFor="resolution-reason">Reason</label><textarea id="resolution-reason" value={resolutionReason} onChange={event => setResolutionReason(event.target.value)} rows={4} placeholder="A brief rationale for this decision." /></div><div className="form-actions"><Button onClick={() => void resolve(confirmAction)} loading={submitting}>{confirmAction === 'approve' ? 'Confirm approval' : 'Confirm rejection'}</Button><Button type="button" variant="secondary" onClick={() => setConfirmAction(null)}>Cancel</Button></div></div></div>}
    <div className="back-link-wrap"><button className="button button-secondary" type="button" onClick={() => navigate('/approvals')}><ShieldAlert size={16} />Back to queue</button></div></div>
}
