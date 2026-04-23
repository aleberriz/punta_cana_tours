# March 2026 conversion collapse — data analysis
_Date: April 3, 2026_
_Data sources: GA4 Traffic Acquisition exports (Jan 2025 – Apr 3, 2026), separated by year_

---

## Summary finding

Key events (form-submission conversions) collapsed to near-zero in March 2026 across **all traffic channels simultaneously**. Sessions were not disrupted — organic traffic actually increased slightly from February to March. The collapse is instantaneous and coincides with the site redesign launch (~March 3, 2026). This points to a conversion mechanism or tracking issue introduced by the redesign, not a traffic or ranking problem.

---

## Year-over-year data

### Paid Search

| Month | 2025 Sessions | 2025 Key Events | 2025 Rate | 2026 Sessions | 2026 Key Events | 2026 Rate |
|-------|--------------|-----------------|-----------|--------------|-----------------|-----------|
| Jan | 1,290 | 115 | 8.9% | 1,082 | 133 | **12.3%** |
| Feb | 863 | 82 | 9.5% | 776 | 71 | 9.2% |
| Mar | 915 | 93 | 10.2% | 545 | **4** | **0.7%** |

### Organic Search

| Month | 2025 Sessions | 2025 Key Events | 2025 Rate | 2026 Sessions | 2026 Key Events | 2026 Rate |
|-------|--------------|-----------------|-----------|--------------|-----------------|-----------|
| Jan | 359 | 32 | 8.9% | 255 | 16 | 6.3% |
| Feb | 314 | 25 | 8.0% | 209 | 19 | 9.1% |
| Mar | 441 | 29 | 6.6% | **241** | **0** | **0%** |

### All channels — March 2026 vs February 2026

| Channel | Feb 2026 Key Events | Mar 2026 Key Events | Change |
|---------|--------------------|--------------------|--------|
| Paid Search | 71 | 4 | −94% |
| Organic Search | 19 | 0 | −100% |
| Referral | 12 | 0 | −100% |
| Direct | 9 | 5 | −44% |
| **Total** | **111** | **9** | **−92%** |

---

## Key observations

### 1. Business was at peak performance immediately before the redesign

January 2026 Paid Search posted a **12.3% key event rate** — the highest of any month in the entire 15-month dataset. February 2026 organic search hit 9.1%, also historically strong. There was no gradual decline into March. The drop is instantaneous.

### 2. Sessions did not drop — only conversions did

March 2026 organic sessions: 241 (up from 209 in February).
March 2026 paid sessions: 545 (moderate seasonal decline from 776 in February — normal).

People were finding the site and visiting. They stopped converting. This eliminates a ranking drop or traffic loss as the primary cause for March.

### 3. The collapse affects every channel

Organic, referral, paid, and direct all dropped simultaneously. A channel-specific explanation (e.g., "Google Ads were paused" or "organic rankings dropped") cannot account for all channels failing at once. The common factor is the new site's conversion mechanism, which launched on ~March 3, 2026.

### 4. Form submission — live test (April 3, 2026)

The form on `/charter/private-yacht-isla-saona/` was tested via automated browser (Chromium):
- Form submitted with realistic test data
- No client-side validation errors
- Redirected to `/thank-you/` with personalized greeting ("Thank You, Test!")
- Personalized greeting **confirms the PHP session flag was set**, meaning the bot checks (CSRF, honeypot, time trap) **passed**
- GA4 real-time could not be verified (requires user auth)

**Conclusion:** The form itself works correctly in a desktop browser environment. The mechanism is not fundamentally broken.

---

## Hypotheses (ranked by evidence)

| Rank | Hypothesis | Evidence for | Evidence against |
|------|-----------|--------------|-----------------|
| 1 | **GA4/GTM event tracking was misconfigured on the new site at launch** | All channels fail simultaneously; form tested working; Ken confirmed Ads were "setup wrong" at launch | Ken says tag fires when he tests it |
| 2 | **Bot check (time trap) rejects real mobile users** | Time trap present; mobile users on slow connections may trigger it; silent failure | Automated browser test passed; personalized greeting confirms session set |
| 3 | **Organic ranking drop reduced high-intent traffic** | Organic sessions slightly lower in 2026 vs 2025 Jan-Feb | Organic sessions in March 2026 (241) are HIGHER than February (209); rate went from 9.1% to 0% |

---

## Full-year 2025 channel breakdown

| Channel | 2025 Sessions | 2025 Key Events | Share of conversions |
|---------|--------------|-----------------|---------------------|
| Paid Search | ~10,735 | ~813 | **60%** |
| Direct | ~8,939 | ~180 | 13% |
| Referral | ~2,775 | ~178 | 13% |
| Organic Search | ~3,204 | ~189 | 14% |

**Implication:** The business depends primarily on paid search for conversions, not organic. Paid search generated 4× more sessions than organic and 60% of all conversions in 2025.

---

## November 2025 anomaly

November 2025 was reportedly the strongest sales month (+60% vs November 2024). GA4 data shows:

| Channel | Nov 2025 Sessions | Nov 2025 Key Events |
|---------|-------------------|---------------------|
| Paid Search | **326** (lowest month) | 35 |
| Direct | **1,100** (highest month of year) | 15 |
| Referral | 133 | **17** (12.8% rate — highest rate of any channel/month) |
| Organic | 158 | 9 |

Paid ads appear to have been largely paused in November. The "best sales month" was carried by direct bookings and high-intent referral traffic, likely from TripAdvisor/Viator (evidenced by the anomalously high referral key event rate). TJ's "we were an organic business" belief does not match the data — organic drove only 14% of conversions annually, and the November anomaly was referral/direct, not organic.

---

## Open questions (require Google Ads access)

1. Does Google Ads show any conversions via gclid in March 2026? If yes: GA4 tracking is broken, not the conversion flow. If no: form is genuinely not converting for real users.
2. Which specific campaigns were running in March and what were their landing pages?
3. What search terms are triggering the Saona campaign?

---

## Next steps

- [ ] Google Ads access → compare gclid conversions vs GA4 key events for March
- [ ] Ken: check server-side logs for `/submit-inquiry` POST requests in March — how many received, how many passed bot checks
- [ ] Ken: SEMrush free trial → historical keyword rankings to validate/rule out TJ's ranking drop theory
- [ ] Enhanced site crawl → identify orphaned pages, internal link gaps, technical issues (see `crawl_report_2026-04-03.md` when generated)
