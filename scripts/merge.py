#!/usr/bin/env python3
"""Merge new haze readings into data.json for the Singapore Haze Replay page.

Usage:
  python3 merge.py data.json [--psi FILE] [--metar FILE] [--nea FILE] [--keep-days N]

--psi   lines "YYYY-MM-DDTHH|n,s,e,w,c|n,s,e,w,c"
        (24-hr PSI, then 24-hr PM2.5; order north,south,east,west,central; SGT hours)
--metar raw Changi (WSSS) METAR lines, e.g. "METAR WSSS 291630Z 06005KT 5000 HZ ... 29/25 Q1013"
--nea   JSON list of NEA update entries (same shape as data.json "nea"); replaces entries with same date+kind
"""
import json, re, math, sys, argparse, datetime as dt

ap = argparse.ArgumentParser()
ap.add_argument("data"); ap.add_argument("--psi"); ap.add_argument("--metar"); ap.add_argument("--nea")
ap.add_argument("--keep-days", type=int, default=0)
a = ap.parse_args()

try:
    D = json.load(open(a.data))
except FileNotFoundError:
    D = {}
D.setdefault("psi", {}); D.setdefault("wx", {}); D.setdefault("nea", [])
_before = json.dumps([D["psi"], D["wx"], D["nea"]], sort_keys=True)

if a.psi:
    n = 0
    for line in open(a.psi):
        line = line.strip()
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2})\|([\d,]+)\|([\d,]+)", line)
        if not m: continue
        p = [int(x) for x in m.group(2).split(",")]; q = [int(x) for x in m.group(3).split(",")]
        if len(p) == 5 and len(q) == 5:
            D["psi"][m.group(1)] = [p, q]; n += 1
    print("psi hours merged:", n)

if a.metar:
    obs = {}
    for line in open(a.metar):
        tok = line.split()
        if tok[:2] in (["METAR", "WSSS"], ["SPECI", "WSSS"]):
            if tok[0] == "SPECI": continue
            tok = tok[2:]
        if not tok or not re.fullmatch(r"\d{6}Z", tok[0]): continue
        if tok[1] == "COR": tok = [tok[0]] + tok[2:]
        day, hh, mm = int(tok[0][:2]), int(tok[0][2:4]), int(tok[0][4:6])
        now = dt.datetime.utcnow()
        y, mo = now.year, now.month
        if day > now.day + 1:  # report from the previous month
            mo -= 1
            if mo == 0: mo, y = 12, y - 1
        t = dt.datetime(y, mo, day, hh, mm) + dt.timedelta(hours=8)
        mw = re.match(r"(VRB|\d{3})(\d{2})(G\d{2})?KT", tok[1])
        if not mw: continue
        ws = int(mw.group(2)); wd = None if (mw.group(1) == "VRB" or ws == 0) else int(mw.group(1))
        vis = None
        for x in tok[2:5]:
            if re.fullmatch(r"\d{4}", x): vis = int(x); break
        T = dew = pres = None
        for x in tok:
            m2 = re.fullmatch(r"(M?\d{2})/(M?\d{2})", x)
            if m2: T, dew = int(m2.group(1).replace("M", "-")), int(m2.group(2).replace("M", "-"))
            if re.fullmatch(r"Q\d{4}", x): pres = int(x[1:])
        if T is None: continue
        rain = ts = 0
        for x in tok:
            if re.fullmatch(r"[-+]?(TS|SH)?RA|[-+]?TS", x):
                if "TS" in x: ts = 1
                if "RA" in x: rain = max(rain, 3 if x.startswith("+") else 1 if x.startswith("-") else 2)
        rh = round(100 * math.exp(17.625 * dew / (243.04 + dew)) / math.exp(17.625 * T / (243.04 + T)))
        obs[t] = [wd, round(ws * 1.852), T, rh, vis, rain, ts, pres, int("HZ" in tok)]
    n = 0
    for t in sorted(obs):
        if t.minute: continue
        r = list(obs[t]); nxt = obs.get(t + dt.timedelta(minutes=30))
        if nxt: r[5] = max(r[5], nxt[5]); r[6] = max(r[6], nxt[6])
        D["wx"][t.strftime("%Y-%m-%dT%H")] = r; n += 1
    print("weather hours merged:", n)

if a.nea:
    new = json.load(open(a.nea))
    if isinstance(new, dict): new = [new]
    keys = {(e["d"], e["kind"]) for e in new}
    D["nea"] = [e for e in D["nea"] if (e["d"], e["kind"]) not in keys] + new
    D["nea"].sort(key=lambda e: (e["d"], e["kind"] != "notice"))
    print("nea entries merged:", len(new))

if a.keep_days and D["psi"]:
    last = max(D["psi"]); cut = (dt.datetime.strptime(last, "%Y-%m-%dT%H") - dt.timedelta(days=a.keep_days)).strftime("%Y-%m-%dT%H")
    D["psi"] = {k: v for k, v in D["psi"].items() if k >= cut}
    D["wx"] = {k: v for k, v in D["wx"].items() if k >= cut}
    D["nea"] = [e for e in D["nea"] if e["d"] >= cut[:10]]

D["psi"] = dict(sorted(D["psi"].items())); D["wx"] = dict(sorted(D["wx"].items()))
if json.dumps([D["psi"], D["wx"], D["nea"]], sort_keys=True) != _before or "updated" not in D:
    D["updated"] = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
D["latest"] = max(D["psi"]) if D["psi"] else None
json.dump(D, open(a.data, "w"), ensure_ascii=False, separators=(",", ":"))
print("latest PSI hour:", D["latest"], "| hours:", len(D["psi"]), "| weather hours:", len(D["wx"]), "| NEA entries:", len(D["nea"]))
