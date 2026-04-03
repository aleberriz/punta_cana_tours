as response to "Ken — pulled the paid search landing page data for March. Good news first: the ads are mostly pointing to the right new URLs, so that wasn't the main issue. Here's what the data actually shows.

The conversion tag only fires on one page. /charter/yacht-charters converted at 33% — great. But /charter/private-yacht-isla-saona got 187 paid sessions and zero key events. /charters/ got 149 sessions, zero. Every page except yacht-charters: zero. The GTM trigger is probably looking for something (a button class, form ID, element name) that exists on the yacht-charters page but not the others. Can you check GTM Preview on /charter/private-yacht-isla-saona/ and see if the conversion tag fires when someone submits the form?

129 paid sessions are going to /punta-cana-yacht-rentals/. That's the content page you just built — no booking form, no direct conversion path. Whichever ad is pointing there should be redirected to a product page.

3 paid sessions are hitting /charter/romantic-cruise-for-two/ — that page returns 404. Small number but it's a dead end. Pause or update that ad.

The fix for the tag issue is probably one GTM change that makes the conversion trigger work site-wide rather than page-specific. Once that's done the numbers should look very different."

This page does have a form https://puntacanayachts.com/charter/private-yacht-isla-saona/  When I fill out the form, the tag triggers.
2:14 AM

This is Google Ads.  As far as I know, this is all the ads

There are only 5. These are the landing pages in the same order as the ads:
https://puntacanayachts.com/charter/private-yacht-isla-saona/
https://puntacanayachts.com/punta-cana-yacht-rentals/
https://puntacanayachts.com/punta-cana-yacht-rentals/
https://puntacanayachts.com/punta-cana-yacht-rentals/
https://puntacanayachts.com/charter/private-yacht-isla-saona/
2:24 AM

Now let me explain how the conversion tag fires. The form on all the pages is the same. If you fill out a form, it POSTs to handle-inquiry.php which runs bot checks (CSRF, honeypot, time trap). If all  pass, you are redirected to the thank-you page and it checks for a session flag. It then Pushes charter_inquiry_submitted event to dataLayer and GTM picks up the charter_inquiry_submitted event and fires the "Google Ads - Charter Inquiry" conversion tag
2:31 AM

👀

If the POST fails the bot checks, you are still redirected to the thank-you page without the session.
2:32 AM

What I dont understand is what a paid session is? Above are my landing pages. The you sent me says no one is filling out a form on any of the landing pages. Instead they are clicking away, browsing the rest of the site, and filling out a form on another page. that sounds odd to me. But whatever.
2:36 AM

👀

Punta Cana Yacht Rentals — Private Charters Since 2008
Rent a private yacht in Punta Cana with captain, crew, food, and snorkeling included. 15+ yachts and catamarans for any group size. 800+ five-star Google rev...
puntacanayachts.com

So If I land on on this page:https://puntacanayachts.com/punta-cana-yacht-rentals/

And then click away to this page:https://puntacanayachts.com/charters/

Then go to this page and fill out a form:https://puntacanayachts.com/charter/picaflor-mini-yacht/

Is that 3 sessions or 1?

Private Yacht Charters in Punta Cana | Boat Charter Since '08
Punta Cana Yacht Rentals, Locally Owned. We've been Renting Private Boats and Luxury Yachts Since 2008. Helping Make Your Vacation FUN! Get A FREE QUOTE TODAY!
puntacanayachts.com

But something seems wrong. According to that chart, there are been 20 sessions on this page:https://puntacanayachts.com/

There is no form on that page.

Another oddity. that report shows all uri's without a trailing backslash /  All of my uri's have a trailing backslash.

as noted here: https://puntacanayachts.com/sitemap.xml
2:41 AM

I am probably creating more questions that answers 🤦🏼  Also make sure you are not using any data prior to mid-March.
2:48 AM

👍

Courtesy of Claude:

Zero key events across the board — Every landing page shows 0 key events (conversions). The total shows 4, but none are attributed to these pages. This likely means conversions are being attributed to /thank-you/ (the page where the event actually fires) rather than the originating landing page. You may want to check if GA4 is attributing the charter_inquiry_submitted event to the thank-you page instead of the page where the user started.

(not set) has 13 sessions — These are sessions where GA4 couldn't determine the landing page, often from session timeouts or direct hits where the page wasn't tracked properly.

If you're trying to measure which charter pages drive conversions, the 0 key events column suggests your GA4 key event setup might be attributing conversions to /thank-you/ rather than the original landing page. You could verify this by checking if /thank-you/ shows up with 4 key events in this same report. If so, you may want to look into using GA4's "session-scoped" attribution so the conversion credit goes back to the landing page.
2:56 AM

Google Ads tracks the full click-to-conversion path natively — it knows which ad, keyword, and landing page URL the user clicked through to, and ties the conversion back to that click via the gclid cookie (which your Conversion Linker tag preserves).                               
  
So in Google Ads you can see something like: Keyword X → Ad Y → landed on /charter/private-yacht-isla-saona/ → converted — all in one report.                               
  
That's fundamentally different from GA4, which attributes the key event to the page where the dataLayer.push       actually fires (/thank-you/). GA4 can do session-scoped attribution, but it takes extra configuration. Google Ads does it out of the box because that's the whole point — measuring ROI per ad/keyword/landing page.

Given that /charter/private-yacht-isla-saona/ is pulling 32% of all your sessions, it'd be worth checking your Google Ads campaign report to see if that page is also your top converter, or just a traffic magnet that isn't closing.

