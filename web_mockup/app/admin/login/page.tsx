'use client';
import { useState } from 'react';

export default function AdminLoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (res.ok) {
      window.location.href = '/admin';
      return;
    }
    const body = await res.json().catch(() => ({}));
    setError(body.error ?? '로그인에 실패했습니다.');
  }

  return (
    <div className="page" style={{ maxWidth: 420, margin: '0 auto' }}>
      <div className="page-head">
        <span className="badge badge-outline" style={{ justifySelf: 'start' }}>관리자 전용</span>
        <h1>관리자 로그인</h1>
        <p>운영 대시보드는 관리자 비밀번호를 입력해야 볼 수 있습니다.</p>
      </div>
      <form className="card stack" onSubmit={submit}>
        <div className="field">
          <label htmlFor="admin-password">비밀번호</label>
          <input
            id="admin-password"
            type="password"
            className="input"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={loading || !password}>
          {loading ? '확인 중…' : '로그인'}
        </button>
      </form>
    </div>
  );
}
