#!/usr/bin/env python3
"""Fetch the latest air-quality readings and Changi weather, then merge them into public/data.json.

Sources
  - NEA 24-hr PSI and 24-hr PM2.5 by region: data.gov.sg real-time API
      https://api-open.data.gov.sg/v2/real-time/api/psi?date=YYYY-MM-DD
    An API key is optional. Set DATA_GOV_SG_API_KEY for higher rate limits.
  - Changi Airport (WSSS) weather reports (METAR): aviationweather.gov

Usage
  python3 scripts/fetch.py              # yesterday and today (SGT)
  python3 scripts/fetch.py --days 7     # the last 7 days
  python3 scripts/fetch.py --date 2026-09-29
"""
import argparse, datetime as dt, json, os, pathlib, subprocess, sys, tempfile, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SGT = dt.timezone(dt.timedelta(hours=8))
REGIONS = ["north", "south", "east", "west", "central"]
PSI_URL = "https://api-open.data.gov.sg/v2/real-time/api/psi"
METAR_URL = "https://aviationweather.gov/api/data/metar?ids=WSSS&hours={hours}&format=raw"
UA = {"User-Agent": "haze-check-sg/1.0"}


def get(url, headers=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # network hiccup or rate limit: back off and retry
            if i == tries - 1:
                raise
            print(f"  retrying after error: {e}", file=sys.stderr)
            time.sleep(3 * (i + 1))


def psi_items_to_lines(payload):
    """Convert one data.gov.sg PSI response into 'YYYY-MM-DDTHH|n,s,e,w,c|n,s,e,w,c' lines."""
    lines = []
    for item in payload.get("data", {}).get("items", []):
        r = item.get("readings", {})
        psi, pm = r.get("psi_twenty_four_hourly"), r.get("pm25_twenty_four_hourly")
        if not psi or not pm or any(k not in psi or k not in pm for k in REGIONS):
            continue
        ts = dt.datetime.fromisoformat(item["timestamp"]).astimezone(SGT)
        lines.append(f"{ts:%Y-%m-%dT%H}|" + ",".join(str(int(psi[k])) for k in REGIONS) + "|" +
                     ",".join(str(int(pm[k])) for k in REGIONS))
    return lines


def fetch_psi(date):
    headers = {"x-api-key": os.environ["DATA_GOV_SG_API_KEY"]} if os.environ.get("DATA_GOV_SG_API_KEY") else {}
    lines, token = [], None
    while True:
        q = {"date": date}
        if token:
            q["paginationToken"] = token
        payload = json.loads(get(f"{PSI_URL}?{urllib.parse.urlencode(q)}", headers))
        if payload.get("code", 0) != 0:
            raise RuntimeError(f"data.gov.sg error for {date}: {payload.get('errorMsg')}")
        lines += psi_items_to_lines(payload)
        token = payload.get("data", {}).get("paginationToken")
        if not token:
            return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="how many days back to fetch, including today")
    ap.add_argument("--date", help="fetch a single SGT date (YYYY-MM-DD)")
    ap.add_argument("--keep-days", type=int, default=21)
    a = ap.parse_args()

    today = dt.datetime.now(SGT).date()
    dates = [a.date] if a.date else [str(today - dt.timedelta(days=i)) for i in range(a.days - 1, -1, -1)]

    psi_lines = []
    for d in dates:
        try:
            got = fetch_psi(d)
            print(f"PSI {d}: {len(got)} hours")
            psi_lines += got
        except Exception as e:
            print(f"PSI {d}: failed ({e})", file=sys.stderr)

    metar = ""
    try:
        metar = get(METAR_URL.format(hours=min(168, 24 * len(dates) + 6)))
        print(f"METAR: {len([l for l in metar.splitlines() if l.strip()])} reports")
    except Exception as e:
        print(f"METAR: failed ({e})", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        args = [sys.executable, str(ROOT / "scripts" / "merge.py"), str(ROOT / "public" / "data.json"),
                "--keep-days", str(a.keep_days), "--nea", str(ROOT / "data" / "nea.json")]
        if psi_lines:
            p = pathlib.Path(tmp, "psi.txt"); p.write_text("\n".join(psi_lines)); args += ["--psi", str(p)]
        if metar.strip():
            m = pathlib.Path(tmp, "metar.txt"); m.write_text(metar); args += ["--metar", str(m)]
        subprocess.run(args, check=True)

    if not psi_lines:
        print("Warning: no PSI readings fetched; data.json only got weather/NEA updates.", file=sys.stderr)


if __name__ == "__main__":
    main()
