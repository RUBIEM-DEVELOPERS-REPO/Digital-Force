/**
 * Digital Force — Auth Utilities
 * JWT token management via localStorage + cookie (for Next.js middleware).
 */

const TOKEN_KEY = 'df_token'
const USER_KEY = 'df_user'

/** Mirror token to a cookie so Next.js middleware can read it server-side. */
function setTokenCookie(token: string) {
  // Expires in 24h; SameSite=Lax works fine for same-origin Next.js apps
  const maxAge = 60 * 60 * 24
  document.cookie = `df_token=${token}; path=/; max-age=${maxAge}; SameSite=Lax`
}

function clearTokenCookie() {
  document.cookie = 'df_token=; path=/; max-age=0; SameSite=Lax'
}

export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token)
  setTokenCookie(token)
}

export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  clearTokenCookie()
}

export const isAuthenticated = (): boolean => {
  return !!getToken()
}

export const setUser = (user: object): void => {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const getUser = (): Record<string, string> | null => {
  if (typeof window === 'undefined') return null
  const u = localStorage.getItem(USER_KEY)
  if (!u) return null
  try { return JSON.parse(u) } catch { return null }
}

export const authHeaders = (): Record<string, string> => {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
