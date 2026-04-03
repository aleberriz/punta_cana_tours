# Agent notes (Cursor / Codex)

## Project intent

- Primary site: **https://puntacanayachts.com/**
- Goals: SEM diagnosis (Google Ads performance) + SEO improvement (organic visibility) for a Punta Cana yacht charter business
- Stakeholders: TJ (business owner), Ken (developer: custom PHP, MariaDB, nginx, GTM)
- This workspace is for evidence-based analysis; stakeholder context lives in `docs/context/`, GA4 data in `data/ga4/exports/` (gitignored), analyses in `docs/analysis/`

---

## Verified site facts (as of April 2026)

### Stack
- Custom PHP + MariaDB; no CMS
- nginx for 301 redirects (old WordPress paths → new `/charter/` paths)
- GTM for tag management; GA4 for analytics; Google Ads for paid traffic
- No GSC history prior to March 2026 (recently set up)

### URL structure
- Old WordPress paths (pre-March 3 redesign): `/malibu-party-boat`, `/caribbean-dream-sail`, etc.
- New paths: `/charter/malibu-party-boat/`, `/charter/caribbean-dream-sail/`, etc.
- Category pages: `/charters/`, `/charters/half-day/`, `/charters/full-day/`, `/charters/powerboats/`, `/charters/sailboats/`
- All production URLs have **trailing slashes**. GA4 strips them in some reports — normalise when cross-referencing with nginx config or sitemap.

### Verified nginx redirects (April 2026)
- 15 of 16 old WordPress paths redirect correctly to new `/charter/` equivalents ✓
- `/romantic-cruise-for-two` → `/charter/sunset-cruise-punta-cana/` ✓ — this is **correct**: the product was renamed "Sunset Cruise"; `/charter/romantic-cruise-for-two/` returns 404. We initially flagged this as a bug — it is not.

### Conversion mechanism (verified via crawl + Ken)
1. User fills inquiry form (POST → `/submit-inquiry`)
2. Server runs bot checks: **CSRF token**, **honeypot** (`website` text field, hidden via CSS), **time trap** (`tentative_date` hidden field checks fill speed)
3. On pass → redirect to `/thank-you/` WITH PHP session flag → `charter_inquiry_submitted` pushed to dataLayer → GTM fires **"Google Ads - Charter Inquiry"** conversion tag
4. On fail → redirect to `/thank-you/` WITHOUT session flag → **no conversion fires, no visible error to user**
5. **Risk**: time trap and honeypot may produce false negatives for fast mobile users or users on slow connections who submit after a long delay. If bot check failures are high, real conversions are being silently lost.

### GA4 attribution model — critical to understand
- Key events fire on `/thank-you/` (where `dataLayer.push` runs), **not** on the form page
- Landing page × key events reports attribute the key event back to the **session's landing page** (session-scoped). This means a user who lands on `/charter/yacht-charters/` (which has **no form**), browses to a product page, and submits a form there, shows as a conversion attributed to `/charter/yacht-charters/`
- Do **not** interpret zero key events on a landing page as "the form doesn't work on this page" — it may mean users arrived there, browsed elsewhere, and either converted on another page or left
- For true per-ad/per-keyword conversion attribution, use **Google Ads reports** (gclid-based), not GA4 landing page reports

### Google Ads campaigns (as of April 2026)
- 5 total active campaigns
- 2 ads → `/charter/private-yacht-isla-saona/` (highest paid traffic destination, 32% of paid sessions)
- 3 ads → `/punta-cana-yacht-rentals/` (informational content page — conversion path concern)
- Google Ads was **turned off and misconfigured at launch (March 3, 2026)** — restored ~March 15–19
- **Use March 15, 2026 onward** for meaningful performance data; pre-mid-March is contaminated

### Canonical tags
Fixed (April 2026). All 33 sitemap pages now have `<link rel="canonical">`. Verify after any template changes.

### JSON-LD
Present on all pages. Schema types: `LocalBusiness`, `TouristAttraction`, `FAQPage` (on content pages). Implemented during March 2026 redesign.

### New content pages (created ~March 21–22, 2026)
- `/punta-cana-yacht-rentals/` — general landing page; 3 of 5 Google Ads campaigns point here
- `/best-time-to-visit-punta-cana/` — informational/SEO content
- `/saona-island-excursion/` — informational/SEO content
- **None of these are linked from the main site** (homepage, `/charters/`, or product pages). They exist in the sitemap only. Internal links needed to pass PageRank.

---

## Data hygiene

- **Use March 15, 2026+ only** for current-state analysis. Google Ads was broken before that date.
- `tagassistant.google.com` sessions (~56/month) = Ken's GTM testing. Filter via GA4 → Admin → Data Streams → Define internal traffic. IP-based filter is unreliable (DHCP + VPN). User-ID exclusion is more robust.
- `localhost:8000` referral = Ken's local dev environment. Same filter.
- GA4 strips trailing slashes in some reports. Add slash when cross-referencing with nginx/sitemap.
- GA4 CSV exports: always note date range, report type, filters, and dimensions applied. The same metric looks different in different report types.

---

## Lessons learned

1. **SEM before SEO when revenue drops suddenly.** The sales dip was caused by Google Ads being misconfigured at launch — not the redesign or organic SEO. Check paid channel health first.
2. **Validate redirect destinations before flagging bugs.** We incorrectly flagged `/romantic-cruise-for-two` → sunset cruise as wrong. Always `curl` both source and destination to confirm the page exists.
3. **Session-scoped attribution ≠ event-scoped.** In a form → redirect → thank-you flow, GA4 landing page reports show key events attributed to the session entry page, not the form page. A page with no form can show conversions (e.g. `/charter/yacht-charters/`). Use Google Ads gclid reports for true ad-level attribution.
4. **Bot checks can silently reject real users.** A time trap or honeypot that's too strict causes false negatives with no visible feedback to the user. Worth monitoring `/thank-you/` sessions with vs without the session flag.
5. **Content pages ≠ ad landing pages.** An SEO-optimised informational page (e.g. `/punta-cana-yacht-rentals/`) is not a good paid search landing page. Product pages with a single inquiry CTA convert better for paid traffic.
6. **Internal links matter for new pages.** Pages reachable only via sitemap carry little PageRank. Every new content page needs at least one in-context internal link from a high-traffic page.
7. **GA4 MCP requires a service account, not OAuth.** The `mcp-server-google-analytics` npm package (now deprecated) uses `GOOGLE_CLIENT_EMAIL` + `GOOGLE_PRIVATE_KEY` from a GCP service account. Your Gmail access to the GA4 UI is separate and does not enable MCP access.

---

## How to work

1. Read `docs/context/` for all stakeholder background before starting a new session.
2. Read `docs/analysis/` for prior findings — do not repeat confirmed facts.
3. Prefer evidence: GA4 exports → `scripts/analyze_ga4.py`; live site → `scripts/crawl_site.py`. Extend these scripts rather than writing one-off code.
4. When you need GA4 data not in `data/ga4/exports/`, document **exactly** what report type, date range, dimensions, metrics, and filters to use — then ask the user to pull it. Prefer Explore → Free form for cross-dimensional queries.
5. **Secrets**: never commit service account JSON, `.env`, or private keys.
6. **Python**: use Poetry (`poetry add`, `poetry run`).
7. **Git**: conventional commits, feature branches per task. Validate commit messages with user before committing.

## MCP

GA4 MCP not yet configured. Data comes from manual exports in `data/ga4/exports/` (gitignored).

To enable: Ken or TJ creates a GCP service account → enables Analytics Data API → grants Viewer on the GA4 property → shares `client_email` + `private_key` + numeric `GA_PROPERTY_ID`. See `README.md` for full setup and example Cursor config.

If MCP is enabled, use it for on-demand GA4 queries. It does not replace live crawls for technical audits.
