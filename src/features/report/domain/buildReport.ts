/**
 * AI 리포트 목업. 실서비스에서는 ai-service 가 LLM 으로 쓰고, 여기 있는 checkNumbers 와 같은
 * 가드레일(F-LLM-02)로 수치를 대조한다. 목업은 템플릿으로 같은 모양의 글을 만든다.
 */
import { GRADE, type Signal } from "@/shared/types/signal";

export interface ReportSection {
  heading: string;
  body: string;
}

const pct = (v: number) => Math.round(v * 100);
const name = (t: string) => t.replaceAll("_", " ");

export function buildReport(s: Signal): ReportSection[] {
  const g = GRADE[s.risk_level];
  const [a, b, c] = s.sales_index;
  const top = Math.max(1, Math.round((1 - s.percentile) * 100));
  const trend =
    c < a
      ? `${a}에서 ${c}로 내려왔습니다`
      : c > a
        ? `${a}에서 ${c}로 올랐습니다`
        : "제자리입니다";

  const sections: ReportSection[] = [
    {
      heading: "한 줄 요약",
      body: `${s.place.dong} ${s.place.service} 사업장의 진단 등급은 ${g.letter}(${g.label})입니다. 최근 석 달 매출 지수가 ${trend}.`,
    },
    {
      heading: "지금 상태",
      body: `매출 지수는 ${a} → ${b} → ${c}입니다. 서울 실제 비율로 보정한 위험 확률은 ${pct(s.level_probs.RED)}%, 관찰 필요 확률은 ${pct(s.level_probs.YELLOW)}%이고, 위험 점수는 100점 중 ${s.score}점입니다.`,
    },
    {
      heading: "우리 동네 안에서",
      body: `${s.as_of} 기준 ${s.place.dong}의 ${s.place.service} 폐업률은 ${s.close_rate}%로, 같은 업종이 있는 서울 행정동 가운데 폐업이 잦은 쪽으로 상위 ${top}%입니다.`,
    },
    {
      heading: "추정 원인",
      body:
        s.risk_type === "정상_유지형"
          ? "뚜렷한 위기 신호는 보이지 않습니다. 석 달 뒤 같은 방법으로 다시 확인해 보세요."
          : `가장 가능성이 높은 원인은 ‘${name(s.risk_type)}’입니다(같은 등급 안에서 ${pct(s.risk_type_confidence)}%). 확정 진단이 아니라 추정이므로, 실제 장부와 대출 상황을 함께 보고 판단하세요.`,
    },
  ];

  if (s.solutions.length)
    sections.push({
      heading: "먼저 확인해 볼 지원사업",
      body: s.solutions
        .map(
          (d) =>
            `${d.title}: ${d.agency}. 대상: ${d.target}. 한도: ${d.limit}.`,
        )
        .join("\n"),
    });
  return sections;
}

/** 리포트에 나온 숫자 가운데, 진단 결과(근거)에 없는 것을 돌려준다. 비어 있어야 통과다. */
export function checkNumbers(text: string, s: Signal): string[] {
  const allowed = new Set<string>();
  const add = (v: unknown) => {
    if (typeof v === "number") {
      allowed.add(String(v));
      allowed.add(String(Math.round(v * 100)));
      allowed.add(String(Math.max(1, Math.round((1 - v) * 100))));
    } else if (typeof v === "string") {
      for (const m of v.match(/\d+(?:\.\d+)?/g) ?? []) allowed.add(m);
    } else if (v && typeof v === "object") Object.values(v).forEach(add);
  };
  add(s);
  allowed.add("100");
  return [...new Set(text.match(/\d+(?:\.\d+)?/g) ?? [])].filter(
    (n) => !allowed.has(n),
  );
}
