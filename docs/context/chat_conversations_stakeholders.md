From TJ:
"Hey man. How you doing? Question for you. We did a redesign of our puntacanayachts.com site early March

We already had sales start to slip in February and March sales really slipped. Ken is doing the best he can but I wonder if you or someone you know is versed in SEO
5:05 PM

I know "of" some people. But honestly... have you used claude desktop (or cowork) lately?

it's abnormally good
6:04 PM

Also, people don't browse punta cana tours in google anymore, they just ask an AI assistant to find the stuff and book it

Therefore: the problem is AI, and the solution is also AI...
6:08 PM

Ken uses Claude too

And he updated the site using claude
6:10 PM

Ok, that's good news because otherwise he'd kind of be wasting his time

Well, Claude or the equivalent AIs (i.e., OpenAI Operator, or Gemini CLI) can surely do a SEO audit really quick

kit.com went through a bot attack this last week and I was looking into it yesterday until like 2AM. All results thanks to mi amigo Claudio
Edited6:12 PM

Oh wow. I assume Ken knows how to that
6:12 PM

A person who knows to do it him/herself is always best using the AI to do the tihng

But the one who does not know can get a long way anyway using AI. So just ask Claude to do it and see what it says. Ken's got access to everything anyway he can set up Claude connections to google analytics, google search console, etc. faster than any external consultant would
6:15 PM

Right. Ya he's working overtime

I think a lot has to do with change in search habits but of course we redesigned the site right around when this happened so Yeny is pissed at me that we did it in the middle of high season
6:17 PM

Well, I'm happy to take a look. To a certain extent I still know a bit. I'm just saying that I may not add a lot of value I'll use an AI too.

Have you thought about doing it yourself? 1) install Claude desktop, 2) ask Ken for the google search console and google analytics accesses, 3) download or connect whatever Claude requires, then ask away!

Or try Gemini CLI (from google) maybe works best for google stuff
6:28 PM

No way man. Data stresses me out haha
6:57 PM

😂

Would you be willing to troubleshoot with Ken? Maybe two Claude users are better than 1
7:07 PM

Yeny is going to kill me
7:11 PM

I just need this from Ken:
"Can you add my Google account email as a user to:

1. the GA4 property for puntacanayachts.com
2. the Google Search Console property for puntacanayachts.com

For GA4, Analyst access should be enough.
For Search Console, Full User is probably enough.

I do not need your login/password, just access granted to my Google account.

Also send me:

* the exact GA4 property name
* the exact Search Console property
* whether the March redesign changed URLs or templates
* who controls redirects / CMS / Tag Manager / Cloudflare
"

aberriz@gmail.com
7:38 PM

Ok let me ask him
7:39 PM

He's going to reach out. Thanks man. We're in a bit of a jam with this. We leave tomorrow to the DR. We were going to celebrate 15 years in business and now no one wants to celebrate ha
7:59 PM

😢

I'll try to save the party
8:00 PM

Haha thx
8:17 PM

"


From Ken:
"⁨Ken Harrington ©⁩No groups in common

Today

Hey, man. Indeed long time hehehe
8:06 PM

You started this chat with ⁨Kenie.01⁩

Cool, we are here. And you are in Spain. Man how time changes.

I'm going to get all that information to you. Give me a bit. I'm running back and forth between BBQ and typing
8:14 PM

Right! Went to DR to make a Dominican kid and took it to Madrid with me haha
8:15 PM

😂

I have Claude Code Pro. I use it command line only. But I run out of tokens every 5 hours. So I have to be frugal
8:16 PM

got it. My company pays for Cursor (a VS Code fork that has a bunch of models) I'll try to fly under the radar and use that a bit

aleberriz - Overview
Alejandro Berrizbeitia. aleberriz has 6 repositories available. Follow their code on GitHub.
github.com

Access to the repo could also help the SEO audit. It's on github? My user is https://github.com/aleberriz
8:17 PM

I wrote this to TJ. He thought I was joking. But you will understand.

I'm exaggerating a bit, but you'll get the idea. Tell him Ken is an idiot and built this website PuntaCanaYachts.com.  he fucked up everything.  Tell Alejandro and Claude to look over that website from a human perspective and a AI or Bot perspective, and tell you everything that Ken has done wrong. And ask for what improvements need or should be made.

No, I don't use GitHub. I keep everything local

GSC won't help you. I'll give you access but there is only data from a week or so. So it's useless

Ga4 will tell a different story. It has all the data.
8:18 PM

👍

Yeah I like my AI replies to be to the point no BS as well
8:18 PM

I control GTM

There is no CMS it's all custom PHP, mariadb backend

Templates and uri changed
8:19 PM

ok
8:19 PM

Redirects are via nginx
8:20 PM

If you can put the code on a read-only shared google drive with aberriz@gmail.com I can ask the tech audit from there. But the most important thing is the GA4 access
8:25 PM

8:27 PM

👍

You
If you can put the code on a read-only shared google drive with aberriz@gmail.com I can ask the tech audit from there. But the most important thing is the GA4 access

No promises, but I will see what I can do.

i have zero errors in my log file. IMHO, the code is pretty damn game.

good

As you know, GA4 gives you history, but it wont tell you what to do moving forward. For that, use curl or a bot and crawl the site.  I've used multiple bot and multiple AI agents. I really cant find anything wrong

This is redirects via nginx

# 301 Redirects: Old WordPress URLs → New /charter/ URLs
rewrite ^/private-yacht-isla-saona/?$ /charter/private-yacht-isla-saona/ permanent;
rewrite ^/saona-island-catamaran/?$ /charter/saona-island-catamaran/ permanent;
rewrite ^/romantic-cruise-for-two/?$ /charter/romantic-cruise-for-two/ permanent;
rewrite ^/punta-cana-wedding-boat/?$ /charter/punta-cana-wedding-boat/ permanent;
rewrite ^/picaflor-mini-yacht/?$ /charter/picaflor-mini-yacht/ permanent;
rewrite ^/media-luna/?$ /charter/media-luna/ permanent;
rewrite ^/margaritas-party-boat/?$ /charter/margaritas-party-boat/ permanent;
rewrite ^/malibu-party-boat/?$ /charter/malibu-party-boat/ permanent;
rewrite ^/fishing-boat-charter/?$ /charter/fishing-boat-charter/ permanent;
rewrite ^/catamaran-st-mary/?$ /charter/catamaran-st-mary/ permanent;
rewrite ^/catamaran-la-palma/?$ /charter/catamaran-la-palma/ permanent;
rewrite ^/caribbean-dream-sail/?$ /charter/caribbean-dream-sail/ permanent;
rewrite ^/big-baby-catamaran/?$ /charter/big-baby-catamaran/ permanent;
rewrite ^/baby-catamaran-ii/?$ /charter/baby-catamaran-ii/ permanent;
rewrite ^/baby-catamaran/?$ /charter/baby-catamaran/ permanent;
rewrite ^/wedding-boat/?$ /charter/punta-cana-wedding-boat/ permanent;

# Categories
rewrite ^/charter/yacht-charters/?$ /charters/ permanent;
rewrite ^/charter/half-day/?$ /charters/half-day/ permanent;
rewrite ^/charter/full-day/?$ /charters/full-day/ permanent;
rewrite ^/charter/powerboats/?$ /charters/powerboats/ permanent;
rewrite ^/charter/sailboats/?$ /charters/sailboats/ permanent;

One mistake above:
rewrite ^/romantic-cruise-for-two/?$ /charter/sunset-cruise-punta-cana/ permanent;



Ok. Well, I really can't say much about the code itself, it'd be just whatever Claude Opus has to say about it and only from a SEO perspective. I guess the sitemap.xml and any crawl reports from SEMrush or whatever if any would be the most useful. A CSV with the backlinks profile also would be ideal. I'll start from all this and will get back with what I find
8:34 PM

https://puntacanayachts.com/sitemap.xml
8:34 PM

👍

I use Opus 4.6
8:35 PM

right, the latest
8:35 PM

And I've done all you said. But you're prompts will be different than mine which is good

I also dont have access to SEMrush

But our backlinks suck. that is pretty simple
8:35 PM

Ok

I wonder if Gemini has an advantage here since it's from Google. GA has an MCP I'll see if I can get Gemini CLI to do the audit as well
8:36 PM

I use Screaming Frog to crawl my site. But realistically, I can do all this stuff on my own with with Claudes help. I can't find anything.

You
Ok

I wonder if Gemini has an advantage here since it's from Google. GA has an MCP I'll see if I can get Gemini CLI to do the audit as well

I've used the free Gemini, to no avail
8:37 PM

I can see there will be no easy wins here, no low hanging fruit hehe. It was to be expected.
8:38 PM

I'll give you a human insight, and I think I'm spot on, and if you feed this to AI, you'll probably get the same response.
8:38 PM

👀

Good is not official shit! They are evil, and 98% useless

I would say 98% of our competitions is fake

They dont have a half million reviews

They dont even work here

I can show you 100 examples of this. And showing boats that dont exist either
8:39 PM

But somehow hacked the SERP
8:39 PM

My theory, Google use to be King.  And google would check all this stuff. You couldnt have duplicate text, you couldnt fake reviews, etc. But the game has now changed. The game is about money not the truth

Google will allow someone to fake review and fake boats if they are paying for placement.

And, AEO dont check anything

So If I fill my site with a million reviews, and 45 boats, there is no checks no verification, and I will rank high!

I have seen this in yachts, tours, and transportation

It's prolific, Not just with Google, I see it everywhere

https://rentalyachtspuntacana.com/
8:43 PM

So it has nothing to do with the redesign
8:44 PM

A quick scan of their site tells me zero boats are in Punta Cana

And that site is #1

You
So it has nothing to do with the redesign

This is my theory

All I can do is check my code, make sure I have all meta tags, OG tags, twitter tags, and JSON-LD correct. And that mine is better than the competition.

At least that is how my brain works

I now think Google, AEO and other rank on quantity not quality.  45 boats it better than 6.  400,000 reviews is better than 500
8:45 PM

That's what's under your direct control, yes. If it's none of that, then a sudden sharp drop indicates something external. Such as algorithmic change like you mention, or competitors.
8:46 PM

Thats what would be good to find out. If possible

Poke around and let me know
8:47 PM

🤞

And thanks!
8:47 PM

👍

This is all my GSC data, 12 days worth. Not even worth looking at
8:50 PM

Add an Emoji, Sticker, or GIF

"