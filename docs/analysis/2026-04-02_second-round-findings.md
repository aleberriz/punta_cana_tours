# Second round findings — PuntaCanaYachts.com
_Data: March 1 – April 3, 2026 (GA4 channel export + live crawl)_
_Compared against: Jan 1 – Feb 28, 2026 baseline_

---

## What Ken fixed (confirmed live)

| Problem | Status |
|---------|--------|
| Canonical tags on all pages | Fixed ✓ |
| Duplicate title tags | Fixed ✓ |
| GA4 / Google Ads tracking restored | Fixed ✓ (but see below) |
| Problem 4 (romantic cruise redirect) | **We were wrong — Ken was right** |

### On Problem 4
`/charter/romantic-cruise-for-two/` returns 404 — the page does not exist.
`/charter/sunset-cruise-punta-cana/` returns 200 — that IS the product (renamed).
The redirect is correct. Acknowledged.

---

## Channel performance: March vs Jan–Feb baseline

| Channel | Sessions/day (Jan–Feb) | Sessions/day (Mar) | Change | KE/day (Jan–Feb) | KE/day (Mar) | Change |
|---------|----------------------|-------------------|--------|-----------------|-------------|--------|
| Paid Search | 31.5 | 17.0 | **−46%** | 3.5 | 0.1 | **−97%** |
| Direct | 30.4 | 22.9 | −25% | 0.3 | 0.1 | −52% |
| Organic Search | 7.9 | 7.4 | **−6%** | 0.6 | 0.0 | −100% |
| Referral | 7.3 | 8.1 | +11% | 0.6 | 0.0 | −100% |
| **Total** | **~78** | **~57** | **−28%** | **~5.0** | **~0.3** | **−97%** |

**Total key events March 1–April 3: 9** (vs ~295 over Jan–Feb, ~2.5/day baseline).

---

## Key findings

### 1. Conversions are still essentially zero — this is the crisis

9 key events over 34 days, 0.26/day, vs a baseline of ~5/day.
Ken said Google Ads has been working for 10–14 days. Even accounting for the first ~20 days of March being broken, the last 10–14 days should show recovery. They don't — 4 key events from Paid Search across the entire month.

**Most likely cause:** Google Ads ads are probably still pointing to **old URLs** (e.g. `/malibu-party-boat`). When a paid visitor clicks an ad and lands on the old URL, nginx 301-redirects them to the new `/charter/malibu-party-boat/`. GA4 / GTM can lose the conversion trigger through this redirect chain, because the tag fires on the final URL but the ad click was attributed to the old URL. This is a classic post-migration Google Ads problem. **Ken needs to update all ad destination URLs to the new `/charter/` paths.**

### 2. Paid Search sessions are down 46% per day

Jan–Feb: 31.5 paid sessions/day → March: 17.0/day. Either:
- Ad spend was reduced
- Ad quality score dropped (landing pages changed, redirects)
- Campaign targeting shifted

Combined with the near-zero conversion rate, this means Google Ads is underperforming on both volume AND quality.

### 3. Organic Search is essentially flat (good news)

Only −6% per day. The redesign did not hurt organic traffic volume. The 0 key events from organic is a tracking issue, not an organic traffic collapse.

### 4. Three new content pages are orphaned — no inbound internal links

Live crawl confirmed: homepage, `/charters/`, and all product pages have zero links pointing to:
- `/punta-cana-yacht-rentals/`
- `/best-time-to-visit-punta-cana/`
- `/saona-island-excursion/`

The pages are reachable via sitemap, but Google will assign them very low PageRank without internal links. These pages are well-built (good canonicals, JSON-LD, meta descriptions) — they just need to be connected to the site's link graph.

### 5. Homepage has no contact form

The homepage gets the most traffic but has no form — only "Contact" links that require a page navigation. Every product page that was checked has a quote request form. The homepage should too, or at minimum a prominent direct CTA. High-intent paid visitors expect to inquire without extra clicks.

### 6. tagassistant.google.com still polluting (56 sessions)

Ken's internal IP filter is not catching his GTM testing sessions. The IP exclusion doesn't work if he's on VPN or if DHCP rotated. Until this is resolved, reported session totals are inflated by ~3%.

### 7. AI referral traffic appearing

`chatgpt.com`: 7 sessions. `perplexity.ai`: 1 session. Small but real — the site is being surfaced in AI chat responses. This validates the AEO angle Ken and TJ discussed. Worth monitoring as a trend.

---

## Open questions for Ken

1. **What URLs are the Google Ads destination URLs currently set to?** Old paths or new `/charter/` paths?
2. **What exactly is the key event?** What user action triggers it — form submit, phone click, specific button?
3. **What was March ad spend** vs Jan–Feb? Was the budget maintained?

---

## Action list

| # | Action | Owner | Priority |
|---|--------|-------|----------|
| 1 | Update all Google Ads destination URLs to new `/charter/` paths | Ken | Urgent |
| 2 | Add internal links to 3 new content pages from homepage / /charters/ | Ken | This week |
| 3 | Add contact/quote form to homepage | Ken | This week |
| 4 | Confirm what the key event is and test it manually end-to-end | Ken | Urgent |
| 5 | Fix tagassistant sessions (use User-ID exclusion not IP) | Ken | Soon |
