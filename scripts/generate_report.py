#!/usr/bin/env python3
"""
Generate a local HTML growth report from GA4, Google Ads, and a live SEO crawl.

Usage:
    poetry run python scripts/generate_report.py

The report answers:
  - What's happening lately?
  - How does that compare vs historic?
  - What changes are recommended next?
"""

from __future__ import annotations

import argparse
import html
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy, RunReportRequest
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import crawl_site
import fetch_ga4
import fetch_google_ads


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "latest" / "index.html"
DEFAULT_TITLE = "Punta Cana Yachts - Growth and SEO report"
SERP_BRAND_NOTE = (
    "Branded and semi-branded checks still show Punta Cana Yachts appearing well, "
    "but generic commercial yacht-rental terms are contested."
)
SERP_COMPETITORS = [
    "rentalyachtspuntacana.com",
    "yachtcharterspuntacana.com",
    "yachtscharterpuntacana.com",
    "canaboat.com",
    "sailo.com",
]

STOPWORDS = {
    "a", "and", "best", "boat", "boats", "by", "can", "cana", "caribbean",
    "charter", "charters", "day", "excursion", "for", "from", "in", "is",
    "isla", "island", "it", "la", "of", "on", "our", "private", "punta",
    "rental", "rentals", "saona", "sail", "the", "to", "tour", "tours",
    "trip", "visit", "with", "yacht", "yachts", "your",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local HTML growth report")
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument("--oauth-client", type=Path, help="OAuth desktop client JSON")
    auth.add_argument("--credentials", type=Path, help="GA4 service account JSON")
    parser.add_argument(
        "--ga4-token",
        type=Path,
        default=fetch_ga4.DEFAULT_OAUTH_TOKEN_PATH,
        help=f"GA4 OAuth token path (default: {fetch_ga4.DEFAULT_OAUTH_TOKEN_PATH})",
    )
    parser.add_argument(
        "--ads-token",
        type=Path,
        default=fetch_google_ads.DEFAULT_OAUTH_TOKEN_PATH,
        help=f"Google Ads OAuth token path (default: {fetch_google_ads.DEFAULT_OAUTH_TOKEN_PATH})",
    )
    parser.add_argument(
        "--developer-token",
        default="",
        help="Google Ads developer token (falls back to GOOGLE_ADS_DEVELOPER_TOKEN)",
    )
    parser.add_argument(
        "--customer-id",
        default="",
        help="Google Ads client customer id (falls back to GOOGLE_ADS_CUSTOMER_ID)",
    )
    parser.add_argument(
        "--login-customer-id",
        default="",
        help="Optional Google Ads manager login customer id",
    )
    parser.add_argument(
        "--comparison-days",
        type=int,
        default=30,
        help="Recent vs previous comparison window in days (default: 30)",
    )
    parser.add_argument(
        "--trend-days",
        type=int,
        default=120,
        help="Trailing daily trend window in days (default: 120)",
    )
    parser.add_argument(
        "--landing-limit",
        type=int,
        default=25,
        help="Top landing pages to include (default: 25)",
    )
    parser.add_argument(
        "--search-term-limit",
        type=int,
        default=5000,
        help="Max Google Ads search-term rows to fetch (default: 5000)",
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip the live SEO crawl and generate a traffic-only report",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"HTML output path (default: {DEFAULT_REPORT_PATH})",
    )
    return parser.parse_args()


def autodetect_oauth_client() -> Path:
    patterns = [
        REPO_ROOT / "data" / "ga4",
        REPO_ROOT / "data" / "google_ads",
    ]
    for base in patterns:
        matches = sorted(base.glob("client_secret*.json"))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        "No OAuth client JSON found under data/ga4/ or data/google_ads/. "
        "Pass --oauth-client explicitly."
    )


def format_int(value: float | int) -> str:
    return f"{int(round(value)):,}"


def format_float(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}"


def format_pct(ratio: float | None) -> str:
    if ratio is None or math.isnan(ratio):
        return "n/a"
    return f"{ratio * 100:.1f}%"


def pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def period_dates(end_date: date, comparison_days: int, trend_days: int) -> dict[str, date]:
    recent_end = end_date
    recent_start = recent_end - timedelta(days=comparison_days - 1)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=comparison_days - 1)
    yoy_start = (pd.Timestamp(recent_start) - pd.DateOffset(years=1)).date()
    yoy_end = (pd.Timestamp(recent_end) - pd.DateOffset(years=1)).date()
    trend_start = recent_end - timedelta(days=trend_days - 1)
    history_start = min(trend_start, yoy_start)
    return {
        "recent_start": recent_start,
        "recent_end": recent_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "yoy_start": yoy_start,
        "yoy_end": yoy_end,
        "trend_start": trend_start,
        "history_start": history_start,
    }


def ga4_run_report(
    client,
    property_id: str,
    start: date,
    end: date,
    dimensions: list[str],
    metrics: list[str],
    limit: int = 10000,
    order_metric: str | None = None,
    order_dimension: str | None = None,
) -> pd.DataFrame:
    order_bys: list[OrderBy] = []
    if order_metric:
        order_bys.append(
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=True)
        )
    elif order_dimension:
        order_bys.append(
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name=order_dimension),
                desc=False,
            )
        )
    response = client.run_report(
        RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
            dimensions=[Dimension(name=name) for name in dimensions],
            metrics=[Metric(name=name) for name in metrics],
            order_bys=order_bys,
            limit=limit,
        )
    )
    rows: list[list[str]] = []
    for row in response.rows:
        rows.append(
            [v.value for v in row.dimension_values] + [v.value for v in row.metric_values]
        )
    df = pd.DataFrame(rows, columns=dimensions + metrics)
    for metric in metrics:
        df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0)
    return df


def load_ga4(args: argparse.Namespace, dates: dict[str, date]) -> dict[str, pd.DataFrame]:
    if args.credentials:
        client = fetch_ga4.client_from_service_account(args.credentials)
    else:
        oauth_client = args.oauth_client or autodetect_oauth_client()
        try:
            client = fetch_ga4.client_from_oauth(oauth_client, args.ga4_token)
        except Exception as exc:
            if "invalid_grant" not in str(exc):
                raise
            if args.ga4_token.exists():
                args.ga4_token.unlink()
            client = fetch_ga4.client_from_oauth(oauth_client, args.ga4_token)

    prop = fetch_ga4.property_resource_id()
    daily = ga4_run_report(
        client,
        prop,
        dates["history_start"],
        dates["recent_end"],
        dimensions=["date"],
        metrics=["sessions", "engagedSessions", "keyEvents"],
        order_dimension="date",
    )
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"], format="%Y%m%d")

    channel_recent = ga4_run_report(
        client,
        prop,
        dates["recent_start"],
        dates["recent_end"],
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "engagedSessions", "keyEvents"],
        order_metric="sessions",
        limit=50,
    )
    channel_previous = ga4_run_report(
        client,
        prop,
        dates["previous_start"],
        dates["previous_end"],
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "engagedSessions", "keyEvents"],
        order_metric="sessions",
        limit=50,
    )
    channel_yoy = ga4_run_report(
        client,
        prop,
        dates["yoy_start"],
        dates["yoy_end"],
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "engagedSessions", "keyEvents"],
        order_metric="sessions",
        limit=50,
    )
    landing = ga4_run_report(
        client,
        prop,
        dates["recent_start"],
        dates["recent_end"],
        dimensions=["landingPagePlusQueryString"],
        metrics=["sessions", "keyEvents"],
        order_metric="sessions",
        limit=max(10, args.landing_limit),
    )
    return {
        "daily": daily,
        "channel_recent": channel_recent,
        "channel_previous": channel_previous,
        "channel_yoy": channel_yoy,
        "landing": landing,
    }


def load_google_ads(args: argparse.Namespace, dates: dict[str, date]) -> dict[str, pd.DataFrame]:
    fetch_google_ads._load_dotenv_simple()

    oauth_client = args.oauth_client or autodetect_oauth_client()
    developer_token = (
        args.developer_token.strip() or fetch_google_ads.os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()
    )
    customer_id = (
        args.customer_id.strip() or fetch_google_ads.os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").strip()
    )
    login_customer_id = (
        args.login_customer_id.strip()
        or fetch_google_ads.os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
        or None
    )

    if not developer_token:
        raise RuntimeError("Missing Google Ads developer token")
    if not customer_id:
        raise RuntimeError("Missing Google Ads customer id")

    access_token = fetch_google_ads.get_access_token(oauth_client, args.ads_token)
    campaigns_raw = fetch_google_ads.gaql_search(
        access_token=access_token,
        developer_token=developer_token,
        customer_id=fetch_google_ads._norm_id(customer_id),
        login_customer_id=fetch_google_ads._norm_id(login_customer_id) if login_customer_id else None,
        query=fetch_google_ads.QUERY_CAMPAIGNS.format(
            start=str(dates["history_start"]),
            end=str(dates["recent_end"]),
        ),
        api_version=fetch_google_ads.ADS_API_VERSION,
    )
    camp_header, camp_rows = fetch_google_ads.build_campaigns(campaigns_raw)
    campaigns = pd.DataFrame(camp_rows, columns=camp_header)
    for col in ("impressions", "clicks", "cost", "conversions", "all_conversions"):
        campaigns[col] = pd.to_numeric(campaigns[col], errors="coerce").fillna(0)
    campaigns["date"] = pd.to_datetime(campaigns["date"])

    search_raw = fetch_google_ads.gaql_search(
        access_token=access_token,
        developer_token=developer_token,
        customer_id=fetch_google_ads._norm_id(customer_id),
        login_customer_id=fetch_google_ads._norm_id(login_customer_id) if login_customer_id else None,
        query=fetch_google_ads.QUERY_SEARCH_TERMS.format(
            start=str(dates["recent_start"]),
            end=str(dates["recent_end"]),
        ),
        max_rows=max(1, args.search_term_limit),
        api_version=fetch_google_ads.ADS_API_VERSION,
    )
    term_header, term_rows = fetch_google_ads.build_search_terms(search_raw)
    search_terms = pd.DataFrame(term_rows, columns=term_header)
    if not search_terms.empty:
        for col in ("impressions", "clicks", "cost", "conversions"):
            search_terms[col] = pd.to_numeric(search_terms[col], errors="coerce").fillna(0)
        search_terms["date"] = pd.to_datetime(search_terms["date"])

    return {"campaigns": campaigns, "search_terms": search_terms}


def load_seo_snapshot(skip_crawl: bool) -> dict[str, object]:
    if skip_crawl:
        return {
            "pages": [],
            "sitemap_urls": set(),
            "inlink_count": {},
            "redirects": [],
            "robots_ok": None,
            "robots_text": "",
        }

    robots_resp = crawl_site.fetch(f"{crawl_site.SITE}/robots.txt")
    robots_ok = bool(robots_resp and robots_resp.status_code == 200)
    robots_text = robots_resp.text[:5000] if robots_resp and robots_resp.text else ""

    sitemap_urls = set(crawl_site.parse_sitemap(crawl_site.SITEMAP))
    to_crawl: list[str] = list(sitemap_urls)
    crawled: dict[str, dict] = {}
    inlink_count: dict[str, int] = defaultdict(int)

    i = 0
    while i < len(to_crawl):
        url = to_crawl[i]
        i += 1
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if any(url.endswith(ext) for ext in (".xml", ".jpg", ".png", ".pdf", ".webp", ".jpeg", ".gif")):
            continue
        if url in crawled:
            continue

        data = crawl_site.audit_url(url)
        crawled[url] = data

        for link in data.get("internal_links", []):
            clean = link.rstrip("/") + "/"
            clean_base = urlparse(clean)._replace(fragment="", query="").geturl()
            inlink_count[clean_base] += 1
            if clean_base not in crawled and clean_base not in to_crawl:
                if crawl_site.is_internal(clean_base) and urlparse(clean_base).scheme in ("http", "https"):
                    to_crawl.append(clean_base)

    redirects = [
        crawl_site.check_redirect(old, expected)
        for old, expected in crawl_site.EXPECTED_REDIRECTS.items()
    ]
    return {
        "pages": list(crawled.values()),
        "sitemap_urls": sitemap_urls,
        "inlink_count": inlink_count,
        "redirects": redirects,
        "robots_ok": robots_ok,
        "robots_text": robots_text,
    }


def filter_period(df: pd.DataFrame, start: date, end: date, date_col: str = "date") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    mask = (df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)
    return df.loc[mask].copy()


def ga4_period_summary(df: pd.DataFrame, start: date, end: date) -> dict[str, float]:
    period = filter_period(df, start, end)
    sessions = float(period["sessions"].sum())
    engaged = float(period["engagedSessions"].sum())
    key_events = float(period["keyEvents"].sum())
    return {
        "sessions": sessions,
        "engaged_sessions": engaged,
        "key_events": key_events,
        "engagement_rate": safe_div(engaged, sessions),
        "conversion_rate": safe_div(key_events, sessions),
    }


def ads_period_summary(df: pd.DataFrame, start: date, end: date) -> dict[str, float]:
    period = filter_period(df, start, end)
    impressions = float(period["impressions"].sum())
    clicks = float(period["clicks"].sum())
    cost = float(period["cost"].sum())
    conversions = float(period["conversions"].sum())
    return {
        "impressions": impressions,
        "clicks": clicks,
        "cost": cost,
        "conversions": conversions,
        "ctr": safe_div(clicks, impressions),
        "cpc": safe_div(cost, clicks),
        "cpa": safe_div(cost, conversions),
        "conv_rate": safe_div(conversions, clicks),
    }


def summarize_channels(recent: pd.DataFrame, previous: pd.DataFrame, yoy: pd.DataFrame) -> pd.DataFrame:
    def prep(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
        out = df.copy()
        out = out.rename(
            columns={
                "sessions": f"sessions_{suffix}",
                "engagedSessions": f"engaged_{suffix}",
                "keyEvents": f"key_events_{suffix}",
            }
        )
        return out

    merged = prep(recent, "recent").merge(
        prep(previous, "prev"), on="sessionDefaultChannelGroup", how="outer"
    ).merge(
        prep(yoy, "yoy"), on="sessionDefaultChannelGroup", how="outer"
    ).fillna(0)
    merged["conv_rate_recent"] = merged.apply(
        lambda row: safe_div(row["key_events_recent"], row["sessions_recent"]), axis=1
    )
    merged["session_change_vs_prev"] = merged.apply(
        lambda row: pct_change(row["sessions_recent"], row["sessions_prev"]), axis=1
    )
    merged["session_change_vs_yoy"] = merged.apply(
        lambda row: pct_change(row["sessions_recent"], row["sessions_yoy"]), axis=1
    )
    merged["key_event_change_vs_prev"] = merged.apply(
        lambda row: pct_change(row["key_events_recent"], row["key_events_prev"]), axis=1
    )
    return merged.sort_values("sessions_recent", ascending=False)


def normalize_path(value: str) -> str:
    if not value:
        return "/"
    full = crawl_site.normalise(value, base=crawl_site.SITE)
    path = urlparse(full).path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path


def enrich_landing_pages(landing: pd.DataFrame, pages: list[dict], inlink_count: dict[str, int]) -> pd.DataFrame:
    if landing.empty:
        return landing

    page_lookup = {}
    for page in pages:
        path = normalize_path(urlparse(page["url"]).path)
        page_lookup[path] = page

    out = landing.copy()
    out["path"] = out["landingPagePlusQueryString"].map(normalize_path)
    out["title"] = out["path"].map(lambda x: (page_lookup.get(x) or {}).get("title", ""))
    out["has_form"] = out["path"].map(lambda x: bool((page_lookup.get(x) or {}).get("forms", [])))
    out["word_count"] = out["path"].map(lambda x: (page_lookup.get(x) or {}).get("word_count", 0))
    out["h1_count"] = out["path"].map(lambda x: (page_lookup.get(x) or {}).get("h1_count", 0))
    out["schema_types"] = out["path"].map(
        lambda x: ", ".join(sorted(set((page_lookup.get(x) or {}).get("schema_types", []))))
    )
    out["inbound_links"] = out["path"].map(
        lambda x: inlink_count.get((crawl_site.SITE.rstrip("/") + x).rstrip("/") + "/", 0)
    )
    out["landingPagePlusQueryString"] = out["landingPagePlusQueryString"].replace({"": "(not set)"})
    return out.sort_values(["sessions", "keyEvents"], ascending=False)


def seo_issue_summary(snapshot: dict[str, object]) -> tuple[dict[str, int], dict[str, object]]:
    pages: list[dict] = snapshot["pages"]  # type: ignore[assignment]
    sitemap_urls: set[str] = snapshot["sitemap_urls"]  # type: ignore[assignment]
    inlink_count: dict[str, int] = snapshot["inlink_count"]  # type: ignore[assignment]
    redirects: list[dict] = snapshot["redirects"]  # type: ignore[assignment]

    title_map: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        if page["status"] == 200 and page["title"]:
            title_map[page["title"]].append(urlparse(page["url"]).path)
    dup_titles = {title: paths for title, paths in title_map.items() if len(paths) > 1}

    orphaned = []
    for page in pages:
        url_norm = page["url"].rstrip("/") + "/"
        if page["url"] in sitemap_urls and inlink_count.get(url_norm, 0) == 0:
            if urlparse(page["url"]).path not in ("/", ""):
                orphaned.append(page)

    external_domains = Counter()
    for page in pages:
        for link in page.get("external_links", []):
            host = urlparse(link).netloc.replace("www.", "")
            if host:
                external_domains[host] += 1

    counts = {
        "redirect_issues": sum(1 for item in redirects if not item["ok"]),
        "non_200_pages": sum(1 for p in pages if p["status"] != 200),
        "missing_canonical": sum(1 for p in pages if p["status"] == 200 and not p["canonical"]),
        "canonical_mismatch": sum(
            1 for p in pages if p["status"] == 200 and p["canonical"] and not p["canonical_matches"]
        ),
        "noindex_pages": sum(1 for p in pages if p["status"] == 200 and p["noindex"]),
        "missing_title": sum(1 for p in pages if p["status"] == 200 and not p["title"]),
        "duplicate_titles": len(dup_titles),
        "missing_h1": sum(1 for p in pages if p["status"] == 200 and p["h1_count"] == 0),
        "missing_meta_description": sum(1 for p in pages if p["status"] == 200 and not p["meta_desc"]),
        "thin_pages": sum(1 for p in pages if p["status"] == 200 and p["word_count"] < 300),
        "charter_pages_without_form": sum(
            1 for p in pages if p["status"] == 200 and "/charter/" in p["url"] and not p["forms"]
        ),
        "orphaned_pages": len(orphaned),
        "charter_pages_without_schema": sum(
            1 for p in pages if p["status"] == 200 and "/charter/" in p["url"] and not p["schema_types"]
        ),
        "pages_missing_og_image": sum(1 for p in pages if p["status"] == 200 and not p["og"].get("og:image")),
    }
    details = {
        "orphaned": orphaned,
        "duplicate_titles": dup_titles,
        "external_domains": external_domains,
        "redirects": redirects,
    }
    return counts, details


def tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def keyword_signals(search_terms: pd.DataFrame, pages: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    if search_terms.empty:
        return pd.DataFrame(), []

    themes = Counter()
    for _, row in search_terms.sort_values(["conversions", "cost"], ascending=False).head(100).iterrows():
        weight = max(1, int(row["conversions"] * 5 + row["clicks"]))
        for token in tokens(str(row["search_term"])):
            themes[token] += weight

    on_page_tokens = Counter()
    for page in pages:
        text = " ".join(
            [
                page.get("title") or "",
                " ".join(page.get("h1_texts", [])),
                urlparse(page["url"]).path.replace("-", " "),
            ]
        )
        for token in tokens(text):
            on_page_tokens[token] += 1

    theme_rows = []
    for token, score in themes.most_common(12):
        theme_rows.append(
            {
                "keyword_theme": token,
                "query_signal_score": score,
                "represented_in_titles_h1s": token in on_page_tokens,
            }
        )
    missing = [row["keyword_theme"] for row in theme_rows if not row["represented_in_titles_h1s"]]
    return pd.DataFrame(theme_rows), missing[:6]


def campaign_table(campaigns: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    period = filter_period(campaigns, start, end)
    if period.empty:
        return period
    grouped = (
        period.groupby(["campaign_name", "campaign_status"], as_index=False)[
            ["impressions", "clicks", "cost", "conversions"]
        ]
        .sum()
        .sort_values("cost", ascending=False)
    )
    grouped["ctr"] = grouped.apply(lambda row: safe_div(row["clicks"], row["impressions"]), axis=1)
    grouped["cpc"] = grouped.apply(lambda row: safe_div(row["cost"], row["clicks"]), axis=1)
    grouped["cpa"] = grouped.apply(lambda row: safe_div(row["cost"], row["conversions"]), axis=1)
    return grouped


def search_term_table(search_terms: pd.DataFrame) -> pd.DataFrame:
    if search_terms.empty:
        return search_terms
    grouped = (
        search_terms.groupby("search_term", as_index=False)[["impressions", "clicks", "cost", "conversions"]]
        .sum()
        .sort_values(["conversions", "cost", "clicks"], ascending=[False, False, False])
    )
    grouped["cpa"] = grouped.apply(lambda row: safe_div(row["cost"], row["conversions"]), axis=1)
    grouped["ctr"] = grouped.apply(lambda row: safe_div(row["clicks"], row["impressions"]), axis=1)
    return grouped


def build_recommendations(
    ga4_recent: dict[str, float],
    ga4_prev: dict[str, float],
    ads_recent: dict[str, float],
    ads_prev: dict[str, float],
    seo_counts: dict[str, int],
    campaigns_recent: pd.DataFrame,
    search_terms_recent: pd.DataFrame,
    missing_keyword_themes: list[str],
) -> list[str]:
    recs: list[str] = []

    ga4_session_delta = pct_change(ga4_recent["sessions"], ga4_prev["sessions"])
    ga4_conv_delta = pct_change(ga4_recent["key_events"], ga4_prev["key_events"])
    ads_conv_delta = pct_change(ads_recent["conversions"], ads_prev["conversions"])

    if ga4_conv_delta is not None and ga4_conv_delta < -0.2:
        recs.append(
            "GA4 key events are down materially versus the previous window. Re-validate the form flow, thank-you-page event firing, and bot-check false negatives before treating this as a demand problem."
        )
    if ads_conv_delta is not None and ads_conv_delta < -0.2:
        recs.append(
            "Google Ads conversions are down versus the previous window. Review bid pressure, search-term quality, and whether paused campaigns should be reactivated or consolidated."
        )
    if seo_counts["orphaned_pages"] > 0:
        recs.append(
            f"{seo_counts['orphaned_pages']} sitemap pages still have zero internal inlinks. Link high-value content pages from main navigation, charter hubs, or relevant product pages so they can earn authority and traffic."
        )
    if seo_counts["charter_pages_without_form"] > 0:
        recs.append(
            f"{seo_counts['charter_pages_without_form']} charter pages lack an inquiry form. Paid or organic traffic landing there has a weaker conversion path than product pages with a direct CTA."
        )
    if seo_counts["noindex_pages"] > 0 or seo_counts["canonical_mismatch"] > 0:
        recs.append(
            "Fix indexability signals before they become a ranking issue: some pages are sending noindex or canonical mismatch signals."
        )
    expensive_nonconverting = search_terms_recent[
        (search_terms_recent["cost"] > 20) & (search_terms_recent["conversions"] == 0)
    ].head(5)
    if not expensive_nonconverting.empty:
        recs.append(
            "Add negatives or tighten match types for expensive zero-conversion queries, especially the highest-spend terms in the search-term section."
        )
    paused = campaigns_recent[campaigns_recent["campaign_status"] == "PAUSED"]
    if not paused.empty:
        recs.append(
            f"{len(paused)} paused campaigns are still present in the account. Confirm whether they are intentionally retired or should be relaunched with updated landing pages and budgets."
        )
    if missing_keyword_themes:
        recs.append(
            "High-intent paid keyword themes are not well represented in page titles/H1s: "
            + ", ".join(f"`{term}`" for term in missing_keyword_themes[:4])
            + ". Consider tightening page-level keyword targeting around proven demand."
        )
    if ga4_session_delta is not None and ga4_session_delta > 0.15 and ads_conv_delta is not None and ads_conv_delta < 0:
        recs.append(
            "Traffic is up while paid conversions are down. Prioritize landing-page relevance, CTA clarity, and search-term quality over broad traffic acquisition."
        )
    return recs[:8]


def build_next_run_checks(
    ga4_recent: dict[str, float],
    ads_recent: dict[str, float],
    seo_counts: dict[str, int],
    campaigns_recent: pd.DataFrame,
    search_terms_recent: pd.DataFrame,
) -> list[str]:
    checks: list[str] = []
    if ga4_recent["key_events"] == 0 and ads_recent["conversions"] > 0:
        checks.append(
            "Fix measurement first: compare Google Ads conversion timestamps to GA4 key events, verify the thank-you event fires in GTM preview, and confirm `/thank-you/` is still the post-submit destination."
        )
        checks.append(
            "Inspect false-negative risk in the form flow: log failed bot-check submissions, test the honeypot/time-trap on mobile, and show a visible error state instead of silent failure."
        )
    if seo_counts.get("orphaned_pages", 0) > 0:
        checks.append(
            "Add at least one contextual internal link to each orphaned page from `/`, `/charters/`, or the most relevant charter detail page, then verify inbound-link counts increase on the next run."
        )
    if seo_counts.get("thin_pages", 0) > 0:
        checks.append(
            "Expand thin pages with unique trip details, pricing context, FAQs, and trust proof so they can compete without publishing filler content."
        )
    expensive_zero_conv = search_terms_recent[
        (search_terms_recent["cost"] >= 20) & (search_terms_recent["conversions"] == 0)
    ].head(5)
    if not expensive_zero_conv.empty:
        checks.append(
            "Review the highest-spend zero-conversion queries and add negatives, tighter match types, or more specific landing pages before the next budget cycle."
        )
    paused = campaigns_recent[campaigns_recent["campaign_status"] == "PAUSED"]
    if not paused.empty:
        checks.append(
            "Document whether paused campaigns are intentionally retired or should be relaunched; if they stay paused, capture the reason in the next report so account changes are explicit."
        )
    return checks[:6]


def metric_cards_html(cards: list[dict[str, str]]) -> str:
    blocks = []
    for card in cards:
        delta_html = f"<div class='metric-delta'>{html.escape(card['delta'])}</div>" if card.get("delta") else ""
        blocks.append(
            "<div class='metric-card'>"
            f"<div class='metric-label'>{html.escape(card['label'])}</div>"
            f"<div class='metric-value'>{html.escape(card['value'])}</div>"
            f"{delta_html}"
            "</div>"
        )
    return "<div class='metric-grid'>" + "".join(blocks) + "</div>"


def df_to_html_table(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    if df.empty:
        return "<p class='muted'>No data returned for this section.</p>"
    table = df.copy()
    if columns is not None:
        table = table[columns]
    return table.to_html(index=False, classes="data-table", border=0, justify="left", escape=False)


def fig_fragment(fig: go.Figure, first: bool = False) -> str:
    return fig.to_html(full_html=False, include_plotlyjs="cdn" if first else False)


def build_figures(
    ga4_daily: pd.DataFrame,
    ads_campaigns: pd.DataFrame,
    campaigns_recent: pd.DataFrame,
    search_terms_recent: pd.DataFrame,
    landing_enriched: pd.DataFrame,
    seo_counts: dict[str, int],
    seo_details: dict[str, object],
    dates: dict[str, date],
) -> list[str]:
    fragments: list[str] = []

    trend = filter_period(ga4_daily, dates["trend_start"], dates["recent_end"])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=trend["date"], y=trend["sessions"], name="GA4 sessions", mode="lines"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=trend["date"], y=trend["keyEvents"], name="GA4 key events", mode="lines"),
        secondary_y=True,
    )
    fig.update_layout(title="GA4 daily sessions and key events", margin=dict(l=20, r=20, t=40, b=20))
    fig.update_yaxes(title_text="Sessions", secondary_y=False)
    fig.update_yaxes(title_text="Key events", secondary_y=True)
    fragments.append(fig_fragment(fig, first=True))

    ads_trend = (
        filter_period(ads_campaigns, dates["trend_start"], dates["recent_end"])
        .groupby("date", as_index=False)[["cost", "conversions", "clicks"]]
        .sum()
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=ads_trend["date"], y=ads_trend["cost"], name="Ads cost"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=ads_trend["date"], y=ads_trend["conversions"], name="Ads conversions", mode="lines+markers"),
        secondary_y=True,
    )
    fig.update_layout(title="Google Ads daily spend and conversions", margin=dict(l=20, r=20, t=40, b=20))
    fig.update_yaxes(title_text="Cost", secondary_y=False)
    fig.update_yaxes(title_text="Conversions", secondary_y=True)
    fragments.append(fig_fragment(fig))

    if not campaigns_recent.empty:
        camp_chart = campaigns_recent.head(10).copy()
        fig = px.bar(
            camp_chart,
            x="campaign_name",
            y=["cost", "conversions"],
            barmode="group",
            title="Top campaigns - cost vs conversions (recent window)",
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), xaxis_title="")
        fragments.append(fig_fragment(fig))

    if not search_terms_recent.empty:
        term_chart = search_terms_recent.sort_values(["cost", "conversions"], ascending=[False, False]).head(10).copy()
        fig = px.bar(
            term_chart,
            x="search_term",
            y="cost",
            color="conversions",
            title="Highest-spend search terms (recent window)",
            color_continuous_scale="Blues",
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), xaxis_title="")
        fragments.append(fig_fragment(fig))

    if not landing_enriched.empty:
        landing_chart = landing_enriched.head(10).copy()
        landing_chart["label"] = landing_chart["path"]
        fig = px.bar(
            landing_chart,
            x="label",
            y=["sessions", "keyEvents"],
            barmode="group",
            title="Top landing pages by recent GA4 traffic",
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), xaxis_title="")
        fragments.append(fig_fragment(fig))

    if seo_counts:
        issue_chart = pd.DataFrame(
            {
                "issue": list(seo_counts.keys()),
                "count": list(seo_counts.values()),
            }
        ).sort_values("count", ascending=False)
        fig = px.bar(issue_chart, x="issue", y="count", title="SEO issue counts")
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), xaxis_title="")
        fragments.append(fig_fragment(fig))

    external_domains: Counter = seo_details.get("external_domains", Counter())  # type: ignore[assignment]
    if external_domains:
        ext_chart = pd.DataFrame(external_domains.most_common(10), columns=["domain", "links"])
        fig = px.bar(ext_chart, x="domain", y="links", title="Top external domains referenced on-site")
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), xaxis_title="")
        fragments.append(fig_fragment(fig))

    return fragments


def build_html(
    generated_at: datetime,
    dates: dict[str, date],
    ga4_recent: dict[str, float],
    ga4_prev: dict[str, float],
    ga4_yoy: dict[str, float],
    ads_recent: dict[str, float],
    ads_prev: dict[str, float],
    ads_yoy: dict[str, float],
    channel_summary: pd.DataFrame,
    campaigns_recent: pd.DataFrame,
    search_terms_recent: pd.DataFrame,
    landing_enriched: pd.DataFrame,
    keyword_themes: pd.DataFrame,
    seo_counts: dict[str, int],
    seo_details: dict[str, object],
    seo_snapshot: dict[str, object],
    figures: list[str],
    recommendations: list[str],
    next_run_checks: list[str],
) -> str:
    ga4_cards = [
        {
            "label": f"GA4 sessions ({dates['recent_start']} to {dates['recent_end']})",
            "value": format_int(ga4_recent["sessions"]),
            "delta": f"vs previous {format_pct(pct_change(ga4_recent['sessions'], ga4_prev['sessions']))} | vs YoY {format_pct(pct_change(ga4_recent['sessions'], ga4_yoy['sessions']))}",
        },
        {
            "label": "GA4 key events",
            "value": format_int(ga4_recent["key_events"]),
            "delta": f"vs previous {format_pct(pct_change(ga4_recent['key_events'], ga4_prev['key_events']))} | conversion rate {format_pct(ga4_recent['conversion_rate'])}",
        },
        {
            "label": "Google Ads spend",
            "value": f"${format_float(ads_recent['cost'])}",
            "delta": f"vs previous {format_pct(pct_change(ads_recent['cost'], ads_prev['cost']))} | CPC ${format_float(ads_recent['cpc'])}",
        },
        {
            "label": "Google Ads conversions",
            "value": format_float(ads_recent["conversions"], 1),
            "delta": f"vs previous {format_pct(pct_change(ads_recent['conversions'], ads_prev['conversions']))} | CPA ${format_float(ads_recent['cpa'])}",
        },
    ]

    executive_points = [
        f"Recent GA4 sessions: {format_int(ga4_recent['sessions'])} ({format_pct(pct_change(ga4_recent['sessions'], ga4_prev['sessions']))} vs previous window).",
        f"Recent GA4 key events: {format_int(ga4_recent['key_events'])} ({format_pct(pct_change(ga4_recent['key_events'], ga4_prev['key_events']))} vs previous window).",
        f"Recent Google Ads spend: ${format_float(ads_recent['cost'])} generating {format_float(ads_recent['conversions'], 1)} conversions.",
    ]
    if ga4_recent["key_events"] == 0 and ads_recent["conversions"] > 0:
        executive_points.append(
            "GA4 and Google Ads are disagreeing materially: Ads is still recording conversions while GA4 key events are at zero, which strongly suggests a measurement break rather than pure demand collapse."
        )
    if seo_counts:
        executive_points.append(
            f"SEO crawl found {seo_counts['orphaned_pages']} orphaned pages, {seo_counts['thin_pages']} thin pages, and {seo_counts['charter_pages_without_form']} charter pages without forms."
        )

    external_domains: Counter = seo_details.get("external_domains", Counter())  # type: ignore[assignment]
    top_external = pd.DataFrame(external_domains.most_common(12), columns=["domain", "links"])
    redirect_issues = [r for r in seo_details.get("redirects", []) if not r["ok"]]  # type: ignore[index]

    styles = """
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #f6f7f9; color: #1f2937; }
      .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
      h1, h2, h3 { margin: 0 0 12px; }
      h1 { font-size: 28px; }
      h2 { font-size: 22px; margin-top: 28px; }
      h3 { font-size: 18px; margin-top: 20px; }
      p, li { line-height: 1.5; }
      .muted { color: #6b7280; }
      .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px 20px; margin-top: 18px; }
      .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 14px; }
      .metric-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; }
      .metric-label { color: #6b7280; font-size: 13px; margin-bottom: 6px; }
      .metric-value { font-size: 28px; font-weight: 700; }
      .metric-delta { margin-top: 8px; color: #374151; font-size: 13px; }
      .two-col { display: grid; grid-template-columns: 1.25fr 1fr; gap: 18px; }
      .data-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 14px; }
      .data-table th, .data-table td { border-bottom: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; vertical-align: top; }
      .data-table th { background: #f9fafb; }
      .tag { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #eef2ff; color: #3730a3; font-size: 12px; margin-right: 6px; }
      .chart-stack > div { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; margin-top: 18px; }
      code { background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }
      @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
    </style>
    """

    html_parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>",
        html.escape(DEFAULT_TITLE),
        "</title>",
        styles,
        "</head><body><div class='container'>",
        f"<h1>{html.escape(DEFAULT_TITLE)}</h1>",
        f"<p class='muted'>Generated {generated_at.strftime('%Y-%m-%d %H:%M:%S')} | Recent window: {dates['recent_start']} to {dates['recent_end']} | Previous window: {dates['previous_start']} to {dates['previous_end']} | YoY comparison: {dates['yoy_start']} to {dates['yoy_end']}</p>",
        "<div class='panel'><h2>Executive summary</h2><ul>",
    ]
    html_parts.extend(f"<li>{html.escape(point)}</li>" for point in executive_points)
    html_parts.append("</ul></div>")
    html_parts.append(metric_cards_html(ga4_cards))

    html_parts.append("<div class='panel'><h2>Recommended actions</h2><ul>")
    html_parts.extend(f"<li>{html.escape(item)}</li>" for item in recommendations)
    html_parts.append("</ul></div>")
    html_parts.append("<div class='panel'><h2>Before next run</h2><ul>")
    html_parts.extend(f"<li>{html.escape(item)}</li>" for item in next_run_checks)
    html_parts.append("</ul></div>")
    html_parts.append(
        "<div class='panel'><h2>SERP market context</h2>"
        f"<p>{html.escape(SERP_BRAND_NOTE)}</p>"
        "<p class='muted'>This is a manual SERP snapshot, not a rank tracker. Use Search Console or a third-party index later for systematic ranking history.</p>"
        "<ul>"
        + "".join(f"<li><code>{html.escape(domain)}</code></li>" for domain in SERP_COMPETITORS)
        + "</ul></div>"
    )

    html_parts.append("<div class='chart-stack'>")
    html_parts.extend(figures)
    html_parts.append("</div>")

    html_parts.append("<div class='two-col'>")
    html_parts.append(
        "<div class='panel'><h2>Channel performance</h2>"
        + df_to_html_table(
            channel_summary.assign(
                sessions_recent=channel_summary["sessions_recent"].map(format_int),
                key_events_recent=channel_summary["key_events_recent"].map(format_int),
                conv_rate_recent=channel_summary["conv_rate_recent"].map(format_pct),
                session_change_vs_prev=channel_summary["session_change_vs_prev"].map(format_pct),
                session_change_vs_yoy=channel_summary["session_change_vs_yoy"].map(format_pct),
            ),
            [
                "sessionDefaultChannelGroup",
                "sessions_recent",
                "key_events_recent",
                "conv_rate_recent",
                "session_change_vs_prev",
                "session_change_vs_yoy",
            ],
        )
        + "</div>"
    )
    html_parts.append(
        "<div class='panel'><h2>SEO issue counts</h2>"
        + "".join(f"<span class='tag'>{html.escape(key.replace('_', ' '))}: {value}</span>" for key, value in seo_counts.items())
        + "</div>"
    )
    html_parts.append("</div>")

    html_parts.append(
        "<div class='panel'><h2>Campaigns</h2>"
        + df_to_html_table(
            campaigns_recent.assign(
                impressions=campaigns_recent["impressions"].map(format_int),
                clicks=campaigns_recent["clicks"].map(format_int),
                cost=campaigns_recent["cost"].map(lambda v: f"${format_float(v)}"),
                conversions=campaigns_recent["conversions"].map(lambda v: format_float(v, 1)),
                ctr=campaigns_recent["ctr"].map(format_pct),
                cpc=campaigns_recent["cpc"].map(lambda v: f"${format_float(v)}"),
                cpa=campaigns_recent["cpa"].map(lambda v: f"${format_float(v)}"),
            ),
            ["campaign_name", "campaign_status", "impressions", "clicks", "cost", "conversions", "ctr", "cpc", "cpa"],
        )
        + "</div>"
    )

    html_parts.append(
        "<div class='panel'><h2>Search terms</h2>"
        + df_to_html_table(
            search_terms_recent.assign(
                impressions=search_terms_recent["impressions"].map(format_int),
                clicks=search_terms_recent["clicks"].map(format_int),
                cost=search_terms_recent["cost"].map(lambda v: f"${format_float(v)}"),
                conversions=search_terms_recent["conversions"].map(lambda v: format_float(v, 1)),
                ctr=search_terms_recent["ctr"].map(format_pct),
                cpa=search_terms_recent["cpa"].map(lambda v: f"${format_float(v)}"),
            ).head(20),
            ["search_term", "impressions", "clicks", "cost", "conversions", "ctr", "cpa"],
        )
        + "</div>"
    )

    html_parts.append(
        "<div class='panel'><h2>Landing pages and conversion-path health</h2>"
        + df_to_html_table(
            landing_enriched.assign(
                sessions=landing_enriched["sessions"].map(format_int),
                keyEvents=landing_enriched["keyEvents"].map(format_int),
                has_form=landing_enriched["has_form"].map(lambda value: "Yes" if value else "No"),
                inbound_links=landing_enriched["inbound_links"].map(format_int),
                word_count=landing_enriched["word_count"].map(format_int),
            ).head(20),
            ["path", "sessions", "keyEvents", "has_form", "inbound_links", "word_count", "title", "schema_types"],
        )
        + "</div>"
    )

    html_parts.append(
        "<div class='two-col'>"
        "<div class='panel'><h2>Keyword themes</h2>"
        + df_to_html_table(keyword_themes)
        + "</div>"
        "<div class='panel'><h2>External links</h2>"
        + df_to_html_table(top_external)
        + "</div></div>"
    )

    html_parts.append(
        "<div class='two-col'>"
        "<div class='panel'><h2>Redirect issues</h2>"
        + (
            df_to_html_table(pd.DataFrame(redirect_issues))
            if redirect_issues
            else "<p class='muted'>All expected legacy redirects are behaving as expected.</p>"
        )
        + "</div>"
        "<div class='panel'><h2>Robots.txt and crawl scope</h2>"
        + f"<p>robots.txt reachable: <strong>{'Yes' if seo_snapshot['robots_ok'] else 'No'}</strong></p>"
        + f"<p>Pages crawled: <strong>{len(seo_snapshot['pages'])}</strong> | Sitemap URLs: <strong>{len(seo_snapshot['sitemap_urls'])}</strong></p>"
        + "<p class='muted'>External link analysis here covers outbound links found on the site. Backlink authority and ranking-position monitoring still need Search Console or a third-party index such as Ahrefs or Semrush.</p>"
        + "</div></div>"
    )

    html_parts.append("</div></body></html>")
    return "".join(html_parts)


def main() -> int:
    args = parse_args()

    if args.oauth_client and not args.oauth_client.is_file():
        raise FileNotFoundError(f"OAuth client file not found: {args.oauth_client}")
    if args.credentials and not args.credentials.is_file():
        raise FileNotFoundError(f"GA4 service account file not found: {args.credentials}")

    end_date = date.today() - timedelta(days=1)
    dates = period_dates(end_date=end_date, comparison_days=args.comparison_days, trend_days=args.trend_days)

    ga4 = load_ga4(args, dates)
    ads = load_google_ads(args, dates)
    seo_snapshot = load_seo_snapshot(skip_crawl=args.skip_crawl)

    ga4_recent = ga4_period_summary(ga4["daily"], dates["recent_start"], dates["recent_end"])
    ga4_prev = ga4_period_summary(ga4["daily"], dates["previous_start"], dates["previous_end"])
    ga4_yoy = ga4_period_summary(ga4["daily"], dates["yoy_start"], dates["yoy_end"])

    ads_recent = ads_period_summary(ads["campaigns"], dates["recent_start"], dates["recent_end"])
    ads_prev = ads_period_summary(ads["campaigns"], dates["previous_start"], dates["previous_end"])
    ads_yoy = ads_period_summary(ads["campaigns"], dates["yoy_start"], dates["yoy_end"])

    channel_summary = summarize_channels(
        ga4["channel_recent"], ga4["channel_previous"], ga4["channel_yoy"]
    )
    campaigns_recent = campaign_table(ads["campaigns"], dates["recent_start"], dates["recent_end"])
    search_terms_recent = search_term_table(ads["search_terms"])
    landing_enriched = enrich_landing_pages(
        ga4["landing"],
        seo_snapshot["pages"],  # type: ignore[arg-type]
        seo_snapshot["inlink_count"],  # type: ignore[arg-type]
    )
    seo_counts, seo_details = seo_issue_summary(seo_snapshot)
    keyword_themes, missing_keyword_themes = keyword_signals(
        search_terms_recent, seo_snapshot["pages"]  # type: ignore[arg-type]
    )
    recommendations = build_recommendations(
        ga4_recent,
        ga4_prev,
        ads_recent,
        ads_prev,
        seo_counts,
        campaigns_recent,
        search_terms_recent,
        missing_keyword_themes,
    )
    next_run_checks = build_next_run_checks(
        ga4_recent,
        ads_recent,
        seo_counts,
        campaigns_recent,
        search_terms_recent,
    )
    figures = build_figures(
        ga4["daily"],
        ads["campaigns"],
        campaigns_recent,
        search_terms_recent,
        landing_enriched,
        seo_counts,
        seo_details,
        dates,
    )
    html_report = build_html(
        generated_at=datetime.now(),
        dates=dates,
        ga4_recent=ga4_recent,
        ga4_prev=ga4_prev,
        ga4_yoy=ga4_yoy,
        ads_recent=ads_recent,
        ads_prev=ads_prev,
        ads_yoy=ads_yoy,
        channel_summary=channel_summary,
        campaigns_recent=campaigns_recent,
        search_terms_recent=search_terms_recent,
        landing_enriched=landing_enriched,
        keyword_themes=keyword_themes,
        seo_counts=seo_counts,
        seo_details=seo_details,
        seo_snapshot=seo_snapshot,
        figures=figures,
        recommendations=recommendations,
        next_run_checks=next_run_checks,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_report, encoding="utf-8")
    print(f"Wrote report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
