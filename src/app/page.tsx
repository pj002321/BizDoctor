import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-bold">상권 신호등</h1>
      <nav className="mt-6 flex flex-col gap-3">
        <Link className="text-accent underline" href="/market">
          우리 동네 상권 신호등 보기
        </Link>
        <Link className="text-accent underline" href="/diagnosis">
          내 가게 진단받기
        </Link>
      </nav>
    </main>
  );
}
