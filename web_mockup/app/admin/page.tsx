import AdminNav from '@/components/AdminNav';
import AdminView from '@/components/AdminView';
import { POLICY_DOCS } from '@/lib/policies';
export const metadata = { title: '운영 · BizDoctor' };
export default function Page() {
  return (
    <>
      <AdminNav current="dashboard" />
      <AdminView docs={POLICY_DOCS} />
    </>
  );
}
