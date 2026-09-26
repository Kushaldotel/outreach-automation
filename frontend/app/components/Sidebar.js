'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

const NAV = [
  ['/', 'Dashboard', null],
  ['/leads', 'Leads', (s) => s.leads_total],
  ['/send', 'Send Email', null],
  ['/inbox', 'Inbox', (s) => s.inbox_total],
  ['/sent', 'Sent Emails', (s) => s.emails_sent],
  ['/drafts', 'Draft Replies', (s) => s.drafts_pending || null],
  ['/template', 'Template', null],
];

export default function Sidebar() {
  const pathname = usePathname();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const loadStats = () => api('/stats/').then(setStats).catch(() => {});
    loadStats();
    window.addEventListener('outreach:refresh', loadStats);
    return () => window.removeEventListener('outreach:refresh', loadStats);
  }, [pathname]);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="name">Horizon Outreach</div>
        <div className="tag">cold email · reply intent · leads</div>
      </div>
      <nav className="nav">
        {NAV.map(([href, label, count]) => (
          <Link key={href} href={href} className={pathname === href ? 'active' : ''}>
            <span>{label}</span>
            {stats && count && count(stats) != null && <span className="count">{count(stats)}</span>}
          </Link>
        ))}
      </nav>
      <div className="foot">{stats ? `${stats.main_leads} main · ${stats.soft_leads} soft leads` : '…'}</div>
    </aside>
  );
}
