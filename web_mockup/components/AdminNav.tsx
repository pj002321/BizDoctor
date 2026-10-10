import Link from 'next/link';
import AdminLogout from './AdminLogout';

// 관리자 화면 상단 메뉴
export default function AdminNav({ current }: { current: 'dashboard' | 'insights' }) {
  return (
    <div className="row between" style={{ marginBottom: 8 }}>
      <div className="row">
        <Link href="/admin" className={`btn btn-sm${current === 'dashboard' ? ' btn-primary' : ''}`}>운영 대시보드</Link>
        <Link href="/admin/insights" className={`btn btn-sm${current === 'insights' ? ' btn-primary' : ''}`}>고객 분석 AI</Link>
      </div>
      <AdminLogout />
    </div>
  );
}
