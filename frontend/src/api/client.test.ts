import { afterEach, describe, expect, it, vi } from 'vitest'
import { authApi, request, sessionStore, setAccessToken } from './client'

const tokenResponse = { access_token: 'new-access', refresh_token: 'rotated-refresh', token_type: 'bearer', expires_in: 900, user: {} }

afterEach(() => {
  vi.restoreAllMocks()
  sessionStore.clear()
  setAccessToken(null)
})

describe('API session handling', () => {
  it('shares one refresh request across simultaneous expired requests and rotates the credential', async () => {
    sessionStore.setRefreshToken('current-refresh')
    setAccessToken('expired-access')
    let refreshCalls = 0
    let protectedCalls = 0
    vi.stubGlobal('fetch', vi.fn(async (input: string) => {
      if (input.endsWith('/auth/refresh')) {
        refreshCalls += 1
        await new Promise(resolve => setTimeout(resolve, 5))
        return new Response(JSON.stringify(tokenResponse), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      protectedCalls += 1
      return protectedCalls <= 2
        ? new Response(JSON.stringify({ detail: 'expired' }), { status: 401, headers: { 'Content-Type': 'application/json' } })
        : new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))

    const results = await Promise.all([request<{ ok: boolean }>('/api/v1/agents'), request<{ ok: boolean }>('/api/v1/agents')])

    expect(results).toEqual([{ ok: true }, { ok: true }])
    expect(refreshCalls).toBe(1)
    expect(sessionStore.getRefreshToken()).toBe('rotated-refresh')
  })

  it('clears session credentials when refresh fails', async () => {
    sessionStore.setRefreshToken('stale-refresh')
    setAccessToken('expired-access')
    const expired = vi.fn()
    window.addEventListener('aegent:session-expired', expired)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'invalid' }), { status: 401, headers: { 'Content-Type': 'application/json' } })))

    await expect(request('/api/v1/agents')).rejects.toMatchObject({ status: 401 })

    expect(sessionStore.getRefreshToken()).toBeNull()
    expect(expired).toHaveBeenCalledTimes(1)
    window.removeEventListener('aegent:session-expired', expired)
  })

  it('clears client credentials even when server logout is unreachable', async () => {
    sessionStore.setRefreshToken('active-refresh')
    setAccessToken('active-access')
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network unavailable') }))

    await expect(authApi.logout()).rejects.toThrow('Unable to reach Aegent')
    expect(sessionStore.getRefreshToken()).toBeNull()
  })
})