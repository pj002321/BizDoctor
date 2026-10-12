// POST /api/chat { diagnosisId, question } — F-LLM-03 후속 질의응답 (목업: 규칙 기반 답변)
import { NextRequest, NextResponse } from 'next/server';
import { POLICY_DOCS } from '@/lib/policies';
import { DIAG_GRADE, RISK_TYPE_META } from '@/lib/risk';
import { CHAT_LIMIT, getDiagnosis, store } from '@/lib/store';

export async function POST(req: NextRequest) {
  const { diagnosisId, question } = await req.json();
  const d = getDiagnosis(diagnosisId);
  if (!d) return NextResponse.json({ error: '진단 결과가 없습니다.' }, { status: 404 });
  const hist = store.chats.get(diagnosisId) ?? [];
  const asked = hist.filter((m) => m.role === 'user').length;
  if (asked >= CHAT_LIMIT) return NextResponse.json({ error: `질문은 진단 1건당 ${CHAT_LIMIT}개까지 가능합니다.`, remaining: 0 }, { status: 429 });

  const q = String(question ?? '').trim();
  if (!q) return NextResponse.json({ error: '질문을 입력해 주세요.' }, { status: 400 });
  let answer: string;
  const doc = POLICY_DOCS.find((p) => q.includes(p.title.split(' ')[0]));
  if (doc) {
    answer = `${doc.title}: ${doc.content} (소관: ${doc.agency}, 한도: ${doc.limit}, 금리: ${doc.rate}) 최종 조건은 공고에서 확인이 필요합니다.`;
  } else if (/등급|왜|이유|원인/.test(q)) {
    answer = `진단 등급은 ${DIAG_GRADE[d.riskLevel].grade}(${DIAG_GRADE[d.riskLevel].label})이며, 추정 원인은 ${RISK_TYPE_META[d.riskType].name}입니다. 같은 업종 내 폐업 위험 상위 ${d.context.topPercent}% 위치와 최근 3개월 매출 지수(${d.revenueIndex.join(' → ')})가 반영되었습니다.`;
  } else if (/점수|score/.test(q)) {
    answer = d.scoreMethod === 'six_month_drop'
      ? `위험 점수 ${d.score}점은 이전 3개월 대비 최근 3개월 매출 감소율을 0~100으로 환산한 값입니다.`
      : `위험 점수 ${d.score}점은 최근 3개월 매출 지수의 기울기로 추정한 값입니다. 이전 3개월 매출을 함께 입력하면 표준 산식으로 계산됩니다.`;
  } else if (/신청|어디|방법/.test(q)) {
    answer = d.solutions.length
      ? `추천된 지원사업: ${d.solutions.map((s) => `${s.title}(${s.agency})`).join(', ')}. 신청 경로는 각 소관기관 공고를 확인해 주세요.`
      : '현재 진단 유형에 연결된 지원사업이 없습니다.';
  } else {
    answer = '제공된 진단 결과와 지원사업 문서 범위에서만 답변할 수 있습니다. 등급 이유, 점수 산식, 지원사업 신청 방법 등을 물어봐 주세요.';
  }
  hist.push({ role: 'user', text: q }, { role: 'assistant', text: answer });
  store.chats.set(diagnosisId, hist);
  store.metrics.chatQuestions++;
  store.metrics.llmTokens += Math.round((q.length + answer.length) / 2);
  return NextResponse.json({ answer, remaining: CHAT_LIMIT - asked - 1 });
}
