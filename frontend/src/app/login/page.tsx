'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { setToken, setUser } from '@/lib/auth'
import { Zap, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      let data: { access_token: string }

      if (mode === 'login') {
        data = await api.auth.login({ email, password })
      } else {
        if (!username.trim()) { setError('Username is required'); setLoading(false); return }
        data = await api.auth.register({ email, password, username, full_name: fullName })
      }

      setToken(data.access_token)
      const me = await api.auth.me()
      setUser(me)
      // Hard redirect so localStorage token is committed before next page loads
      window.location.href = '/'
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glows */}
      <div style={{
        position: 'absolute', top: '20%', left: '25%',
        width: 400, height: 400, borderRadius: '50%',
        background: 'rgba(124,58,237,0.12)', filter: 'blur(80px)', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '20%', right: '25%',
        width: 300, height: 300, borderRadius: '50%',
        background: 'rgba(34,211,238,0.08)', filter: 'blur(60px)', pointerEvents: 'none',
      }} />

      <div className="animate-slide-up" style={{ width: '100%', maxWidth: 420, position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            width: 60, height: 60, borderRadius: 18,
            background: 'linear-gradient(135deg, #7C3AED, #4F46E5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 1rem', boxShadow: '0 0 40px rgba(124,58,237,0.4)',
          }}>
            <Zap size={28} color="white" />
          </div>
          <h1 style={{
            fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em',
            background: 'linear-gradient(135deg, #fff 30%, rgba(255,255,255,0.5))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>Digital Force</h1>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.85rem', marginTop: 4 }}>
            Autonomous Social Media Intelligence Agency
          </p>
        </div>

        {/* Card */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          {/* Mode tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: '1.75rem',
            background: 'rgba(255,255,255,0.04)', borderRadius: 10, padding: 4 }}>
            {(['login', 'register'] as const).map(m => (
              <button key={m} onClick={() => { setMode(m); setError('') }}
                style={{
                  flex: 1, padding: '0.5rem', borderRadius: 8, fontWeight: 500,
                  fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s',
                  background: mode === m ? 'rgba(124,58,237,0.25)' : 'transparent',
                  color: mode === m ? '#A78BFA' : 'rgba(255,255,255,0.4)',
                  border: mode === m ? '1px solid rgba(124,58,237,0.3)' : '1px solid transparent',
                }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {mode === 'register' && (
              <>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>
                    Username *
                  </label>
                  <input
                    id="username" type="text" value={username} required
                    onChange={e => setUsername(e.target.value)}
                    placeholder="your_username"
                    style={{
                      width: '100%', padding: '0.65rem 0.875rem', borderRadius: 10,
                      background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                      color: '#fff', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>
                    Full Name
                  </label>
                  <input
                    id="full_name" type="text" value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Jane Smith"
                    style={{
                      width: '100%', padding: '0.65rem 0.875rem', borderRadius: 10,
                      background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                      color: '#fff', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </div>
              </>
            )}

            <div>
              <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>
                Email *
              </label>
              <input
                id="email" type="email" value={email} required
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                style={{
                  width: '100%', padding: '0.65rem 0.875rem', borderRadius: 10,
                  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>
                Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="password" type={showPassword ? 'text' : 'password'} value={password} required
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%', padding: '0.65rem 2.75rem 0.65rem 0.875rem',
                    borderRadius: 10, background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
                    fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box',
                  }}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)',
                    cursor: 'pointer', padding: 4, display: 'flex',
                  }}>
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '0.65rem 0.875rem',
                borderRadius: 10, background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.25)', color: '#FCA5A5', fontSize: '0.85rem',
              }}>
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                {error}
              </div>
            )}

            <button id="submit-auth" type="submit" className="btn-primary"
              disabled={loading}
              style={{ marginTop: 4, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center' }}>
                  <span style={{ display: 'flex', gap: 4 }}>
                    <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                  </span>
                  {mode === 'login' ? 'Signing in...' : 'Creating account...'}
                </span>
              ) : (
                mode === 'login' ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.8rem', color: 'rgba(255,255,255,0.3)' }}>
          Digital Force — Powered by ASMIA AI
        </p>
      </div>
    </div>
  )
}
