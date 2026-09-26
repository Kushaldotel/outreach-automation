'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useActions } from '../lib/hooks';
import { Msg } from '../components/ui';

export default function TemplatePage() {
  const [template, setTemplate] = useState({ subject: '', body: '' });
  const { msg, busy, run } = useActions();

  const refresh = useCallback(() => api('/template/').then(setTemplate), []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const saveTemplate = () =>
    run(
      () => api('/template/', { method: 'PUT', body: JSON.stringify({ subject: template.subject, body: template.body }) }),
      'Template saved',
      refresh
    );

  return (
    <>
      <h1>Campaign Template</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      <div className="panel">
        <h2>Campaign Template</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Placeholders: {'{{first_name}}'}, {'{{last_name}}'}, {'{{full_name}}'}, {'{{company_name}}'}, {'{{title}}'}, {'{{city}}'}
        </p>
        <label>Subject</label>
        <input
          type="text"
          value={template.subject}
          onChange={(e) => setTemplate({ ...template, subject: e.target.value })}
        />
        <label>Body</label>
        <textarea
          style={{ minHeight: 280 }}
          value={template.body}
          onChange={(e) => setTemplate({ ...template, body: e.target.value })}
        />
        <div style={{ marginTop: 10 }}>
          <button disabled={busy} onClick={saveTemplate}>Save Template</button>
        </div>
      </div>
    </>
  );
}
