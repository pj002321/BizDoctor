// POST /api/admin/logout — 로그인 쿠키 삭제
import { NextResponse } from 'next/server';
import { ADMIN_COOKIE } from '@/lib/adminAuth';

export async function POST() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(ADMIN_COOKIE, '', { path: '/', maxAge: 0 });
  return res;
}
