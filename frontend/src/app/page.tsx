'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'

// Root route: authenticated users → /overview, guests → /landing
export default function RootPage() {
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/overview')
    } else {
      router.replace('/landing')
    }
  }, [router])

  // Render nothing while redirecting
  return (
    <div style={{
      minHeight: '100vh', background: '#080B12',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <span className="thinking-dot" />
        <span className="thinking-dot" />
        <span className="thinking-dot" />
      </div>
    </div>
  )
}
