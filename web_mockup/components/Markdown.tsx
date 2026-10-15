/** 리포트용 최소 마크다운 렌더러 (#, ##, -, **굵게**, ---) */
import { Fragment } from 'react';

function inline(s: string) {
  return s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <Fragment key={i}>{p}</Fragment>));
}

export default function Markdown({ text, streaming }: { text: string; streaming?: boolean }) {
  const lines = text.split('\n');
  const out: React.ReactNode[] = [];
  let list: string[] = [];
  const flush = () => { if (list.length) { out.push(<ul key={out.length}>{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>); list = []; } };
  lines.forEach((l) => {
    if (l.startsWith('- ')) { list.push(l.slice(2)); return; }
    flush();
    if (l.startsWith('## ')) out.push(<h2 key={out.length}>{inline(l.slice(3))}</h2>);
    else if (l.startsWith('# ')) out.push(<h1 key={out.length}>{inline(l.slice(2))}</h1>);
    else if (l.trim() === '---') out.push(<hr key={out.length} />);
    else if (l.trim()) out.push(<p key={out.length}>{inline(l)}</p>);
  });
  flush();
  return <div className={`md${streaming ? ' cursor' : ''}`}>{out}</div>;
}
