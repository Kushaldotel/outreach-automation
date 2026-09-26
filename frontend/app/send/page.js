'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useActions } from '../lib/hooks';
import { Badge, Msg } from '../components/ui';

export default function SendEmailPage() {
  const [leads, setLeads] = useState([]);
  const [template, setTemplate] = useState({ subject: '', body: '' });
  const [sendIds, setSendIds] = useState([]);
  const [sendFilter, setSendFilter] = useState('pending');
  const { msg, busy, run } = useActions();

  const refresh = useCallback(async () => {
    const [l, t] = await Promise.all([api('/leads/'), api('/template/')]);
    setLeads(l);
    setTemplate(t);
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const campaignResultText = (r) =>
    r.queued != null
      ? `Campaign queued: ${r.queued} email(s) sending in background — watch the worker terminal, refresh for status`
      : `Campaign: ${r.sent.length} sent, ${r.failed.length} failed` +
        (r.failed.length ? ` — first error: ${r.failed[0].error}` : '');

  const sendToSelected = () => {
    if (!sendIds.length) return;
    if (!confirm(`Send campaign email to ${sendIds.length} selected lead(s)?`)) return;
    run(
      () => api('/campaign/send/', { method: 'POST', body: JSON.stringify({ lead_ids: sendIds }) }),
      campaignResultText,
      refresh
    ).then(() => setSendIds([]));
  };

  const eligible =
    sendFilter === 'pending'
      ? leads.filter((l) => l.status === 'pending' || l.status === 'failed')
      : sendFilter === 'soft_lead' || sendFilter === 'main_lead'
        ? leads.filter((l) => l.intent === sendFilter)
        : leads;
  const allChecked = eligible.length > 0 && eligible.every((l) => sendIds.includes(l.id));

  return (
    <>
      <h1>Send Email</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      <div className="panel">
        <h2>Template being sent</h2>
        <div style={{ fontWeight: 600, fontSize: 14 }}>{template.subject || '(empty subject)'}</div>
        <div className="reply-quote">{(template.body || '(empty body)').slice(0, 300)}…</div>
        <p style={{ color: 'var(--muted)', fontSize: 12 }}>
          Edit it in the Template section. Placeholders fill per lead.
        </p>
      </div>
      <div className="panel">
        <div className="row" style={{ marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>Recipients ({eligible.length})</h2>
          {[['pending', 'Not Yet Emailed'], ['all', 'All Leads'], ['soft_lead', 'Soft Leads'], ['main_lead', '★ Main Leads']].map(([f, label]) => (
            <button
              key={f}
              className={`sm ${sendFilter === f ? '' : 'secondary'}`}
              onClick={() => { setSendFilter(f); setSendIds([]); }}
            >
              {label}
            </button>
          ))}
          <button
            className="sm secondary"
            disabled={busy || !eligible.length}
            onClick={() => setSendIds(allChecked ? [] : eligible.map((l) => l.id))}
          >
            {allChecked ? 'Clear All' : 'Select All'}
          </button>
          <button
            className="success"
            disabled={busy || !sendIds.length}
            onClick={sendToSelected}
          >
            Send to {sendIds.length} lead(s)
          </button>
        </div>
        <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8 }}>
          "Not Yet Emailed" is the safe default (pending/failed only). Other filters let you
          email anyone — soft leads, main leads, or the whole list — even if already contacted.
          Replies get auto-classified into soft / main leads.
        </p>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 30 }}>
                  <input type="checkbox" checked={allChecked} onChange={() => setSendIds(allChecked ? [] : eligible.map((l) => l.id))} />
                </th>
                <th>Name</th><th>Company</th><th>City</th><th>Email</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {eligible.map((l) => (
                <tr key={l.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={sendIds.includes(l.id)}
                      onChange={() =>
                        setSendIds((prev) =>
                          prev.includes(l.id) ? prev.filter((x) => x !== l.id) : [...prev, l.id]
                        )
                      }
                    />
                  </td>
                  <td>{l.full_name}<div style={{ color: 'var(--muted)', fontSize: 11 }}>{l.title}</div></td>
                  <td>{l.company_name}</td>
                  <td>{l.city}</td>
                  <td>{l.email}</td>
                  <td>
                    <Badge value={l.status} />{l.intent !== 'none' && <> <Badge value={l.intent} /></>}
                    {l.last_error && <div style={{ color: 'var(--red)', fontSize: 11 }}>{l.last_error.slice(0, 50)}</div>}
                  </td>
                </tr>
              ))}
              {eligible.length === 0 && (
                <tr><td colSpan={6} style={{ color: 'var(--muted)' }}>No leads match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
