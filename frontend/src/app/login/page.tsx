'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'

// Login page now redirects — authenticated users to /overview, guests to /landing
export default function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/overview')
    } else {
      // Redirect to the landing page which has the auth modal built-in
      router.replace('/landing')
    }
  }, [router])

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
