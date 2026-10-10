// POST /api/chatbot — 챗봇 상담 (목업: 정책 문서 키워드 매칭. 실제 LLM+RAG는 백엔드에서 연결)
import { NextRequest, NextResponse } from 'next/server';
import { POLICY_DOCS } from '@/lib/policies';
import { store } from '@/lib/store';
import type { ChatbotRequest, ChatbotResponse } from '@/lib/types';

const KEYWORDS: { words: RegExp; docIds: string[] }[] = [
  { words: /빚|대출|상환|연체|이자|채무/, docIds: ['POL_001', 'POL_002', 'POL_006'] },
  { words: /매출|급감|폭락|긴급|운전자금/, docIds: ['POL_003', 'POL_004'] },
  { words: /폐업|재기|재창업|그만/, docIds: ['POL_005'] },
  { words: /임대료|월세|인건비|재료비|원가/, docIds: ['POL_004', 'POL_006', 'POL_007'] },
  { words: /청년/, docIds: ['POL_008'] },
  { words: /디지털|바우처|온라인/, docIds: ['POL_007'] },
];

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Partial<ChatbotRequest>;
  const message = String(body.message ?? '').trim();
  if (!message) return NextResponse.json({ error: '질문을 입력해 주세요.' }, { status: 400 });
  if (message.length > 500) return NextResponse.json({ error: '질문은 500자 이내로 입력해 주세요.' }, { status: 400 });

  const ids = new Set(KEYWORDS.filter((k) => k.words.test(message)).flatMap((k) => k.docIds));
  const docs = POLICY_DOCS.filter((d) => ids.has(d.docId)).slice(0, 3);

  let answer: string;
  const links: ChatbotResponse['links'] = [];
  if (/진단|등급|위험|우리 가게|내 가게/.test(message)) {
    answer = '내 가게의 위험 등급은 행정동·업종·최근 3개월 매출을 입력하면 확인할 수 있어요. 진단 후에는 결과에 맞는 지원사업과 AI 리포트도 볼 수 있습니다.';
    links.push({ label: '사업장 진단하기', href: '/diagnosis' });
  } else if (/상권|동네|지도|폐업률/.test(message)) {
    answer = '동네·업종별 폐업 통계는 상권 신호등 지도에서 볼 수 있어요. 자치구를 고르면 행정동별 성적표가 나옵니다.';
    links.push({ label: '상권 신호등 보기', href: '/market' });
  } else if (docs.length) {
    answer = `말씀하신 상황에는 이런 지원사업을 먼저 확인해 보세요.\n${docs.map((d) => `- ${d.title} (${d.agency})`).join('\n')}\n정확한 대상과 조건은 소관기관 공고에서 꼭 확인해 주세요.`;
    links.push({ label: '내 가게 맞춤 추천 받기', href: '/diagnosis' });
  } else {
    answer = '지금은 정책자금, 사업장 진단, 상권 정보에 대해서만 답할 수 있어요. 예: "대출 상환이 힘들어요", "임대료 지원이 있나요?"';
  }

  store.metrics.llmTokens += Math.round((message.length + answer.length) / 2);
  const res: ChatbotResponse = { answer, sources: docs.map((d) => ({ docId: d.docId, title: d.title })), links };
  return NextResponse.json(res);
}
