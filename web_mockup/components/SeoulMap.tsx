'use client';
import { useState } from 'react';
import type { Signal } from '@/lib/types';
import { MARKET_SIGNAL } from '@/lib/risk';

export interface GuShape { gu: string; d: string; cx: number; cy: number }
const FILL: Record<Signal, string> = { GREEN: 'var(--green-fill)', YELLOW: 'var(--yellow-fill)', RED: 'var(--red-fill)' };

/** F-MAP-01 자치구 단계구분도 — 색 + 아이콘 라벨 병기 (F-SYS-04) */
export default function SeoulMap({ width, height, shapes, signals, values, selected, onSelect }: {
  width: number; height: number; shapes: GuShape[];
  signals: Record<string, Signal>; values: Record<string, string>;
  selected?: string; onSelect: (gu: string) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const h = shapes.find((s) => s.gu === hover);
  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="map-svg gu-map" role="group" aria-label="서울 자치구 상권 신호등 지도">
        {shapes.map((s) => {
          const sig = signals[s.gu];
          return (
            <path key={s.gu} d={s.d} fill={sig ? FILL[sig] : 'var(--na-fill)'} className={selected === s.gu ? 'sel' : undefined}
              tabIndex={0} role="button" aria-label={`${s.gu} ${sig ? MARKET_SIGNAL[sig].label : ''} ${values[s.gu] ?? ''}`}
              aria-pressed={selected === s.gu}
              onClick={() => onSelect(s.gu)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSelect(s.gu))}
              onMouseEnter={() => setHover(s.gu)} onMouseLeave={() => setHover(null)} />
          );
        })}
        {shapes.map((s) => {
          const sig = signals[s.gu];
          return (
            <text key={s.gu} x={s.cx} y={s.cy} textAnchor="middle">
              <tspan x={s.cx} dy={-2}>{sig ? MARKET_SIGNAL[sig].icon : ''} {s.gu.replace(/구$/, '')}</tspan>
            </text>
          );
        })}
      </svg>
      {h && (
        <div style={{ position: 'absolute', left: `${(h.cx / width) * 100}%`, top: `${(h.cy / height) * 100}%`, transform: 'translate(-50%, -130%)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 10px', fontSize: 12, boxShadow: 'var(--shadow)', pointerEvents: 'none', whiteSpace: 'nowrap' }}>
          <b>{h.gu}</b> · {signals[h.gu] ? MARKET_SIGNAL[signals[h.gu]].label : '–'}<br /><span className="muted">{values[h.gu]}</span>
        </div>
      )}
    </div>
  );
}
