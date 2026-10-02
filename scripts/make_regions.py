#!/usr/bin/env python3
"""Regenerate src/regions.json: SVG outlines of NEA's five reporting regions.

You only need this if you want to change the map. It merges URA planning areas into
NEA's five regions (north, south, east, west, central) by nearest region centre and
projects them onto a 1000-unit-wide SVG canvas.

Usage:
  pip install shapely
  curl -L -o /tmp/planning-areas.geojson \
    https://raw.githubusercontent.com/yinshanyang/singapore/master/maps/2-planning-area.geojson
  python3 scripts/make_regions.py /tmp/planning-areas.geojson
"""
import json, sys, pathlib
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/planning-areas.geojson"
areas = json.load(open(src))

# NEA region label points (from the data.gov.sg PSI API regionMetadata)
CENTRES = {"central": (103.82, 1.35735), "east": (103.94, 1.35735), "north": (103.82, 1.41803),
           "south": (103.82, 1.29587), "west": (103.70, 1.35735)}
# Manual fixes where nearest-centre puts a town in a region people wouldn't expect
OVERRIDES = {"CLEMENTI": "west", "BUKIT PANJANG": "west"}

groups = {k: [] for k in CENTRES}
for f in areas["features"]:
    g = shape(f["geometry"]).buffer(0)
    c = g.centroid
    name = f["properties"]["name"]
    best = min(CENTRES, key=lambda k: (CENTRES[k][0] - c.x) ** 2 + (CENTRES[k][1] - c.y) ** 2)
    groups[OVERRIDES.get(name, best)].append(g)

LON0, LON1, LAT0, LAT1, W = 103.59, 104.10, 1.15, 1.48, 1000
H = (LAT1 - LAT0) * W / (LON1 - LON0)
P = lambda x, y: ((x - LON0) / (LON1 - LON0) * W, (LAT1 - y) / (LAT1 - LAT0) * H)

out = {}
for k, gs in groups.items():
    u = unary_union(gs).simplify(0.0006, preserve_topology=True)
    parts = []
    for poly in (u.geoms if hasattr(u, "geoms") else [u]):
        if poly.area < 2e-6:
            continue
        for ring in [poly.exterior, *poly.interiors]:
            parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (P(*c) for c in ring.coords)) + "Z")
    out[k] = "".join(parts)
out["labels"] = {k: [round(v, 1) for v in P(*CENTRES[k])] for k in CENTRES}
(ROOT / "src" / "regions.json").write_text(json.dumps(out))
print("wrote src/regions.json")
