import MarketExplorer from '@/components/MarketExplorer';
import { getGuPaths } from '@/lib/data';

export const metadata = { title: '상권 신호등 · BizDoctor' };

export default function MarketPage() {
  const geo = getGuPaths();
  return <MarketExplorer geo={geo} />;
}
