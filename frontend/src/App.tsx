import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { LoadingState } from './components/ui'
import { useAuth } from './features/auth/AuthProvider'
import { AppShell } from './layouts/AppShell'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { ForbiddenPage, NotFoundPage, OverviewPage, SessionExpiredPage } from './pages/AppPages'
import { AgentDetailPage, AgentsPage } from './pages/AgentsPages'
import { ApprovalDetailPage, ApprovalsPage } from './pages/ApprovalsPages'
import { PoliciesPage, PolicyDetailPage } from './pages/PoliciesPages'

function ProtectedRoute() { const { user, initializing, sessionExpired } = useAuth(); if (initializing) return <LoadingState />; if (sessionExpired) return <SessionExpiredPage />; return user ? <Outlet /> : <Navigate to="/login" replace /> }
function PublicRoute() { const { user, initializing } = useAuth(); if (initializing) return <LoadingState />; return user ? <Navigate to="/" replace /> : <Outlet /> }

export function App() { return <Routes><Route element={<PublicRoute />}><Route path="/login" element={<LoginPage />} /><Route path="/register" element={<RegisterPage />} /></Route><Route element={<ProtectedRoute />}><Route element={<AppShell />}><Route path="/" element={<OverviewPage />} /><Route path="/agents" element={<AgentsPage />} /><Route path="/agents/:agentId" element={<AgentDetailPage />} /><Route path="/policies" element={<PoliciesPage />} /><Route path="/policies/:policyId" element={<PolicyDetailPage />} /><Route path="/approvals" element={<ApprovalsPage />} /><Route path="/approvals/:approvalId" element={<ApprovalDetailPage />} /><Route path="/forbidden" element={<ForbiddenPage />} /></Route></Route><Route path="*" element={<NotFoundPage />} /></Routes> }