'use client';
import { useEffect, useState } from 'react';

export interface MetaResp {
  quarters: string[];
  gus: string[];
  dongs: { code: string; name: string; gu: string }[];
  industries: string[];
  services: { code: string; name: string; kosis: string }[];
}

let cached: MetaResp | null = null;
export function useMeta() {
  const [meta, setMeta] = useState<MetaResp | null>(cached);
  useEffect(() => {
    if (cached) return;
    fetch('/api/meta').then((r) => r.json()).then((m) => { cached = m; setMeta(m); });
  }, []);
  return meta;
}

export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error ?? `요청 실패 (${r.status})`);
  return j as T;
}
