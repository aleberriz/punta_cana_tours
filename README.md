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

The common GA4 MCP servers (for example [`mcp-server-google-analytics`](https://github.com/ruchernchong/mcp-server-google-analytics)) use a **Google Cloud service account** (JSON key). They do **not** support “sign in with Google” OAuth in the MCP the way a browser does—OAuth with your Gmail is possible in custom apps, but this npm server expects **service account** credentials.

1. **GA4 access for `aberriz@gmail.com`**  
   Ken should add your Google account to the GA4 property (Analyst or Viewer) so you can use the GA UI and confirm the numeric **property ID**.

2. **MCP access (service account)**  
   - In [Google Cloud Console](https://console.cloud.google.com/): enable **Google Analytics Data API**.  
   - **IAM → Service accounts** → create one → **Keys → Add key → JSON** (keep this file private).  
   - In GA4 → **Admin → Property access management** → add the JSON’s **`client_email`** (`…@….iam.gserviceaccount.com`) with **Viewer**.  
   - Map JSON → MCP env: `GOOGLE_CLIENT_EMAIL`, `GOOGLE_PRIVATE_KEY` (PEM string with `\n` for newlines), `GA_PROPERTY_ID`.

3. **Cursor (install / configure now, fill secrets when ready)**  
   - Needs **Node.js 20+** (for `npx`).  
   - **Cursor → Settings → MCP** (or edit your MCP config): add a server that runs `npx` with args `-y`, `mcp-server-google-analytics` and the three `env` keys above.  
   - Example block: [`docs/google-analytics-mcp.cursor.example.json`](docs/google-analytics-mcp.cursor.example.json) (copy values from your JSON key; do not commit them).  
   - Until the key exists, you can still add the server with placeholders—the process will fail to auth until `GOOGLE_*` and `GA_PROPERTY_ID` are correct.

Local overrides with real keys: use `~/.cursor/mcp.json` or project `.cursor/mcp.json` (see `.gitignore` if you keep secrets there).

**URL-specific SEO:** GA4 reports are great for traffic, landing pages, and trends. For “audit this URL” (crawl, meta, redirects), combine MCP/GA with crawl tools (Screaming Frog, `curl`, or a small Python script in this repo later).

## Conventional commits

Use [Conventional Commits](https://www.conventionalcommits.org/), for example: `chore: add poetry and docs layout`, `docs: document GA4 MCP setup`.

## Branch

Active setup work: `chore/repo-init` (or follow-up branches per task).
