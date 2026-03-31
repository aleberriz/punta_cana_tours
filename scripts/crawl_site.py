"""
Live site crawler for PuntaCanaYachts SEO audit.

Crawls the sitemap, checks every URL for:
  - HTTP status & final URL after redirects
  - Canonical tag
  - Title, meta description, H1
  - Whether old WordPress URLs 301 to the correct new /charter/ path

Usage:
    poetry run python scripts/crawl_site.py

Output: prints a report and writes docs/analysis/crawl_report_YYYY-MM-DD.md
"""

import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SITE = "https://puntacanayachts.com"
SITEMAP = f"{SITE}/sitemap.xml"
REQUEST_DELAY = 0.5  # seconds between requests; be polite

# Old WordPress paths that should redirect to new /charter/ equivalents.
EXPECTED_REDIRECTS = {
    "/private-yacht-isla-saona":     "/charter/private-yacht-isla-saona/",
    "/saona-island-catamaran":        "/charter/saona-island-catamaran/",
    "/romantic-cruise-for-two":       "/charter/romantic-cruise-for-two/",   # known wrong
    "/punta-cana-wedding-boat":       "/charter/punta-cana-wedding-boat/",
    "/picaflor-mini-yacht":           "/charter/picaflor-mini-yacht/",
    "/media-luna":                    "/charter/media-luna/",
    "/margaritas-party-boat":         "/charter/margaritas-party-boat/",
    "/malibu-party-boat":             "/charter/malibu-party-boat/",
    "/fishing-boat-charter":          "/charter/fishing-boat-charter/",
    "/catamaran-st-mary":             "/charter/catamaran-st-mary/",
    "/catamaran-la-palma":            "/charter/catamaran-la-palma/",
    "/caribbean-dream-sail":          "/charter/caribbean-dream-sail/",
    "/big-baby-catamaran":            "/charter/big-baby-catamaran/",
    "/baby-catamaran-ii":             "/charter/baby-catamaran-ii/",
    "/baby-catamaran":                "/charter/baby-catamaran/",
    "/wedding-boat":                  "/charter/punta-cana-wedding-boat/",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; PuntaCanaToursAuditBot/1.0; +audit)"
})


def fetch(url: str, follow_redirects=True) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=10, allow_redirects=follow_redirects)
        return r
    except requests.RequestException as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return None


def parse_sitemap(url: str) -> list[str]:
    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  Cannot fetch sitemap ({url}): status {r.status_code if r else 'N/A'}")
        return []
    soup = BeautifulSoup(r.text, "xml")
    locs = [t.text.strip() for t in soup.find_all("loc")]
    # Handle sitemap index (nested sitemaps)
    if soup.find("sitemapindex"):
        nested: list[str] = []
        for loc in locs:
            nested.extend(parse_sitemap(loc))
            time.sleep(REQUEST_DELAY)
        return nested
    return locs


def audit_url(url: str) -> dict:
    r = fetch(url)
    if r is None:
        return {"url": url, "status": "ERROR", "final_url": None,
                "title": None, "canonical": None, "h1": None, "meta_desc": None}

    final = r.url
    soup = BeautifulSoup(r.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else None

    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag["href"].strip() if canonical_tag and canonical_tag.get("href") else None

    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else None

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    return {
        "url": url,
        "status": r.status_code,
        "final_url": final if final != url else None,
        "title": title,
        "canonical": canonical,
        "h1": h1,
        "meta_desc": meta_desc,
    }


def check_redirect(old_path: str, expected_path: str) -> dict:
    url = SITE + old_path
    r = fetch(url, follow_redirects=False)
    if r is None:
        return {"old": old_path, "expected": expected_path,
                "actual_status": "ERROR", "actual_dest": None, "ok": False}

    dest = r.headers.get("Location", "")
    # normalise to path only for comparison
    dest_path = urlparse(dest).path if dest else None
    expected_norm = expected_path.rstrip("/") + "/"
    dest_norm = (dest_path or "").rstrip("/") + "/"

    ok = dest_norm == expected_norm and r.status_code == 301

    return {
        "old": old_path,
        "expected": expected_path,
        "actual_status": r.status_code,
        "actual_dest": dest_path,
        "ok": ok,
    }


def section(title: str):
    print(f"\n{'='*64}")
    print(f"  {title}")
    print(f"{'='*64}")


def main():
    lines: list[str] = []

    def out(s=""):
        print(s)
        lines.append(s)

    out(f"# PuntaCanaYachts — Live crawl report")
    out(f"_Date: {date.today()}_\n")

    # ── 1. Redirect audit ─────────────────────────────────────────
    section("1 / REDIRECT AUDIT  (old WordPress → new /charter/ paths)")
    out("## 1. Redirect audit\n")
    out(f"{'Old path':<38} {'Expected dest':<38} {'Status':>6} {'Actual dest':<38} {'OK':>4}")
    out("-" * 130)
    issues: list[str] = []
    for old, expected in EXPECTED_REDIRECTS.items():
        result = check_redirect(old, expected)
        ok_str = "✓" if result["ok"] else "✗"
        actual = result["actual_dest"] or "(none)"
        print(f"  {old:<38} {expected:<38} {str(result['actual_status']):>6} "
              f"{actual:<38} {ok_str:>4}")
        out(f"| `{old}` | `{expected}` | {result['actual_status']} | `{actual}` | {ok_str} |")
        if not result["ok"]:
            issues.append(f"- `{old}` → got `{actual}` (status {result['actual_status']}), "
                          f"expected `{expected}`")
        time.sleep(REQUEST_DELAY)

    if issues:
        out("\n### Redirect issues\n")
        for i in issues:
            out(i)

    # ── 2. Sitemap crawl ──────────────────────────────────────────
    section("2 / SITEMAP CRAWL")
    out("\n## 2. Sitemap URLs\n")
    print(f"  Fetching {SITEMAP} …")
    urls = parse_sitemap(SITEMAP)
    out(f"Found **{len(urls)} URLs** in sitemap.\n")

    if not urls:
        out("No URLs found. Check sitemap manually.")
    else:
        out(f"| URL | Status | Canonical | Title | H1 |")
        out(f"|-----|--------|-----------|-------|----|")
        errors: list = []
        no_canonical: list = []
        duplicate_titles: dict = {}
        title_map: dict[str, list[str]] = {}

        for url in urls:
            data = audit_url(url)
            path = urlparse(url).path
            status = str(data["status"])
            canon_path = urlparse(data["canonical"] or "").path if data["canonical"] else "—"
            title = (data["title"] or "—")[:60]
            h1 = (data["h1"] or "—")[:50]

            row = f"| `{path}` | {status} | `{canon_path}` | {title} | {h1} |"
            out(row)
            print(f"  {status}  {path}")

            if data["status"] not in (200, None):
                errors.append(url)
            if not data["canonical"]:
                no_canonical.append(path)
            if data["title"]:
                title_map.setdefault(data["title"], []).append(path)

            time.sleep(REQUEST_DELAY)

        # Duplicate titles
        dupes = {t: pages for t, pages in title_map.items() if len(pages) > 1}

        out("\n## 3. Issues found\n")
        if errors:
            out(f"### Non-200 URLs ({len(errors)})\n")
            for e in errors:
                out(f"- {e}")
        if no_canonical:
            out(f"\n### Missing canonical tag ({len(no_canonical)})\n")
            for p in no_canonical:
                out(f"- `{p}`")
        if dupes:
            out(f"\n### Duplicate `<title>` tags ({len(dupes)} titles shared by multiple pages)\n")
            for title, pages in dupes.items():
                out(f"- **\"{title}\"** used on: {', '.join(f'`{p}`' for p in pages)}")

        if not errors and not no_canonical and not dupes:
            out("No structural issues found.")

    # ── 3. Write markdown report ──────────────────────────────────
    out_dir = Path(__file__).parent.parent / "docs" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"crawl_report_{date.today()}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Report written → {report_path}")


if __name__ == "__main__":
    main()
