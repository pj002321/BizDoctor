import "server-only";
import { createClient } from "@supabase/supabase-js";

/**
 * 서버 전용 Supabase 클라이언트. 로그인이 없는 서비스라 사용자 세션 쿠키를 다루지 않는다.
 *
 * - 상권 집계 테이블(F-MAP)을 Server Component 가 직접 읽을 때 쓴다.
 * - 키는 anon 키다. 읽기 권한은 RLS select 정책이 정한다 — service role 키는 쓰지 않는다.
 * - 값을 모듈 최상위가 아니라 함수 안에서 읽는 이유: 빌드 시점에 env 가 없어도 빌드는 통과해야 한다.
 */
export function getSupabase() {
  const url = process.env.SUPABASE_URL?.trim();
  const key = process.env.SUPABASE_ANON_KEY?.trim();
  if (!url || !key) {
    throw new Error(
      "SUPABASE_URL · SUPABASE_ANON_KEY 가 비었습니다. .env.local 을 확인하세요.",
    );
  }
  return createClient(url, key, { auth: { persistSession: false } });
}
