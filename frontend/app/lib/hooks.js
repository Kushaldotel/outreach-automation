'use client';

import { useState } from 'react';
import { notifyRefresh } from './api';

export function useActions() {
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const flash = (ok, text) => {
    setMsg({ ok, text });
    setTimeout(() => setMsg(null), 8000);
  };

  const run = async (fn, okText, refresh) => {
    setBusy(true);
    try {
      const result = await fn();
      flash(true, typeof okText === 'function' ? okText(result) : okText);
      if (refresh) await refresh();
      notifyRefresh();
      return result;
    } catch (e) {
      flash(false, e.message);
    } finally {
      setBusy(false);
    }
  };

  return { msg, busy, flash, run };
}
