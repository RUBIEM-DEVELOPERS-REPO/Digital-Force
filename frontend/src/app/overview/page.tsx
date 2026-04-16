'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import {
  Target, TrendingUp, Network, Plus,
  ArrowRight, Activity, Zap, CheckCircle2, Clock, AlertCircle, Cpu
} from 'lucide-react'
import api from '@/lib/api'

interface Goal {
  id: string
  title: string
  status: string
  priority: string
  progress_percent: number
  tasks_total: number
  tasks_completed: number
  platforms: string[]
  created_at: string
  latest_activity?: string
}

const STATUS_CONFIG: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
  planning:          { label: 'Synthesizing',  cls: 'badge-planning',   icon: Clock },
  awaiting_approval: { label: 'Authorization', cls: 'badge-awaiting',   icon: AlertCircle },
  executing:         { label: 'Executing',     cls: 'badge-executing',  icon: Activity },
  monitoring:        { label: 'Monitoring',    cls: 'badge-monitoring', icon: TrendingUp },
  complete:          { label: 'Complete',      cls: 'badge-complete',   icon: CheckCircle2 },
  failed:            { label: 'Failed',        cls: 'badge-failed',     icon: AlertCircle },
}

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LI', facebook: 'FB', twitter: 'X', tiktok: 'TK',
  instagram: 'IG', youtube: 'YT', threads: 'TH',
}

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.08 } } },
  item: { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] } } },
}

export default function OverviewPage() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.goals.list()
      .then(setGoals)
      .catch(() => setGoals([]))
      .finally(() => setLoading(false))
  }, [])

  const activeGoals = goals.filter(g => ['planning','awaiting_approval','executing','monitoring'].includes(g.status))
  const awaiting = goals.filter(g => g.status === 'awaiting_approval')

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* ── Page Header ── */}
        <div style={{ padding: '3rem 3rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
                  DIGITAL FORCE — COMMAND CENTER
                </div>
                <h1 style={{
                  fontSize: 'clamp(2rem, 4vw, 2.75rem)', fontWeight: 900, letterSpacing: '-0.035em',
                  background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                  lineHeight: 1.1, marginBottom: '0.75rem',
                }}>
                  Overview
                </h1>
                <p style={{ fontSize: '0.9rem', color: '#475569', fontWeight: 400 }}>
                  Autonomous Digital Media Intelligent Agency
                </p>
              </div>
              <Link href="/goals/new" style={{
                display: 'inline-flex', alignItems: 'center', gap: 10,
                padding: '0.75rem 1.75rem', borderRadius: '0.875rem',
                background: 'linear-gradient(135deg, #00A3FF, #006199)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fff', fontSize: '0.875rem', fontWeight: 700,
                cursor: 'pointer', transition: 'all 0.2s',
                boxShadow: '0 8px 32px rgba(0,163,255,0.35)',
                textDecoration: 'none', letterSpacing: '0.03em',
              }}>
                <Plus size={16} />
                Deploy Task
              </Link>
            </div>
          </motion.div>
        </div>

        <div style={{ padding: '2.5rem 3rem' }}>

          {/* ── Authorization Alert ── */}
          {awaiting.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
              style={{
                marginBottom: '2rem', padding: '1.25rem 1.5rem',
                borderRadius: '1rem', display: 'flex', alignItems: 'center', gap: '1rem',
                background: 'rgba(245,158,11,0.06)',
                border: '1px solid rgba(245,158,11,0.25)',
                boxShadow: '0 0 40px rgba(245,158,11,0.08)',
              }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(245,158,11,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <AlertCircle size={20} style={{ color: '#F59E0B' }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, color: '#FCD34D', fontSize: '0.875rem' }}>
                  {awaiting.length} protocol{awaiting.length > 1 ? 's' : ''} pending authorization
                </div>
                <div style={{ fontSize: '0.78rem', color: '#92400E', marginTop: 3 }}>
                  Agent synthesis is complete — review before execution begins
                </div>
              </div>
              <Link href={`/goals/${awaiting[0].id}/approve`} style={{
                padding: '0.6rem 1.25rem', borderRadius: 8,
                background: 'linear-gradient(135deg, #00A3FF, #006199)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fff', fontSize: '0.8rem', fontWeight: 700,
                textDecoration: 'none', letterSpacing: '0.03em', flexShrink: 0,
              }}>
                Authorize
              </Link>
            </motion.div>
          )}

          {/* ── KPI Stats ── */}
          <motion.div variants={stagger.container} initial="hidden" animate="show"
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginBottom: '2.5rem' }}>
            {[
              { label: 'Active Tasks', value: activeGoals.length, icon: Target, color: '#00A3FF', glow: 'rgba(0,163,255,0.1)' },
              { label: 'Pending Authorization', value: awaiting.length, icon: AlertCircle, color: '#F59E0B', glow: 'rgba(245,158,11,0.1)' },
              { label: 'Total Operations', value: goals.length, icon: Zap, color: '#10B981', glow: 'rgba(16,185,129,0.1)' },
            ].map((stat, i) => (
              <motion.div key={i} variants={stagger.item}
                style={{
                  padding: '1.75rem', borderRadius: '1.125rem', display: 'flex', alignItems: 'center', gap: '1.25rem',
                  background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%)',
                  border: '1px solid rgba(255,255,255,0.04)',
                  backdropFilter: 'blur(16px)',
                  boxShadow: `inset 0 1px 0 rgba(255,255,255,0.04)`,
                }}>
                <div style={{
                  width: 52, height: 52, borderRadius: '0.875rem', flexShrink: 0,
                  background: stat.glow, border: `1px solid ${stat.color}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <stat.icon size={24} style={{ color: stat.color }} />
                </div>
                <div>
                  <div style={{ fontSize: '2.25rem', fontWeight: 900, color: '#F8FAFC', lineHeight: 1, letterSpacing: '-0.04em' }}>{stat.value}</div>
                  <div style={{ fontSize: '0.72rem', color: '#475569', fontWeight: 700, letterSpacing: '0.06em', marginTop: 6 }}>{stat.label.toUpperCase()}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* ── Active Directives ── */}
          <div style={{ marginBottom: '2.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#F8FAFC', letterSpacing: '-0.01em' }}>Active Tasks</h2>
              <Link href="/goals" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: '#475569', fontWeight: 600, textDecoration: 'none', letterSpacing: '0.04em', transition: 'color 0.2s' }}
                onMouseEnter={e => (e.currentTarget.style.color = '#00A3FF')}
                onMouseLeave={e => (e.currentTarget.style.color = '#475569')}>
                VIEW ALL <ArrowRight size={13} />
              </Link>
            </div>

            {loading ? (
              <div style={{ padding: '4rem', display: 'flex', justifyContent: 'center', borderRadius: '1rem', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.03)' }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                </div>
              </div>
            ) : goals.length === 0 ? (
              <div style={{
                padding: '5rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
                borderRadius: '1.25rem', border: '1px dashed rgba(0,163,255,0.15)',
                background: 'rgba(0,163,255,0.02)',
              }}>
                <div style={{ width: 64, height: 64, borderRadius: '1.125rem', background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem' }}>
                  <Target size={28} style={{ color: '#00A3FF' }} />
                </div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#F8FAFC', marginBottom: '0.75rem', letterSpacing: '-0.01em' }}>No Active Tasks</h3>
                <p style={{ fontSize: '0.875rem', color: '#475569', maxWidth: 380, lineHeight: 1.7, marginBottom: '2rem' }}>
                  Deploy a task and watch the neural agents autonomously synthesize and execute a complete strategy.
                </p>
                <Link href="/goals/new" style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '0.75rem 1.75rem', borderRadius: '0.875rem',
                  background: 'linear-gradient(135deg, #00A3FF, #006199)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff', fontSize: '0.875rem', fontWeight: 700,
                  textDecoration: 'none', boxShadow: '0 8px 32px rgba(0,163,255,0.35)',
                }}>
                  <Plus size={16} /> Deploy First Task
                </Link>
              </div>
            ) : (
              <motion.div variants={stagger.container} initial="hidden" animate="show" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {goals.slice(0, 6).map((goal) => {
                  const s = STATUS_CONFIG[goal.status] || { label: goal.status, cls: 'badge-paused', icon: Clock }
                  const StatusIcon = s.icon
                  return (
                    <motion.div key={goal.id} variants={stagger.item}>
                      <Link href={`/goals/${goal.id}`} style={{ textDecoration: 'none', display: 'block' }}>
                        <div style={{
                          padding: '1.25rem 1.5rem', borderRadius: '1rem', display: 'flex', alignItems: 'center', gap: '1.25rem',
                          background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%)',
                          border: '1px solid rgba(255,255,255,0.04)',
                          backdropFilter: 'blur(12px)', cursor: 'pointer',
                          transition: 'border-color 0.2s, box-shadow 0.2s, transform 0.2s',
                          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)',
                        }}
                          onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(0,163,255,0.25)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)' }}
                          onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)' }}>

                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                              <span className={s.cls} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                <StatusIcon size={11} style={{ flexShrink: 0 }} />
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{goal.latest_activity || s.label}</span>
                              </span>
                              <span style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 600, letterSpacing: '0.04em' }}>
                                {goal.tasks_completed}/{goal.tasks_total} ops
                              </span>
                              {goal.platforms.slice(0, 4).map(p => (
                                <span key={p} style={{ fontSize: '0.65rem', fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(255,255,255,0.05)', color: '#64748B', letterSpacing: '0.04em' }}>
                                  {PLATFORM_LABELS[p] || p.toUpperCase().slice(0, 2)}
                                </span>
                              ))}
                            </div>
                            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#E2E8F0', marginBottom: '0.75rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {goal.title}
                            </div>
                            <div className="progress-bar">
                              <div className="progress-fill" style={{ width: `${goal.progress_percent}%` }} />
                            </div>
                          </div>

                          <ArrowRight size={16} style={{ color: '#334155', flexShrink: 0 }} />
                        </div>
                      </Link>
                    </motion.div>
                  )
                })}
              </motion.div>
            )}
          </div>

          {/* ── Command Protocols ── */}
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#F8FAFC', letterSpacing: '-0.01em', marginBottom: '1.25rem' }}>Command Protocols</h2>
            <motion.div variants={stagger.container} initial="hidden" animate="show"
              style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
              {[
                { href: '/goals/new', icon: Target, title: 'Deploy Task', desc: 'Initialize autonomous campaign', color: '#00A3FF' },
                { href: '/knowledge', icon: Network, title: 'Knowledge Core', desc: 'Inject intelligence assets', color: '#22D3EE' },
                { href: '/skills', icon: Cpu, title: 'SkillForge', desc: 'Upgrade neural capabilities', color: '#10B981' },
              ].map(({ href, icon: Icon, title, desc, color }) => (
                <motion.div key={href} variants={stagger.item}>
                  <Link href={href} style={{ textDecoration: 'none', display: 'block' }}>
                    <div style={{
                      padding: '1.75rem', borderRadius: '1.125rem',
                      background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%)',
                      border: '1px solid rgba(255,255,255,0.04)', display: 'flex', flexDirection: 'column', gap: '1rem',
                      backdropFilter: 'blur(12px)', cursor: 'pointer',
                      transition: 'border-color 0.2s, transform 0.2s',
                      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)',
                    }}
                      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = `${color}44`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)' }}
                      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)' }}>
                      <div style={{ width: 48, height: 48, borderRadius: '0.875rem', background: `${color}15`, border: `1px solid ${color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Icon size={22} style={{ color }} />
                      </div>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#F8FAFC', marginBottom: 6, letterSpacing: '-0.01em' }}>{title}</div>
                        <div style={{ fontSize: '0.8rem', color: '#475569', fontWeight: 500 }}>{desc}</div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </motion.div>
          </div>

        </div>
      </main>
    </div>
  )
}
