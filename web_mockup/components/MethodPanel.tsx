import { BASE_RED_RATE, MODEL_PERF, REAL_RED_RATE } from '@/lib/risk';
import { Spec } from './badges';

/** F-SYS-08 모델 한계 고지 UI — '이 결과는 어떻게 계산되나요' */
export default function MethodPanel({ open = false }: { open?: boolean }) {
  return (
    <details className="panel" open={open}>
      <summary>이 결과는 어떻게 계산되나요? <Spec ids="F-SYS-08" /></summary>
      <div>
        <p><b>1. 입력 정규화</b> — 3개월 매출을 1개월차=100 지수로 바꿔 금액 규모를 지웁니다. 금액은 저장하지 않습니다.</p>
        <p><b>2. 상권 피처 결합</b> — 선택한 행정동·업종의 최신 분기 업종내 폐업률 percentile, 폐업률·개업률, 프랜차이즈 비중을 붙입니다.</p>
        <p><b>3. 진단 등급 예측</b> — LSTM(16) + Dense 모델이 A(안정)/B(관찰 필요)/C(위험) 확률을 냅니다.
          현재 성능: 등급 정확도 {(MODEL_PERF.accuracy * 100).toFixed(1)}%, C등급(RED) 재현율 {(MODEL_PERF.redRecall * 100).toFixed(1)}%, B등급(YELLOW) 재현율 {(MODEL_PERF.yellowRecall * 100).toFixed(1)}%.</p>
        <p><b>4. 사전확률 보정</b> — 학습 데이터는 위험군 비중이 {BASE_RED_RATE * 100}%로 실제 서울(약 {REAL_RED_RATE * 100}%)보다 많습니다. 그대로 쓰면 모두가 위험해 보이므로, 확률을 실제 비중 기준으로 다시 계산해 보여드립니다.</p>
        <p><b>5. 원인 유형 추정</b> — 6개 유형 중 하나를 고르지만 한계가 큽니다:</p>
        <ul>
          <li>매출 폭락형 재현율 1.2%</li>
          <li>원가 상승 부담형 · 상권 침체 붕괴형 재현율 0% (실제 해당 사례를 거의 못 잡음)</li>
          <li>그래서 &lsquo;확정 진단&rsquo;이 아닌 &lsquo;추정 원인&rsquo;으로만, 확률과 함께 표기합니다.</li>
        </ul>
        <p><b>6. 데이터의 성격</b> — 가게별 월매출은 공개 데이터가 아니어서, 실제 통계(서울시 상권분석, KOSIS 애로사항, 신용보증기금 부실사유)로 양 끝을 맞춘 <b>시뮬레이션</b>으로 학습했습니다. 정확도는 실제 예측력이 아니라 시뮬레이션 규칙을 얼마나 복원하는지를 뜻합니다.</p>
        <p className="muted small">상권 신호등(지도)은 실제 통계 기반 행정동×업종 단위 결과이고, 진단 등급은 모델 기반 개별 가게 결과입니다. 둘은 서로 다른 값입니다. <Spec ids="F-SYS-01" /></p>
      </div>
    </details>
  );
}
