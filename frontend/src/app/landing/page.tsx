'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, AlertCircle, X, ArrowRight, Zap, Shield, Activity, Globe, ChevronDown } from 'lucide-react'
import api from '@/lib/api'
import { setToken, setUser, isAuthenticated } from '@/lib/auth'
import Image from 'next/image'

// ─── Animated Background Mesh ─────────────────────────────────────────────────
function MeshBackground() {
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {/* Deep ambient orbs */}
      <motion.div
        animate={{ x: [0, 60, 0], y: [0, -40, 0] }}
        transition={{ repeat: Infinity, duration: 20, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: '-10%', left: '10%',
          width: 700, height: 700, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,163,255,0.12) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      <motion.div
        animate={{ x: [0, -50, 0], y: [0, 60, 0] }}
        transition={{ repeat: Infinity, duration: 25, ease: 'easeInOut', delay: 5 }}
        style={{
          position: 'absolute', bottom: '0%', right: '5%',
          width: 600, height: 600, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      <motion.div
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
        transition={{ repeat: Infinity, duration: 15, ease: 'easeInOut', delay: 8 }}
        style={{
          position: 'absolute', top: '40%', right: '30%',
          width: 300, height: 300, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,100,180,0.08) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />

      {/* Grid overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `
          linear-gradient(rgba(0,163,255,0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,163,255,0.025) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
      }} />

      {/* Top fade */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '30%',
        background: 'linear-gradient(to bottom, #080B12, transparent)',
      }} />
      {/* Bottom fade */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: '20%',
        background: 'linear-gradient(to top, #080B12, transparent)',
      }} />
    </div>
  )
}

// ─── Auth Modal Overlay ────────────────────────────────────────────────────────
function AuthModal({ onClose }: { onClose: () => void }) {
  const router = useRouter()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      let data: { access_token: string }
      if (mode === 'login') {
        data = await api.auth.login({ email, password })
      } else {
        if (!username.trim()) { setError('Handle is required'); setLoading(false); return }
        data = await api.auth.register({ email, password, username, full_name: fullName })
      }
      setToken(data.access_token)
      try { const me = await api.auth.me(); setUser(me) } catch { /* proceed */ }
      window.location.replace('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Access denied. Verify credentials.')
    } finally { setLoading(false) }
  }

  const inputStyle = {
    width: '100%', padding: '0.8rem 1rem', borderRadius: '0.75rem',
    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
    color: '#F8FAFC', fontSize: '0.875rem', outline: 'none', fontFamily: 'inherit',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    boxSizing: 'border-box' as const,
  }

  return (
    <motion.div
      ref={overlayRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(4, 6, 10, 0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <motion.div
        initial={{ scale: 0.94, y: 20, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.94, y: 20, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        style={{
          width: '100%', maxWidth: 440,
          background: 'linear-gradient(160deg, rgba(15,23,42,0.95) 0%, rgba(8,11,18,0.98) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '1.5rem',
          boxShadow: '0 40px 120px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,163,255,0.08)',
          overflow: 'hidden',
        }}
      >
        {/* Modal Header */}
        <div style={{
          padding: '2rem 2rem 1.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 48, height: 48, borderRadius: 14,
              background: 'linear-gradient(135deg, #00A3FF, #0061A0)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 30px rgba(0,163,255,0.4)',
              border: '1px solid rgba(255,255,255,0.1)',
              flexShrink: 0,
            }}>
              <Zap size={22} color="white" />
            </div>
            <div>
              <div style={{
                fontWeight: 800, fontSize: '1.2rem',
                background: 'linear-gradient(180deg, #FFFFFF 0%, #94BFDB 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
              }}>
                Digital Force
              </div>
              <div style={{ fontSize: '0.68rem', color: '#475569', fontWeight: 600, letterSpacing: '0.06em', marginTop: 2 }}>
                SECURE ACCESS PROTOCOL
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, padding: 6, cursor: 'pointer', color: '#94A3B8',
            display: 'flex', transition: 'all 0.2s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#F8FAFC'; e.currentTarget.style.background = 'rgba(255,255,255,0.08)' }}
          onMouseLeave={e => { e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Mode Tabs */}
        <div style={{ padding: '1.5rem 2rem 0' }}>
          <div style={{
            display: 'flex', gap: 4,
            background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 4,
          }}>
            {(['login', 'register'] as const).map(m => (
              <button key={m} onClick={() => { setMode(m); setError('') }}
                style={{
                  flex: 1, padding: '0.5rem', borderRadius: 8, fontWeight: 600,
                  fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.2s',
                  background: mode === m ? 'rgba(0,163,255,0.2)' : 'transparent',
                  color: mode === m ? '#33BAFF' : 'rgba(255,255,255,0.4)',
                  border: mode === m ? '1px solid rgba(0,163,255,0.35)' : '1px solid transparent',
                  letterSpacing: '0.04em',
                }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem 2rem 2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {mode === 'register' && (
            <>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>
                  OPERATOR HANDLE
                </label>
                <input type="text" value={username} required onChange={e => setUsername(e.target.value)}
                  placeholder="your_handle" style={inputStyle}
                  onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,163,255,0.5)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,163,255,0.1)' }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.boxShadow = 'none' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>
                  FULL NAME
                </label>
                <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                  placeholder="Jane Smith" style={inputStyle}
                  onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,163,255,0.5)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,163,255,0.1)' }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.boxShadow = 'none' }}
                />
              </div>
            </>
          )}

          <div>
            <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>
              EMAIL ADDRESS
            </label>
            <input type="email" value={email} required onChange={e => setEmail(e.target.value)}
              placeholder="operator@agency.com" style={inputStyle}
              onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,163,255,0.5)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,163,255,0.1)' }}
              onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.boxShadow = 'none' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>
              PASSPHRASE
            </label>
            <div style={{ position: 'relative' }}>
              <input type={showPassword ? 'text' : 'password'} value={password} required onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••" style={{ ...inputStyle, paddingRight: '2.75rem' }}
                onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,163,255,0.5)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,163,255,0.1)' }}
                onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.boxShadow = 'none' }}
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#64748B', cursor: 'pointer', padding: 4 }}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '0.75rem 1rem',
                  borderRadius: 10, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
                  color: '#FCA5A5', fontSize: '0.82rem',
                }}>
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          <button type="submit" disabled={loading}
            style={{
              marginTop: 4, padding: '0.85rem', borderRadius: '0.75rem',
              background: 'linear-gradient(135deg, #00A3FF, #006199)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: 'white', fontWeight: 700, fontSize: '0.9rem',
              cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.7 : 1,
              transition: 'all 0.2s', letterSpacing: '0.04em',
              boxShadow: '0 8px 32px rgba(0,163,255,0.35)',
            }}
            onMouseEnter={e => { if (!loading) { e.currentTarget.style.boxShadow = '0 8px 40px rgba(0,163,255,0.6)'; e.currentTarget.style.transform = 'translateY(-1px)' }}}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,163,255,0.35)'; e.currentTarget.style.transform = 'translateY(0)' }}
            onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.98)' }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center' }}>
                <span style={{ display: 'flex', gap: 4 }}>
                  <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                </span>
                {mode === 'login' ? 'Authenticating...' : 'Deploying Access...'}
              </span>
            ) : (
              mode === 'login' ? 'INITIALIZE ACCESS' : 'DEPLOY ACCOUNT'
            )}
          </button>
        </form>
      </motion.div>
    </motion.div>
  )
}

// ─── Stat Counter ─────────────────────────────────────────────────────────────
function StatCounter({ from, to, suffix = '', label }: { from: number; to: number; suffix?: string; label: string }) {
  const [val, setVal] = useState(from)
  useEffect(() => {
    const steps = 60
    const step = (to - from) / steps
    let current = from
    let i = 0
    const interval = setInterval(() => {
      i++
      current += step
      setVal(Math.round(current))
      if (i >= steps) { setVal(to); clearInterval(interval) }
    }, 20)
    return () => clearInterval(interval)
  }, [from, to])
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.03em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94BFDB 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
        {val}{suffix}
      </div>
      <div style={{ fontSize: '0.8rem', color: '#64748B', fontWeight: 600, letterSpacing: '0.05em', marginTop: 4 }}>
        {label}
      </div>
    </div>
  )
}

// ─── Landing Page ──────────────────────────────────────────────────────────────
export default function LandingPage() {
  const router = useRouter()
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/overview')
    }
  }, [router])

  const openModal = (mode: 'login' | 'register') => {
    setAuthMode(mode)
    setShowAuth(true)
  }

  const CAPABILITIES = [
    { icon: Activity, title: 'Autonomous Execution', desc: 'Neural agents synthesize, plan, and execute entire campaigns without human intervention.' },
    { icon: Shield, title: 'Intelligent Memory', desc: 'Semantic knowledge core retains your brand voice, media, and strategies across every operation.' },
    { icon: Globe, title: 'Omni-Channel Reach', desc: 'Simultaneous deployment across LinkedIn, X, Instagram, TikTok, Facebook, and beyond.' },
    { icon: Zap, title: 'Real-Time Intelligence', desc: 'Live analytics feedback loops allow the agency to adapt strategy mid-execution.' },
  ]

  return (
    <div style={{ minHeight: '100vh', background: '#080B12', color: '#F8FAFC', fontFamily: 'Inter, system-ui, sans-serif', overflowX: 'hidden' }}>

      {/* ── Navigation Bar ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        background: 'rgba(8,11,18,0.8)',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 2rem', height: 70, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'linear-gradient(135deg, #00A3FF, #006199)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 20px rgba(0,163,255,0.4)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}>
              <Zap size={18} color="white" />
            </div>
            <div>
              <span style={{ fontWeight: 800, fontSize: '1.05rem', background: 'linear-gradient(180deg, #FFFFFF 0%, #94BFDB 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.02em' }}>
                Digital Force
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={() => openModal('login')}
              style={{ padding: '0.5rem 1.25rem', borderRadius: 8, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: '#94A3B8', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s', letterSpacing: '0.02em' }}
              onMouseEnter={e => { e.currentTarget.style.color = '#F8FAFC'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)' }}
              onMouseLeave={e => { e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}>
              Sign In
            </button>
            <button onClick={() => openModal('register')}
              style={{ padding: '0.5rem 1.25rem', borderRadius: 8, background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s', boxShadow: '0 4px 16px rgba(0,163,255,0.3)', letterSpacing: '0.04em' }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,163,255,0.6)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,163,255,0.3)'; e.currentTarget.style.transform = 'translateY(0)' }}>
              Deploy Agency
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section style={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        <MeshBackground />

        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 900, padding: '0 2rem', paddingTop: '6rem' }}>
          {/* Tag label */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: '2rem', padding: '0.4rem 1rem 0.4rem 0.6rem', borderRadius: 999, background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.25)' }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00A3FF', boxShadow: '0 0 12px #00A3FF', animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: '0.78rem', color: '#33BAFF', fontWeight: 600, letterSpacing: '0.06em' }}>AUTONOMOUS DIGITAL MEDIA INTELLIGENT AGENCY</span>
          </motion.div>

          {/* Main headline */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            style={{ fontSize: 'clamp(3rem, 8vw, 6rem)', fontWeight: 900, lineHeight: 1.05, letterSpacing: '-0.04em', marginBottom: '1.75rem' }}>
            <span style={{ background: 'linear-gradient(180deg, #FFFFFF 0%, #C0D8EC 60%, #94BFDB 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Your Digital Agency.
            </span>
            <br />
            <span style={{ background: 'linear-gradient(135deg, #00A3FF 0%, #22D3EE 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Fully Autonomous.
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
            style={{ fontSize: 'clamp(1rem, 2vw, 1.25rem)', color: '#64748B', maxWidth: 620, margin: '0 auto 3rem', lineHeight: 1.7, fontWeight: 400 }}>
            Coordinate, deploy, and optimize AI agents across every social platform simultaneously — with zero manual overhead.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}
            style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => openModal('register')}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '1rem 2.5rem', borderRadius: 12, background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', fontSize: '1rem', fontWeight: 700, cursor: 'pointer', transition: 'all 0.25s', boxShadow: '0 8px 40px rgba(0,163,255,0.45)', letterSpacing: '0.02em' }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 12px 60px rgba(0,163,255,0.7)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 8px 40px rgba(0,163,255,0.45)'; e.currentTarget.style.transform = 'translateY(0)' }}
              onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.98)' }}>
              Deploy Your Agency <ArrowRight size={18} />
            </button>
            <button onClick={() => openModal('login')}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '1rem 2.5rem', borderRadius: 12, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#94A3B8', fontSize: '1rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.25s', letterSpacing: '0.02em' }}
              onMouseEnter={e => { e.currentTarget.style.color = '#F8FAFC'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)' }}
              onMouseLeave={e => { e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)' }}>
              Access System
            </button>
          </motion.div>

          {/* Scroll hint */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.4 }}
            style={{ marginTop: '5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, color: '#334155' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.08em' }}>EXPLORE CAPABILITIES</span>
            <motion.div animate={{ y: [0, 6, 0] }} transition={{ repeat: Infinity, duration: 1.8 }}>
              <ChevronDown size={20} />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Stats Bar ── */}
      <section style={{ borderTop: '1px solid rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)', background: 'rgba(15,23,42,0.5)', padding: '3rem 2rem' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '3rem' }}>
          <StatCounter from={0} to={12} suffix="+" label="SUPPORTED PLATFORMS" />
          <StatCounter from={0} to={99} suffix="%" label="AUTOMATION RATE" />
          <StatCounter from={0} to={500} suffix="+" label="DAILY OPERATIONS" />
          <StatCounter from={0} to={24} suffix="/7" label="NEURAL UPTIME" />
        </div>
      </section>

      {/* ── Capabilities Grid ── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '8rem 2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#00A3FF', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '1rem' }}>SYSTEM ARCHITECTURE</div>
          <h2 style={{ fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 900, letterSpacing: '-0.03em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94BFDB 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Built to Operate at Scale
          </h2>
          <p style={{ color: '#64748B', fontSize: '1.05rem', marginTop: '1rem', maxWidth: 500, margin: '1rem auto 0' }}>
            Every component engineered for autonomous, reliable, enterprise-grade performance.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
          {CAPABILITIES.map((cap, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
              whileHover={{ y: -4, borderColor: 'rgba(0,163,255,0.3)' }}
              style={{
                padding: '2.5rem 2rem', borderRadius: '1.25rem',
                background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%)',
                border: '1px solid rgba(255,255,255,0.05)',
                backdropFilter: 'blur(12px)',
                transition: 'border-color 0.3s',
              }}>
              <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem' }}>
                <cap.icon size={24} style={{ color: '#00A3FF' }} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '0.75rem', letterSpacing: '-0.01em' }}>{cap.title}</h3>
              <p style={{ fontSize: '0.875rem', color: '#64748B', lineHeight: 1.7 }}>{cap.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section style={{ maxWidth: 800, margin: '0 auto', padding: '4rem 2rem 10rem', textAlign: 'center' }}>
        <div style={{ padding: '5rem 3rem', borderRadius: '2rem', background: 'linear-gradient(135deg, rgba(0,163,255,0.1) 0%, rgba(0,97,153,0.1) 100%)', border: '1px solid rgba(0,163,255,0.2)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: '-50%', left: '50%', transform: 'translateX(-50%)', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,163,255,0.15) 0%, transparent 70%)', filter: 'blur(40px)', pointerEvents: 'none' }} />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <h2 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.75rem)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: '1rem', background: 'linear-gradient(180deg, #FFFFFF 0%, #94BFDB 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Ready to Deploy?
            </h2>
            <p style={{ color: '#64748B', fontSize: '1rem', marginBottom: '2.5rem', maxWidth: 420, margin: '0 auto 2.5rem' }}>
              Join the network of operators building autonomous digital empires.
            </p>
            <button onClick={() => openModal('register')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '1rem 3rem', borderRadius: 12, background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', fontSize: '1rem', fontWeight: 700, cursor: 'pointer', transition: 'all 0.25s', boxShadow: '0 8px 40px rgba(0,163,255,0.45)', letterSpacing: '0.02em' }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 12px 60px rgba(0,163,255,0.7)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 8px 40px rgba(0,163,255,0.45)'; e.currentTarget.style.transform = 'translateY(0)' }}>
              Initialize Agency <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: '1px solid rgba(255,255,255,0.04)', padding: '2rem', textAlign: 'center' }}>
        <span style={{ fontSize: '0.8rem', color: '#334155', fontWeight: 500, letterSpacing: '0.04em' }}>
          DIGITAL FORCE — AUTONOMOUS DIGITAL MEDIA INTELLIGENT AGENCY
        </span>
      </footer>

      {/* ── Auth Modal ── */}
      <AnimatePresence>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </AnimatePresence>
    </div>
  )
}
