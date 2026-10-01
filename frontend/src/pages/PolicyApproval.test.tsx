import { type ReactElement } from 'react'
import { act } from 'react-dom/test-utils'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { approvalsApi } from '../api/client'
import { PolicyPriorityLegend } from './PoliciesPages'
import { ApprovalStatusBadge, ApprovalsPage } from './ApprovalsPages'

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
})

describe('policy and approval governance UI', () => {
  it('displays the deterministic priority rule and default deny guidance', () => {
    renderIntoDom(<PolicyPriorityLegend />)
    expect(document.body.textContent).toContain('Higher numeric priority is evaluated before lower priority.')
    expect(document.body.textContent).toContain('DENY > REQUIRE_APPROVAL > ALLOW')
    expect(document.body.textContent).toContain('If no enabled policy matches an authorization request, the backend defaults to DENY.')
  })

  it('renders approval states with the exact status text', () => {
    renderIntoDom(<ApprovalStatusBadge status="PENDING" />)
    expect(document.body.textContent).toContain('PENDING')
  })

  it('shows no pending approvals for an empty queue', async () => {
    vi.spyOn(approvalsApi, 'list').mockResolvedValue({ items: [], total: 0, offset: 0, limit: 10 })
    renderIntoDom(<ApprovalsPage />)
    await act(async () => {
      await Promise.resolve()
    })
    expect(document.body.textContent).toContain('No pending approval requests')
  })
})
