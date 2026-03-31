# Agent notes (Cursor / Codex)

## Project intent

- Primary site under review: **https://puntacanayachts.com/**  
- Goals: SEO / traffic diagnosis (post–early-2025 redesign), aligned with stakeholder threads in `docs/context/chat_conversations_stakeholders.md`.  
- Stakeholders: TJ (business), Ken (build: custom PHP, MariaDB, nginx redirects, GTM). Code may be shared read-only via Drive; **GA4 is the main historical data source** (Ken noted GSC has very little data).

## Facts from context (verify before stating as current)

- Templates and URIs changed; nginx 301s map old WordPress paths to `/charter/…` (see transcript for snippet). One redirect may point romantic cruise to sunset cruise URL—treat as hypothesis until verified in live nginx config.  
- Ken controls GTM; redirects via nginx; no CMS.  
- Competitor / SERP quality concerns are **opinions** in chat—label them as such in summaries.

## How to work

1. Read `docs/context/chat_conversations_stakeholders.md` when answering stakeholder-style questions.  
2. Prefer **evidence**: GA4 (via MCP when configured), crawl/sitemap, and on-page checks—not generic SEO platitudes.  
3. **Secrets**: never commit service account JSON, `.env`, or private keys. Use env vars / Cursor MCP config only.  
4. **Python**: use Poetry (`poetry add`, `poetry run`). Keep changes minimal unless the user expands scope.

## MCP

If Google Analytics MCP is enabled, use it for GA4 reports; it does not replace technical crawls for a single-URL audit.
