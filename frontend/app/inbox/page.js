'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useActions } from '../lib/hooks';
import { Badge, Msg, CATEGORY_LABEL } from '../components/ui';

export default function InboxPage() {
  const [inbox, setInbox] = useState([]);
  const [inboxFilter, setInboxFilter] = useState('');
  const [openEmailId, setOpenEmailId] = useState(null);
  const { msg, busy, run } = useActions();

  const refresh = useCallback(
    () => api(`/inbox/${inboxFilter ? `?category=${inboxFilter}` : ''}`).then(setInbox),
    [inboxFilter]
  );

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const pollInbox = () =>
    run(
      () => api('/inbox/poll/', { method: 'POST', body: JSON.stringify({}) }),
      (r) =>
        `Inbox: ${r.fetched} fetched, ${r.stored} stored, ` +
        `${r.lead_replies.length} lead replies, ${r.new_leads.length} new leads`,
      refresh
    );

  const reanalyzeEmail = (id) =>
    run(
      () => api(`/inbox/${id}/reanalyze/`, { method: 'POST' }),
      (r) =>
        `Re-analyzed: ${r.sender_email} -> ` +
        (r.category === 'reply'
          ? r.intent
          : r.is_lead
            ? `new lead (${r.intent || 'soft_lead'})`
            : 'not a lead'),
      refresh
    );

  return (
    <>
      <h1>Inbox</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      <div className="panel">
        <div className="row" style={{ marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>Inbox</h2>
          {[['', 'All'], ['reply', 'Lead Replies'], ['new_lead', 'New Leads'], ['other', 'Not Leads']].map(([f, label]) => (
            <button
              key={f}
              className={`sm ${inboxFilter === f ? '' : 'secondary'}`}
              onClick={() => setInboxFilter(f)}
            >
              {label}
            </button>
          ))}
          <button className="sm success" disabled={busy} onClick={pollInbox}>Poll Now</button>
        </div>
        {inbox.length === 0 && <p style={{ color: 'var(--muted)' }}>No emails stored — poll the inbox.</p>}
        {inbox.map((e) => (
          <div className="draft-card" key={e.id}>
            <div className="meta">
              <strong style={{ color: 'var(--text)' }}>{e.sender_name || e.sender_email}</strong>
              {' '}&lt;{e.sender_email}&gt;
              {' '}<Badge value={CATEGORY_LABEL[e.category] ? e.category : 'other'} />
              {e.intent && <> <Badge value={e.intent} /></>}
              {e.received_at && <span> · {new Date(e.received_at).toLocaleString()}</span>}
              {' '}
              <button
                className="sm secondary"
                disabled={busy}
                style={{ float: 'right' }}
                onClick={() => reanalyzeEmail(e.id)}
              >
                Re-analyze
              </button>
            </div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{e.subject}</div>
            {e.category === 'reply' && e.replied_to_subject && (
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                ↩ reply to: "{e.replied_to_subject}" ({e.lead_name}, {e.company_name})
              </div>
            )}
            {e.category !== 'reply' && e.classification_reason && (
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>AI: {e.classification_reason}</div>
            )}
            {e.category === 'reply' && e.intent_reason && (
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>AI: {e.intent_reason}</div>
            )}
            <div
              className="reply-quote"
              style={{ cursor: 'pointer' }}
              onClick={() => setOpenEmailId(openEmailId === e.id ? null : e.id)}
            >
              {openEmailId === e.id ? e.body_text : `${e.body_text.slice(0, 200)}${e.body_text.length > 200 ? '… (click to expand)' : ''}`}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
