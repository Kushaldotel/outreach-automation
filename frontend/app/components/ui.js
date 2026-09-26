'use client';

import { useState } from 'react';

export function Badge({ value }) {
  if (!value) return null;
  return <span className={`badge ${value}`}>{String(value).replace(/_/g, ' ')}</span>;
}

export function Msg({ msg }) {
  if (!msg) return null;
  return <div className={`msg ${msg.ok ? 'ok' : 'err'}`}>{msg.text}</div>;
}

export const EMPTY_LEAD = {
  first_name: '',
  last_name: '',
  title: '',
  company_name: '',
  company_name_for_emails: '',
  city: '',
  email: '',
};

export function LeadForm({ initial, busy, onSave, onCancel }) {
  const [form, setForm] = useState({ ...EMPTY_LEAD, ...initial });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const fields = [
    ['first_name', 'First name *'],
    ['last_name', 'Last name'],
    ['title', 'Title'],
    ['company_name', 'Company name'],
    ['company_name_for_emails', 'Company name for emails'],
    ['city', 'City'],
    ['email', 'Email *'],
  ];
  return (
    <div className="draft-card" style={{ background: '#10131a' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
        {fields.map(([k, label]) => (
          <div key={k}>
            <label>{label}</label>
            <input type="text" value={form[k]} onChange={set(k)} />
          </div>
        ))}
      </div>
      <div className="row" style={{ marginTop: 12 }}>
        <button
          className="success"
          disabled={busy || !form.first_name || !form.email}
          onClick={() => onSave(form)}
        >
          Save Lead
        </button>
        <button className="secondary" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export const CATEGORY_LABEL = {
  reply: 'lead reply',
  new_lead: 'new lead',
  other: 'not a lead',
};
