// POST /api/admin/login — 관리자 비밀번호 확인 후 로그인 쿠키 발급
import { NextResponse } from 'next/server';
import { ADMIN_COOKIE, ADMIN_SESSION_HOURS, adminSessionToken } from '@/lib/adminAuth';

export async function POST(req: Request) {
  const token = await adminSessionToken();
  if (!token) {
    return NextResponse.json({ error: '서버에 관리자 비밀번호가 설정되지 않았습니다. (.env.local)' }, { status: 500 });
  }
  const { password } = await req.json().catch(() => ({ password: '' }));
  if (password !== process.env.ADMIN_PASSWORD) {
    return NextResponse.json({ error: '비밀번호가 올바르지 않습니다.' }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(ADMIN_COOKIE, token, {
    httpOnly: true, // 브라우저 스크립트에서 읽을 수 없음
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * ADMIN_SESSION_HOURS,
  });
  return res;
}
