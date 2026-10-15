import SharedView from '@/components/SharedView';
export const metadata = { title: '공유된 진단 결과 · BizDoctor' };
export default async function Page({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <SharedView token={token} />;
}
