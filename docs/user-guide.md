# User Guide

## First Access

1. Open Prima Pagina in your browser
2. Log in with the credentials your admin provided
3. On first login, go to **Settings** (top right) and choose your preferred language

---

## Adding RSS Feeds

RSS feeds are managed by administrators and visible to all users to subscribe to.

**As a user:**
1. Go to **Reader** → sidebar
2. Browse available feeds by category
3. Click **Subscribe** on any feed you want to follow

**As an admin:**
1. Go to **Admin** → **Feeds** → **Add feed**
2. Paste the feed's RSS/Atom URL
3. The app will auto-detect the title — you can override it
4. Set the polling interval (how often to check for new articles)
5. Assign a category (optional but recommended)

**Finding feed URLs:**  
Most news sites have an RSS link in their footer, or add `/rss` or `/feed` to the site URL.
Example: `https://www.theguardian.com/world/rss`

---

## Reader

The Reader shows articles from all your subscribed feeds.

### Navigation

- **Left sidebar** — switch between "All feeds" or a specific feed
- **Filter bar** — show Unread only, Starred only, or All
- **Article list** — click any article to read it inline
- **Keyboard shortcuts:**
  - `j` / `k` — next / previous article
  - `r` — mark as read / unread
  - `s` — star / unstar
  - `o` — open original in new tab
  - `?` — show all shortcuts

### Reading Articles

Click an article title to open it in the reader panel. Prima Pagina fetches the full article text when available (not just the excerpt).

---

## Front Page

The Front Page shows the most important articles from all your feeds in a newspaper layout:

- **Hero** (top left) — the single highest-scored article
- **Second row** — next 3 articles
- **Columns** — articles grouped by category

Scoring factors: recency, source weight, and your reading history (articles similar to ones you've read score higher).

### Digest Banner

If a press digest has been generated today, a banner appears at the top. Click **Read digest** to open the full digest, which summarises the day's top stories.

Click **Generate digest** to generate a new one on demand (takes 30–90 seconds).

---

## Virtual Feeds

Virtual feeds are custom aggregations that you can share as an RSS feed.

1. Go to **Reader** → (coming soon via settings)
2. Set filters: category, tags, or a combination
3. Copy the generated RSS URL — use it in any RSS reader
4. The URL includes a secret token; regenerate it if you need to revoke access

---

## Press Digest

The digest is an AI-generated summary of the day's top articles.

- **Automatic**: generated every day at 07:00 (configurable by admin)
- **On demand**: click **Generate digest** on the Front Page

The digest groups articles by topic and provides a concise summary of each group.

---

## Telegram Notifications

If configured by your admin, you can receive:

- **New article alerts** — for feeds you're subscribed to
- **Daily digest** — when the press digest is ready

Ask your admin to configure a Telegram bot for your account.

---

## Settings

Go to **Settings** (top navigation) to:

- **Change language** — switch between IT, EN, FR, DE, ES, PT
- **Change password** — enter current and new password
- **Manage sessions** — see all active sessions, revoke any you don't recognise

---

## Offline Mode

Prima Pagina works as a Progressive Web App (PWA):

- **Install** — use your browser's "Add to home screen" or "Install app" option
- **Offline reading** — articles you've already loaded remain readable without internet
- **Mark as read offline** — syncs automatically when you come back online

An orange banner appears at the top when you're offline.

---

## Keyboard Shortcuts (Reader)

| Key | Action |
|-----|--------|
| `j` | Next article |
| `k` | Previous article |
| `r` | Toggle read/unread |
| `s` | Toggle star |
| `o` | Open original URL |
| `←` | Back to list |
| `?` | Show shortcut help |
