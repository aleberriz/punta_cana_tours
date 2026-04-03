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

---

## Quickstart

```bash
poetry install

# Analyse GA4 exports (place CSVs in data/ga4/exports/ first)
poetry run python scripts/analyze_ga4.py

# Live crawl of puntacanayachts.com (~35s, hits the network)
poetry run python scripts/crawl_site.py
```

Requires **Python 3.11+**. Lockfile committed for reproducibility.

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
