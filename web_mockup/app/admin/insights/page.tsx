import AdminInsights from '@/components/AdminInsights';
import AdminNav from '@/components/AdminNav';
export const metadata = { title: '고객 분석 AI · BizDoctor' };
export default function Page() {
  return (
    <>
      <AdminNav current="insights" />
      <AdminInsights />
    </>
  );
}
