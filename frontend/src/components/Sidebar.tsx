'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  Zap, LayoutDashboard, Target, BarChart2,
  Cpu, Settings, MessageSquare,
  LogOut, Activity, Network
} from 'lucide-react'
import { clearToken, getUser } from '@/lib/auth'
import api from '@/lib/api'
import { motion } from 'framer-motion'

interface NavItem {
  href: string
  label: string
  icon: React.ElementType
  badge?: number | string
  accent?: string
}

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [mounted, setMounted] = useState(false)
  const [awaitingCount, setAwaitingCount] = useState(0)
  const [agentStatus, setAgentStatus] = useState<'idle' | 'planning' | 'executing' | 'awaiting'>('idle')

  useEffect(() => {
    setMounted(true)
    setUser(getUser())

    // Poll for goal statuses
    const check = async () => {
      try {
        const goals = await api.goals.list()
        const awaiting = goals.filter(g => g.status === 'awaiting_approval').length
        const executing = goals.filter(g => g.status === 'executing').length
        const planning = goals.filter(g => g.status === 'planning').length

        setAwaitingCount(awaiting)
        if (executing > 0) setAgentStatus('executing')
        else if (planning > 0) setAgentStatus('planning')
        else if (awaiting > 0) setAgentStatus('awaiting')
        else setAgentStatus('idle')
      } catch { /* no-op */ }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  const NAV: NavItem[] = [
    { href: '/chat',     label: 'Neural Link',     icon: MessageSquare, accent: '#00A3FF' },
    { href: '/overview', label: 'Overview',         icon: LayoutDashboard },
    { href: '/goals',    label: 'Directives',       icon: Target, badge: awaitingCount || undefined },
    { href: '/analytics',label: 'Analytics',        icon: BarChart2 },
    { href: '/knowledge',label: 'Knowledge Core',   icon: Network },
    { href: '/skills',   label: 'SkillForge',       icon: Cpu },
    { href: '/settings', label: 'Settings',         icon: Settings },
  ]

  const STATUS_CONFIG = {
    idle:      { label: 'System Idle', color: '#475569', dot: '#94A3B8' },
    planning:  { label: 'Synthesizing...', color: '#22D3EE', dot: '#67E8F9' },
    executing: { label: 'Executing', color: '#00A3FF', dot: '#33BAFF' },
    awaiting:  { label: 'Approval Required', color: '#F59E0B', dot: '#FCD34D' },
  }
  const st = STATUS_CONFIG[agentStatus]

  const handleLogout = () => {
    clearToken()
    router.push('/login')
  }

  return (
    <aside style={{
      width: 240, minHeight: '100vh', flexShrink: 0,
      background: 'rgba(8, 11, 18, 0.65)',
      backdropFilter: 'blur(24px)',
      WebkitBackdropFilter: 'blur(24px)',
      borderRight: '1px solid rgba(255,255,255,0.03)',
      display: 'flex', flexDirection: 'column',
      position: 'sticky', top: 0, height: '100vh',
      zIndex: 50,
    }}>
      {/* Brand Identity / Logo */}
      <div style={{ padding: '2rem 1.25rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <div style={{
            width: 36, height: 36, borderRadius: 12,
            background: 'linear-gradient(135deg, #00A3FF, #006199)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 24px rgba(0,163,255,0.4)',
            border: '1px solid rgba(255,255,255,0.1)'
          }}>
            <Zap size={18} color="white" />
          </div>
          <div>
            <div style={{ 
              fontWeight: 800, fontSize: '1.05rem', 
              background: 'linear-gradient(180deg, #FFFFFF 0%, #A0B4CB 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              lineHeight: 1.1, letterSpacing: '-0.02em'
            }}>
              Digital Force
            </div>
            <div style={{ fontSize: '0.65rem', color: '#64748B', fontWeight: 600, letterSpacing: '0.05em', marginTop: 2 }}>
              AUTONOMOUS AGENCY
            </div>
          </div>
        </Link>
      </div>

      {/* Cybernetic Status Indicator */}
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '0.5rem 0.85rem',
          borderRadius: 8, background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.04)',
          position: 'relative', overflow: 'hidden'
        }}>
          {/* Subtle animated background for active states */}
          {agentStatus === 'executing' && (
            <motion.div 
              style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg, transparent, rgba(0,163,255,0.1), transparent)' }}
              animate={{ x: ['-100%', '100%'] }}
              transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
            />
          )}

          <div style={{
            width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
            background: st.dot,
            boxShadow: agentStatus !== 'idle' ? `0 0 12px ${st.dot}` : 'none',
            animation: agentStatus !== 'idle' ? 'pulse 2s infinite' : 'none',
            zIndex: 1
          }} />
          <div style={{ zIndex: 1 }}>
            <div style={{ fontSize: '0.72rem', color: st.color, fontWeight: 600, letterSpacing: '0.02em' }}>{st.label}</div>
            <div style={{ fontSize: '0.62rem', color: '#475569', marginTop: 1 }}>Neural Core Status</div>
          </div>
          {agentStatus === 'executing' && <Activity size={14} style={{ color: '#00A3FF', marginLeft: 'auto', zIndex: 1 }} />}
        </div>
      </div>

      {/* Primary Navigation System */}
      <nav style={{ flex: 1, padding: '1.25rem 0.75rem', overflowY: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV.map(item => {
            const Icon = item.icon
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
            const isChatLink = item.href === '/chat'
            const navAccent = item.accent || '#00A3FF'

            return (
              <Link key={item.href} href={item.href} style={{ textDecoration: 'none', position: 'relative' }}>
                {active && (
                  <motion.div
                    layoutId="activeNavIndicator"
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: '100%',
                      background: isChatLink ? `linear-gradient(90deg, rgba(0,163,255,0.15) 0%, transparent 100%)` : `rgba(255,255,255,0.03)`,
                      borderRadius: 8,
                      borderLeft: `2px solid ${navAccent}`,
                      zIndex: 0
                    }}
                    initial={false}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '0.65rem 1rem', borderRadius: 8,
                  color: active ? '#F8FAFC' : '#94A3B8',
                  position: 'relative', zIndex: 1,
                  transition: 'color 0.2s ease',
                }}>
                  <Icon size={18} style={{ color: active ? navAccent : 'inherit' }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: active ? 500 : 400 }}>
                    {item.label}
                  </span>
                  {item.badge ? (
                    <span style={{
                      marginLeft: 'auto', minWidth: 20, height: 20, borderRadius: 10, padding: '0 6px',
                      background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)',
                      color: '#F59E0B', fontSize: '0.65rem', fontWeight: 700,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {item.badge}
                    </span>
                  ) : null}
                </div>
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Operator Metadata */}
      <div style={{ padding: '1rem', borderTop: '1px solid rgba(255,255,255,0.02)' }}>
        {mounted && user && (
          <div style={{ padding: '0.6rem 0.75rem', marginBottom: 8, borderRadius: 8, background: 'rgba(255,255,255,0.015)' }}>
            <div style={{ fontSize: '0.8rem', color: '#F8FAFC', fontWeight: 500 }}>
              {user.full_name || user.email?.split('@')[0] || 'Operator_01'}
            </div>
            <div style={{ fontSize: '0.65rem', color: '#64748B', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {user.role || 'Clearance: Level 1'}
            </div>
          </div>
        )}
        <button onClick={handleLogout}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 10,
            padding: '0.5rem 0.75rem', borderRadius: 8, cursor: 'pointer',
            background: 'none', border: 'none', color: '#64748B',
            fontSize: '0.8rem', transition: 'all 0.2s', fontWeight: 500
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#FCA5A5' }}
          onMouseLeave={e => { e.currentTarget.style.color = '#64748B' }}>
          <LogOut size={16} /> Disconnect
        </button>
      </div>
    </aside>
  )
}
