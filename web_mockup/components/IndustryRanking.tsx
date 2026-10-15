'use client';
import { useEffect, useState } from 'react';
import { BarList, industryColor } from './charts';
import { ScopeChip, Spec } from './badges';
import { getJSON } from './useMeta';
import type { IndustryRank } from '@/lib/types';

export default function IndustryRanking() {
  const [sort, setSort] = useState<'avg' | 'real'>('avg');
  const [top, setTop] = useState(20);
  const [items, setItems] = useState<IndustryRank[] | null>(null);
  const [pick, setPick] = useState<string>('');
  useEffect(() => { getJSON<{ items: IndustryRank[] }>(`/api/market/industries?sort=${sort}&top=${top}`).then((r) => setItems(r.items)); }, [sort, top]);
  const p = items?.find((i) => i.name === pick);
  return (
    <div className="page">
      <div className="page-head">
        <div className="row"><ScopeChip scope="market" /><Spec ids="F-MAP-05 · P1" /></div>
        <h1>업종별 폐업률 순위</h1>
        <p>3개년 관측 200건 이상인 업종만 비교합니다. 평균폐업률과 실질폐업률(점포수 가중)을 함께 확인하세요.</p>
      </div>
      <section className="card">
        <div className="card-head">
          <div className="seg" role="group" aria-label="정렬 기준">
            <button aria-pressed={sort === 'avg'} onClick={() => setSort('avg')}>평균폐업률순</button>
            <button aria-pressed={sort === 'real'} onClick={() => setSort('real')}>실질폐업률순</button>
          </div>
          <div className="seg" role="group" aria-label="표시 개수">
            {[10, 20, 50, 100].map((n) => <button key={n} aria-pressed={top === n} onClick={() => setTop(n)}>상위 {n}</button>)}
          </div>
        </div>
        {items ? (
          <div className="grid-2">
            <BarList items={items.map((i) => ({ key: i.name, label: `${i.rank}. ${i.name}`, value: sort === 'avg' ? i.avgCloseRate : i.realCloseRate, sub: i.industry }))}
              onPick={setPick} selected={pick} color="#2a78d6" />
            <div className="stack">
              {p ? (
                <div className="card" style={{ background: 'var(--surface-2)', boxShadow: 'none' }}>
                  <div className="row" style={{ marginBottom: 6 }}><i className="sw" style={{ background: industryColor(p.industry) }} /><span className="small muted">{p.industry}</span></div>
                  <h2>{p.rank}위 · {p.name}</h2>
                  <div className="stats" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))', marginTop: 12 }}>
                    <div className="stat" style={{ background: 'var(--surface)' }}><div className="k">평균폐업률</div><div className="v">{p.avgCloseRate.toFixed(2)}%</div></div>
                    <div className="stat" style={{ background: 'var(--surface)' }}><div className="k">실질폐업률</div><div className="v">{p.realCloseRate.toFixed(2)}%</div></div>
                    <div className="stat" style={{ background: 'var(--surface)' }}><div className="k">관측수</div><div className="v" style={{ fontSize: 16 }}>{p.obs.toLocaleString()}</div></div>
                    <div className="stat" style={{ background: 'var(--surface)' }}><div className="k">점포수(분기 합)</div><div className="v" style={{ fontSize: 16 }}>{p.stores.toLocaleString()}</div></div>
                  </div>
                </div>
              ) : <p className="notice">막대를 누르면 업종 상세가 표시됩니다.</p>}
              <p className="notice notice-info small">업종 랭킹은 전체 비교라 관측 200건 이상으로 엄격하게 거르고, 지도·상세의 최소 점포수 필터(기본 5)는 개별 조회용이라 더 낮게 둡니다.</p>
            </div>
          </div>
        ) : <p className="muted">불러오는 중…</p>}
      </section>
    </div>
  );
}
