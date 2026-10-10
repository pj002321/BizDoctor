// 관리자 로그인 쿠키 (middleware와 로그인 API가 같이 사용)
export const ADMIN_COOKIE = 'admin_session';
export const ADMIN_SESSION_HOURS = 8;

// 비밀번호 자체를 쿠키에 넣지 않고 해시값을 넣음
export async function adminSessionToken(): Promise<string | null> {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) return null;
  const secret = process.env.ADMIN_SECRET ?? '';
  const data = new TextEncoder().encode(`${password}:${secret}`);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, '0')).join('');
}
