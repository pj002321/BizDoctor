/** @type {import('next').NextConfig} */
const nextConfig = {
  // 백엔드(FastAPI)가 준비되면 BACKEND_URL을 지정해 /api/* 요청을 그쪽으로 넘긴다.
  // 예) set BACKEND_URL=http://localhost:8000 && npm run dev   (Windows cmd)
  // beforeFiles: 목업 route handler(app/api)보다 먼저 적용되어 실제 백엔드가 우선함
  async rewrites() {
    const backend = process.env.BACKEND_URL;
    return {
      beforeFiles: [
        // 첫 화면(/)은 랜딩 페이지(public/landing.html)를 보여줌
        { source: '/', destination: '/landing.html' },
        ...(backend ? [{ source: '/api/:path*', destination: `${backend}/api/:path*` }] : []),
      ],
    };
  },
};
export default nextConfig;
