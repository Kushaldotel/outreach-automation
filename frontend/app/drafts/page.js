'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useActions } from '../lib/hooks';
import { Badge, Msg } from '../components/ui';

export default function DraftsPage() {
  const [drafts, setDrafts] = useState([]);
  const { msg, busy, run, flash } = useActions();

  const refresh = useCallback(() => api('/drafts/').then(setDrafts), []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const sendDraft = (id) => run(() => api(`/drafts/${id}/send/`, { method: 'POST' }), 'Draft sent', refresh);

  const rejectDraft = (id) => run(() => api(`/drafts/${id}/reject/`, { method: 'POST' }), 'Draft rejected', refresh);

  const updateDraftBody = async (id, body_text, subject) => {
    try {
      await api(`/drafts/${id}/`, { method: 'PATCH', body: JSON.stringify({ body_text, subject }) });
      flash(true, 'Draft updated');
    } catch (e) {
      flash(false, e.message);
    }
  };

  return (
    <>
      <h1>Draft Replies</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      <div className="panel">
        <h2>Draft Replies — soft leads get the portfolio link, main leads get the booking link. Approve to send.</h2>
        {drafts.length === 0 && <p style={{ color: 'var(--muted)' }}>No drafts yet.</p>}
        {drafts.map((d) => (
          <div className="draft-card" key={d.id}>
            <div className="meta">
              To: <strong style={{ color: 'var(--text)' }}>{d.lead_name}</strong> ({d.lead_email}) — {d.company_name}
              {' '}<Badge value={d.lead_intent} /> <Badge value={d.status} />
            </div>
            {d.reply_body && (
              <details>
                <summary style={{ color: 'var(--muted)', fontSize: 12, cursor: 'pointer' }}>Their reply</summary>
                <div className="reply-quote">{d.reply_body.slice(0, 600)}</div>
              </details>
            )}
            <label>Subject</label>
            <input
              type="text"
              defaultValue={d.subject}
              disabled={d.status !== 'pending'}
              onBlur={(e) => e.target.value !== d.subject && updateDraftBody(d.id, d.body_text, e.target.value)}
              id={`subj-${d.id}`}
            />
            <label>Body</label>
            <textarea
              defaultValue={d.body_text}
              disabled={d.status !== 'pending'}
              onBlur={(e) =>
                e.target.value !== d.body_text &&
                updateDraftBody(d.id, e.target.value, document.getElementById(`subj-${d.id}`).value)
              }
            />
            {d.status === 'pending' && (
              <div className="row" style={{ marginTop: 10 }}>
                <button className="success" disabled={busy} onClick={() => sendDraft(d.id)}>Approve & Send</button>
                <button className="danger" disabled={busy} onClick={() => rejectDraft(d.id)}>Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
