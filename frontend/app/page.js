'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from './lib/api';
import { useActions } from './lib/hooks';
import { Badge, Msg } from './components/ui';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [inbox, setInbox] = useState([]);
  const [pollDays, setPollDays] = useState(7);
  const { msg, busy, run } = useActions();

  const refresh = useCallback(async () => {
    const [s, ib, st] = await Promise.all([
      api('/stats/'),
      api('/inbox/'),
      api('/settings/'),
    ]);
    setStats(s);
    setInbox(ib);
    setPollDays(st.poll_days);
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const uploadCsv = (file) =>
    run(
      () => {
        const fd = new FormData();
        fd.append('file', file);
        return api('/leads/upload/', { method: 'POST', body: fd });
      },
      (r) => `Imported: ${r.created} new, ${r.updated} updated, ${r.skipped} skipped`,
      refresh
    );

  const campaignResultText = (r) =>
    r.queued != null
      ? `Campaign queued: ${r.queued} email(s) sending in background — watch the worker terminal, refresh for status`
      : `Campaign: ${r.sent.length} sent, ${r.failed.length} failed` +
        (r.failed.length ? ` — first error: ${r.failed[0].error}` : '');

  const sendCampaign = () => {
    if (!confirm('Send campaign email to ALL pending/failed leads?')) return;
    run(() => api('/campaign/send/', { method: 'POST', body: JSON.stringify({}) }), campaignResultText, refresh);
  };

  const pollInbox = (days) =>
    run(
      () => api('/inbox/poll/', { method: 'POST', body: JSON.stringify(days ? { days } : {}) }),
      (r) =>
        `Inbox: ${r.fetched} fetched, ${r.stored} stored, ` +
        `${r.lead_replies.length} lead replies, ${r.new_leads.length} new leads`,
      refresh
    );

  const savePollDays = () =>
    run(
      () => api('/settings/', { method: 'PUT', body: JSON.stringify({ poll_days: pollDays }) }),
      (r) => `Poll window saved: last ${r.poll_days} days`,
      refresh
    );

  return (
    <>
      <h1>Dashboard</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      {stats && (
        <>
          <div className="stats">
            <div className="stat"><div className="num">{stats.leads_total}</div><div className="lbl">Leads</div></div>
            <div className="stat"><div className="num">{stats.leads_pending}</div><div className="lbl">Pending</div></div>
            <div className="stat"><div className="num">{stats.emails_sent}</div><div className="lbl">Emails Sent</div></div>
            <div className="stat"><div className="num">{stats.leads_replied}</div><div className="lbl">Replied</div></div>
            <div className="stat"><div className="num">{stats.soft_leads}</div><div className="lbl">Soft Leads</div></div>
            <div className="stat hl"><div className="num">{stats.main_leads}</div><div className="lbl">Main Leads</div></div>
            <div className="stat hl"><div className="num">{stats.inbox_new_leads}</div><div className="lbl">New Inbox Leads</div></div>
            <div className="stat"><div className="num">{stats.drafts_pending}</div><div className="lbl">Drafts Waiting</div></div>
          </div>

          <div className="panel">
            <h2>Actions</h2>
            <div className="row">
              <label style={{ margin: 0 }}>
                <input
                  type="file"
                  accept=".csv,.tsv,.txt"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files[0]) uploadCsv(e.target.files[0]);
                    e.target.value = '';
                  }}
                />
                <span
                  className="badge"
                  style={{
                    background: '#2a2e3a', color: 'var(--text)', padding: '8px 16px',
                    borderRadius: 8, fontSize: 14, fontWeight: 400, cursor: 'pointer',
                  }}
                >
                  Upload CSV
                </span>
              </label>
              <button disabled={busy} onClick={sendCampaign}>Send Campaign</button>
              <button className="success" disabled={busy} onClick={() => pollInbox()}>Poll Inbox</button>
              <button className="secondary" disabled={busy} onClick={refresh}>Refresh</button>
            </div>
            <div className="row" style={{ marginTop: 14 }}>
              <label style={{ margin: 0 }}>Poll window (days)</label>
              <input
                type="text"
                inputMode="numeric"
                style={{ width: 70 }}
                value={pollDays}
                onChange={(e) => setPollDays(e.target.value.replace(/\D/g, ''))}
              />
              <button className="sm secondary" disabled={busy} onClick={savePollDays}>Save</button>
              <button className="sm" disabled={busy || !pollDays} onClick={() => pollInbox(Number(pollDays))}>
                Re-poll last {pollDays || '?'} days
              </button>
            </div>
            <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>
              Poll Inbox continues from the last seen email. Re-poll forces a full scan of the last N days
              (already-stored emails are skipped).
            </p>
          </div>

          <div className="panel">
            <h2>Recent Inbox</h2>
            {inbox.slice(0, 5).map((e) => (
              <div className="draft-card" key={e.id}>
                <div className="meta">
                  <strong style={{ color: 'var(--text)' }}>{e.sender_name || e.sender_email}</strong>
                  {' '}<Badge value={e.category === 'reply' ? e.intent : e.category} />
                  {e.received_at && <span> · {new Date(e.received_at).toLocaleString()}</span>}
                </div>
                <div style={{ fontSize: 13 }}>{e.subject}</div>
              </div>
            ))}
            {inbox.length === 0 && <p style={{ color: 'var(--muted)' }}>Inbox empty — poll to fetch.</p>}
          </div>
        </>
      )}
    </>
  );
}
