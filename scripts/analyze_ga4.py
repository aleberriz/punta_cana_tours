"""
GA4 export analyzer for PuntaCanaYachts SEO audit.

Usage:
    poetry run python scripts/analyze_ga4.py

Reads all CSVs from data/ga4/exports/ and prints a structured report.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

EXPORTS = Path(__file__).parent.parent / "data" / "ga4" / "exports"

REDESIGN_DATE = None  # detected automatically


def read_ga4_csv(path: Path) -> pd.DataFrame:
    """Strip GA4's comment header and return a DataFrame."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next(
        i for i, l in enumerate(lines) if l.strip() and not l.startswith("#")
    )
    from io import StringIO
    return pd.read_csv(StringIO("\n".join(lines[start:])))


def detect_redesign_date(df: pd.DataFrame) -> str | None:
    """
    Find the day when /charter/ URLs first overtook old-style URLs.
    Expects a DataFrame with columns: Landing page, Date + hour (YYYYMMDDHH), Sessions.
    """
    df = df.copy()
    col = "Date + hour (YYYYMMDDHH)"
    if col not in df.columns:
        return None
    df = df.dropna(subset=[col])
    df[col] = df[col].astype(str).str.strip()
    df = df[df[col].str.match(r"^\d{10}$")]
    df["day"] = df[col].str[:8]
    df["is_new"] = df["Landing page"].str.match(r"^/charters?(/|$)")
    df["Sessions"] = pd.to_numeric(df["Sessions"], errors="coerce").fillna(0)

    by_day = df.groupby(["day", "is_new"])["Sessions"].sum().unstack(fill_value=0)
    by_day.columns = ["old", "new"]

    crossover = by_day[by_day["new"] > by_day["old"]]
    if not crossover.empty:
        return crossover.index[0]
    return None


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    # ── 1. Redesign date ──────────────────────────────────────────
    hourly_file = EXPORTS / "Landing_page_Landing_page_jan_feb.csv"
    if hourly_file.exists():
        hourly = read_ga4_csv(hourly_file)
        global REDESIGN_DATE
        REDESIGN_DATE = detect_redesign_date(hourly)

        section("REDESIGN DATE DETECTION (Feb 15 – Mar 15, hourly data)")
        if REDESIGN_DATE:
            from datetime import datetime
            d = datetime.strptime(REDESIGN_DATE, "%Y%m%d")
            print(f"  Detected cutover: {d.strftime('%B %d, %Y')} "
                  f"(first day new /charter/ URLs > old URLs)\n")
        else:
            print("  Could not detect automatically.\n")

        # Show daily breakdown around the cutover
        col = "Date + hour (YYYYMMDDHH)"
        df = hourly.copy()
        df = df.dropna(subset=[col])
        df[col] = df[col].astype(str).str.strip()
        df = df[df[col].str.match(r"^\d{10}$")]
        df["day"] = df[col].str[:8]
        df["is_new"] = df["Landing page"].str.match(r"^/charters?(/|$)")
        df["Sessions"] = pd.to_numeric(df["Sessions"], errors="coerce").fillna(0)
        by_day = df.groupby(["day", "is_new"])["Sessions"].sum().unstack(fill_value=0)
        by_day.columns = ["old_urls", "new_charter_urls"]
        by_day["total"] = by_day.sum(axis=1)
        by_day.index = pd.to_datetime(by_day.index, format="%Y%m%d").strftime("%Y-%m-%d")

        print(f"  {'Date':<12} {'Old URLs':>10} {'New /charter/':>14} {'Total':>7}")
        print(f"  {'-'*46}")
        for day, row in by_day.iterrows():
            marker = " ← cutover" if REDESIGN_DATE and day == pd.to_datetime(
                REDESIGN_DATE, format="%Y%m%d").strftime("%Y-%m-%d") else ""
            print(f"  {day:<12} {int(row.old_urls):>10} {int(row.new_charter_urls):>14}"
                  f" {int(row.total):>7}{marker}")

    # ── 2. Channel performance Jan–Feb ────────────────────────────
    ch_file = EXPORTS / "Traffic_acquisition_Session_default_channel_group.csv"
    if ch_file.exists():
        section("CHANNEL PERFORMANCE  Jan 1 – Feb 28, 2026")
        ch = read_ga4_csv(ch_file)
        ch["Sessions"] = pd.to_numeric(ch["Sessions"], errors="coerce").fillna(0)
        ch["Key events"] = pd.to_numeric(ch["Key events"], errors="coerce").fillna(0)
        ch["conv_%"] = (ch["Key events"] / ch["Sessions"].replace(0, float("nan")) * 100).round(1)
        ch = ch.sort_values("Key events", ascending=False)

        print(f"\n  {'Channel':<22} {'Sessions':>9} {'Key events':>11} {'Conv %':>8}")
        print(f"  {'-'*54}")
        for _, row in ch.iterrows():
            print(f"  {row['Session default channel group']:<22} "
                  f"{int(row['Sessions']):>9} {int(row['Key events']):>11} "
                  f"{row['conv_%']:>7.1f}%")
        total_s = int(ch["Sessions"].sum())
        total_ke = int(ch["Key events"].sum())
        print(f"  {'TOTAL':<22} {total_s:>9} {total_ke:>11}")
        print(f"\n  ► Paid Search drove {ch[ch['Session default channel group']=='Paid Search']['Key events'].sum():.0f} "
              f"of {total_ke} key events ({ch[ch['Session default channel group']=='Paid Search']['Key events'].sum()/total_ke*100:.0f}% of all conversions).")

    # ── 3. Landing page shifts: old vs new URLs ───────────────────
    lp_file = EXPORTS / "Landing_page_Landing_page.csv"
    if lp_file.exists():
        section("LANDING PAGE SHIFT  (Jan–Feb vs March top 15 pages)")
        lp = read_ga4_csv(lp_file)

        # The file has two comparison blocks — split on blank rows
        lp["Sessions"] = pd.to_numeric(lp["Sessions"], errors="coerce").fillna(0)
        lp["Key events"] = pd.to_numeric(lp["Key events"], errors="coerce").fillna(0)

        # GA4 comparison exports repeat the column header; use "All Users" blocks
        # The file was exported with comparison so rows appear once each period
        # We label them by date range embedded in headers — simpler: half by index
        # Actually the CSV just has all rows; first N are Jan-Feb, second N are March
        # Detect split: look for repeated header row
        raw_lines = (EXPORTS / "Landing_page_Landing_page.csv").read_text(encoding="utf-8-sig").splitlines()
        header_indices = [i for i, l in enumerate(raw_lines)
                          if "Start date" in l or "End date" in l]

        periods = []
        for i, h in enumerate(header_indices):
            date_val = raw_lines[h].split(":")[-1].strip() if ":" in raw_lines[h] else ""
            periods.append(date_val)

        print(f"\n  Periods found: {periods}\n")

        # Split the dataframe at repeated column header
        from io import StringIO
        non_comment = [l for l in raw_lines if not l.startswith("#")]
        header_row_idx = [i for i, l in enumerate(non_comment) if l.startswith("Landing page,")]

        if len(header_row_idx) >= 2:
            period_a = pd.read_csv(StringIO("\n".join(non_comment[header_row_idx[0]:header_row_idx[1]])))
            period_b = pd.read_csv(StringIO("\n".join(non_comment[header_row_idx[1]:])))
        else:
            period_a = lp
            period_b = pd.DataFrame()

        for label, df in [("Jan–Feb (pre-redesign)", period_a), ("March (post-redesign)", period_b)]:
            if df.empty:
                continue
            df["Sessions"] = pd.to_numeric(df["Sessions"], errors="coerce").fillna(0)
            df["Key events"] = pd.to_numeric(df["Key events"], errors="coerce").fillna(0)
            top = df[df["Sessions"] > 0].sort_values("Sessions", ascending=False).head(15)
            print(f"  {label}")
            print(f"  {'Landing page':<42} {'Sessions':>9} {'Key events':>11}")
            print(f"  {'-'*65}")
            for _, row in top.iterrows():
                print(f"  {str(row['Landing page']):<42} {int(row['Sessions']):>9} "
                      f"{int(row['Key events']):>11}")
            print()

    # ── 4. Redirect audit summary ─────────────────────────────────
    section("REDIRECT / KEY EVENT ALERTS")
    print("""
  [!] Key events went to 0 in March across ALL channels and pages.
      → Likely cause: GTM tag not firing on new site templates.
      → Action: GTM Preview → trigger conversion tag manually on live site.

  [!] Paid Search drove 69% of all Jan-Feb key events (204/295) at 11% conv rate.
      → If Google Ads campaigns were paused/disrupted at launch, sales dip is
        explained by paid, NOT organic. Verify ad status in Google Ads console.

  [!] Redirect confirmed wrong:
        /romantic-cruise-for-two  →  /charter/sunset-cruise-punta-cana  (nginx)
      Should be:
        /romantic-cruise-for-two  →  /charter/romantic-cruise-for-two
      → One-line nginx fix.

  [!] 56 sessions from tagassistant.google.com in March = Ken's GTM testing.
      → Define internal traffic filter in GA4 (Admin → Data Streams).
    """)


if __name__ == "__main__":
    main()
