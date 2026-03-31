# What we found — PuntaCanaYachts.com audit

_Based on GA4 data (Jan–Mar 2026) and a live crawl of the site (Apr 1, 2026)_

---

## Problem 1 — Conversion tracking broke at launch *(most urgent)*

**Evidence:** In January and February, the site recorded **295 "key events"** (the thing GA4 calls a conversion — contact form, phone click, or whatever Ken set up). In March, after the redesign went live on **March 3**, that number went to **zero on every single page**. Not lower — zero. Conversions don't drop to exactly zero unless tracking is broken.

**Suggestion for Ken:** Open GTM in Preview/Debug mode on the live site. Go through the contact or booking flow and confirm the conversion tag actually fires. If it doesn't fire, the tag is referencing something that no longer exists on the new templates (a CSS class, a button ID, a form that was renamed). Fix that first, because until tracking is restored we cannot tell if sales actually dropped or if we just stopped measuring them.

---

## Problem 2 — Google Ads was carrying the business, not SEO

**Evidence:** Of the 295 conversions in Jan–Feb, **204 (69%) came from Paid Search (Google Ads)** at an 11% conversion rate. Organic search contributed only 35 conversions. This means the site was never primarily an "SEO site" — it ran on paid ads. If the Google Ads campaigns were paused or disrupted when the new site launched, that alone explains the sales dip, with no SEO explanation needed.

**Suggestion for Ken / TJ:** Check the Google Ads account. Were campaigns running continuously through March? Did any ads point to old URLs that now redirect? If campaigns were paused or landing pages broke, that's the revenue story.

---

## Problem 3 — Every page is missing a canonical tag

**Evidence:** The live crawl checked all 33 pages in the sitemap. Zero of them have a `<link rel="canonical">` tag. A canonical tag tells Google "this is the definitive version of this URL." Without it, Google has to guess — and it often guesses wrong (e.g., treating `/contact` and `/contact/` as two different pages, or picking an HTTP version instead of HTTPS).

We also see a likely symptom of this in the Google Search Console data: four pages (`/about-us`, `/our-story`, `/team`, `/why-us`) all show exactly 168 impressions at nearly identical ranking positions — which strongly suggests Google is confused about their relationship and treating them as equivalent.

**Suggestion for Ken:** Add `<link rel="canonical" href="[full URL of this page]">` to the `<head>` of every page template. Since the site is custom PHP, this is probably one template change that propagates everywhere.

---

## Problem 4 — One redirect is sending visitors to the wrong page

**Evidence:** The live crawl confirmed it. When someone visits `/romantic-cruise-for-two` (the old URL that used to rank and get bookings), nginx sends them to `/charter/sunset-cruise-punta-cana/` — a completely different product. The correct destination is `/charter/romantic-cruise-for-two/`, which is a real page that exists and got 10 sessions in March on its own.

**Suggestion for Ken:** One line change in the nginx config:

```nginx
# Current (wrong):
rewrite ^/romantic-cruise-for-two/?$ /charter/sunset-cruise-punta-cana/ permanent;

# Fix:
rewrite ^/romantic-cruise-for-two/?$ /charter/romantic-cruise-for-two/ permanent;
```

Reload nginx after the change.

---

## Problem 5 — Three pages share the same title tag

**Evidence:** `/privacy-policy/`, `/terms-and-conditions/`, and `/punta-cana-yacht-rentals/` all have the title `"Punta Cana Yacht Rentals & Private Boats Charter Since 2008"`. Google uses the title tag as one of its main signals for what a page is about. Three pages with the same title creates confusion.

**Suggestion for Ken:** Give `/punta-cana-yacht-rentals/` a unique, descriptive title (it's actually a real landing page, not a legal page). The legal pages are low priority — give them generic but distinct titles like "Privacy Policy | Punta Cana Yachts".

---

## Problem 6 — Ken's own testing is polluting the data

**Evidence:** 56 sessions in March came from `tagassistant.google.com` — that's the GTM tag debugger. Ken was testing the site, and those sessions are mixed in with real visitor data, making the numbers slightly misleading.

**Suggestion for Ken:** In GA4 → Admin → Data Streams → your web stream → Define internal traffic → add your office/home IP. This filters out your own visits automatically going forward.

---

## Suggested order of action

| # | Action | Who | Urgency |
|---|--------|-----|---------|
| 1 | GTM: confirm conversion tag fires on new site | Ken | This week |
| 2 | Check Google Ads: were campaigns running uninterrupted through March? | Ken / TJ | This week |
| 3 | Fix nginx redirect for `/romantic-cruise-for-two` | Ken | This week |
| 4 | Add canonical tags to all page templates | Ken | This week |
| 5 | Fix duplicate title on `/punta-cana-yacht-rentals/` | Ken | Soon |
| 6 | Set up internal traffic filter in GA4 | Ken | Soon |

---

## On backlinks — not yet

Backlinks are a long-term signal. Auditing them now is useful for understanding *why* the site doesn't rank organically, but it won't change anything quickly. The problems above are immediate and fixable, and two of them (broken conversion tracking, Google Ads disruption) are the most likely explanation for the sales dip TJ is worried about.

Ken already noted "our backlinks suck" — a Semrush or Ahrefs export would quantify that, but the prescription would be "start a content and outreach strategy," which is a longer conversation. Once the technical foundation above is clean, the backlink and organic ranking conversation makes more sense.
