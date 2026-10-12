import { NextResponse, type NextRequest } from 'next/server';
import { ADMIN_COOKIE, adminSessionToken } from '@/lib/adminAuth';

// /admin, /api/admin 요청은 로그인 쿠키가 있어야 통과
export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname === '/admin/login' || pathname === '/api/admin/login') return NextResponse.next();

  const expected = await adminSessionToken();
  const cookie = req.cookies.get(ADMIN_COOKIE)?.value;
  if (expected && cookie === expected) return NextResponse.next();

  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: '관리자 로그인이 필요합니다.' }, { status: 401 });
  }
  const url = req.nextUrl.clone();
  url.pathname = '/admin/login';
  url.search = '';
  return NextResponse.redirect(url);
}

export const config = { matcher: ['/admin', '/admin/:path*', '/api/admin/:path*'] };
