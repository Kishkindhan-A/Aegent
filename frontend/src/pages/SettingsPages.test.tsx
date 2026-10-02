import { type ReactElement } from 'react'
import { act } from 'react-dom/test-utils'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { orgApi } from '../api/client'
import * as authModule from '../features/auth/AuthProvider'
import { AuthProvider } from '../features/auth/AuthProvider'
import { OrganizationSettingsPage, MemberDirectoryPage } from './SettingsPages'

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
})

describe('organization settings UI', () => {
  it('renders settings data and read-only slug for owners', async () => {
    vi.spyOn(orgApi, 'getCurrent').mockResolvedValue({
      id: 'org-1',
      name: 'Acme Security',
      slug: 'acme-security',
      status: 'ACTIVE',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    })
    vi.spyOn(authModule, 'useAuth').mockReturnValue({
      user: { id: 'owner-id', email: 'owner@example.com', full_name: 'Owner User', role: 'OWNER', organization_id: 'org-1', status: 'ACTIVE', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-02T00:00:00Z' },
      initializing: false,
      sessionExpired: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      clearSessionExpired: vi.fn(),
    })

    renderIntoDom(<OrganizationSettingsPage />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(document.body.textContent).toContain('Organization settings')
    expect(document.body.textContent).toContain('Acme Security')
    expect(document.body.textContent).toContain('acme-security')
    expect(document.body.textContent).not.toContain('Organization slug')
  })

  it('shows member directory and blocks unauthorized roles from mutation controls', async () => {
    vi.spyOn(orgApi, 'listMembers').mockResolvedValue({
      items: [{ id: 'user-1', email: 'owner@example.com', full_name: 'Owner User', role: 'OWNER', status: 'ACTIVE', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-02T00:00:00Z' }],
      total: 1,
      offset: 0,
      limit: 20,
    })
    vi.spyOn(authModule, 'useAuth').mockReturnValue({
      user: { id: 'member-id', email: 'member@example.com', full_name: 'Member User', role: 'MEMBER', organization_id: 'org-1', status: 'ACTIVE', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-02T00:00:00Z' },
      initializing: false,
      sessionExpired: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      clearSessionExpired: vi.fn(),
    })

    renderIntoDom(<MemberDirectoryPage />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(document.body.textContent).toContain('Access restricted')
    expect(document.body.textContent).not.toContain('Edit role')
  })
})
