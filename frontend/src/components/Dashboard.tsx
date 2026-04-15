'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import {
  Target, TrendingUp, Cpu, Network, Plus,
  ArrowRight, Activity, Zap, CheckCircle2, Clock, AlertCircle
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
}

const STATUS_CONFIG: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
  planning:          { label: 'Synthesizing', cls: 'badge-planning',   icon: Clock },
  awaiting_approval: { label: 'Approval Req', cls: 'badge-awaiting',   icon: AlertCircle },
  executing:         { label: 'Executing',    cls: 'badge-executing',  icon: Activity },
  monitoring:        { label: 'Monitoring',   cls: 'badge-monitoring', icon: TrendingUp },
  complete:          { label: 'Complete',     cls: 'badge-complete',   icon: CheckCircle2 },
  failed:            { label: 'Failed',       cls: 'badge-failed',     icon: AlertCircle },
}

const PLATFORM_ICONS: Record<string, string> = {
  linkedin: '💼', facebook: '👥', twitter: '🐦', tiktok: '🎵',
  instagram: '📸', youtube: '▶️', threads: '🔗',
}

export default function Dashboard() {
  const router = useRouter()
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.goals.list()
      .then(setGoals)
      .catch(() => setGoals([]))
      .finally(() => setLoading(false))
  }, [router])

  const activeGoals = goals.filter(g => ['planning','awaiting_approval','executing','monitoring'].includes(g.status))
  const awaiting = goals.filter(g => g.status === 'awaiting_approval')

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">

        {/* Header */}
        <div className="mb-8 animate-slide-up">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight"
                  style={{ background: 'linear-gradient(135deg, #fff 30%, rgba(255,255,255,0.5))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Command Center
              </h1>
              <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
                Autonomous Digital Media Intelligent Agency
              </p>
            </div>
            <Link href="/goals/new" className="btn-primary">
              <Plus size={16} />
              Deploy Directive
            </Link>
          </div>
        </div>

        {/* Approval Alert */}
        {awaiting.length > 0 && (
          <div className="mb-6 p-5 rounded-2xl glass-panel animate-slide-up"
               style={{ borderColor: 'rgba(245,158,11,0.3)', boxShadow: '0 0 40px rgba(245,158,11,0.1)' }}>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-amber-500/10">
                <AlertCircle size={20} className="text-amber-400" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-amber-300 text-sm">
                  {awaiting.length} protocol{awaiting.length > 1 ? 's' : ''} awaiting authorization
                </div>
                <div className="text-xs text-amber-400/70 mt-1">Review neural agent synthesis before execution begins</div>
              </div>
              <Link href={`/goals/${awaiting[0].id}/approve`} className="btn-primary text-xs px-5 py-2.5">
                Authorize → 
              </Link>
            </div>
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-5 mb-8 stagger-children">
          {[
            { label: 'Active Directives', value: activeGoals.length, icon: Target, color: '#00A3FF', glow: 'rgba(0,163,255,0.15)' },
            { label: 'Awaiting Authorization', value: awaiting.length, icon: AlertCircle, color: '#FCD34D', glow: 'rgba(245,158,11,0.15)' },
            { label: 'Total Operations', value: goals.length, icon: Zap, color: '#34D399', glow: 'rgba(16,185,129,0.15)' },
          ].map((stat, i) => (
            <div key={i} className="glass-panel p-6 animate-slide-up flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0"
                   style={{ background: stat.glow, border: `1px solid ${stat.color}30` }}>
                <stat.icon size={24} style={{ color: stat.color }} />
              </div>
              <div>
                <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{stat.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Active Goals */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white tracking-wide">Active Directives</h2>
            <Link href="/goals" className="btn-ghost text-xs font-semibold uppercase tracking-wider">
              View all <ArrowRight size={13} />
            </Link>
          </div>

          {loading ? (
            <div className="glass-panel p-8 flex items-center justify-center">
              <div className="flex gap-1.5 pt-4 pb-4">
                <div className="thinking-dot" />
                <div className="thinking-dot" />
                <div className="thinking-dot" />
              </div>
            </div>
          ) : goals.length === 0 ? (
            <div className="glass-panel p-16 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 rounded-[2rem] flex items-center justify-center mb-5"
                   style={{ background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)' }}>
                <Target size={32} className="text-primary-400" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">No Active Directives</h3>
              <p className="text-sm mb-8 max-w-sm" style={{ color: '#94A3B8' }}>
                Deploy a new autonomous directive and watch the neural agents synthesize a strategy.
              </p>
              <Link href="/goals/new" className="btn-primary px-6 py-3">
                <Plus size={16} />
                Deploy First Directive
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {goals.slice(0, 5).map((goal, i) => {
                const s = STATUS_CONFIG[goal.status] || { label: goal.status, cls: 'badge-paused', icon: Clock }
                return (
                  <Link key={goal.id} href={`/goals/${goal.id}`}
                        className="glass-panel p-6 flex items-center gap-5 hover:glass-panel-active cursor-pointer block animate-slide-up transition-transform hover:-translate-y-0.5"
                        style={{ animationDelay: `${i * 50}ms` }}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-3">
                        <span className={s.cls} style={{ padding: '0.35rem 0.75rem' }}><s.icon size={12} />{s.label}</span>
                        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                          {goal.tasks_completed}/{goal.tasks_total} operations
                        </span>
                        <div className="flex gap-2">
                          {goal.platforms.slice(0,3).map(p => (
                            <span key={p} className="text-xs grayscale opacity-70">{PLATFORM_ICONS[p] || '📱'}</span>
                          ))}
                        </div>
                      </div>
                      <div className="font-semibold text-base text-white truncate">{goal.title}</div>
                      <div className="progress-bar mt-4 w-full">
                        <div className="progress-fill" style={{ width: `${goal.progress_percent}%` }} />
                      </div>
                    </div>
                    <ArrowRight size={18} style={{ color: '#475569', flexShrink: 0 }} className="mr-2" />
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="font-semibold text-white tracking-wide mb-5">Command Protocols</h2>
          <div className="grid grid-cols-3 gap-5">
            {[
              { href: '/goals/new',  icon: Target,    title: 'Deploy Directive',   desc: 'Initialize autonomous campaign',  color: '#00A3FF' },
              { href: '/knowledge',  icon: Network,   title: 'Knowledge Core',     desc: 'Inject text & media assets',      color: '#22D3EE' },
              { href: '/skills',     icon: Cpu,       title: 'SkillForge',         desc: 'Upgrade neural capabilities',     color: '#10B981' },
            ].map(({ href, icon: Icon, title, desc, color }) => (
               <Link key={href} href={href}
                    className="glass-panel p-6 flex flex-col gap-4 hover:glass-panel-active cursor-pointer transition-transform hover:-translate-y-1">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg"
                     style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                  <Icon size={22} style={{ color }} />
                </div>
                <div>
                  <div className="font-bold text-sm text-white tracking-wide">{title}</div>
                  <div className="text-xs mt-1.5 font-medium text-slate-400">{desc}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

      </main>
    </div>
  )
}
