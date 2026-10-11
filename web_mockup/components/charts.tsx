'use client';
import { useState } from 'react';

/** 범주형 팔레트 — 고정 순서, 엔티티에 고정 (색은 순위가 아니라 산업을 따라감) */
export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
export const INDUSTRY_ORDER = [
  '숙박 및 음식점업', '도매 및 소매업', '교육 서비스업', '예술, 스포츠 및 여가관련 서비스업',
  '협회 및 단체, 수리 및 기타 개인서비스업', '전문과학기술서비스업', '부동산업', '사업시설관리, 사업지원 및 임대 서비스업',
];
export const industryColor = (name: string) => SERIES[Math.max(0, INDUSTRY_ORDER.indexOf(name)) % SERIES.length];

/* ---------------- Sparkline ---------------- */
export function Sparkline({ values, color = 'var(--brand)', w = 120, h = 32, label }: { values: (number | null)[]; color?: string; w?: number; h?: number; label: string }) {
  const nums = values.filter((v): v is number => v != null);
  if (nums.length < 2) return <span className="tiny muted">–</span>;
  const min = Math.min(...nums), max = Math.max(...nums);
  const x = (i: number) => 3 + (i * (w - 6)) / (values.length - 1);
  const y = (v: number) => h - 4 - ((v - min) / (max - min || 1)) * (h - 8);
  let d = ''; let pen = false;
  values.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true; });
  const li = values.length - 1 - [...values].reverse().findIndex((v) => v != null);
  return (
    <svg width={w} height={h} role="img" aria-label={label}>
      <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(li)} cy={y(values[li] as number)} r={3} fill={color} stroke="var(--surface)" strokeWidth={2} />
    </svg>
  );
}

/* ---------------- Line chart (단일 y축, crosshair + tooltip) ---------------- */
export interface LineSeries { name: string; color: string; values: (number | null)[]; dashed?: boolean }
export function LineChart({ labels, series, annotations = [], unit = '%', height = 260, yTitle }: {
  labels: string[]; series: LineSeries[]; annotations?: { index: number; label: string }[]; unit?: string; height?: number; yTitle?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 900, H = height, L = 40, R = 34, T = 18, B = 30;
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  const min = Math.min(0, ...all), maxV = Math.max(...all, 1);
  const max = Math.ceil(maxV);
  const x = (i: number) => L + (i * (W - L - R)) / Math.max(1, labels.length - 1);
  const y = (v: number) => T + (1 - (v - min) / (max - min || 1)) * (H - T - B);
  const ticks = Array.from({ length: 5 }, (_, i) => min + ((max - min) * i) / 4);
  const path = (vals: (number | null)[]) => { let d = ''; let pen = false; vals.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true; }); return d; };
  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img" aria-label={`${yTitle ?? ''} 추이 차트`} onMouseLeave={() => setHover(null)}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeWidth={1} />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--muted)" style={{ fontWeight: 500 }}>{t.toFixed(1)}</text>
          </g>
        ))}
        {labels.map((l, i) => (i % 2 === 0 || i === labels.length - 1) && (
          <text key={l} x={x(i)} y={H - 8} textAnchor={i === labels.length - 1 ? 'end' : i === 0 ? 'start' : 'middle'} fontSize={11} fill="var(--muted)" style={{ fontWeight: 500 }}>{l.replace(' ', ' ')}</text>
        ))}
        {annotations.map((a) => (
          <g key={a.index}>
            <rect x={x(a.index) - 14} y={T} width={28} height={H - T - B} fill="var(--brand)" opacity={0.08} />
            <text x={x(a.index)} y={T + 12} textAnchor="middle" fontSize={11} fill="var(--brand)" style={{ fontWeight: 700 }}>{a.label}</text>
          </g>
        ))}
        {series.map((s) => (
          <path key={s.name} d={path(s.values)} fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? '5 4' : undefined} strokeLinejoin="round" style={{ cursor: 'default' }} />
        ))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="var(--muted)" strokeWidth={1} />}
        {hover != null && series.map((s) => s.values[hover] != null && (
          <circle key={s.name} cx={x(hover)} cy={y(s.values[hover]!)} r={4.5} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
        ))}
        {labels.map((_, i) => (
          <rect key={i} x={x(i) - (W - L - R) / labels.length / 2} y={T} width={(W - L - R) / labels.length} height={H - T - B} fill="transparent" style={{ cursor: 'crosshair', stroke: 'none' }} onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      {hover != null && (
        <div role="status" style={{ position: 'absolute', top: 8, left: `${Math.min(70, (x(hover) / W) * 100 + 2)}%`, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 10px', fontSize: 12, boxShadow: 'var(--shadow)', pointerEvents: 'none', minWidth: 140 }}>
          <div style={{ fontWeight: 700, marginBottom: 2 }}>{labels[hover]}</div>
          {series.map((s) => (
            <div key={s.name} className="row" style={{ gap: 6, flexWrap: 'nowrap' }}>
              <span className="sw" style={{ background: s.color }} />
              <span className="muted" style={{ flex: 1 }}>{s.name}</span>
              <b className="num">{s.values[hover] == null ? '–' : `${s.values[hover]!.toFixed(2)}${unit}`}</b>
            </div>
          ))}
        </div>
      )}
      {series.length >= 2 && (
        <div className="legend" style={{ marginTop: 6 }}>
          {series.map((s) => <span key={s.name}><i className="sw" style={{ background: s.color }} />{s.name}{s.dashed ? ' (점선)' : ''}</span>)}
        </div>
      )}
    </div>
  );
}

/* ---------------- Horizontal bars ---------------- */
export function BarList({ items, max, color = '#2a78d6', unit = '%', onPick, selected }: {
  items: { key: string; label: string; value: number; sub?: string }[]; max?: number; color?: string; unit?: string; onPick?: (k: string) => void; selected?: string;
}) {
  const m = max ?? Math.max(...items.map((i) => i.value), 1);
  return (
    <div style={{ display: 'grid', gap: 2 }}>
      {items.map((it) => (
        <button key={it.key} type="button" onClick={() => onPick?.(it.key)} title={`${it.label}: ${it.value.toFixed(2)}${unit}${it.sub ? ` · ${it.sub}` : ''}`}
          style={{ display: 'grid', gridTemplateColumns: 'minmax(84px, 140px) 1fr 56px', gap: 8, alignItems: 'center', background: selected === it.key ? 'var(--brand-weak)' : 'transparent', border: 0, padding: '4px 6px', borderRadius: 6, textAlign: 'left', cursor: onPick ? 'pointer' : 'default' }}>
          <span className="small" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.label}</span>
          <span style={{ height: 12, background: 'var(--surface-2)', borderRadius: 4, overflow: 'hidden' }}>
            <span style={{ display: 'block', height: '100%', width: `${(it.value / m) * 100}%`, background: color, borderRadius: '0 4px 4px 0' }} />
          </span>
          <span className="small num" style={{ textAlign: 'right', fontWeight: 700 }}>{it.value.toFixed(2)}{unit}</span>
        </button>
      ))}
    </div>
  );
}

/* ---------------- 분포 히스토그램 + 내 위치 마커 (F-DIA-07) ---------------- */
export function PositionHistogram({ hist, percentile, label }: { hist: number[]; percentile: number; label: string }) {
  const W = 560, H = 110, B = 22, n = hist.length, bw = W / n;
  const m = Math.max(...hist, 1);
  const mx = percentile * W;
  const myBin = Math.min(n - 1, Math.floor(percentile * n));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img" aria-label={label}>
      {hist.map((v, i) => {
        const h = (v / m) * (H - B - 18);
        return <rect key={i} x={i * bw + 1} y={H - B - h} width={bw - 2} height={h} rx={3} fill={i === myBin ? 'var(--brand)' : 'var(--na-fill)'} opacity={i === myBin ? 1 : 0.6}><title>{`percentile ${(i / n).toFixed(2)}~${((i + 1) / n).toFixed(2)}: ${v}개 행정동`}</title></rect>;
      })}
      <line x1={mx} x2={mx} y1={10} y2={H - B} stroke="var(--brand)" strokeWidth={2} />
      <text x={Math.min(W - 40, Math.max(40, mx))} y={10} textAnchor="middle" fontSize={11} fill="var(--brand)" style={{ fontWeight: 700 }}>내 위치</text>
      <text x={0} y={H - 6} fontSize={11} fill="var(--muted)" style={{ fontWeight: 500 }}>폐업 위험 낮음</text>
      <text x={W} y={H - 6} textAnchor="end" fontSize={11} fill="var(--muted)" style={{ fontWeight: 500 }}>높음</text>
    </svg>
  );
}
