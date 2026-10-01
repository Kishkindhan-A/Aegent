import { Activity, Bot, FileKey2, Gauge, LogOut, Settings, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthProvider'

const nav = [{ label: 'Overview', icon: Gauge, to: '/' }, { label: 'Agents', icon: Bot, to: '/agents' }, { label: 'Policies', icon: SlidersHorizontal, to: '/policies' }, { label: 'Approvals', icon: FileKey2, to: '/approvals' }]
const futureNav = [{ label: 'Security events', icon: Activity }]

export function AppShell() {
  const { user, signOut } = useAuth()
  const canReviewApprovals = ['OWNER', 'ADMIN', 'SECURITY_ANALYST'].includes(user?.role ?? '')
  const visibleNav = nav.filter(({ to }) => to !== '/approvals' || canReviewApprovals)

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark"><ShieldCheck size={20} /></span><span>Aegent</span></div><div className="workspace-switcher"><span className="workspace-avatar">{(user?.full_name || user?.email || 'A').charAt(0).toUpperCase()}</span><span><strong>{user?.full_name || 'Workspace user'}</strong><small>{user?.role.replace('_', ' ')}</small></span></div><nav aria-label="Primary navigation"><p className="nav-label">Workspace</p>{visibleNav.map(({ label, icon: Icon, to }) => <NavLink key={to} to={to} end className="nav-link"><Icon size={17} />{label}</NavLink>)}<p className="nav-label nav-label-spaced">Coming next</p>{futureNav.map(({ label, icon: Icon }) => <span className="nav-link nav-link-disabled" key={label} aria-disabled="true"><Icon size={17} />{label}<span className="soon">Soon</span></span>)}</nav><div className="sidebar-bottom"><span className="nav-link nav-link-disabled"><Settings size={17} />Settings</span><button className="nav-link logout-button" onClick={() => void signOut()}><LogOut size={17} />Sign out</button></div></aside><main className="app-content"><header className="topbar"><span className="topbar-context">{user?.organization_id ? 'Organization workspace' : 'Workspace'}</span><span className="connection-status"><span className="status-dot" />Connected</span></header><div className="page-content"><Outlet /></div></main></div>
}