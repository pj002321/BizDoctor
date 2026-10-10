'use client';

export default function AdminLogout() {
  async function logout() {
    await fetch('/api/admin/logout', { method: 'POST' });
    window.location.href = '/admin/login';
  }
  return <button className="btn btn-sm" onClick={logout}>로그아웃</button>;
}
