#!/usr/bin/env python3
"""
Pull GA4 reports via the official Data API (no CSV export).

You do NOT need "Property access management" in GA4 if you use OAuth:
any role that can open reports (Viewer, Analyst, etc.) is enough.

You DO need a one-time Google Cloud setup — that is only for OAuth client
credentials / API enablement. The business does not need an existing Cloud account.

Auth (pick one)
---------------
1) OAuth (recommended if you cannot invite a service account)
   - Cloud Console → APIs & Services → enable "Google Analytics Data API"
   - OAuth consent screen (External, test users: add your Gmail if app is Testing)
   - Credentials → Create OAuth client ID → Desktop app → download JSON
   - Save as e.g. data/ga4/client_secret.json (gitignored) or outside the repo
   - Run:  poetry run python scripts/fetch_ga4.py --oauth-client path/to/client_secret.json
   - First run opens a browser; token is saved to data/ga4/oauth-token.json

2) Service account (needs someone with Editor on GA4 to add the SA email as Viewer)
   - Cloud → IAM → service account → key JSON
   - GA4 Admin → Property access management → Invite SA email as Viewer
   - Run:  poetry run python scripts/fetch_ga4.py --credentials path/to/key.json

Property ID: defaults to PuntaCanaYachts (override with GA4_PROPERTY_ID env).

Usage examples
----------------
  poetry run python scripts/fetch_ga4.py --oauth-client ~/secrets/ga4-oauth-client.json
  poetry run python scripts/fetch_ga4.py --credentials ~/secrets/ga4-sa.json
  poetry run python scripts/fetch_ga4.py --oauth-client ... --start 2025-01-01 --end 2026-04-08

Output: CSV to stdout (pipe to file) or --out path.csv

Reports (--report)
------------------
  traffic   — sessions / engagedSessions / keyEvents by sessionDefaultChannelGroup (default)
  events    — eventName with eventCount + keyEvents (see which events drive key events)
  daily     — date + sessions + engagedSessions + keyEvents (trend line)
  landing   — landingPagePlusQueryString + sessions + keyEvents (top paths; session-scoped)
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)

# PuntaCanaYachts — from GA4 Admin URL / property selector (not a secret)
DEFAULT_PROPERTY_NUMERIC_ID = "452157058"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OAUTH_TOKEN_PATH = REPO_ROOT / "data" / "ga4" / "oauth-token.json"


def property_resource_id() -> str:
    pid = os.environ.get("GA4_PROPERTY_ID", DEFAULT_PROPERTY_NUMERIC_ID).strip()
    if pid.startswith("properties/"):
        return pid
    return f"properties/{pid}"


def client_from_service_account(json_path: Path) -> BetaAnalyticsDataClient:
    creds = service_account.Credentials.from_service_account_file(
        str(json_path),
        scopes=SCOPES,
    )
    return BetaAnalyticsDataClient(credentials=creds)


def client_from_oauth(client_secrets: Path, token_path: Path) -> BetaAnalyticsDataClient:
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), list(SCOPES))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets),
                list(SCOPES),
            )
            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                open_browser=False,
                authorization_prompt_message="Open this URL in your browser to authorize GA4 access:\n{url}\n",
                success_message="GA4 authorization received. You can close this tab.",
            )
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return BetaAnalyticsDataClient(credentials=creds)


def run_traffic_by_channel(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: str,
    end: str,
) -> tuple[list[str], list[list[str]]]:
    """Sessions + key events by session default channel group."""
    resp = client.run_report(
        RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[
                Dimension(name="sessionDefaultChannelGroup"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="engagedSessions"),
                Metric(name="keyEvents"),
            ],
            limit=100,
        )
    )
    header = ["sessionDefaultChannelGroup", "sessions", "engagedSessions", "keyEvents"]
    rows: list[list[str]] = []
    for row in resp.rows:
        dims = [dv.value for dv in row.dimension_values]
        mets = [mv.value for mv in row.metric_values]
        rows.append(dims + mets)
    return header, rows


def _rows_from_response(resp, dim_names: list[str], met_names: list[str]) -> tuple[list[str], list[list[str]]]:
    header = dim_names + met_names
    rows: list[list[str]] = []
    for row in resp.rows:
        dims = [dv.value for dv in row.dimension_values]
        mets = [mv.value for mv in row.metric_values]
        rows.append(dims + mets)
    return header, rows


def run_events_by_name(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: str,
    end: str,
    limit: int,
) -> tuple[list[str], list[list[str]]]:
    resp = client.run_report(
        RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="eventName")],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="keyEvents"),
            ],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="keyEvents"),
                    desc=True,
                ),
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="eventCount"),
                    desc=True,
                ),
            ],
            limit=limit,
        )
    )
    return _rows_from_response(resp, ["eventName"], ["eventCount", "keyEvents"])


def run_daily_totals(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: str,
    end: str,
) -> tuple[list[str], list[list[str]]]:
    resp = client.run_report(
        RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="engagedSessions"),
                Metric(name="keyEvents"),
            ],
            order_bys=[
                OrderBy(
                    dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                    desc=False,
                )
            ],
            limit=5000,
        )
    )
    return _rows_from_response(resp, ["date"], ["sessions", "engagedSessions", "keyEvents"])


def run_landing_pages(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: str,
    end: str,
    limit: int,
) -> tuple[list[str], list[list[str]]]:
    resp = client.run_report(
        RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="landingPagePlusQueryString")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="keyEvents"),
            ],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="keyEvents"),
                    desc=True,
                )
            ],
            limit=limit,
        )
    )
    return _rows_from_response(resp, ["landingPagePlusQueryString"], ["sessions", "keyEvents"])


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch GA4 report via Data API")
    mx = p.add_mutually_exclusive_group(required=True)
    mx.add_argument(
        "--oauth-client",
        type=Path,
        metavar="CLIENT_SECRET.json",
        help="OAuth desktop client secret JSON from Google Cloud",
    )
    mx.add_argument(
        "--credentials",
        type=Path,
        metavar="SERVICE_ACCOUNT.json",
        help="Service account JSON key (SA must be Viewer on the GA4 property)",
    )
    p.add_argument(
        "--token",
        type=Path,
        default=DEFAULT_OAUTH_TOKEN_PATH,
        help=f"Where to store OAuth user token (default: {DEFAULT_OAUTH_TOKEN_PATH})",
    )
    p.add_argument("--start", default="2026-03-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default="2026-04-08", help="End date YYYY-MM-DD")
    p.add_argument(
        "--report",
        choices=("traffic", "events", "daily", "landing"),
        default="traffic",
        help="Which report to pull (default: traffic)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=250,
        metavar="N",
        help="Max rows for events and landing reports (default: 250)",
    )
    p.add_argument("--out", type=Path, help="Write CSV here instead of stdout")
    args = p.parse_args()

    prop = property_resource_id()

    if args.oauth_client:
        if not args.oauth_client.is_file():
            print(f"OAuth client file not found: {args.oauth_client}", file=sys.stderr)
            return 1
        client = client_from_oauth(args.oauth_client, args.token)
    else:
        if not args.credentials.is_file():
            print(f"Service account file not found: {args.credentials}", file=sys.stderr)
            return 1
        client = client_from_service_account(args.credentials)

    try:
        if args.report == "traffic":
            header, rows = run_traffic_by_channel(client, prop, args.start, args.end)
        elif args.report == "events":
            header, rows = run_events_by_name(
                client, prop, args.start, args.end, limit=max(1, args.limit)
            )
        elif args.report == "daily":
            header, rows = run_daily_totals(client, prop, args.start, args.end)
        else:
            header, rows = run_landing_pages(
                client, prop, args.start, args.end, limit=max(1, args.limit)
            )
    except Exception as e:
        print(f"GA4 API error: {e}", file=sys.stderr)
        return 1

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    text = buf.getvalue()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
