# Outreach MVP

Cold email campaign system: CSV leads → Gmail SMTP campaign → IMAP reply detection → Claude intent classification → soft-lead draft approval / main-lead tracking.

## Setup

### Backend (Django + DRF, SQLite)
```bash
cd backend
cp .env.example .env   # fill in GMAIL_EMAIL, GMAIL_APP_PASSWORD, ANTHROPIC_API_KEY
./venv/bin/python manage.py runserver 8001
```
(venv already created; recreate with `python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`)

Gmail app password: Google Account → Security → 2-Step Verification → App passwords.

### Background polling (Celery + Redis)
Inbox is polled automatically every 20 seconds (IMAP UID cursor — only new mail is fetched; a Redis lock prevents overlapping runs). Requires Redis running locally.
```bash
cd backend
./venv/bin/celery -A config worker -l info --concurrency=1   # terminal 1
./venv/bin/celery -A config beat -l info                     # terminal 2
```
Manual "Poll Inbox" / "Re-poll last N days" buttons still work alongside.

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev    # http://localhost:3001
```

## Flow
1. **Upload CSV** — Apollo-style export (First Name, Last Name, Title, Company Name, Company Name for Emails, Email, Email Status). Comma or tab delimited. Deduped by email.
2. **Template tab** — edit subject/body. Placeholders: `{{first_name}}`, `{{company_name}}`, etc.
3. **Send Campaign** — emails all `pending`/`failed` leads one by one (3s delay, `SEND_DELAY_SECONDS` in .env). Gmail limit ~500/day.
4. **Poll Inbox** (Dashboard tab) — polls Gmail inbox (configurable window in days; "Re-poll last N days" forces a rescan, stored emails are skipped). Every email is stored in the **Inbox** tab. Senders matching leads become replies, Claude classifies intent:
   - `soft_lead` (asks for links/proof/details) → AI drafts reply with portfolio link → **Drafts tab** → approve & send
   - `main_lead` (wants call / talk numbers) → flagged, filter with **★ Main Leads** button on Leads tab
   - `not_interested` / `other` → logged only
   - Unknown senders → Claude lead-or-not check, flagged "new lead" in Inbox
   All outbound emails logged in the **Sent** tab.
5. Draft replies thread correctly (In-Reply-To/References).

## API (localhost:8001)
```
POST /api/leads/upload/      multipart 'file'
GET  /api/leads/?intent=main_lead
GET/PUT /api/template/
POST /api/campaign/send/     {} or {"lead_ids":[...]}
POST /api/inbox/poll/        {} or {"days": 14}
GET  /api/inbox/?category=reply|new_lead|other
GET  /api/sent/
GET/PUT /api/settings/       {"poll_days": 7}
GET  /api/replies/
GET  /api/drafts/            PATCH /api/drafts/<id>/
POST /api/drafts/<id>/send/  POST /api/drafts/<id>/reject/
GET  /api/stats/
```
