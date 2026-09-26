'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useActions } from '../lib/hooks';
import { Badge, Msg, LeadForm } from '../components/ui';

export default function LeadsPage() {
  const [leads, setLeads] = useState([]);
  const [intentFilter, setIntentFilter] = useState('');
  const [addingLead, setAddingLead] = useState(false);
  const [editingLeadId, setEditingLeadId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const { msg, busy, run } = useActions();

  const refresh = useCallback(() => api('/leads/').then(setLeads), []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const createLead = (form) =>
    run(() => api('/leads/', { method: 'POST', body: JSON.stringify(form) }), 'Lead added', refresh)
      .then(() => setAddingLead(false));

  const updateLead = (id, form) =>
    run(() => api(`/leads/${id}/`, { method: 'PATCH', body: JSON.stringify(form) }), 'Lead updated', refresh)
      .then(() => setEditingLeadId(null));

  const deleteLead = (lead) => {
    if (!confirm(`Delete lead ${lead.full_name} <${lead.email}>?`)) return;
    run(() => api(`/leads/${lead.id}/`, { method: 'DELETE' }), 'Lead deleted', refresh);
  };

  const filteredLeads = intentFilter ? leads.filter((l) => l.intent === intentFilter) : leads;

  const toggleSelect = (id) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const toggleSelectAll = () =>
    setSelectedIds(selectedIds.length === filteredLeads.length ? [] : filteredLeads.map((l) => l.id));

  const deleteSelected = () => {
    if (!selectedIds.length) return;
    if (!confirm(`Delete ${selectedIds.length} selected lead(s)? This cannot be undone.`)) return;
    run(
      () => api('/leads/bulk-delete/', { method: 'POST', body: JSON.stringify({ lead_ids: selectedIds }) }),
      (r) => `Deleted ${r.deleted} lead(s)`,
      refresh
    ).then(() => setSelectedIds([]));
  };

  return (
    <>
      <h1>Leads</h1>
      <p className="sub">Cold email campaign → inbox polling → reply intent → soft-lead drafts / main-lead tracking</p>
      <Msg msg={msg} />

      <div className="panel">
        <div className="row" style={{ marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>Leads</h2>
          {['', 'main_lead', 'soft_lead'].map((f) => (
            <button
              key={f}
              className={`sm ${intentFilter === f ? '' : 'secondary'}`}
              onClick={() => setIntentFilter(f)}
            >
              {f === '' ? 'All' : f === 'main_lead' ? '★ Main Leads' : 'Soft Leads'}
            </button>
          ))}
          <button className="sm" disabled={busy} onClick={() => { setAddingLead(!addingLead); setEditingLeadId(null); }}>
            + Add Lead
          </button>
          {selectedIds.length > 0 && (
            <button className="sm danger" disabled={busy} onClick={deleteSelected}>
              Delete Selected ({selectedIds.length})
            </button>
          )}
        </div>
        {addingLead && (
          <LeadForm busy={busy} onSave={createLead} onCancel={() => setAddingLead(false)} />
        )}
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 30 }}>
                  <input
                    type="checkbox"
                    checked={filteredLeads.length > 0 && selectedIds.length === filteredLeads.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th>Name</th><th>Company</th><th>City</th><th>Email</th><th>Source</th><th>Status</th><th>Intent</th><th>Sent</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filteredLeads.map((l) =>
                editingLeadId === l.id ? (
                  <tr key={l.id}>
                    <td colSpan={9}>
                      <LeadForm
                        initial={l}
                        busy={busy}
                        onSave={(form) => updateLead(l.id, form)}
                        onCancel={() => setEditingLeadId(null)}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr key={l.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(l.id)}
                        onChange={() => toggleSelect(l.id)}
                      />
                    </td>
                    <td>{l.full_name}<div style={{ color: 'var(--muted)', fontSize: 11 }}>{l.title}</div></td>
                    <td>{l.company_name}</td>
                    <td>{l.city}</td>
                    <td>{l.email}</td>
                    <td><Badge value={l.source} /></td>
                    <td><Badge value={l.status} /></td>
                    <td><Badge value={l.intent} /></td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {l.sent_at ? new Date(l.sent_at).toLocaleString() : '—'}
                      {l.last_error && <div style={{ color: 'var(--red)', fontSize: 11 }}>{l.last_error.slice(0, 60)}</div>}
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button className="sm secondary" disabled={busy} onClick={() => { setEditingLeadId(l.id); setAddingLead(false); }}>
                        Edit
                      </button>{' '}
                      <button className="sm danger" disabled={busy} onClick={() => deleteLead(l)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              )}
              {filteredLeads.length === 0 && (
                <tr><td colSpan={9} style={{ color: 'var(--muted)' }}>No leads yet — upload a CSV or add manually.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
