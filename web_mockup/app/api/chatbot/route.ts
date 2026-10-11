// POST /api/chatbot — 서비스 챗봇 (목업: 규칙 기반 답변. 실제 LLM+RAG는 백엔드에서 연결)
// diagnosisId가 있으면 그 진단 결과 기준으로 답변 (기존 리포트 Q&A 통합)
import { NextRequest, NextResponse } from 'next/server';
import { POLICY_DOCS } from '@/lib/policies';
import { DIAG_GRADE, RISK_TYPE_META } from '@/lib/risk';
import { CHAT_LIMIT, getDiagnosis, store } from '@/lib/store';
import type { ChatbotRequest, ChatbotResponse, SignalResponse } from '@/lib/types';

const KEYWORDS: { words: RegExp; docIds: string[] }[] = [
  { words: /빚|대출|상환|연체|이자|채무/, docIds: ['POL_001', 'POL_002', 'POL_006'] },
  { words: /매출|급감|폭락|긴급|운전자금/, docIds: ['POL_003', 'POL_004'] },
  { words: /폐업|재기|재창업|그만/, docIds: ['POL_005'] },
  { words: /임대료|월세|인건비|재료비|원가/, docIds: ['POL_004', 'POL_006', 'POL_007'] },
  { words: /청년/, docIds: ['POL_008'] },
  { words: /디지털|바우처|온라인/, docIds: ['POL_007'] },
];

function findDocs(message: string) {
  const ids = new Set(KEYWORDS.filter((k) => k.words.test(message)).flatMap((k) => k.docIds));
  return POLICY_DOCS.filter((d) => ids.has(d.docId)).slice(0, 3);
}

// 진단 결과 기준 답변
function answerWithDiagnosis(q: string, d: SignalResponse): Omit<ChatbotResponse, 'remaining'> {
  const doc = POLICY_DOCS.find((p) => q.includes(p.title.split(' ')[0]));
  if (doc) {
    return {
      answer: `${doc.title}: ${doc.content} (소관: ${doc.agency}, 한도: ${doc.limit}, 금리: ${doc.rate}) 최종 조건은 공고에서 확인이 필요합니다.`,
      sources: [{ docId: doc.docId, title: doc.title }], links: [],
    };
  }
  if (/등급|왜|이유|원인/.test(q)) {
    return {
      answer: `진단 등급은 ${DIAG_GRADE[d.riskLevel].grade}(${DIAG_GRADE[d.riskLevel].label})이며, 추정 원인은 ${RISK_TYPE_META[d.riskType].name}입니다. 같은 업종 내 폐업 위험 상위 ${d.context.topPercent}% 위치와 최근 3개월 매출 지수(${d.revenueIndex.join(' → ')})가 반영되었습니다.`,
      sources: [], links: [],
    };
  }
  if (/점수|score/.test(q)) {
    return {
      answer: d.scoreMethod === 'six_month_drop'
        ? `위험 점수 ${d.score}점은 이전 3개월 대비 최근 3개월 매출 감소율을 0~100으로 환산한 값입니다.`
        : `위험 점수 ${d.score}점은 최근 3개월 매출 지수의 기울기로 추정한 값입니다. 이전 3개월 매출을 함께 입력하면 표준 산식으로 계산됩니다.`,
      sources: [], links: [],
    };
  }
  if (/신청|어디|방법|지원/.test(q)) {
    return {
      answer: d.solutions.length
        ? `추천된 지원사업: ${d.solutions.map((s) => `${s.title}(${s.agency})`).join(', ')}. 신청 경로는 각 소관기관 공고를 확인해 주세요.`
        : '현재 진단 유형에 연결된 지원사업이 없습니다.',
      sources: d.solutions.map((s) => ({ docId: s.solutionId, title: s.title })), links: [],
    };
  }
  return {
    answer: '진단 결과와 지원사업 문서 범위에서만 답변할 수 있습니다. 등급 이유, 점수 산식, 지원사업 신청 방법 등을 물어봐 주세요.',
    sources: [], links: [],
  };
}

// 진단 없이 들어온 일반 상담
function answerGeneral(message: string): ChatbotResponse {
  const docs = findDocs(message);
  if (/진단|등급|위험|우리 가게|내 가게/.test(message)) {
    return {
      answer: '내 가게의 위험 등급은 행정동·업종·최근 3개월 매출을 입력하면 확인할 수 있어요. 진단 후에는 결과에 맞는 지원사업과 AI 리포트도 볼 수 있습니다.',
      sources: [], links: [{ label: '사업장 진단하기', href: '/diagnosis' }],
    };
  }
  if (/상권|동네|지도|폐업률/.test(message)) {
    return {
      answer: '동네·업종별 폐업 통계는 상권 신호등 지도에서 볼 수 있어요. 자치구를 고르면 행정동별 성적표가 나옵니다.',
      sources: [], links: [{ label: '상권 신호등 보기', href: '/market' }],
    };
  }
  if (docs.length) {
    return {
      answer: `말씀하신 상황에는 이런 지원사업을 먼저 확인해 보세요.\n${docs.map((d) => `- ${d.title} (${d.agency})`).join('\n')}\n정확한 대상과 조건은 소관기관 공고에서 꼭 확인해 주세요.`,
      sources: docs.map((d) => ({ docId: d.docId, title: d.title })),
      links: [{ label: '내 가게 맞춤 추천 받기', href: '/diagnosis' }],
    };
  }
  return {
    answer: '지금은 정책자금, 사업장 진단, 상권 정보에 대해서만 답할 수 있어요. 예: "대출 상환이 힘들어요", "임대료 지원이 있나요?"',
    sources: [], links: [],
  };
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Partial<ChatbotRequest>;
  const message = String(body.message ?? '').trim();
  if (!message) return NextResponse.json({ error: '질문을 입력해 주세요.' }, { status: 400 });
  if (message.length > 500) return NextResponse.json({ error: '질문은 500자 이내로 입력해 주세요.' }, { status: 400 });

  let res: ChatbotResponse;
  if (body.diagnosisId) {
    const d = getDiagnosis(body.diagnosisId);
    if (!d) return NextResponse.json({ error: '진단 결과가 없거나 만료되었습니다.' }, { status: 404 });
    const hist = store.chats.get(d.diagnosisId) ?? [];
    const asked = hist.filter((m) => m.role === 'user').length;
    if (asked >= CHAT_LIMIT) {
      return NextResponse.json({ error: `질문은 진단 1건당 ${CHAT_LIMIT}개까지 가능합니다.`, remaining: 0 }, { status: 429 });
    }
    res = { ...answerWithDiagnosis(message, d), remaining: CHAT_LIMIT - asked - 1 };
    hist.push({ role: 'user', text: message }, { role: 'assistant', text: res.answer });
    store.chats.set(d.diagnosisId, hist);
  } else {
    res = answerGeneral(message);
  }

  store.metrics.chatQuestions++;
  store.metrics.llmTokens += Math.round((message.length + res.answer.length) / 2);
  return NextResponse.json(res);
}
