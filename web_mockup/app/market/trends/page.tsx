import TrendsView from '@/components/TrendsView';
import { getQuarterly } from '@/lib/data';

export const metadata = { title: '산업 추이 · BizDoctor' };

export default function TrendsPage() {
  const weights: Record<string, Record<string, number>> = {};
  for (const r of getQuarterly()) (weights[r.quarter] ??= {})[r.industry] = r.stores;
  return <TrendsView weights={weights} />;
}
