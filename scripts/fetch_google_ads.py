#!/usr/bin/env python3
r"""
Pull Google Ads reports via the Google Ads REST API (GAQL over HTTPS).

Uses the REST endpoint instead of gRPC so it works in WSL and proxied environments.
No gRPC; only `requests` + `google-auth` (already installed as a dependency of GA4 lib).

Setup (one-time)
-----------------
1. Google Cloud project → enable **Google Ads API**.
2. OAuth consent screen → scope **Google Ads API** (https://www.googleapis.com/auth/adwords).
   Use a Desktop OAuth client (same JSON as GA4 after adding the Ads scope, or a new one).
3. Developer token — only from a Manager account (MCC) → API Center.
   Apply for / copy the token there. Basic / test access is immediate.
4. Customer ID (10 digits, no dashes) — from the Punta Cana client account header.
5. Login Customer ID — your MCC manager id (10 digits, no dashes).

Environment variables (see .env.example)
-----------------------------------------
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CUSTOMER_ID          # client account, 10 digits
  GOOGLE_ADS_LOGIN_CUSTOMER_ID    # MCC manager id, 10 digits

Usage
-----
  poetry run python scripts/fetch_google_ads.py \
    --oauth-client data/ga4/client_secret_....json \
    --report campaigns \
    --start 2026-03-01 --end 2026-04-08 \
    --out data/google_ads/exports/campaigns.csv

  poetry run python scripts/fetch_google_ads.py \
    --oauth-client data/ga4/client_secret_....json \
    --report search_terms \
    --start 2026-03-01 --end 2026-04-08 \
    --out data/google_ads/exports/search_terms.csv

Reports
-------
  campaigns     — date, campaign id/name/status, impressions, clicks, cost, conversions
  search_terms  — date, campaign name, search term, impressions, clicks, cost, conversions

Cost is in account currency (micros / 1e6).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ("https://www.googleapis.com/auth/adwords",)
ADS_API_VERSION = "v23"   # v23 is the current stable version; older versions route to wrong backend
ADS_REST_BASE_TPL = "https://googleads.googleapis.com/{version}"
PAGE_SIZE = 1000

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OAUTH_TOKEN_PATH = REPO_ROOT / "data" / "google_ads" / "oauth-token.json"


# ── env / .env loading ────────────────────────────────────────────────────────

def _load_dotenv_simple() -> None:
    path = REPO_ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _norm_id(raw: str) -> str:
    return raw.replace("-", "").strip()


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_access_token(client_secret_path: Path, token_path: Path) -> str:
    """Return a valid access token, refreshing / re-authorising as needed."""
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), list(SCOPES))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), list(SCOPES)
            )
            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                open_browser=False,
                authorization_prompt_message="Open this URL in your browser to authorize Google Ads access:\n{url}\n",
                success_message="Google Ads authorization received. You can close this tab.",
            )
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    assert creds and creds.token
    return creds.token


# ── REST search (paginated) ───────────────────────────────────────────────────

def gaql_search(
    access_token: str,
    developer_token: str,
    customer_id: str,
    login_customer_id: str | None,
    query: str,
    max_rows: int = 0,
    api_version: str = ADS_API_VERSION,
    debug: bool = False,
) -> list[dict]:
    """Call the Google Ads REST search endpoint with pagination."""
    base = ADS_REST_BASE_TPL.format(version=api_version)
    url = f"{base}/customers/{customer_id}/googleAds:search"
    base_headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "Content-Type": "application/json",
    }

    if debug:
        print(f"[debug] POST {url}", file=sys.stderr)
        print(f"[debug] login-customer-id: {login_customer_id or '(not set)'}", file=sys.stderr)

    results: list[dict] = []
    page_token: str | None = None

    while True:
        body: dict = {"query": query}
        if page_token:
            body["pageToken"] = page_token

        headers = dict(base_headers)
        if login_customer_id:
            headers["login-customer-id"] = login_customer_id

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if (
            resp.status_code == 403
            and login_customer_id
            and "USER_PERMISSION_DENIED" in resp.text
        ):
            # Some directly accessible client accounts reject the MCC header.
            if debug:
                print(
                    "[debug] retrying without login-customer-id after USER_PERMISSION_DENIED",
                    file=sys.stderr,
                )
            headers = dict(base_headers)
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        if debug:
            print(f"[debug] status: {resp.status_code}", file=sys.stderr)
            if not resp.ok:
                print(f"[debug] response: {resp.text[:800]}", file=sys.stderr)
        if not resp.ok:
            raise RuntimeError(
                f"Google Ads API error {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        for row in data.get("results", []):
            results.append(row)
            if max_rows and len(results) >= max_rows:
                return results
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return results


# ── Report builders ───────────────────────────────────────────────────────────

def _safe(obj: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        if obj is None:
            return default
        obj = obj.get(k)  # type: ignore[assignment]
    if obj is None:
        return default
    return str(obj)


def _micros(obj: dict, *keys: str) -> str:
    val = _safe(obj, *keys, default="0")
    try:
        return str(int(val) / 1_000_000)
    except (ValueError, TypeError):
        return "0"


def build_campaigns(rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    header = [
        "date", "campaign_id", "campaign_name", "campaign_status",
        "advertising_channel_type", "impressions", "clicks",
        "cost", "conversions", "all_conversions",
    ]
    out: list[list[str]] = []
    for r in rows:
        out.append([
            _safe(r, "segments", "date"),
            _safe(r, "campaign", "id"),
            _safe(r, "campaign", "name"),
            _safe(r, "campaign", "status"),
            _safe(r, "campaign", "advertisingChannelType"),
            _safe(r, "metrics", "impressions", default="0"),
            _safe(r, "metrics", "clicks", default="0"),
            _micros(r, "metrics", "costMicros"),
            _safe(r, "metrics", "conversions", default="0"),
            _safe(r, "metrics", "allConversions", default="0"),
        ])
    return header, out


def build_search_terms(rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    header = [
        "date", "campaign_name", "search_term",
        "impressions", "clicks", "cost", "conversions",
    ]
    out: list[list[str]] = []
    for r in rows:
        out.append([
            _safe(r, "segments", "date"),
            _safe(r, "campaign", "name"),
            _safe(r, "searchTermView", "searchTerm"),
            _safe(r, "metrics", "impressions", default="0"),
            _safe(r, "metrics", "clicks", default="0"),
            _micros(r, "metrics", "costMicros"),
            _safe(r, "metrics", "conversions", default="0"),
        ])
    return header, out


# ── GAQL queries ──────────────────────────────────────────────────────────────

QUERY_CAMPAIGNS = """
    SELECT
      segments.date,
      campaign.id,
      campaign.name,
      campaign.status,
      campaign.advertising_channel_type,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros,
      metrics.conversions,
      metrics.all_conversions
    FROM campaign
    WHERE segments.date BETWEEN '{start}' AND '{end}'
    ORDER BY segments.date, campaign.id
"""

QUERY_SEARCH_TERMS = """
    SELECT
      segments.date,
      campaign.name,
      search_term_view.search_term,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros,
      metrics.conversions
    FROM search_term_view
    WHERE segments.date BETWEEN '{start}' AND '{end}'
    ORDER BY metrics.cost_micros DESC
"""


# ── Connectivity test ─────────────────────────────────────────────────────────

def test_connection(
    access_token: str,
    developer_token: str,
    customer_id: str,
    login_customer_id: str | None,
    api_version: str,
) -> None:
    """Diagnose auth/token/URL issues with two simple GET requests."""
    base = ADS_REST_BASE_TPL.format(version=api_version)
    url = f"{base}/customers/{customer_id}"

    def _get(label: str, hdrs: dict) -> None:
        print(f"\n[test:{label}] GET {url}", file=sys.stderr)
        resp = requests.get(url, headers=hdrs, timeout=15)
        print(f"[test:{label}] status: {resp.status_code}", file=sys.stderr)
        try:
            print(f"[test:{label}] body: {json.dumps(resp.json(), indent=2)[:800]}", file=sys.stderr)
        except Exception:
            print(f"[test:{label}] body (raw, first 300 chars): {resp.text[:300]}", file=sys.stderr)

    # 1. With full headers (normal operation)
    full_headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
    }
    if login_customer_id:
        full_headers["login-customer-id"] = login_customer_id
    _get("full-headers", full_headers)

    # 2. Without developer-token — a 401/403 JSON means URL is fine, token is the issue
    no_token_headers = {"Authorization": f"Bearer {access_token}"}
    _get("no-dev-token", no_token_headers)

    # 3. Without any auth — should be 401 JSON if URL resolves correctly
    _get("no-auth", {})

    # 4. POST to googleAds:search with full headers — the actual endpoint we need
    search_url = f"{base}/customers/{customer_id}/googleAds:search"
    print(f"\n[test:search-post] POST {search_url}", file=sys.stderr)
    resp = requests.post(
        search_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
            "login-customer-id": login_customer_id or "",
            "Content-Type": "application/json",
        },
        json={"query": "SELECT campaign.id FROM campaign LIMIT 1", "pageSize": 1},
        timeout=15,
    )
    print(f"[test:search-post] status: {resp.status_code}", file=sys.stderr)
    try:
        print(f"[test:search-post] body: {json.dumps(resp.json(), indent=2)[:800]}", file=sys.stderr)
    except Exception:
        print(f"[test:search-post] body (raw): {resp.text[:300]}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    _load_dotenv_simple()

    p = argparse.ArgumentParser(description="Fetch Google Ads reports via REST API")
    p.add_argument(
        "--oauth-client", type=Path, required=True, metavar="CLIENT_SECRET.json",
        help="OAuth Desktop client secret JSON",
    )
    p.add_argument(
        "--token", type=Path, default=DEFAULT_OAUTH_TOKEN_PATH,
        help=f"OAuth token storage (default: {DEFAULT_OAUTH_TOKEN_PATH})",
    )
    p.add_argument(
        "--developer-token",
        default=os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        help="Ads developer token (or GOOGLE_ADS_DEVELOPER_TOKEN in .env)",
    )
    p.add_argument(
        "--customer-id",
        default=os.environ.get("GOOGLE_ADS_CUSTOMER_ID", ""),
        help="Client account customer id, no dashes (or GOOGLE_ADS_CUSTOMER_ID)",
    )
    p.add_argument(
        "--login-customer-id",
        default=os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "") or None,
        help="MCC manager id when using manager access (GOOGLE_ADS_LOGIN_CUSTOMER_ID)",
    )
    p.add_argument(
        "--report", choices=("campaigns", "search_terms"), default="campaigns",
        help="Which report to pull",
    )
    p.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    p.add_argument(
        "--limit", type=int, default=10000, metavar="N",
        help="Max rows for search_terms (default: 10000)",
    )
    p.add_argument("--out", type=Path, help="Write CSV here (default: stdout)")
    p.add_argument(
        "--api-version", default=ADS_API_VERSION, metavar="vN",
        help=f"Google Ads API version (default: {ADS_API_VERSION})",
    )
    p.add_argument("--debug", action="store_true", help="Print request URL and status to stderr")
    p.add_argument("--test-connection", action="store_true",
                   help="Run a simple GET /customers/{id} to diagnose auth/token issues, then exit")
    args = p.parse_args()

    if not args.oauth_client.is_file():
        print(f"OAuth client file not found: {args.oauth_client}", file=sys.stderr)
        return 1
    if not args.developer_token.strip():
        print("Missing developer token (--developer-token or GOOGLE_ADS_DEVELOPER_TOKEN)", file=sys.stderr)
        return 1
    if not args.customer_id.strip():
        print("Missing customer id (--customer-id or GOOGLE_ADS_CUSTOMER_ID)", file=sys.stderr)
        return 1

    customer_id = _norm_id(args.customer_id)
    login_id = _norm_id(args.login_customer_id) if args.login_customer_id else None

    try:
        access_token = get_access_token(args.oauth_client, args.token)
    except Exception as e:
        print(f"OAuth error: {e}", file=sys.stderr)
        return 1

    if args.test_connection:
        test_connection(
            access_token, args.developer_token.strip(),
            customer_id, login_id, args.api_version,
        )
        return 0

    if not args.start or not args.end:
        print("--start and --end are required for report fetching", file=sys.stderr)
        return 1

    try:
        if args.report == "campaigns":
            query = QUERY_CAMPAIGNS.format(start=args.start, end=args.end)
            raw = gaql_search(
                access_token, args.developer_token.strip(),
                customer_id, login_id, query,
                api_version=args.api_version, debug=args.debug,
            )
            header, rows = build_campaigns(raw)
        else:
            query = QUERY_SEARCH_TERMS.format(start=args.start, end=args.end)
            raw = gaql_search(
                access_token, args.developer_token.strip(),
                customer_id, login_id, query,
                max_rows=max(1, args.limit),
                api_version=args.api_version, debug=args.debug,
            )
            header, rows = build_search_terms(raw)
    except RuntimeError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    text = buf.getvalue()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out} ({len(rows)} rows)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
