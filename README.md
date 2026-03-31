# Punta Cana tours / PuntaCanaYachts SEO workspace

Private workspace for analytics-backed SEO review of **https://puntacanayachts.com/** and related stakeholder context (TJ, Ken).

## Repository layout

| Path | Purpose |
|------|--------|
| `docs/context/chat_conversations_stakeholders.md` | Exported Signal/thread notes: access asks, stack (custom PHP, MariaDB, nginx, GTM), redirects, sitemap link |
| `docs/screenshots/` | Supporting screenshots from those conversations |

## Python (Poetry)

```bash
poetry install
poetry run python ...
```

Requires **Python 3.11+**. Lockfile is committed for reproducible environments.

## Google Analytics 4 MCP (Cursor / Claude-style clients)

The common GA4 MCP servers (for example [`mcp-server-google-analytics`](https://github.com/ruchernchong/mcp-server-google-analytics)) authenticate with a **Google Cloud service account**, not by logging in as your Gmail user inside the MCP.

1. **GA4 access for `aberriz@gmail.com`**  
   Ken should add your Google account to the GA4 property (Analyst or Viewer) so you can use the GA UI and confirm property ID.

2. **MCP access (service account)**  
   - Create or pick a GCP project → enable **Google Analytics Data API**.  
   - Create a **service account** → download JSON key.  
   - In GA4 → **Admin → Property access management** → add the service account **`client_email`** with **Viewer**.  
   - Set env vars (or Cursor MCP `env` block): `GOOGLE_CLIENT_EMAIL`, `GOOGLE_PRIVATE_KEY` (escape newlines as `\n`), `GA_PROPERTY_ID` (numeric property ID).

3. **Cursor**  
   Add an MCP server entry that runs e.g. `npx -y mcp-server-google-analytics` with those env vars. Do **not** commit keys or `.env` (see `.gitignore`).

**URL-specific SEO:** GA4 reports are great for traffic, landing pages, and trends. For “audit this URL” (crawl, meta, redirects), combine MCP/GA with crawl tools (Screaming Frog, `curl`, or a small Python script in this repo later).

## Conventional commits

Use [Conventional Commits](https://www.conventionalcommits.org/), for example: `chore: add poetry and docs layout`, `docs: document GA4 MCP setup`.

## Branch

Active setup work: `chore/repo-init` (or follow-up branches per task).
