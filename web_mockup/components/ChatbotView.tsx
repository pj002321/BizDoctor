'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { Spec } from './badges';
import { getJSON } from './useMeta';
import type { ChatbotResponse } from '@/lib/types';

type Msg = { role: 'user' | 'assistant'; text: string; res?: ChatbotResponse };

const EXAMPLES = ['대출 상환이 너무 힘들어요', '임대료 지원이 있나요?', '내 가게 위험도를 알고 싶어요', '우리 동네 폐업률은요?'];

export default function ChatbotView() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { box.current?.scrollTo({ top: 1e6, behavior: 'smooth' }); }, [msgs]);

  async function ask(message: string) {
    if (!message.trim() || loading) return;
    setErr('');
    setQ('');
    const history = msgs.slice(-10).map(({ role, text }) => ({ role, text }));
    setMsgs((m) => [...m, { role: 'user', text: message }]);
    setLoading(true);
    try {
      const res = await getJSON<ChatbotResponse>('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
      });
      setMsgs((m) => [...m, { role: 'assistant', text: res.answer, res }]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 760, margin: '0 auto' }}>
      <div className="page-head">
        <span className="badge badge-brand" style={{ justifySelf: 'start' }}>AI 상담</span>
        <h1>챗봇 상담</h1>
        <p>정책자금, 사업장 진단, 상권 정보에 대해 물어보세요. <Spec ids="POST /api/chatbot" /></p>
      </div>

      <section className="card stack">
        {msgs.length === 0 ? (
          <div className="stack">
            <p className="muted small">이렇게 물어볼 수 있어요</p>
            <div className="row">{EXAMPLES.map((s) => <button key={s} className="btn btn-sm" onClick={() => ask(s)}>{s}</button>)}</div>
          </div>
        ) : (
          <div className="chat" ref={box} aria-live="polite" style={{ maxHeight: 420 }}>
            {msgs.map((m, i) => (
              <div key={i} className={`msg msg-${m.role}`}>
                <div style={{ whiteSpace: 'pre-line' }}>{m.text}</div>
                {m.res && m.res.sources.length > 0 && (
                  <div className="hint" style={{ marginTop: 6 }}>근거: {m.res.sources.map((s) => s.docId).join(', ')}</div>
                )}
                {m.res && m.res.links.length > 0 && (
                  <div className="row" style={{ marginTop: 8 }}>
                    {m.res.links.map((l) => <Link key={l.href} href={l.href} className="btn btn-sm">{l.label} →</Link>)}
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="msg msg-assistant muted">답변 작성 중…</div>}
          </div>
        )}
        <form className="row" style={{ flexWrap: 'nowrap' }} onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <label htmlFor="chatbot-q" className="sr-only">질문</label>
          <input id="chatbot-q" className="input" placeholder="궁금한 점을 입력하세요" value={q} onChange={(e) => setQ(e.target.value)} maxLength={500} />
          <button className="btn btn-primary" disabled={loading || !q.trim()}>보내기</button>
        </form>
        {err && <p className="error" role="alert">{err}</p>}
        <p className="hint">답변은 참고용이며, 지원사업의 최종 조건은 소관기관 공고에서 확인해 주세요.</p>
      </section>
    </div>
  );
}
