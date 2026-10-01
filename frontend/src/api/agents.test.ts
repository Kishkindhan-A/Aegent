import { afterEach, describe, expect, it, vi } from 'vitest'
import { agentsApi, setAccessToken } from './client'

afterEach(() => {
  vi.restoreAllMocks()
  setAccessToken(null)
})

describe('agent API contracts', () => {
  it('serializes only supported server filters and pagination', async () => {
    const fetchMock = vi.fn(async (input: string) => new Response(JSON.stringify({ items: [], total: 0, offset: 10, limit: 10 }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await agentsApi.list({ offset: 10, limit: 10, status: 'ACTIVE', agent_type: 'SECURITY', risk_level: 'HIGH' })

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/agents?offset=10&limit=10&status=ACTIVE&agent_type=SECURITY&risk_level=HIGH', expect.objectContaining({ headers: expect.any(Headers) }))
  })

  it('sends scan content only in the request body', async () => {
    const fetchMock = vi.fn(async (input: string, options: RequestInit) => new Response(JSON.stringify({ prompt_injection_detected: false, sensitive_data_detected: false, finding_count: 0, highest_finding_severity: null, findings: [], scan_version: 'phase9-v1' }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const content = 'transient content for a single scan'

    await agentsApi.scan('agent-id', { content, content_type: 'TEXT', source_context: 'USER_INPUT' })

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/agents/agent-id/security/scan')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body as string).content).toBe(content)
    expect(url).not.toContain(encodeURIComponent(content))
  })
})