/**
 * Digital Force — Typed API Client
 * Full coverage of all backend endpoints.
 */

import { getToken, clearToken } from './auth'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }

  if (token) headers['Authorization'] = `Bearer ${token}`

  // Only set Content-Type for non-FormData bodies
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    // Only auto-logout on protected routes, not on the login/register endpoints themselves.
    // We use clearToken() (not localStorage.clear()) so only auth data is wiped,
    // and the cookie is also cleared for middleware consistency.
    const isAuthEndpoint = path.startsWith('/api/auth/')
    if (!isAuthEndpoint && typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      clearToken()
      window.location.replace('/login')
    }
    let msg = 'Invalid credentials'
    try {
      const err = await res.json()
      msg = err.detail || err.message || msg
    } catch { /* ignore */ }
    throw new ApiError(msg, 401)
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const err = await res.json()
      msg = err.detail || err.message || msg
    } catch { /* ignore */ }
    throw new ApiError(msg, res.status)
  }

  if (res.status === 204) return {} as T
  return res.json() as Promise<T>
}

const GET  = <T>(path: string) => request<T>(path, { method: 'GET' })
const POST = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) })
const PUT  = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
const DEL  = <T>(path: string) => request<T>(path, { method: 'DELETE' })

// ─── Typed response shapes ─────────────────────────────────

export interface Goal {
  id: string
  title: string
  description: string
  status: string
  priority: string
  progress_percent: number
  tasks_total: number
  tasks_completed: number
  tasks_failed: number
  platforms: string[]
  plan: CampaignPlan | null
  success_metrics: Record<string, unknown>
  agent_logs: AgentLog[]
  created_at: string
  deadline?: string
  approved_at?: string
}

export interface CampaignPlan {
  campaign_name: string
  campaign_summary: string
  duration_days: number
  tasks: CampaignTask[]
}

export interface CampaignTask {
  id: string
  title: string
  platform: string
  content_type: string
  scheduled_at: string
  content_brief: string
  hashtags: string[]
  asset_id?: string
  status: string
}

export interface AgentLog {
  id: string
  agent: string
  level: string
  thought: string
  action?: string
  created_at: string
}

export interface Skill {
  id: string
  name: string
  display_name: string
  description: string
  code?: string
  sandbox_test_result?: string
  test_passed: boolean
  usage_count: number
  is_active: boolean
  created_at: string
}

export interface MediaAsset {
  id: string
  filename: string
  original_filename: string
  public_url: string
  asset_type: string
  mime_type: string
  file_size_bytes: number
  width?: number
  height?: number
  ai_description?: string
  auto_tags?: string[]
  usage_count: number
  created_at: string
}

export interface TrainingDoc {
  id: string
  title: string
  source_type: string
  content_summary?: string
  chunk_count: number
  processing_status: string
  category?: string
  tags?: string[]
  created_at: string
}

export interface AnalyticsOverview {
  total_goals: number
  goals_completed: number
  goals_executing: number
  goals_awaiting_approval: number
  goals_planning: number
  goals_monitoring: number
  goals_failed: number
  total_posts: number
  total_posts_published: number
  total_impressions: number
  total_likes: number
  total_comments: number
  total_shares: number
  total_reach: number
  avg_engagement_rate: number
  posts_per_day: { date: string; count: number }[]
  platform_breakdown: Record<string, number>
  platform_engagement: Record<string, { likes: number; comments: number; shares: number; impressions: number }>
  status_distribution: Record<string, number>
  skill_count: number
  training_doc_count: number
  media_asset_count: number
}

// ─── API client ──────────────────────────────────────────────

const api = {
  auth: {
    login: (body: { email: string; password: string }) =>
      POST<{ access_token: string; token_type: string }>('/api/auth/login', body),
    register: (body: { email: string; password: string; username: string; full_name?: string }) =>
      POST<{ access_token: string; token_type: string }>('/api/auth/register', body),
    me: () => GET<{ sub: string; email: string; role: string }>('/api/auth/me'),
  },

  goals: {
    list: () => GET<Goal[]>('/api/goals'),
    get: (id: string) => GET<Goal>(`/api/goals/${id}`),
    create: (body: {
      description: string
      title?: string
      platforms?: string[]
      deadline?: string
      asset_ids?: string[]
      success_metrics?: Record<string, unknown>
      constraints?: Record<string, unknown>
      priority?: string
    }) => POST<{ id: string; title: string; status: string; message: string }>('/api/goals', body),
    approve: (id: string, body: {
      approved: boolean
      notes?: string
      modifications?: Record<string, unknown>
    }) => POST<{ status: string; message: string }>(`/api/goals/${id}/approve`, body),
    kpis: (id: string) => GET<Record<string, unknown>>(`/api/goals/${id}/kpis`),
  },

  training: {
    list: () => GET<TrainingDoc[]>('/api/training'),
    get: (id: string) => GET<TrainingDoc>(`/api/training/${id}`),
    upload: (formData: FormData) =>
      POST<{ id: string; title: string; status: string }>('/api/training/upload', formData),
    uploadUrl: (url: string, category: string) =>
      POST<{ id: string; title: string; status: string }>('/api/training/url', { url, category }),
    reindex: (id: string) =>
      POST<{ status: string; message: string }>(`/api/training/${id}/reindex`),
    delete: (id: string) => DEL<void>(`/api/training/${id}`),
  },

  media: {
    list: () => GET<MediaAsset[]>('/api/media'),
    upload: (formData: FormData) =>
      POST<MediaAsset>('/api/media/upload', formData),
    delete: (id: string) => DEL<void>(`/api/media/${id}`),
  },

  skills: {
    list: () => GET<Skill[]>('/api/skills'),
    get: (id: string) => GET<Skill>(`/api/skills/${id}`),
    toggle: (id: string) => request<Skill>(`/api/skills/${id}/toggle`, { method: 'PATCH' }),
    delete: (id: string) => DEL<void>(`/api/skills/${id}`),
  },

  analytics: {
    overview: () => GET<AnalyticsOverview>('/api/analytics/overview'),
  },

  settings: {
    get: () => GET<Record<string, unknown>>('/api/settings'),
    status: () => GET<Record<string, unknown>>('/api/settings/status'),
    update: (body: Record<string, unknown>) =>
      PUT<{ status: string; updated_keys: string[]; message: string }>('/api/settings', body),
    resetOverrides: () => DEL<{ status: string }>('/api/settings/overrides'),
  },

  chat: {
    history: () => GET<{ id: string; role: 'user' | 'assistant'; content: string; created_at: string }[]>('/api/chat/history'),
    clearHistory: () => DEL<{ status: string }>('/api/chat/history'),
    streamUrl: () => `${BASE}/api/chat/stream`,
  },

  stream: {
    goalLogs: (goalId: string) => `${BASE}/api/stream/goal/${goalId}`,
  },
}

export default api
export { BASE, ApiError }
