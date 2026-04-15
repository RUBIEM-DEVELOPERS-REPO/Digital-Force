'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import { Plus, Target, ArrowRight, Clock, Activity, CheckCircle2, AlertCircle, TrendingUp, Filter } from 'lucide-react'
import api from '@/lib/api'

const STATUS_CONFIG: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
  planning:          { label: 'Synthesizing',  cls: 'badge-planning',   icon: Clock },
  awaiting_approval: { label: 'Authorization', cls: 'badge-awaiting',   icon: AlertCircle },
  executing:         { label: 'Executing',     cls: 'badge-executing',  icon: Activity },
  monitoring:        { label: 'Monitoring',    cls: 'badge-monitoring', icon: TrendingUp },
  complete:          { label: 'Complete',      cls: 'badge-complete',   icon: CheckCircle2 },
  failed:            { label: 'Failed',        cls: 'badge-failed',     icon: AlertCircle },
}

const PRIORITY_COLORS: Record<string, { color: string; label: string }> = {
  urgent: { color: '#EF4444', label: 'URGENT' },
  high:   { color: '#F59E0B', label: 'HIGH' },
  normal: { color: '#00A3FF', label: 'NORMAL' },
  low:    { color: '#475569', label: 'LOW' },
}

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LI', facebook: 'FB', twitter: 'X', tiktok: 'TK',
  instagram: 'IG', youtube: 'YT', threads: 'TH',
}

interface Goal {
  id: string; title: string; status: string; priority: string
  progress_percent: number; tasks_total: number; tasks_completed: number
  platforms: string[]; created_at: string; deadline?: string
}

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.06 } } },
  item: { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: [0.4,0,0.2,1] } } },
}

export default function DirectivesPage() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    api.goals.list().then(setGoals).finally(() => setLoading(false))
  }, [])

  const filtered = statusFilter ? goals.filter(g => g.status === statusFilter) : goals

  const filterTabs = [
    { id: '', label: 'All', count: goals.length },
    ...Object.entries(STATUS_CONFIG).map(([id, v]) => ({
      id, label: v.label, count: goals.filter(g => g.status === id).length
    }))
  ]

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* ── Header ── */}
        <div style={{ padding: '3rem 3rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
                  DIGITAL FORCE — OPERATIONS
                </div>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.035em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, marginBottom: '0.625rem' }}>
                  Directives
                </h1>
                <p style={{ fontSize: '0.875rem', color: '#475569' }}>
                  {goals.length} total operation{goals.length !== 1 ? 's' : ''} · {goals.filter(g => ['executing','monitoring','planning'].includes(g.status)).length} active
                </p>
              </div>
              <Link href="/goals/new" style={{
                display: 'inline-flex', alignItems: 'center', gap: 10,
                padding: '0.75rem 1.75rem', borderRadius: '0.875rem',
                background: 'linear-gradient(135deg, #00A3FF, #006199)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
                fontSize: '0.875rem', fontWeight: 700, cursor: 'pointer',
                boxShadow: '0 8px 32px rgba(0,163,255,0.35)',
                textDecoration: 'none', letterSpacing: '0.03em',
              }}>
                <Plus size={16} /> Deploy Directive
              </Link>
            </div>
          </motion.div>
        </div>

        <div style={{ padding: '2rem 3rem' }}>

          {/* ── Status Filters ── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            style={{ display: 'flex', gap: 6, marginBottom: '1.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <Filter size={14} style={{ color: '#334155', marginRight: 4 }} />
            {filterTabs.map(tab => (
              <button key={tab.id} onClick={() => setStatusFilter(tab.id)}
                style={{
                  padding: '0.45rem 0.875rem', borderRadius: 8, fontSize: '0.78rem', fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap',
                  background: statusFilter === tab.id ? 'rgba(0,163,255,0.15)' : 'rgba(255,255,255,0.03)',
                  color: statusFilter === tab.id ? '#33BAFF' : '#64748B',
                  border: `1px solid ${statusFilter === tab.id ? 'rgba(0,163,255,0.3)' : 'rgba(255,255,255,0.05)'}`,
                }}>
                {tab.label}
                <span style={{ marginLeft: 6, opacity: 0.6 }}>({tab.count})</span>
              </button>
            ))}
          </motion.div>

          {/* ── Goals List ── */}
          {loading ? (
            <div style={{ padding: '5rem', display: 'flex', justifyContent: 'center', borderRadius: '1rem', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.03)' }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: '6rem 2rem', textAlign: 'center', borderRadius: '1.25rem', border: '1px dashed rgba(0,163,255,0.1)', background: 'rgba(0,163,255,0.02)' }}>
              <div style={{ width: 64, height: 64, borderRadius: '1.125rem', background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
                <Target size={28} style={{ color: '#00A3FF' }} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#475569', marginBottom: '0.5rem' }}>No directives found</h3>
              <p style={{ fontSize: '0.82rem', color: '#334155', marginBottom: '1.75rem' }}>
                {statusFilter ? 'No operations match this filter' : 'Deploy your first autonomous directive to begin'}
              </p>
              {!statusFilter && (
                <Link href="/goals/new" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0.75rem 1.75rem', borderRadius: '0.875rem', background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '0.875rem', fontWeight: 700, textDecoration: 'none', boxShadow: '0 8px 32px rgba(0,163,255,0.35)' }}>
                  <Plus size={15} /> Deploy First Directive
                </Link>
              )}
            </div>
          ) : (
            <motion.div variants={stagger.container} initial="hidden" animate="show"
              style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {filtered.map(goal => {
                const s = STATUS_CONFIG[goal.status] || { label: goal.status, cls: 'badge-paused', icon: Clock }
                const StatusIcon = s.icon
                const pColor = PRIORITY_COLORS[goal.priority] || PRIORITY_COLORS.normal

                return (
                  <motion.div key={goal.id} variants={stagger.item}>
                    <Link href={`/goals/${goal.id}`} style={{ textDecoration: 'none', display: 'block' }}>
                      <div style={{
                        padding: '1.375rem 1.5rem', borderRadius: '1rem', display: 'flex', alignItems: 'center', gap: '1.25rem',
                        background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)',
                        border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)',
                        cursor: 'pointer', transition: 'border-color 0.2s, transform 0.2s',
                        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
                      }}
                        onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(0,163,255,0.25)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)' }}
                        onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)' }}>

                        {/* Priority glow line */}
                        <div style={{ width: 3, height: 40, borderRadius: 3, flexShrink: 0, background: pColor.color, boxShadow: `0 0 12px ${pColor.color}80` }} />

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                            <span className={s.cls} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.72rem' }}>
                              <StatusIcon size={11} />{s.label}
                            </span>
                            {goal.platforms.slice(0, 4).map(p => (
                              <span key={p} style={{ fontSize: '0.65rem', fontWeight: 700, padding: '2px 7px', borderRadius: 4, background: 'rgba(255,255,255,0.05)', color: '#64748B', letterSpacing: '0.04em' }}>
                                {PLATFORM_LABELS[p] || p.toUpperCase().slice(0, 2)}
                              </span>
                            ))}
                            {goal.deadline && (
                              <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#475569', fontWeight: 500 }}>
                                Due {new Date(goal.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#E2E8F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '0.875rem', letterSpacing: '-0.01em' }}>
                            {goal.title}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div className="progress-bar" style={{ flex: 1 }}>
                              <div className="progress-fill" style={{ width: `${goal.progress_percent}%` }} />
                            </div>
                            <span style={{ fontSize: '0.72rem', color: '#475569', fontWeight: 600, flexShrink: 0, letterSpacing: '0.04em' }}>
                              {goal.tasks_completed}/{goal.tasks_total} OPS
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.65rem', fontWeight: 700, color: pColor.color, letterSpacing: '0.06em' }}>{pColor.label}</div>
                          </div>
                          <ArrowRight size={16} style={{ color: '#334155' }} />
                        </div>
                      </div>
                    </Link>
                  </motion.div>
                )
              })}
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}
