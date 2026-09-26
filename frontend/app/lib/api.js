export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers:
      options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : undefined,
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// Fired after any mutating action so the sidebar (stats/counts) stays in
// sync even though each route now fetches only its own page data.
export function notifyRefresh() {
  window.dispatchEvent(new Event('outreach:refresh'));
}
