'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Badge } from '../components/ui';

export default function SentEmailsPage() {
  const [sent, setSent] = useState([]);
  const [openEmailId, setOpenEmailId] = useState(null);

  const refresh = useCallback(() => api('/sent/').then(setSent), []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  return (
    <>
      <h1>Sent Emails</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>

      <div className="panel">
        <h2>Sent Emails</h2>
        {sent.length === 0 && <p style={{ color: 'var(--muted)' }}>Nothing sent yet.</p>}
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr><th>To</th><th>Subject</th><th>Type</th><th>Lead Status</th><th>When</th></tr>
            </thead>
            <tbody>
              {sent.map((s) => (
                <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => setOpenEmailId(openEmailId === s.id ? null : s.id)}>
                  <td>
                    {s.lead_name || s.to_email}
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>{s.to_email}</div>
                  </td>
                  <td>
                    {s.subject}
                    {openEmailId === s.id && (
                      <div className="reply-quote">{s.body_text}</div>
                    )}
                  </td>
                  <td><Badge value={s.kind} /></td>
                  <td>
                    <Badge value={s.lead_status || 'unknown'} />
                    {s.lead_intent && s.lead_intent !== 'none' && <> <Badge value={s.lead_intent} /></>}
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
