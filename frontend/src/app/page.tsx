'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import {
  Target, TrendingUp, Cpu, BookOpen, Plus,
  ArrowRight, Activity, Zap, CheckCircle2, Clock, AlertCircle
} from 'lucide-react'
import api from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

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
  planning:          { label: 'Planning',    cls: 'badge-planning',   icon: Clock },
  awaiting_approval: { label: 'Needs ✓',    cls: 'badge-awaiting',   icon: AlertCircle },
  executing:         { label: 'Executing',   cls: 'badge-executing',  icon: Activity },
  monitoring:        { label: 'Monitoring',  cls: 'badge-monitoring', icon: TrendingUp },
  complete:          { label: 'Complete',    cls: 'badge-complete',   icon: CheckCircle2 },
  failed:            { label: 'Failed',      cls: 'badge-failed',     icon: AlertCircle },
}

const PLATFORM_ICONS: Record<string, string> = {
  linkedin: '💼', facebook: '👥', twitter: '🐦', tiktok: '🎵',
  instagram: '📸', youtube: '▶️', threads: '🔗',
}

export default function MissionControl() {
  const router = useRouter()
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Client-side auth guard — if no token, bail out immediately
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

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
                Mission Control
              </h1>
              <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.45)' }}>
                Your autonomous social media intelligence agency
              </p>
            </div>
            <Link href="/goals/new" className="btn-primary">
              <Plus size={16} />
              New Mission
            </Link>
          </div>
        </div>

        {/* Approval Alert */}
        {awaiting.length > 0 && (
          <div className="mb-6 p-4 rounded-2xl border animate-slide-up"
               style={{ background: 'rgba(245,158,11,0.08)', borderColor: 'rgba(245,158,11,0.3)' }}>
            <div className="flex items-center gap-3">
              <AlertCircle size={20} className="text-amber-400 flex-shrink-0" />
              <div className="flex-1">
                <div className="font-semibold text-amber-300 text-sm">
                  {awaiting.length} plan{awaiting.length > 1 ? 's' : ''} awaiting your approval
                </div>
                <div className="text-xs text-amber-400/70 mt-0.5">Review agent plans before execution begins</div>
              </div>
              <Link href={`/goals/${awaiting[0].id}/approve`} className="btn-primary text-xs px-4 py-2">
                Review → 
              </Link>
            </div>
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-4 mb-8 stagger-children">
          {[
            { label: 'Active Missions', value: activeGoals.length, icon: Target, color: '#A78BFA', glow: 'rgba(124,58,237,0.2)' },
            { label: 'Awaiting Approval', value: awaiting.length, icon: AlertCircle, color: '#FCD34D', glow: 'rgba(245,158,11,0.2)' },
            { label: 'Total Goals', value: goals.length, icon: Zap, color: '#34D399', glow: 'rgba(16,185,129,0.2)' },
          ].map((stat, i) => (
            <div key={i} className="glass-panel p-6 animate-slide-up flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0"
                   style={{ background: stat.glow }}>
                <stat.icon size={22} style={{ color: stat.color }} />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{stat.value}</div>
                <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.45)' }}>{stat.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Active Goals */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Active Missions</h2>
            <Link href="/goals" className="btn-ghost text-xs">
              View all <ArrowRight size={13} />
            </Link>
          </div>

          {loading ? (
            <div className="glass-panel p-8 flex items-center justify-center">
              <div className="flex gap-1.5">
                <div className="thinking-dot" />
                <div className="thinking-dot" />
                <div className="thinking-dot" />
              </div>
            </div>
          ) : goals.length === 0 ? (
            <div className="glass-panel p-12 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-3xl flex items-center justify-center mb-4"
                   style={{ background: 'rgba(124,58,237,0.1)' }}>
                <Target size={28} className="text-primary-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">No missions yet</h3>
              <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Brief your AI agency with a goal in plain English
              </p>
              <Link href="/goals/new" className="btn-primary">
                <Plus size={15} />
                Create your first mission
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {goals.slice(0, 5).map((goal, i) => {
                const s = STATUS_CONFIG[goal.status] || { label: goal.status, cls: 'badge-paused', icon: Clock }
                return (
                  <Link key={goal.id} href={`/goals/${goal.id}`}
                        className="glass-panel p-5 flex items-center gap-4 hover:glass-panel-active cursor-pointer block animate-slide-up"
                        style={{ animationDelay: `${i * 50}ms` }}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 mb-2">
                        <span className={s.cls}><s.icon size={10} />{s.label}</span>
                        <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                          {goal.tasks_completed}/{goal.tasks_total} tasks
                        </span>
                        {goal.platforms.slice(0,3).map(p => (
                          <span key={p} className="text-xs">{PLATFORM_ICONS[p] || '📱'}</span>
                        ))}
                      </div>
                      <div className="font-medium text-sm text-white truncate">{goal.title}</div>
                      <div className="progress-bar mt-3 w-full">
                        <div className="progress-fill" style={{ width: `${goal.progress_percent}%` }} />
                      </div>
                    </div>
                    <ArrowRight size={16} style={{ color: 'rgba(255,255,255,0.3)', flexShrink: 0 }} />
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { href: '/goals/new',  icon: Target,   title: 'New Mission',      desc: 'Brief the AI agency',           color: '#A78BFA' },
              { href: '/training',   icon: BookOpen,  title: 'Add Knowledge',    desc: 'Train with your content',       color: '#22D3EE' },
              { href: '/media',      icon: Activity,  title: 'Media Library',    desc: 'Manage assets & flyers',        color: '#34D399' },
            ].map(({ href, icon: Icon, title, desc, color }) => (
              <Link key={href} href={href}
                    className="glass-panel p-5 flex flex-col gap-3 hover:glass-panel-active cursor-pointer">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                     style={{ background: `${color}18` }}>
                  <Icon size={18} style={{ color }} />
                </div>
                <div>
                  <div className="font-semibold text-sm text-white">{title}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>{desc}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

      </main>
    </div>
  )
}
