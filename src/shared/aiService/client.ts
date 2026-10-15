import "server-only";

/**
 * ai-service(FastAPI) 호출. 서버에서만 부른다 — 토큰이 브라우저로 나가면 LLM 엔드포인트가 열린다.
 *
 * ai-service 는 공개 도메인이 없고 내부망 주소(AI_SERVICE_URL)로만 닿는다.
 * `X-Service-Token` 은 ai-service 의 `require_service_token` 과 같은 값이어야 한다.
 */
export async function aiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const base = process.env.AI_SERVICE_URL?.trim();
  const token = process.env.AI_SERVICE_TOKEN?.trim();
  if (!base || !token) {
    throw new Error(
      "AI_SERVICE_URL · AI_SERVICE_TOKEN 이 비었습니다. .env.local 을 확인하세요.",
    );
  }
  const headers = new Headers(init.headers);
  headers.set("X-Service-Token", token);
  return fetch(new URL(path, base), { ...init, headers, cache: "no-store" });
}
