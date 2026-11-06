/** 장식용 신호등. 초록 → 노랑 → 빨강 순서로 2초씩 불이 옮겨 간다(globals.css .lamp). */
const LAMPS = [
  ["text-lamp-red", 2],
  ["text-lamp-yellow", 1],
  ["text-lamp-green", 0],
] as const;

export default function Lamps({
  size,
  vertical = false,
  className = "",
}: {
  size: string;
  vertical?: boolean;
  className?: string;
}) {
  return (
    <div
      aria-hidden="true"
      className={`inline-flex rounded-full bg-black/45 ${vertical ? "flex-col" : ""} ${className}`}
      style={{ gap: `calc(${size} * 0.45)`, padding: `calc(${size} * 0.45)` }}
    >
      {LAMPS.map(([c, l]) => (
        <span
          key={c}
          className={`lamp block ${c}`}
          style={{ width: size, height: size, ["--l" as string]: l }}
        />
      ))}
    </div>
  );
}
