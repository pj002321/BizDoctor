// F-MAP: 지역(행정동 × 업종) 단위 "신호등". 사업장 결과(/diagnosis)와 섞지 않는다(F-SYS-01).
import type { Metadata } from "next";
import MarketPage from "@/features/market/MarketPage";

export const metadata: Metadata = { title: "상권 신호등" };

export default async function Page({ searchParams }: PageProps<"/market">) {
  const sp = await searchParams;
  const one = (v: string | string[] | undefined) =>
    Array.isArray(v) ? v[0] : v;
  return (
    <MarketPage
      q={{
        gu: one(sp.gu),
        dong: one(sp.dong),
        ind: one(sp.ind),
        svc: one(sp.svc),
      }}
    />
  );
}
