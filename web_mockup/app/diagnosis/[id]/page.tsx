import DiagnosisResult from '@/components/DiagnosisResult';
export const metadata = { title: '진단 결과 · BizDoctor' };
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DiagnosisResult id={id} />;
}
