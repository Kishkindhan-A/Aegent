import { AlertTriangle, Check, ChevronLeft, ChevronRight, Eye, FilePenLine, Plus, ShieldBan, ShieldCheck, ShieldX, SlidersHorizontal, X } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { policiesApi } from '../api/client'
import { Button, Field, LoadingState, Notice } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import type { ActionType, AgentRiskLevel, AgentType, DataSensitivity, Environment, PrivilegeLevel } from '../types/agents'
import type { Policy, PolicyConditions, PolicyCreateInput, PolicyEffect, PolicyUpdateInput } from '../types/policies'

const pageSize = 10
const effectOptions: PolicyEffect[] = ['ALLOW', 'DENY', 'REQUIRE_APPROVAL']
const typeOptions: AgentType[] = ['GENERAL', 'CODING', 'DATA', 'SECURITY', 'AUTOMATION', 'CUSTOM']
const actionOptions: ActionType[] = ['READ', 'WRITE', 'DELETE', 'EXECUTE', 'NETWORK', 'TRANSFER', 'ADMIN']
const environmentOptions: Environment[] = ['DEVELOPMENT', 'STAGING', 'PRODUCTION']
const sensitivityOptions: DataSensitivity[] = ['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED']
const privilegeOptions: PrivilegeLevel[] = ['LOW', 'STANDARD', 'ELEVATED', 'ADMIN']
const riskLevels: AgentRiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

function label(value: string | undefined | null) {
  if (!value) return '—'
  return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, char => char.toUpperCase())
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function canManagePolicies(role?: string) {
  return role === 'OWNER' || role === 'ADMIN'
}

export function PolicyPriorityLegend() {
  return <div className="policy-legend surface-card"><p className="card-kicker">Deterministic policy order</p><h2>Priority and effect semantics</h2><ul className="legend-list"><li><strong>Higher numeric priority</strong> is evaluated before lower priority.</li><li><strong>For equal priority:</strong> DENY &gt; REQUIRE_APPROVAL &gt; ALLOW.</li><li><strong>If no enabled policy matches</strong> an authorization request, the backend defaults to DENY.</li></ul></div>
}

export function PolicyEffectBadge({ effect, enabled: _enabled }: { effect: PolicyEffect; enabled: boolean }) {
  const variant = effect.toLowerCase()
  return <span className={`semantic-badge ${variant}`}><span aria-hidden="true" className="badge-mark">{effect === 'DENY' ? 'D' : effect === 'REQUIRE_APPROVAL' ? 'A' : 'P'}</span>{label(effect)}</span>
}

function PolicyStateBadge({ enabled }: { enabled: boolean }) {
  return <span className={`semantic-badge ${enabled ? 'status-active' : 'status-disabled'}`}><span aria-hidden="true" className="badge-mark">{enabled ? <Check size={11} /> : <X size={11} />}</span>{enabled ? 'Enabled' : 'Disabled'}</span>
}

function makeConditionSummary(conditions: PolicyConditions | undefined): string {
  if (!conditions) return 'No structured conditions were set.'
  const parts: string[] = []
  if (conditions.action_type) parts.push(`Action ${label(conditions.action_type)}`)
  if (conditions.environment) parts.push(`Environment ${label(conditions.environment)}`)
  if (conditions.data_sensitivity) parts.push(`Sensitivity ${label(conditions.data_sensitivity)}`)
  if (conditions.privilege_level) parts.push(`Privilege ${label(conditions.privilege_level)}`)
  if (conditions.minimum_risk_score !== undefined && conditions.minimum_risk_score !== null) parts.push(`Risk >= ${conditions.minimum_risk_score}`)
  if (conditions.minimum_risk_level) parts.push(`Risk level >= ${label(conditions.minimum_risk_level)}`)
  if (conditions.external_network_access !== undefined) parts.push(`External network: ${conditions.external_network_access ? 'enabled' : 'disabled'}`)
  if (conditions.destructive_capability !== undefined) parts.push(`Destructive capability: ${conditions.destructive_capability ? 'enabled' : 'disabled'}`)
  if (conditions.credential_access !== undefined) parts.push(`Credential access: ${conditions.credential_access ? 'enabled' : 'disabled'}`)
  if (conditions.financial_impact !== undefined) parts.push(`Financial impact: ${conditions.financial_impact ? 'enabled' : 'disabled'}`)
  return parts.length ? parts.join(' • ') : 'No structured conditions were set.'
}

function PolicyForm({ initial, onSubmit, onCancel, loading }: { initial?: Policy; onSubmit: (payload: PolicyCreateInput | PolicyUpdateInput) => Promise<void>; onCancel?: () => void; loading: boolean }) {
  const [name, setName] = useState(initial?.name || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [effect, setEffect] = useState<PolicyEffect>(initial?.effect || 'ALLOW')
  const [enabled, setEnabled] = useState(initial?.enabled ?? true)
  const [priority, setPriority] = useState(initial?.priority ?? 100)
  const [agentType, setAgentType] = useState<AgentType | ''>(initial?.conditions.agent_type || '')
  const [actionType, setActionType] = useState<ActionType | ''>(initial?.conditions.action_type || '')
  const [environment, setEnvironment] = useState<Environment | ''>(initial?.conditions.environment || '')
  const [dataSensitivity, setDataSensitivity] = useState<DataSensitivity | ''>(initial?.conditions.data_sensitivity || '')
  const [privilegeLevel, setPrivilegeLevel] = useState<PrivilegeLevel | ''>(initial?.conditions.privilege_level || '')
  const [minimumRiskScore, setMinimumRiskScore] = useState<number | ''>(initial?.conditions.minimum_risk_score ?? '')
  const [minimumRiskLevel, setMinimumRiskLevel] = useState<AgentRiskLevel | ''>(initial?.conditions.minimum_risk_level || '')
  const [externalNetworkAccess, setExternalNetworkAccess] = useState<boolean | undefined>(initial?.conditions.external_network_access)
  const [destructiveCapability, setDestructiveCapability] = useState<boolean | undefined>(initial?.conditions.destructive_capability)
  const [credentialAccess, setCredentialAccess] = useState<boolean | undefined>(initial?.conditions.credential_access)
  const [financialImpact, setFinancialImpact] = useState<boolean | undefined>(initial?.conditions.financial_impact)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) {
      setError('Policy name is required.')
      return
    }
    const conditions: PolicyConditions = {}
    if (agentType) conditions.agent_type = agentType
    if (actionType) conditions.action_type = actionType
    if (environment) conditions.environment = environment
    if (dataSensitivity) conditions.data_sensitivity = dataSensitivity
    if (privilegeLevel) conditions.privilege_level = privilegeLevel
    if (minimumRiskScore !== '') conditions.minimum_risk_score = Number(minimumRiskScore)
    if (minimumRiskLevel) conditions.minimum_risk_level = minimumRiskLevel
    if (externalNetworkAccess !== undefined) conditions.external_network_access = externalNetworkAccess
    if (destructiveCapability !== undefined) conditions.destructive_capability = destructiveCapability
    if (credentialAccess !== undefined) conditions.credential_access = credentialAccess
    if (financialImpact !== undefined) conditions.financial_impact = financialImpact

    const payload: PolicyCreateInput | PolicyUpdateInput = {
      name: name.trim(),
      description: description.trim() || null,
      effect,
      enabled,
      priority: Number(priority),
      conditions,
    }

    setError('')
    await onSubmit(payload)
  }

  const isUpdate = Boolean(initial)

  return <form className="policy-form" onSubmit={submit} noValidate>
    <div className="form-grid">
      <Field label="Policy name" name="policy-name" value={name} onChange={event => setName(event.target.value)} placeholder="e.g. Production write guard" />
      <div className="field"><label htmlFor="policy-effect">Effect</label><select id="policy-effect" value={effect} onChange={event => setEffect(event.target.value as PolicyEffect)}>{effectOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="policy-priority">Priority</label><input id="policy-priority" type="number" min={0} max={1000} value={priority} onChange={event => setPriority(Number(event.target.value) || 0)} /></div>
      <div className="field"><label htmlFor="policy-enabled">Enabled</label><select id="policy-enabled" value={enabled ? 'true' : 'false'} onChange={event => setEnabled(event.target.value === 'true')}><option value="true">Enabled</option><option value="false">Disabled</option></select></div>
    </div>
    <div className="field"><label htmlFor="policy-description">Description</label><textarea id="policy-description" value={description} onChange={event => setDescription(event.target.value)} rows={4} placeholder="Operational explanation for this rule." /></div>
    <div className="toggle-grid">
      <label className="toggle-field"><input type="checkbox" checked={Boolean(externalNetworkAccess)} onChange={event => setExternalNetworkAccess(event.target.checked)} /><span><strong>External network access</strong><small>Only match when requests involve external network access.</small></span></label>
      <label className="toggle-field"><input type="checkbox" checked={Boolean(destructiveCapability)} onChange={event => setDestructiveCapability(event.target.checked)} /><span><strong>Destructive capability</strong><small>Only match destructive or write-intensive actions.</small></span></label>
      <label className="toggle-field"><input type="checkbox" checked={Boolean(credentialAccess)} onChange={event => setCredentialAccess(event.target.checked)} /><span><strong>Credential access</strong><small>Only match operations involving credentials or secret access.</small></span></label>
      <label className="toggle-field"><input type="checkbox" checked={Boolean(financialImpact)} onChange={event => setFinancialImpact(event.target.checked)} /><span><strong>Financial impact</strong><small>Only match actions with monetary or payment impact.</small></span></label>
    </div>
    <div className="form-grid">
      <div className="field"><label htmlFor="condition-agent-type">Agent type</label><select id="condition-agent-type" value={agentType} onChange={event => setAgentType(event.target.value as AgentType | '')}><option value="">Any agent type</option>{typeOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="condition-action-type">Action type</label><select id="condition-action-type" value={actionType} onChange={event => setActionType(event.target.value as ActionType | '')}><option value="">Any action</option>{actionOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="condition-environment">Environment</label><select id="condition-environment" value={environment} onChange={event => setEnvironment(event.target.value as Environment | '')}><option value="">Any environment</option>{environmentOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="condition-sensitivity">Data sensitivity</label><select id="condition-sensitivity" value={dataSensitivity} onChange={event => setDataSensitivity(event.target.value as DataSensitivity | '')}><option value="">Any sensitivity</option>{sensitivityOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="condition-privilege">Privilege level</label><select id="condition-privilege" value={privilegeLevel} onChange={event => setPrivilegeLevel(event.target.value as PrivilegeLevel | '')}><option value="">Any privilege</option>{privilegeOptions.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
      <div className="field"><label htmlFor="condition-risk-score">Minimum risk score</label><input id="condition-risk-score" type="number" min={0} max={100} value={minimumRiskScore} onChange={event => setMinimumRiskScore(event.target.value === '' ? '' : Number(event.target.value))} /></div>
      <div className="field"><label htmlFor="condition-risk-level">Minimum risk level</label><select id="condition-risk-level" value={minimumRiskLevel} onChange={event => setMinimumRiskLevel(event.target.value as AgentRiskLevel | '')}><option value="">Any risk level</option>{riskLevels.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></div>
    </div>
    {error && <Notice tone="error">{error}</Notice>}
    <div className="form-actions">
      <Button type="submit" loading={loading}>{isUpdate ? 'Save policy' : 'Create policy'}</Button>
      {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>}
    </div>
  </form>
}

export function PoliciesPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const canManage = canManagePolicies(user?.role)
  const [policies, setPolicies] = useState<Policy[]>([]) 
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [enabledFilter, setEnabledFilter] = useState<'all' | 'enabled' | 'disabled'>('all')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  async function load(nextOffset = offset) {
    setLoading(true)
    setError('')
    try {
      const result = await policiesApi.list({ offset: nextOffset, limit: pageSize, enabled: enabledFilter === 'all' ? undefined : enabledFilter === 'enabled' ? true : false })
      setPolicies(result.items)
      setTotal(result.total)
      setOffset(result.offset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load policies.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(0)
  }, [enabledFilter])

  async function submitPolicy(payload: PolicyCreateInput | PolicyUpdateInput) {
    setCreating(true)
    try {
      await policiesApi.create(payload as PolicyCreateInput)
      setShowCreate(false)
      await load(0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create the policy.')
    } finally {
      setCreating(false)
    }
  }

  const page = Math.max(1, Math.floor(offset / pageSize) + 1)
  const pages = Math.max(1, Math.ceil(total / pageSize))

  return <div className="policies-page"><div className="page-heading"><div><p className="eyebrow">Policy management</p><h1>Policies</h1><p className="page-description">Deterministic authorization rules for this tenant.</p></div>{canManage && <Button onClick={() => setShowCreate(current => !current)}><Plus size={16} />Create policy</Button>}</div><PolicyPriorityLegend />{showCreate && <section className="surface-card form-panel"><div className="section-heading"><div><p className="card-kicker">New policy</p><h2>Create rule</h2></div><button className="icon-button" aria-label="Close policy form" type="button" onClick={() => setShowCreate(false)}><X size={18} /></button></div><PolicyForm onSubmit={submitPolicy} onCancel={() => setShowCreate(false)} loading={creating} /></section>}{error && <Notice tone="error">{error}</Notice>}<section className="inventory-section"><div className="section-heading"><div><p className="card-kicker">Tenant inventory</p><h2>{total} polic{total === 1 ? 'y' : 'ies'}</h2></div><button className="icon-button" aria-label="Refresh policies" type="button" onClick={() => void load()} disabled={loading}><SlidersHorizontal size={17} /></button></div><div className="filter-bar" aria-label="Policy filters"><label><span>Enabled state</span><select value={enabledFilter} onChange={event => setEnabledFilter(event.target.value as 'all' | 'enabled' | 'disabled')}><option value="all">All policies</option><option value="enabled">Enabled</option><option value="disabled">Disabled</option></select></label></div>{loading ? <LoadingState label="Loading policies" /> : policies.length === 0 ? <div className="empty-state"><ShieldBan size={28} /><h2>No policies yet</h2><p>If no enabled policy matches an authorization request, the backend defaults to DENY. {canManage ? 'Create a policy to define the tenant rule set.' : 'Ask an owner or admin to create one.'}</p>{canManage && <Button onClick={() => setShowCreate(true)}><Plus size={16} />Create policy</Button>}</div> : <div className="table-wrap"><table className="policy-table"><thead><tr><th>Name</th><th>Effect</th><th>Priority</th><th>Status</th><th>Conditions</th><th>Updated</th></tr></thead><tbody>{policies.map(policy => <tr key={policy.id} onClick={() => navigate(`/policies/${policy.id}`)}><td><div className="policy-name-block"><strong>{policy.name}</strong>{policy.description && <span>{policy.description}</span>}</div></td><td><PolicyEffectBadge effect={policy.effect} enabled={policy.enabled} /></td><td><strong className="priority-value">{policy.priority}</strong></td><td><PolicyStateBadge enabled={policy.enabled} /></td><td><span className="cell-truncate">{makeConditionSummary(policy.conditions)}</span></td><td>{formatDate(policy.updated_at)}</td></tr>)}</tbody></table></div>}{total > pageSize && <div className="pagination"><div><button type="button" className="icon-button" aria-label="Previous page" disabled={page <= 1} onClick={() => void load(Math.max(0, offset - pageSize))}><ChevronLeft size={18} /></button><button type="button" className="icon-button" aria-label="Next page" disabled={page >= pages} onClick={() => void load(offset + pageSize)}><ChevronRight size={18} /></button></div><span>Page {page} of {pages}</span></div>}</section></div>
}

export function PolicyDetailPage() {
  const { policyId } = useParams()
  const { user } = useAuth()
  const canManage = canManagePolicies(user?.role)
  const navigate = useNavigate()
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [disabling, setDisabling] = useState(false)

  async function loadPolicy() {
    if (!policyId) return
    setLoading(true)
    setError('')
    try {
      const result = await policiesApi.get(policyId)
      setPolicy(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load this policy.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPolicy()
  }, [policyId])

  async function savePolicy(payload: PolicyCreateInput | PolicyUpdateInput) {
    if (!policyId) return
    setSaving(true)
    try {
      const nextPolicy = await policiesApi.update(policyId, payload as PolicyUpdateInput)
      setPolicy(nextPolicy)
      setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save this policy.')
    } finally {
      setSaving(false)
    }
  }

  async function disablePolicy() {
    if (!policyId) return
    setDisabling(true)
    try {
      const nextPolicy = await policiesApi.disable(policyId)
      setPolicy(nextPolicy)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to disable this policy.')
    } finally {
      setDisabling(false)
    }
  }

  if (loading) return <LoadingState label="Loading policy" />
  if (error && !policy) return <div className="center-state"><AlertTriangle size={22} /><h1>Unable to load policy</h1><p>{error}</p><Link to="/policies"><Button>Back to policies</Button></Link></div>
  if (!policy) return null

  return <div className="policy-detail"><div className="page-heading"><div><Link className="back-link" to="/policies"><ChevronLeft size={16} />Policies</Link><p className="eyebrow">Policy details</p><h1>{policy.name}</h1></div>{canManage && <div className="detail-actions"><Button variant="secondary" onClick={() => setEditing(value => !value)}><FilePenLine size={16} />{editing ? 'Cancel edit' : 'Edit policy'}</Button>{!policy.enabled && <Button variant="secondary" onClick={() => void disablePolicy()} loading={disabling}>Disabled</Button>}</div>}</div>
    <div className="policy-summary-grid">
      <div className="surface-card"><p className="card-kicker">Effect</p><PolicyEffectBadge effect={policy.effect} enabled={policy.enabled} /></div>
      <div className="surface-card"><p className="card-kicker">Priority</p><strong>{policy.priority}</strong></div>
      <div className="surface-card"><p className="card-kicker">Status</p><PolicyStateBadge enabled={policy.enabled} /></div>
      <div className="surface-card"><p className="card-kicker">Updated</p><strong>{formatDate(policy.updated_at)}</strong></div>
    </div>
    {!editing ? <div className="detail-section"><div className="section-heading"><div><p className="card-kicker">Rule context</p><h2>Structured conditions</h2></div>{canManage && <Button variant="danger" onClick={() => void disablePolicy()} loading={disabling} disabled={policy.enabled === false}>Disable policy</Button>}</div><p className="policy-description">{policy.description || 'No description provided.'}</p><ul className="condition-list">{Object.entries(policy.conditions).length === 0 ? <li>No structured conditions were set.</li> : Object.entries(policy.conditions).map(([key, value]) => <li key={key}><strong>{label(key)}</strong><span>{String(value)}</span></li>)}</ul></div> : <section className="surface-card form-panel"><div className="section-heading"><div><p className="card-kicker">Update policy</p><h2>Modify rule</h2></div><button type="button" className="icon-button" aria-label="Close edit form" onClick={() => setEditing(false)}><X size={18} /></button></div><PolicyForm initial={policy} onSubmit={savePolicy} onCancel={() => setEditing(false)} loading={saving} /></section>}
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Evaluation</p><h2>Human-readable summary</h2></div></div><p className="small-summary">{makeConditionSummary(policy.conditions)}</p></section>
    <section className="detail-section"><div className="section-heading"><div><p className="card-kicker">Backend guidance</p><h2>Evaluation model</h2></div></div><ul className="info-list"><li>Higher numeric priority is evaluated before lower priority.</li><li>For equal priority: DENY &gt; REQUIRE_APPROVAL &gt; ALLOW.</li><li>Disabled policies are excluded from evaluation.</li><li>If no enabled policy matches an authorization request, the backend defaults to DENY.</li></ul></section>
    {error && <Notice tone="error">{error}</Notice>}
    <div className="back-link-wrap"><button className="button button-secondary" type="button" onClick={() => navigate('/policies')}><Eye size={16} />Back to inventory</button></div></div>
}
