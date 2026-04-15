import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/login', '/landing', '/api', '/_next', '/favicon.ico']

/**
 * Next.js Edge Middleware — MUST be named `middleware` to be executed.
 * Protects all private routes by checking the df_token cookie.
 * The cookie is set alongside localStorage during login (see auth.ts).
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Check for token in cookies (set at login for SSR support)
  const token = request.cookies.get('df_token')?.value

  if (!token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('from', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
}

