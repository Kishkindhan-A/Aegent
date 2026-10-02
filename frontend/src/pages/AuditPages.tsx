import { AlertTriangle, ArrowRight, ChevronLeft, ChevronRight, Clock3, Copy, FileText, ShieldAlert, ShieldCheck, X } from 'lucide-react'
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { auditsApi } from '../api/client'
import { Button, LoadingState, Notice } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import type { AuditEvent, AuditEventCategory, AuditEventType, EventSeverity } from '../types/audit'

const pageSize = 10

const eventTypeOptions: AuditEventType[] = [
  'AUTH_LOGIN_SUCCESS',
  'AUTH_LOGOUT',
  'AGENT_CREATED',
  'AGENT_UPDATED',
  'AGENT_DISABLED',
  'RISK_EVALUATED',
  'POLICY_CREATED',
  'POLICY_UPDATED',
  'POLICY_DISABLED',
  'AUTHORIZATION_EVALUATED',
  'APPROVAL_REQUESTED',
  'APPROVAL_APPROVED',
  'APPROVAL_REJECTED',
  'APPROVAL_EXPIRED',
  'PROMPT_INJECTION_DETECTED',
  'SENSITIVE_DATA_DETECTED',
  'POLICY_VIOLATION',
  'ANOMALOUS_AGENT_BEHAVIOR',
]

const categoryOptions: AuditEventCategory[] = ['AUTHENTICATION', 'AGENT', 'RISK', 'POLICY', 'AUTHORIZATION', 'APPROVAL', 'SECURITY']
const severityOptions: EventSeverity[] = ['INFO', 'WARNING', 'HIGH', 'CRITICAL']

type AuditFilterState = {
  event_type: string
  category: string
  severity: string
  agent_id: string
  correlation_id: string
  created_after: string
  created_before: string
}

const defaultFilters: AuditFilterState = {
  event_type: '',
  category: '',
  severity: '',
  agent_id: '',
  correlation_id: '',
  created_after: '',
  created_before: '',
}

export function canAccessAudit(role?: string) {
  return role === 'OWNER' || role === 'ADMIN' || role === 'SECURITY_ANALYST'
}

function label(value: string | null | undefined) {
  if (!value) return '—'
  return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, match => match.toUpperCase())
}

function formatDate(value: string) {
  if (!value) return '—'
  const timestamp = new Date(value)
  if (Number.isNaN(timestamp.getTime())) return value
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(timestamp)
}

function shortId(value: string | null | undefined, length = 8) {
  if (!value) return '—'
  return value.length > length ? `${value.slice(0, length)}…` : value
}

function isSecurityEvent(type: string | undefined | null) {
  return type === 'PROMPT_INJECTION_DETECTED' || type === 'SENSITIVE_DATA_DETECTED'
}

function detailsHasMeaningfulContent(details: Record<string, unknown> | undefined) {
  if (!details) return false
  return Object.keys(details).length > 0
}

function renderNestedDetails(value: unknown, depth = 0): ReactNode {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return <span>{String(value)}</span>
  if (Array.isArray(value)) return <ul className="detail-list detail-list-nested">{value.map((item, index) => <li key={`${depth}-${index}`}>{renderNestedDetails(item, depth + 1)}</li>)}</ul>
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return '—'
    return <dl className="detail-list detail-list-nested">{entries.map(([key, nestedValue]) => <div className="detail-item" key={`${depth}-${key}`}><dt>{label(key)}</dt><dd>{renderNestedDetails(nestedValue, depth + 1)}</dd></div>)}</dl>
  }
  return String(value)
}

function serializeFilters(filters: AuditFilterState) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value)
  })
  return params
}

function parseFilters(searchParams: URLSearchParams): AuditFilterState {
  return {
    event_type: searchParams.get('event_type') || '',
    category: searchParams.get('category') || '',
    severity: searchParams.get('severity') || '',
    agent_id: searchParams.get('agent_id') || '',
    correlation_id: searchParams.get('correlation_id') || '',
    created_after: searchParams.get('created_after') || '',
    created_before: searchParams.get('created_before') || '',
  }
}

export function AuditPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState<AuditFilterState>(() => parseFilters(searchParams))
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState('')

  if (!user || !canAccessAudit(user.role)) {
    return <div className="center-state"><ShieldAlert size={22} /><h1>Access restricted</h1><p>Your role does not include audit investigation access.</p><Link to="/"><Button>Back to overview</Button></Link></div>
  }

  const hasActiveFilters = useMemo(() => Object.values(filters).some(Boolean), [filters])

  async function load(nextOffset = 0, nextFilters = filters) {
    if (nextFilters.created_after && nextFilters.created_before && new Date(nextFilters.created_after) > new Date(nextFilters.created_before)) {
      setError('created_after must be before created_before.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    try {
      const result = await auditsApi.list({
        event_type: nextFilters.event_type || undefined,
        category: nextFilters.category || undefined,
        severity: nextFilters.severity || undefined,
        agent_id: nextFilters.agent_id || undefined,
        correlation_id: nextFilters.correlation_id || undefined,
        created_after: nextFilters.created_after || undefined,
        created_before: nextFilters.created_before || undefined,
        offset: nextOffset,
        limit: pageSize,
      })
      setEvents(result.items)
      setTotal(result.total)
      setOffset(result.offset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load the audit trail.')
      setEvents([])
      setTotal(0)
      setOffset(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const nextFilters = parseFilters(searchParams)
    setFilters(nextFilters)
    void load(0, nextFilters)
  }, [searchParams])

  function submitFilters(event: FormEvent) {
    event.preventDefault()
    setSearchParams(serializeFilters(filters))
    void load(0, filters)
  }

  function resetFilters() {
    setFilters(defaultFilters)
    setSearchParams(new URLSearchParams())
    void load(0, defaultFilters)
  }

  function onFilterChange(key: keyof AuditFilterState, value: string) {
    setFilters(current => ({ ...current, [key]: value }))
  }

  const page = Math.max(1, Math.floor(offset / pageSize) + 1)
  const pages = Math.max(1, Math.ceil(total / pageSize))

  return <div className="audit-page"><div className="page-heading"><div><p className="eyebrow">Audit trail</p><h1>Investigation workspace</h1><p className="page-description">Immutable tenant events, security findings, and authorization lifecycle records.</p></div>{Boolean(user && !canAccessAudit(user.role)) && <span className="status-badge status-badge-info"><ShieldAlert size={14} />Read only</span>}</div>
    <section className="surface-card audit-toolbar"><form onSubmit={submitFilters} className="filter-bar" aria-label="Audit filters"><div className="field"><label htmlFor="audit-event-type">Event type</label><select id="audit-event-type" value={filters.event_type} onChange={event => onFilterChange('event_type', event.target.value)}><option value="">All event types</option>{eventTypeOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div><div className="field"><label htmlFor="audit-category">Category</label><select id="audit-category" value={filters.category} onChange={event => onFilterChange('category', event.target.value)}><option value="">All categories</option>{categoryOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div><div className="field"><label htmlFor="audit-severity">Severity</label><select id="audit-severity" value={filters.severity} onChange={event => onFilterChange('severity', event.target.value)}><option value="">All severities</option>{severityOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div><div className="field"><label htmlFor="audit-agent-id">Agent</label><input id="audit-agent-id" type="text" value={filters.agent_id} onChange={event => onFilterChange('agent_id', event.target.value)} placeholder="UUID or ID" /></div><div className="field"><label htmlFor="audit-correlation-id">Correlation ID</label><input id="audit-correlation-id" type="text" value={filters.correlation_id} onChange={event => onFilterChange('correlation_id', event.target.value)} placeholder="correlation" /></div><div className="field"><label htmlFor="audit-created-after">Created after</label><input id="audit-created-after" type="datetime-local" value={filters.created_after} onChange={event => onFilterChange('created_after', event.target.value)} /></div><div className="field"><label htmlFor="audit-created-before">Created before</label><input id="audit-created-before" type="datetime-local" value={filters.created_before} onChange={event => onFilterChange('created_before', event.target.value)} /></div><div className="filter-actions"><Button type="submit" variant="primary">Apply</Button><Button type="button" variant="secondary" onClick={resetFilters}>Reset</Button></div></form>{error && <Notice tone="error">{error}</Notice>}</section>
    <section className="inventory-section"><div className="section-heading"><div><p className="card-kicker">Events</p><h2>{total} record{total === 1 ? '' : 's'} found</h2></div>{!loading && <button className="icon-button" aria-label="Refresh audit trail" type="button" onClick={() => void load(0, filters)}><ArrowRight size={17} /></button>}</div>
      {loading ? <LoadingState label="Loading audit events" /> : events.length === 0 ? <div className="empty-state"><FileText size={28} /><h2>{hasActiveFilters ? 'No events match these filters.' : 'No audit events found.'}</h2><p>{hasActiveFilters ? 'Adjust the filters or clear them to inspect the broader tenant history.' : 'The organization does not currently have any audit records available.'}</p>{hasActiveFilters && <Button type="button" variant="secondary" onClick={resetFilters}>Clear filters</Button>}</div> : <div className="table-wrap"><table className="audit-table"><thead><tr><th>Timestamp</th><th>Event type</th><th>Severity</th><th>Actor</th><th>Summary</th><th>Correlation</th></tr></thead><tbody>{events.map(event => <tr key={event.id}><td><Link to={`/audit/${event.id}`}>{formatDate(event.created_at)}</Link></td><td><span className={`semantic-badge ${isSecurityEvent(event.event_type) ? 'severity-critical' : 'status-active'}`}><span aria-hidden="true" className="badge-mark">{isSecurityEvent(event.event_type) ? 'S' : 'E'}</span>{label(event.event_type)}</span></td><td><span className={`semantic-badge severity-${event.severity.toLowerCase()}`}>{event.severity}</span></td><td>{event.actor_type} / {event.actor_user_id ? shortId(event.actor_user_id) : 'system'}</td><td><Link to={`/audit/${event.id}`} className="audit-summary-link">{event.summary}</Link></td><td>{event.correlation_id ? <Link to={`/audit?correlation_id=${encodeURIComponent(event.correlation_id)}`}>{shortId(event.correlation_id, 12)}</Link> : '—'}</td></tr>)}</tbody></table></div>}
      {!loading && total > 0 && <div className="pagination"><div><Button type="button" variant="secondary" disabled={offset === 0} onClick={() => void load(Math.max(0, offset - pageSize), filters)}><ChevronLeft size={15} />Previous</Button><Button type="button" variant="secondary" disabled={offset + pageSize >= total} onClick={() => void load(offset + pageSize, filters)}>Next<ChevronRight size={15} /></Button></div><span>Page {page} of {pages}</span></div>}
    </section>
  </div>
}

export function AuditDetailPage() {
  const { user } = useAuth()
  const { eventId } = useParams()
  const navigate = useNavigate()
  const [event, setEvent] = useState<AuditEvent | null>(null)
  const [related, setRelated] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  if (!user || !canAccessAudit(user.role)) {
    return <div className="center-state"><ShieldAlert size={22} /><h1>Access restricted</h1><p>Your role does not include audit investigation access.</p><Link to="/"><Button>Back to overview</Button></Link></div>
  }

  async function loadDetail() {
    if (!eventId) return
    setLoading(true)
    setError('')
    try {
      const result = await auditsApi.get(eventId)
      setEvent(result)
      if (result.correlation_id) {
        const relatedResult = await auditsApi.list({ correlation_id: result.correlation_id, limit: 50 })
        const ordered = [...relatedResult.items].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime())
        setRelated(ordered)
      } else {
        setRelated([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load this audit event.')
      setEvent(null)
      setRelated([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDetail()
  }, [eventId])

  if (loading) return <LoadingState label="Loading audit event" />
  if (error && !event) return <div className="center-state"><AlertTriangle size={22} /><h1>Unable to load this event</h1><p>{error}</p><Link to="/audit"><Button>Back to audit trail</Button></Link></div>
  if (!event) return <div className="center-state"><AlertTriangle size={22} /><h1>Event not found</h1><p>The requested audit record is unavailable in this tenant.</p><Link to="/audit"><Button>Back to audit trail</Button></Link></div>

  const relatedTimeline = related.filter(item => item.id !== event.id)

  return <div className="audit-detail"><div className="page-heading"><div><Link className="back-link" to="/audit"><ChevronLeft size={16} />Audit trail</Link><p className="eyebrow">Event detail</p><h1>{shortId(event.id)}</h1></div><Button type="button" variant="secondary" onClick={() => navigate('/audit')}>Back to list</Button></div>
    <div className="audit-summary-grid"><div className="surface-card"><p className="card-kicker">Timestamp</p><strong>{formatDate(event.created_at)}</strong><small>{event.created_at}</small></div><div className="surface-card"><p className="card-kicker">Type</p><strong>{label(event.event_type)}</strong><small>{event.category}</small></div><div className="surface-card"><p className="card-kicker">Severity</p><span className={`semantic-badge severity-${event.severity.toLowerCase()}`}>{event.severity}</span></div><div className="surface-card"><p className="card-kicker">Actor</p><strong>{event.actor_type}</strong><small>{event.actor_user_id ? shortId(event.actor_user_id) : 'system'}</small></div></div>
    {error && <Notice tone="error">{error}</Notice>}
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Context</p><h2>Event record</h2></div></div><dl className="detail-list">{[
      ['Event ID', event.id],
      ['Source', event.source],
      ['Summary', event.summary],
      ['Event Type', event.event_type],
      ['Category', event.category],
      ['Severity', event.severity],
      ['Actor Type', event.actor_type],
      ['Actor User ID', event.actor_user_id || '—'],
      ['Agent ID', event.agent_id || '—'],
      ['Policy ID', event.policy_id || '—'],
      ['Approval Request ID', event.approval_request_id || '—'],
      ['Correlation ID', event.correlation_id || '—'],
      ['Request ID', event.request_id || '—'],
    ].map(([key, value]) => <div className="detail-item" key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl>{event.agent_id && <div className="detail-actions"><Link to={`/agents/${event.agent_id}`}><Button type="button" variant="secondary">View agent</Button></Link>{event.policy_id && <Link to={`/policies/${event.policy_id}`}><Button type="button" variant="secondary">View policy</Button></Link>}{event.approval_request_id && <Link to={`/approvals/${event.approval_request_id}`}><Button type="button" variant="secondary">View approval</Button></Link>}{event.correlation_id && <Link to={`/audit?correlation_id=${encodeURIComponent(event.correlation_id)}`}><Button type="button" variant="primary">View related events</Button></Link>}</div>}</section>
    {detailsHasMeaningfulContent(event.details) && <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Structured details</p><h2>Safe event payload</h2></div></div>{renderNestedDetails(event.details)}</section>}
    {event.correlation_id && <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Investigation</p><h2>Correlation timeline</h2></div></div>{relatedTimeline.length === 0 ? <Notice tone="info">No additional tenant-visible events were recorded for this correlation ID.</Notice> : <ol className="timeline-list">{relatedTimeline.map(item => <li key={item.id} className="timeline-item"><div className="timeline-marker" aria-hidden="true" /><div className="timeline-card"><div className="timeline-meta"><span>{formatDate(item.created_at)}</span><span className={`semantic-badge severity-${item.severity.toLowerCase()}`}>{item.severity}</span></div><strong>{label(item.event_type)}</strong><p>{item.summary}</p><Link to={`/audit/${item.id}`}>Open event</Link></div></li>)}</ol>}</section>}
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Raw payload</p><h2>Sanitized JSON</h2></div></div><pre className="json-view">{JSON.stringify(event, null, 2)}</pre></section>
  </div>
}
