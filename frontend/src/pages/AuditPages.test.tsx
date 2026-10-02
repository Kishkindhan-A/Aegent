import { type ReactElement } from 'react'
import { act } from 'react-dom/test-utils'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { auditsApi, setAccessToken } from '../api/client'
import * as authModule from '../features/auth/AuthProvider'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AuditPage } from './AuditPages'

let root: Root | null = null
let container: HTMLDivElement | null = null

function renderIntoDom(ui: ReactElement) {
  if (!container) {
    container = document.createElement('div')
    document.body.appendChild(container)
  }
  root = createRoot(container)
  act(() => {
    root!.render(<BrowserRouter><AuthProvider>{ui}</AuthProvider></BrowserRouter>)
  })
}

afterEach(() => {
  act(() => {
    root?.unmount()
  })
  if (container) {
    document.body.removeChild(container)
    container = null
    root = null
  }
  vi.restoreAllMocks()
  setAccessToken(null)
})

describe('audit trail UI', () => {
  it('renders the read-only audit trail and hides mutation controls', async () => {
    vi.spyOn(auditsApi, 'list').mockResolvedValue({
      items: [{
        id: '11111111-1111-4111-8111-111111111111',
        organization_id: '22222222-2222-4222-8222-222222222222',
        event_type: 'AUTH_LOGIN_SUCCESS',
        category: 'AUTHENTICATION',
        severity: 'INFO',
        actor_type: 'USER',
        actor_user_id: '33333333-3333-4333-8333-333333333333',
        agent_id: null,
        policy_id: null,
        approval_request_id: null,
        correlation_id: 'corr-123',
        request_id: null,
        source: 'auth.login',
        summary: 'User signed in successfully.',
        details: { status: 'SUCCESS' },
        created_at: '2024-01-02T12:00:00Z',
      }],
      total: 1,
      offset: 0,
      limit: 10,
    })
    vi.spyOn(authModule, 'useAuth').mockReturnValue({
      user: { id: 'owner-id', email: 'owner@example.com', full_name: 'Owner User', role: 'OWNER', organization_id: 'org-1', status: 'ACTIVE', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      initializing: false,
      sessionExpired: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      clearSessionExpired: vi.fn(),
    })

    renderIntoDom(<AuditPage />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(document.body.textContent).toContain('Audit trail')
    expect(document.body.textContent).toContain('User signed in successfully.')
    expect(document.body.textContent).not.toContain('Create event')
    expect(document.body.textContent).not.toContain('Delete event')
    expect(document.body.textContent).not.toContain('Resolve event')
  })

  it('blocks member access to the audit workspace before fetching data', async () => {
    const listSpy = vi.spyOn(auditsApi, 'list')
    vi.spyOn(authModule, 'useAuth').mockReturnValue({
      user: { id: 'member-id', email: 'member@example.com', full_name: 'Member User', role: 'MEMBER', organization_id: 'org-1', status: 'ACTIVE', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      initializing: false,
      sessionExpired: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      clearSessionExpired: vi.fn(),
    })

    renderIntoDom(<AuditPage />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(listSpy).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Access restricted')
  })

  it('serializes only supported audit filters into the query string', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 10 }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await auditsApi.list({
      event_type: 'AUTH_LOGIN_SUCCESS',
      severity: 'HIGH',
      agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      correlation_id: 'corr-123',
      created_after: '2024-01-01T00:00:00Z',
      created_before: '2024-01-02T00:00:00Z',
      offset: 20,
      limit: 10,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const url = (fetchMock.mock.calls[0] as unknown as [RequestInfo | URL, RequestInit?])[0]
    expect(String(url)).toContain('/api/v1/audit/events?')
    expect(String(url)).toContain('event_type=AUTH_LOGIN_SUCCESS')
    expect(String(url)).toContain('severity=HIGH')
    expect(String(url)).toContain('agent_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
    expect(String(url)).toContain('correlation_id=corr-123')
    expect(String(url)).toContain('created_after=2024-01-01T00%3A00%3A00Z')
    expect(String(url)).toContain('created_before=2024-01-02T00%3A00%3A00Z')
    expect(String(url)).toContain('offset=20')
    expect(String(url)).toContain('limit=10')
  })
})
