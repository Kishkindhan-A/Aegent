import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, sessionStore, setAccessToken } from '../../api/client'
import type { ApiError, CurrentUser, TokenResponse } from '../../types/auth'

interface AuthContextValue {
  user: CurrentUser | null
  initializing: boolean
  sessionExpired: boolean
  signIn: (tokens: TokenResponse) => void
  signOut: () => Promise<void>
  clearSessionExpired: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    const handleSessionExpired = () => { setUser(null); setSessionExpired(true) }
    window.addEventListener('aegent:session-expired', handleSessionExpired)
    if (!sessionStore.getRefreshToken()) {
      setInitializing(false)
      return () => window.removeEventListener('aegent:session-expired', handleSessionExpired)
    }
    authApi.restore()
      .then(user => { if (user) setUser(user); else setSessionExpired(true) })
      .catch((_error: ApiError) => setSessionExpired(true))
      .finally(() => setInitializing(false))
    return () => window.removeEventListener('aegent:session-expired', handleSessionExpired)
  }, [])

  const signIn = (tokens: TokenResponse) => {
    try {
      setAccessToken(tokens.access_token)
      sessionStore.setRefreshToken(tokens.refresh_token)
      setUser(tokens.user)
      setSessionExpired(false)
    } catch (error) {
      sessionStore.clear()
      throw error
    }
  }

  const signOut = async () => {
    try { await authApi.logout() } finally { sessionStore.clear(); setUser(null); setSessionExpired(false) }
  }

  return <AuthContext.Provider value={{ user, initializing, sessionExpired, signIn, signOut, clearSessionExpired: () => setSessionExpired(false) }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}