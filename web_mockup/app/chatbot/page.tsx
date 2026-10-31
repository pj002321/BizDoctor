import ChatbotView from '@/components/ChatbotView';
export const metadata = { title: '챗봇 상담 · BizDoctor' };

// /chatbot?diagnosis=진단ID 로 들어오면 그 진단 기준으로 상담
export default async function Page({ searchParams }: { searchParams: Promise<{ diagnosis?: string }> }) {
  const { diagnosis } = await searchParams;
  return <ChatbotView diagnosisId={diagnosis} />;
}
