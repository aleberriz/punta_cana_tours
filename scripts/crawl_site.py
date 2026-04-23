"""
Live site crawler for PuntaCanaYachts — full technical SEO audit.

Crawls the sitemap + follows internal links to find orphaned pages.
For each URL, collects:
  - HTTP status, final URL, redirect chain
  - Canonical tag
  - Title (length, content)
  - H1 count and content, H2/H3 counts
  - Meta description (length, content)
  - Word count (visible text)
  - Form presence
  - JSON-LD schema types
  - Image count, images missing alt text
  - Internal links (outgoing)
  - Open Graph tags
  - Viewport meta tag

Produces:
  - Console summary
  - docs/analysis/crawl_report_YYYY-MM-DD.md

Usage:
    poetry run python scripts/crawl_site.py
"""

import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SITE = "https://puntacanayachts.com"
SITEMAP = f"{SITE}/sitemap.xml"
REQUEST_DELAY = 0.6

EXPECTED_REDIRECTS = {
    "/private-yacht-isla-saona":  "/charter/private-yacht-isla-saona/",
    "/saona-island-catamaran":    "/charter/saona-island-catamaran/",
    "/romantic-cruise-for-two":   "/charter/sunset-cruise-punta-cana/",
    "/punta-cana-wedding-boat":   "/charter/punta-cana-wedding-boat/",
    "/picaflor-mini-yacht":       "/charter/picaflor-mini-yacht/",
    "/media-luna":                "/charter/media-luna/",
    "/margaritas-party-boat":     "/charter/margaritas-party-boat/",
    "/malibu-party-boat":         "/charter/malibu-party-boat/",
    "/fishing-boat-charter":      "/charter/fishing-boat-charter/",
    "/catamaran-st-mary":         "/charter/catamaran-st-mary/",
    "/catamaran-la-palma":        "/charter/catamaran-la-palma/",
    "/caribbean-dream-sail":      "/charter/caribbean-dream-sail/",
    "/big-baby-catamaran":        "/charter/big-baby-catamaran/",
    "/baby-catamaran-ii":         "/charter/baby-catamaran-ii/",
    "/baby-catamaran":            "/charter/baby-catamaran/",
    "/wedding-boat":              "/charter/punta-cana-wedding-boat/",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; PuntaCanaToursAuditBot/1.0; +audit)"
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str, follow_redirects: bool = True) -> requests.Response | None:
    try:
        return SESSION.get(url, timeout=12, allow_redirects=follow_redirects)
    except requests.RequestException as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return None


def is_internal(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == "" or parsed.netloc.replace("www.", "") == urlparse(SITE).netloc.replace("www.", "")


def normalise(url: str, base: str = SITE) -> str:
    full = urljoin(base, url)
    p = urlparse(full)
    # strip fragment and query for deduplication
    return p._replace(fragment="", query="").geturl()


def normalise_for_compare(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(normalise(url))
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(path=path, fragment="", query="").geturl()


def visible_word_count(soup: BeautifulSoup) -> int:
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return len(text.split())


def extract_schema_types(data) -> list[str]:
    types: list[str] = []
    if isinstance(data, list):
        for item in data:
            types.extend(extract_schema_types(item))
    elif isinstance(data, dict):
        raw_type = data.get("@type")
        if isinstance(raw_type, list):
            types.extend(str(item) for item in raw_type if item)
        elif raw_type:
            types.append(str(raw_type))
        if "@graph" in data:
            types.extend(extract_schema_types(data["@graph"]))
        for value in data.values():
            if isinstance(value, (dict, list)):
                types.extend(extract_schema_types(value))
    return types


def parse_sitemap(url: str) -> list[str]:
    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  Cannot fetch sitemap: {url}", file=sys.stderr)
        return []
    soup = BeautifulSoup(r.text, "xml")
    locs = [t.text.strip() for t in soup.find_all("loc")]
    if soup.find("sitemapindex"):
        nested: list[str] = []
        for loc in locs:
            nested.extend(parse_sitemap(loc))
            time.sleep(REQUEST_DELAY)
        return nested
    return locs


# ── Per-URL audit ─────────────────────────────────────────────────────────────

def audit_url(url: str) -> dict:
    r = fetch(url)
    if r is None:
        return _empty(url, "FETCH_ERROR")

    final_url = r.url
    status = r.status_code

    if status != 200:
        return _empty(url, status, final_url=final_url)

    soup = BeautifulSoup(r.text, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Canonical
    canon_tag = soup.find("link", rel="canonical")
    canonical = canon_tag["href"].strip() if canon_tag and canon_tag.get("href") else None

    # Indexability / robots
    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots = robots_tag.get("content", "").strip() if robots_tag else None
    x_robots = r.headers.get("X-Robots-Tag", "").strip() or None
    robots_blob = " ".join(part for part in (robots, x_robots) if part).lower()
    noindex = "noindex" in robots_blob

    # H1 / H2 / H3
    h1_tags = soup.find_all("h1")
    h1_texts = [t.get_text(strip=True) for t in h1_tags]
    h2_count = len(soup.find_all("h2"))
    h3_count = len(soup.find_all("h3"))

    # Meta description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    # Open Graph
    og = {}
    for prop in ("og:title", "og:description", "og:image", "og:type"):
        tag = soup.find("meta", property=prop)
        og[prop] = tag["content"].strip() if tag and tag.get("content") else None

    # Viewport
    vp_tag = soup.find("meta", attrs={"name": "viewport"})
    has_viewport = vp_tag is not None

    # Images
    imgs = soup.find_all("img")
    imgs_missing_alt = [
        img.get("src", "")[:80]
        for img in imgs
        if not img.get("alt") and img.get("src", "").startswith("http")
    ]

    # Forms
    forms = soup.find_all("form")
    form_actions = [f.get("action", "") for f in forms]

    # JSON-LD schema types
    schema_types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schema_types += extract_schema_types(data)
        except (json.JSONDecodeError, TypeError):
            pass

    # Internal links
    internal_links: list[str] = []
    external_links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        norm = normalise(href, base=final_url)
        if is_internal(norm):
            if norm not in internal_links:
                internal_links.append(norm)
        elif urlparse(norm).scheme in ("http", "https") and norm not in external_links:
            external_links.append(norm)

    # Word count (approximate — run after all decompose operations)
    word_count = visible_word_count(BeautifulSoup(r.text, "html.parser"))

    return {
        "url": url,
        "final_url": final_url if final_url != url else None,
        "status": status,
        "title": title,
        "title_len": len(title) if title else 0,
        "canonical": canonical,
        "canonical_matches": (
            normalise_for_compare(canonical) in {
                normalise_for_compare(final_url),
                normalise_for_compare(url),
            }
            if canonical
            else False
        ),
        "robots": robots,
        "x_robots_tag": x_robots,
        "noindex": noindex,
        "h1_count": len(h1_tags),
        "h1_texts": h1_texts,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "meta_desc": meta_desc,
        "meta_desc_len": len(meta_desc) if meta_desc else 0,
        "og": og,
        "has_viewport": has_viewport,
        "img_count": len(imgs),
        "imgs_missing_alt": imgs_missing_alt,
        "forms": form_actions,
        "schema_types": [t for t in schema_types if t],
        "internal_links": internal_links,
        "external_links": external_links,
        "word_count": word_count,
    }


def _empty(url: str, status, final_url: str | None = None) -> dict:
    return {
        "url": url, "final_url": final_url, "status": status,
        "title": None, "title_len": 0, "canonical": None, "canonical_matches": False,
        "robots": None, "x_robots_tag": None, "noindex": False,
        "h1_count": 0, "h1_texts": [], "h2_count": 0, "h3_count": 0,
        "meta_desc": None, "meta_desc_len": 0, "og": {},
        "has_viewport": False, "img_count": 0, "imgs_missing_alt": [],
        "forms": [], "schema_types": [], "internal_links": [], "external_links": [],
        "word_count": 0,
    }


# ── Redirect audit ────────────────────────────────────────────────────────────

def check_redirect(old_path: str, expected_path: str) -> dict:
    url = SITE + old_path
    r = fetch(url, follow_redirects=False)
    if r is None:
        return {"old": old_path, "expected": expected_path,
                "actual_status": "ERROR", "actual_dest": None, "ok": False}
    dest = r.headers.get("Location", "")
    dest_path = urlparse(dest).path if dest else None
    expected_norm = expected_path.rstrip("/") + "/"
    dest_norm = (dest_path or "").rstrip("/") + "/"
    ok = dest_norm == expected_norm and r.status_code == 301
    return {"old": old_path, "expected": expected_path,
            "actual_status": r.status_code, "actual_dest": dest_path, "ok": ok}


# ── Report helpers ────────────────────────────────────────────────────────────

def section(title: str):
    print(f"\n{'='*70}\n  {title}\n{'='*70}")


def flag(condition: bool, msg: str) -> str:
    return f"{'⚠ ' if condition else ''}{msg}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    lines: list[str] = []

    def out(s: str = ""):
        print(s)
        lines.append(s)

    today = date.today()
    out(f"# PuntaCanaYachts — Technical SEO crawl report")
    out(f"_Date: {today}_\n")

    # ── 1. Redirect audit ─────────────────────────────────────────────────────
    section("1 / REDIRECT AUDIT")
    out("## 1. Redirect audit (old WordPress → new /charter/ paths)\n")
    out("| Old path | Expected | Status | Actual dest | OK |")
    out("|----------|----------|--------|-------------|-----|")
    redirect_issues: list[str] = []
    for old, expected in EXPECTED_REDIRECTS.items():
        res = check_redirect(old, expected)
        ok_str = "✓" if res["ok"] else "✗"
        actual = res["actual_dest"] or "(none)"
        out(f"| `{old}` | `{expected}` | {res['actual_status']} | `{actual}` | {ok_str} |")
        if not res["ok"]:
            redirect_issues.append(f"- `{old}` → got `{actual}` ({res['actual_status']}), expected `{expected}`")
        time.sleep(REQUEST_DELAY)

    if redirect_issues:
        out("\n### Redirect issues\n")
        for i in redirect_issues:
            out(i)
    else:
        out("\n_All redirects correct._")

    # ── 2. Crawl sitemap + follow internal links ───────────────────────────────
    section("2 / SITEMAP + INTERNAL LINK CRAWL")
    print(f"  Fetching sitemap: {SITEMAP}")
    sitemap_urls = set(parse_sitemap(SITEMAP))
    out(f"\n_Sitemap contains **{len(sitemap_urls)} URLs**._\n")

    # Crawl: sitemap first, then discover via internal links
    to_crawl: list[str] = list(sitemap_urls)
    crawled: dict[str, dict] = {}
    inlink_count: dict[str, int] = defaultdict(int)

    i = 0
    while i < len(to_crawl):
        url = to_crawl[i]
        i += 1
        # Only crawl internal HTML pages
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if any(url.endswith(ext) for ext in (".xml", ".jpg", ".png", ".pdf", ".webp")):
            continue
        if url in crawled:
            continue

        print(f"  [{i}/{len(to_crawl)}] {url}")
        data = audit_url(url)
        crawled[url] = data
        time.sleep(REQUEST_DELAY)

        # Enqueue newly discovered internal links
        for link in data.get("internal_links", []):
            clean = link.rstrip("/") + "/"
            clean_base = urlparse(clean)._replace(fragment="", query="").geturl()
            inlink_count[clean_base] += 1
            if clean_base not in crawled and clean_base not in to_crawl:
                if is_internal(clean_base) and urlparse(clean_base).scheme in ("http", "https"):
                    to_crawl.append(clean_base)

    pages = list(crawled.values())
    out(f"_Crawled **{len(pages)} pages** total ({len(sitemap_urls)} from sitemap + "
        f"{len(pages) - len(sitemap_urls)} discovered via internal links)._\n")

    # ── 3. Summary table ──────────────────────────────────────────────────────
    section("3 / PAGE SUMMARY")
    out("## 2. Page summary\n")
    out("| Page | Status | Title len | H1 | H2s | Words | Form | Schema |")
    out("|------|--------|-----------|-----|-----|-------|------|--------|")

    for p in sorted(pages, key=lambda x: x["url"]):
        path = urlparse(p["url"]).path or "/"
        status = str(p["status"])
        t_len = f"{p['title_len']}ch" if p["title_len"] else "—"
        h1 = str(p["h1_count"]) if p["h1_count"] else "—"
        h2 = str(p["h2_count"]) if p["h2_count"] else "—"
        words = str(p["word_count"]) if p["word_count"] else "—"
        has_form = "✓" if p["forms"] else "—"
        schema = ", ".join(set(p["schema_types"])) if p["schema_types"] else "—"
        out(f"| `{path}` | {status} | {t_len} | {h1} | {h2} | {words} | {has_form} | {schema} |")

    # ── 4. Issues ─────────────────────────────────────────────────────────────
    section("4 / ISSUES")
    out("\n## 3. Issues\n")

    # 4a. Non-200 pages
    non_200 = [p for p in pages if p["status"] != 200]
    out(f"### Non-200 pages ({len(non_200)})\n")
    if non_200:
        for p in non_200:
            out(f"- `{urlparse(p['url']).path}` → status {p['status']}"
                + (f" (→ `{p['final_url']}`)" if p["final_url"] else ""))
    else:
        out("_None._")

    # 4b. Missing canonical
    no_canon = [p for p in pages if p["status"] == 200 and not p["canonical"]]
    out(f"\n### Missing canonical tag ({len(no_canon)})\n")
    if no_canon:
        for p in no_canon:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")

    # 4c. Canonical mismatch
    canon_mismatch = [p for p in pages
                      if p["status"] == 200 and p["canonical"]
                      and not p["canonical_matches"]]
    out(f"\n### Canonical mismatch (canonical ≠ page URL) ({len(canon_mismatch)})\n")
    if canon_mismatch:
        for p in canon_mismatch:
            out(f"- `{urlparse(p['url']).path}` → canonical: `{p['canonical']}`")
    else:
        out("_None._")

    # 4c2. Noindex pages
    noindex_pages = [p for p in pages if p["status"] == 200 and p["noindex"]]
    out(f"\n### Pages marked noindex ({len(noindex_pages)})\n")
    if noindex_pages:
        for p in noindex_pages:
            robots_txt = p["robots"] or p["x_robots_tag"] or "(unspecified)"
            out(f"- `{urlparse(p['url']).path}` — `{robots_txt}`")
    else:
        out("_None._")

    # 4d. Missing / duplicate titles
    title_map: dict[str, list[str]] = defaultdict(list)
    for p in pages:
        if p["status"] == 200 and p["title"]:
            title_map[p["title"]].append(urlparse(p["url"]).path)
    no_title = [p for p in pages if p["status"] == 200 and not p["title"]]
    dup_titles = {t: paths for t, paths in title_map.items() if len(paths) > 1}

    out(f"\n### Missing title tag ({len(no_title)})\n")
    if no_title:
        for p in no_title:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")

    out(f"\n### Duplicate title tags ({len(dup_titles)} titles shared by multiple pages)\n")
    if dup_titles:
        for title, paths in dup_titles.items():
            out(f"- **\"{title[:80]}\"** → {', '.join(f'`{p}`' for p in paths)}")
    else:
        out("_None._")

    # 4e. Title length issues
    short_titles = [p for p in pages if p["status"] == 200 and 0 < p["title_len"] < 30]
    long_titles = [p for p in pages if p["status"] == 200 and p["title_len"] > 65]
    out(f"\n### Title too short (<30 chars): {len(short_titles)}\n")
    for p in short_titles:
        out(f"- `{urlparse(p['url']).path}` — \"{p['title']}\" ({p['title_len']} chars)")
    out(f"\n### Title too long (>65 chars): {len(long_titles)}\n")
    for p in long_titles:
        out(f"- `{urlparse(p['url']).path}` — \"{p['title'][:80]}\" ({p['title_len']} chars)")

    # 4f. H1 issues
    no_h1 = [p for p in pages if p["status"] == 200 and p["h1_count"] == 0]
    multi_h1 = [p for p in pages if p["status"] == 200 and p["h1_count"] > 1]
    out(f"\n### Missing H1 ({len(no_h1)})\n")
    if no_h1:
        for p in no_h1:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")
    out(f"\n### Multiple H1 tags ({len(multi_h1)})\n")
    if multi_h1:
        for p in multi_h1:
            out(f"- `{urlparse(p['url']).path}` — {p['h1_count']} H1s: "
                + " | ".join(f'\"{t[:50]}\"' for t in p["h1_texts"]))
    else:
        out("_None._")

    # 4g. Meta description issues
    no_meta = [p for p in pages if p["status"] == 200 and not p["meta_desc"]]
    short_meta = [p for p in pages if p["status"] == 200 and 0 < p["meta_desc_len"] < 70]
    long_meta = [p for p in pages if p["status"] == 200 and p["meta_desc_len"] > 160]
    out(f"\n### Missing meta description ({len(no_meta)})\n")
    if no_meta:
        for p in no_meta:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")
    if short_meta:
        out(f"\n### Meta description too short (<70 chars): {len(short_meta)}\n")
        for p in short_meta:
            out(f"- `{urlparse(p['url']).path}` — \"{p['meta_desc']}\" ({p['meta_desc_len']} chars)")
    if long_meta:
        out(f"\n### Meta description too long (>160 chars): {len(long_meta)}\n")
        for p in long_meta:
            out(f"- `{urlparse(p['url']).path}` — ({p['meta_desc_len']} chars)")

    # 4h. Images missing alt text
    alt_issues = [(p, p["imgs_missing_alt"]) for p in pages
                  if p["status"] == 200 and p["imgs_missing_alt"]]
    out(f"\n### Images missing alt text ({sum(len(x[1]) for x in alt_issues)} images across "
        f"{len(alt_issues)} pages)\n")
    if alt_issues:
        for p, imgs in alt_issues:
            out(f"- `{urlparse(p['url']).path}` — {len(imgs)} image(s) without alt")
    else:
        out("_None._")

    # 4i. Pages without a form (product/charter pages expected to have one)
    charter_no_form = [p for p in pages
                       if p["status"] == 200
                       and "/charter/" in p["url"]
                       and not p["forms"]]
    out(f"\n### Charter pages without a form ({len(charter_no_form)})\n")
    if charter_no_form:
        for p in charter_no_form:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")

    # 4j. Pages in sitemap but with no inbound internal links (orphaned)
    orphaned = []
    for p in pages:
        url_norm = p["url"].rstrip("/") + "/"
        if p["url"] in sitemap_urls and inlink_count.get(url_norm, 0) == 0:
            if urlparse(p["url"]).path not in ("/", ""):
                orphaned.append(p)
    out(f"\n### Orphaned pages (in sitemap, 0 inbound internal links) ({len(orphaned)})\n")
    if orphaned:
        for p in orphaned:
            out(f"- `{urlparse(p['url']).path}` — \"{(p['title'] or '')[:60]}\"")
    else:
        out("_None._")

    # 4k. Pages missing schema
    no_schema = [p for p in pages
                 if p["status"] == 200
                 and "/charter/" in p["url"]
                 and not p["schema_types"]]
    out(f"\n### Charter pages without JSON-LD schema ({len(no_schema)})\n")
    if no_schema:
        for p in no_schema:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")

    # 4l. Open Graph coverage
    no_og = [p for p in pages
             if p["status"] == 200 and not p["og"].get("og:image")]
    out(f"\n### Pages missing og:image ({len(no_og)})\n")
    if no_og:
        for p in no_og:
            out(f"- `{urlparse(p['url']).path}`")
    else:
        out("_None._")

    # ── 5. Internal link heatmap ──────────────────────────────────────────────
    section("5 / INTERNAL LINK HEATMAP")
    out("\n## 4. Internal links — inbound count per page\n")
    out("| Page | Inbound internal links |")
    out("|------|------------------------|")

    ranked = sorted(
        [(url, cnt) for url, cnt in inlink_count.items() if is_internal(url)],
        key=lambda x: x[1], reverse=True
    )
    for url, cnt in ranked[:40]:
        path = urlparse(url).path or "/"
        bar = "█" * min(cnt, 30)
        out(f"| `{path}` | {cnt} {bar} |")

    # ── 5b. External links ────────────────────────────────────────────────────
    ext_domains = Counter()
    for p in pages:
        for link in p.get("external_links", []):
            host = urlparse(link).netloc.replace("www.", "")
            if host:
                ext_domains[host] += 1

    section("5B / EXTERNAL LINKS")
    out("\n## 4b. External link domains referenced on-site\n")
    out("| Domain | Links found |")
    out("|--------|-------------|")
    if ext_domains:
        for domain, cnt in ext_domains.most_common(30):
            out(f"| `{domain}` | {cnt} |")
    else:
        out("| _None_ | 0 |")

    # ── 6. Word count overview ────────────────────────────────────────────────
    section("6 / WORD COUNT")
    out("\n## 5. Word count by page\n")
    out("| Page | Words | Assessment |")
    out("|------|-------|------------|")
    for p in sorted(pages, key=lambda x: x["word_count"], reverse=True):
        if p["status"] != 200:
            continue
        path = urlparse(p["url"]).path or "/"
        wc = p["word_count"]
        if wc > 800:
            note = "✓ good"
        elif wc > 300:
            note = "acceptable"
        else:
            note = "⚠ thin"
        out(f"| `{path}` | {wc} | {note} |")

    # ── Write report ──────────────────────────────────────────────────────────
    out_dir = Path(__file__).parent.parent / "docs" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"crawl_report_{today}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Report written → {report_path}")


if __name__ == "__main__":
    main()
