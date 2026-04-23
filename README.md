# Punta Cana tours / PuntaCanaYachts SEO & SEM workspace

Evidence-based SEO and SEM analysis workspace for **https://puntacanayachts.com/** — a Punta Cana yacht charter business (operating since 2008). Stakeholders: TJ (owner), Ken (developer).

---

## Repository layout

| Path | Purpose |
|------|---------|
| `docs/context/` | Stakeholder chat exports, Ken's technical responses |
| `docs/screenshots/` | Supporting screenshots from conversations |
| `docs/analysis/` | Dated findings documents and crawl reports |
| `data/ga4/exports/` | Manual GA4 CSV exports (**gitignored** — place files here) |
| `scripts/analyze_ga4.py` | Parse GA4 exports, detect redesign date, channel breakdown |
| `scripts/crawl_site.py` | Live sitemap crawl, redirect audit, canonical/meta check |
| `scripts/fetch_ga4.py` | Pull GA4 via **Data API** (OAuth or service account; no CSV) |
| `scripts/fetch_google_ads.py` | Pull Google Ads via **Ads API** + GAQL (OAuth; see `.env.example`) |
| `scripts/generate_report.py` | Build the unified **HTML** report (GA4 + Ads + crawl); `make report` |
| `Makefile` | `make report` — runs `generate_report.py` with optional env overrides |

---

## HTML growth report (`make report`)

**What it does:** Writes **`reports/latest/index.html`** — a single local dashboard that combines **GA4** (daily sessions, key events, channels, landing pages), **Google Ads** (campaigns and search terms over the same windows), and a **live crawl** of the sitemap (redirects, canonicals, meta, JSON-LD, external links). Plotly charts, period comparisons, recommendations, and a short “before next run” checklist (including GA4 vs Ads conversion sanity checks when relevant).

**How to run:** Install deps, add secrets locally (see below), place or point to an OAuth Desktop client JSON (`client_secret*.json` under `data/ga4/` or `data/google_ads/`, or set `OAUTH_CLIENT` when calling Make). Repo-root **`.env`** is loaded automatically for Ads (and optional `GA4_PROPERTY_ID`).

```bash
poetry install
cp .env.example .env   # fill GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CUSTOMER_ID, etc.
make report
# Optional: OAUTH_CLIENT=/absolute/path/to/client_secret….json make report
poetry run python scripts/generate_report.py --help   # e.g. --skip-crawl for traffic-only
```

The HTML output path is **gitignored**; regenerate anytime. First OAuth run opens a browser; refresh tokens are stored under `data/` (ignored).

---

## Local secrets and tokens (not in Git)

If you delete this folder and re-clone, **restore or recreate** these (they are never committed):

| Item | Purpose |
|------|---------|
| `.env` | Ads developer token and customer IDs — copy from `.env.example` and refill |
| `data/ga4/client_secret*.json` (or your chosen path) | OAuth “Desktop app” client from Google Cloud Console |
| `data/ga4/oauth-token.json` | GA4 OAuth refresh token (re-created by signing in again if missing) |
| `data/google_ads/oauth-token.json` | Google Ads OAuth refresh token |
| Optional GA4 CSVs in `data/ga4/exports/` | Manual exports for `analyze_ga4.py` |

**Backups:** Encrypted disk, password-manager secure notes, or **encrypted** files in a private repo (e.g. [sops](https://github.com/mozilla/sops) / age, [git-crypt](https://github.com/AGWA/git-crypt)) are appropriate for `.env` and OAuth JSON. A **private dotfiles repo** is a good home for **shell config and install scripts**; avoid storing **plaintext** OAuth clients and refresh tokens there even if the repo is private (risk of accidental exposure, fork leaks, or laptop copy). Prefer a password manager or encrypted blob, then copy files into this repo after clone.

---

## GA4 Data API (`scripts/fetch_ga4.py`)

You do **not** need Google Cloud for hosting the site. You only need a **free Google Cloud project** to enable the Analytics Data API and create credentials (OAuth “Desktop app” or a service account key).

- **Property ID** (PuntaCanaYachts): `452157058` — default in script; override with env `GA4_PROPERTY_ID`.
- If you **do not** see **Property access management** in GA4 Admin, your role is likely Viewer/Analyst: you **cannot** add a service account, but **OAuth still works** (same Google account you use for GA4).

```bash
# One-time: create OAuth Desktop client JSON in Cloud Console, save outside repo or under data/ga4/ (gitignored)
poetry run python scripts/fetch_ga4.py --oauth-client /path/to/client_secret.apps.googleusercontent.com.json --out data/ga4/exports/api-traffic-by-channel.csv --start 2026-03-01 --end 2026-04-08

# Other reports: --report traffic | events | daily | landing
poetry run python scripts/fetch_ga4.py --oauth-client ... --report events --start 2026-03-01 --end 2026-03-31 --out data/ga4/exports/api-events.csv
poetry run python scripts/fetch_ga4.py --oauth-client ... --report daily --start 2026-01-01 --end 2026-04-08 --out data/ga4/exports/api-daily.csv
poetry run python scripts/fetch_ga4.py --oauth-client ... --report landing --limit 100 --start 2026-03-01 --end 2026-03-31 --out data/ga4/exports/api-landing.csv
```

Service account path (requires someone with **Editor** on GA4 to invite the SA email as **Viewer**):

```bash
poetry run python scripts/fetch_ga4.py --credentials /path/to/service-account.json --start 2026-01-01 --end 2026-04-08
```

---

## Google Ads API (`scripts/fetch_google_ads.py`)

Same idea as GA4: **Google Cloud project** → enable **Google Ads API** → OAuth **Desktop** client with scope **Google Ads API** (`…/auth/adwords`). You can reuse the same Desktop JSON as GA4 **after** adding that scope to the client in Cloud Console.

You also need from the **Google Ads** UI: **Developer token** and **Customer ID** (10 digits, no dashes). Copy `.env.example` → `.env` or export variables — see `.env.example`. The script loads **`.env`** from the repo root automatically (no `python-dotenv` dependency).

**Developer token:** Google only shows **API Center** (where you apply for / copy the token) on a **Manager account (MCC)**, not on a regular client account. Create a free [manager account](https://ads.google.com/home/tools/manager-accounts/), link the Punta Cana client under it, then open **API Center** from the **manager**. In some account setups you can query the client directly without `login-customer-id`; if you do set `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, the script now falls back automatically when that header causes `USER_PERMISSION_DENIED`. Until Basic Access is approved, use Ads UI CSV exports instead of the API.

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN="…"
export GOOGLE_ADS_CUSTOMER_ID="1234567890"

poetry run python scripts/fetch_google_ads.py \
  --oauth-client data/ga4/client_secret_….json \
  --report campaigns \
  --start 2026-03-01 --end 2026-04-08 \
  --out data/google_ads/exports/campaigns.csv

poetry run python scripts/fetch_google_ads.py \
  --oauth-client data/ga4/client_secret_….json \
  --report search_terms \
  --start 2026-03-01 --end 2026-04-08 \
  --out data/google_ads/exports/search_terms.csv
```

First run opens a browser; refresh token is stored in `data/google_ads/oauth-token.json` (gitignored), separate from GA4’s token.

---

## Quickstart

```bash
poetry install

# Analyse GA4 exports (place CSVs in data/ga4/exports/ first)
poetry run python scripts/analyze_ga4.py

# Live crawl of puntacanayachts.com (~35s, hits the network)
poetry run python scripts/crawl_site.py

# Unified HTML report (needs .env + OAuth client JSON — see "HTML growth report")
# make report

# GA4 / Google Ads API pulls (see sections below; Ads script auto-loads repo-root .env)
# poetry run python scripts/fetch_ga4.py --oauth-client …
# poetry run python scripts/fetch_google_ads.py --oauth-client …
```

Requires **Python 3.11–3.13** (`google-ads` does not support 3.14 yet). Lockfile committed for reproducibility.

---

## Where we are (April 2026)

### What was found and fixed
- **Google Ads misconfigured at launch (March 3, 2026)** — restored ~March 15–19. This was the primary cause of the sales dip, not SEO.
- **Canonical tags** — missing on all pages at launch, now fixed.
- **Duplicate title tags** — fixed.
- **Redirects** — 15/16 old WordPress paths correctly 301 to new `/charter/` paths.

### Open issues
| Issue | Priority |
|-------|----------|
| 3 of 5 Google Ads campaigns point to `/punta-cana-yacht-rentals/` (content page, not ideal for paid) | High |
| New content pages orphaned — no inbound internal links from main site | Medium |
| Homepage has no contact/quote form | Medium |
| Ken's GTM testing sessions still polluting GA4 (~56/month) | Low |
| `/charter/romantic-cruise-for-two/` returns 404 — one ad still references it | Medium |

### What to read
- `docs/analysis/2026-04-01_findings-for-ken.md` — plain-language first-round findings (sent to Ken)
- `docs/analysis/2026-04-02_second-round-findings.md` — post-fix analysis with paid traffic breakdown

---

## Google Analytics 4 MCP (Cursor)

The GA4 MCP uses a **GCP service account** (not your Gmail login). Setup:

1. [Google Cloud Console](https://console.cloud.google.com/) → enable **Google Analytics Data API**
2. **IAM → Service accounts** → create → **Keys → Add key → JSON**
3. GA4 → **Admin → Property access management** → add the JSON's `client_email` as **Viewer**
4. Add to Cursor MCP config (see example: `docs/google-analytics-mcp.cursor.example.json`):

```json
{
  "mcpServers": {
    "google-analytics": {
      "command": "npx",
      "args": ["-y", "mcp-server-google-analytics"],
      "env": {
        "GOOGLE_CLIENT_EMAIL": "your-sa@your-project.iam.gserviceaccount.com",
        "GOOGLE_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
        "GA_PROPERTY_ID": "123456789"
      }
    }
  }
}
```

Keep credentials in `~/.cursor/mcp.json` or `.cursor/mcp.json` (gitignored). Never commit keys.

**Note:** `mcp-server-google-analytics` (npm) is deprecated. Prefer the [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1) directly via `scripts/` once credentials are available.

---

## Git conventions

- [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `analysis:`
- One branch per task; validate commit message with human before committing
- After each PR merge: `git checkout main && git pull origin main && git branch -d <branch>`
- Delete stale remote branches: `git push origin --delete <branch>`
