import MethodPanel from '@/components/MethodPanel';
import { DISCLAIMER } from '@/lib/report';
export const metadata = { title: '계산 방법 · BizDoctor' };
export default function Page() {
  return (
    <div className="page" style={{ maxWidth: 820 }}>
      <div className="page-head"><h1>계산 방법과 한계</h1><p>심사·발표 대응용으로 모델 한계를 그대로 공개합니다.</p></div>
      <MethodPanel open />
      <p className="notice">{DISCLAIMER}</p>
    </div>
  );
}
