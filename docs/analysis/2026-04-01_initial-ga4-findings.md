# Initial GA4 findings — PuntaCanaYachts
_Period covered: Jan 1–Feb 28, 2026 vs Mar 1–Mar 31, 2026 (post-redesign)_  
_Property: PuntaCanaYachts (account: Caribbean Dream)_  
_Generated: 2026-04-01 from manual GA4 exports_

---

## TL;DR for TJ and Ken

1. **Key events (conversions) went to zero in March.** This is the most urgent finding. Either the site's conversion action broke in the redesign, or GTM tags stopped firing. Until this is confirmed as a tracking issue vs real, you cannot tell if the sales dip is Google's fault or the site's.
2. **Organic search was never the main channel.** In March, only ~9% of active users came from Google organic. ~43% came direct and ~35% from paid Google Ads. The redesign did not kill organic traffic because organic was already very small.
3. **The URL migration mostly worked, but left real gaps.** Old pages that ranked in Jan–Feb now get zero sessions in March. New `/charter/` pages are picking up some of that, but not fully.
4. **One confirmed wrong redirect:** `/romantic-cruise-for-two` → `/charter/sunset-cruise-punta-cana` (should be `/charter/romantic-cruise-for-two`).
5. **56 sessions in March are Ken's own GTM tag-testing** (`tagassistant.google.com`). These inflate March numbers and should be filtered in GA4.

---

## 1. Traffic channels (March only — `download.csv`)

| First acquisition channel | Active users | Share |
|--------------------------|-------------|-------|
| Direct / (none) | 492 | 43% |
| Google / cpc (paid) | 400 | 35% |
| Google / organic | 107 | 9% |
| puntacanatours.com / referral | 93 | 8% |
| (data not available) | 17 | 1% |
| **Total** | **1,144** | |

> **Note for Ken:** The `Traffic_acquisition` CSV export came back with only minor sources (DuckDuckGo, Yahoo, referrals). It is missing Google organic and direct. Please re-export **Traffic acquisition → Session default channel group** (not session source/medium) with no filters applied so we get the full channel split for Jan–Feb for comparison.

---

## 2. Key events (conversions) — critical

| Period | Homepage key events | All-pages total key events |
|--------|--------------------|-----------------------------|
| Jan–Feb | 16 (homepage) + ~20 across product pages | ~36+ |
| March | **0 everywhere** | **0** |

**This is the most important finding in the dataset.**  
Every key event went to zero after the redesign. Possible causes:
- GTM trigger or tag was broken in new templates (most likely).
- The conversion action (e.g., contact form submit, button click, phone call) was renamed or removed from the new design.
- The GA4 Measurement ID changed or was mis-installed.

**Action for Ken:** Check GTM → which tag fires as a "key event"? Preview mode → does it fire on the new site? Check GA4 → Admin → Events → is the key event still marked as a "key event"?

---

## 3. Landing pages — URL migration

### Jan–Feb (old URLs, non-zero sessions only)

| Landing page | Sessions | Key events |
|---|---|---|
| / (homepage) | 177 | 16 |
| /caribbean-dream-sail | 45 | 3 |
| /private-yacht-isla-saona | 39 | 8 |
| /malibu-party-boat | 32 | 2 |
| /romantic-cruise-for-two | 26 | 1 |
| /picaflor-mini-yacht | 28 | 1 |
| /catamaran-st-mary | 15 | 1 |
| /charter/yacht-charters | 17 | 2 |

Old-style URLs (no `/charter/` prefix) were getting real traffic and conversions in Jan–Feb. These are mostly WordPress-era paths.

### March (new URLs showing up, old ones gone)

| Landing page | Sessions | Key events |
|---|---|---|
| / (homepage) | 64 | **0** |
| /charter/private-yacht-isla-saona | 30 | 0 |
| /charter/caribbean-dream-sail | 23 | 0 |
| /charter/malibu-party-boat | 23 | 0 |
| /charters | 14 | 0 |
| /charter/picaflor-mini-yacht | 12 | 0 |
| /charter/romantic-cruise-for-two | 10 | 0 |
| /punta-cana-yacht-rentals | 10 | 0 |
| /charter/punta-cana-wedding-boat | 6 | 0 |

**Homepage sessions dropped from 177 to 64 (−64%).** New `/charter/` URLs are appearing, which confirms the redesign went live and people are finding the new paths. But no key events on any page.

---

## 4. Organic search (Google) — GSC data via GA4

Jan–Feb shows **0 GSC clicks and impressions** for everything — confirms Ken's statement that GSC was set up very recently and has no historical data.

March shows GSC starting to populate:

| Page | Impressions | Clicks | Avg. position |
|------|------------|--------|--------------|
| / | 2,553 | 18 | 18.2 |
| /charters/ | 779 | 1 | 49.4 |
| /charter/caribbean-dream-sail/ | 219 | 2 | 28.4 |
| /about-us (and /our-story, /why-us, /team) | 168 each | 0 | ~9–10 |
| /charter/malibu-party-boat/ | 243 | 3 | 12.6 |
| /charter/picaflor-mini-yacht/ | 37 | 7 | 12.5 |

**Observations:**
- `/about-us`, `/our-story`, `/team`, `/why-us` all show **exactly 168 impressions** at position ~9–10. This is suspicious — it may indicate a canonical issue or that Google sees them as equivalent pages. Worth checking `<link rel="canonical">` on all four.
- Homepage gets 2,553 impressions but only 18 clicks (0.7% CTR) at position 18. That's page 2 territory, which is normal for a competitive market. Nothing broken here — this is just where the site's organic visibility sits.
- Old URL `/private-yacht-isla-saona/` still shows 139 impressions and 5 clicks in March but **0 sessions in the landing page report** — traffic is likely being swallowed by the redirect chain without GA4 registering the final landing page. Check that GA4 tag fires on the post-redirect URL.

---

## 5. Confirmed redirect issue

From Ken's nginx config vs data:

```nginx
# What's in nginx:
rewrite ^/romantic-cruise-for-two/?$ /charter/sunset-cruise-punta-cana/ permanent;

# What it should probably be:
rewrite ^/romantic-cruise-for-two/?$ /charter/romantic-cruise-for-two/ permanent;
```

- `/charter/romantic-cruise-for-two` got 10 sessions in March (a real page exists at this URL).
- `/charter/sunset-cruise-punta-cana` got only 3 sessions, and may be a different product.
- Anyone following the old `/romantic-cruise-for-two` link lands on the wrong product page.

**Fix:** Update the nginx `rewrite` for `/romantic-cruise-for-two` to point to `/charter/romantic-cruise-for-two/`.

---

## 6. Noise to filter

- **`tagassistant.google.com` — 56 sessions in March.** This is Ken using the GTM tag assistant to test the site. Create a filter or internal traffic definition in GA4 (Admin → Data Streams → Define internal traffic) using Ken's IP so these don't contaminate reports.
- **`localhost:8000` referral** — also Ken's local development environment. Same fix.

---

## 7. What we still need

| Gap | Why it matters | Ask |
|-----|----------------|-----|
| Traffic acquisition (all channels) for Jan–Feb | Can't compare organic/direct/paid pre vs post without it | Re-export with no filters, channel grouping view |
| Same period last year (Jan–Mar 2025) | True seasonality baseline | Another export or GA4 comparison range |
| Key event definition | Can't diagnose conversion drop without knowing what the key event is | Ken: what event is marked as key event in GA4? Contact form? Button click? |
| GTM tag audit | Whether conversion tracking is broken | Ken: GTM Preview on new site — does the tag fire? |
| Canonical tags on `/about-us`, `/our-story`, `/team`, `/why-us` | 4 pages with identical impressions count | Quick curl / view-source check |
