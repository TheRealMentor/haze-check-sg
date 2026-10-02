#!/usr/bin/env python3
"""Build public/index.html from src/page.html and merge data/nea.json into public/data.json.

Usage: python3 scripts/build.py
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
page = (ROOT / "src" / "page.html").read_text()
shapes = (ROOT / "src" / "regions.json").read_text()
page = page.replace("/*SHAPES*/", shapes)

# The template holds <title>, fonts, <style> and the theme script, then the page body.
split = page.index('<div class="wrap">')
head, body = page[:split], page[split:]

RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0}img{max-width:100%}[hidden]{display:none!important}")
doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Singapore's latest haze level with plain health advice, a region map, the past week and NEA's daily haze updates.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%23ec7b2d'/%3E%3Cpath d='M14 38h36M18 28h28M22 48h20' stroke='%23fff' stroke-width='5' stroke-linecap='round'/%3E%3C/svg%3E">
<style>{RESET}</style>
{head.strip()}
</head>
<body>
{body.strip()}
</body>
</html>
"""
(ROOT / "public").mkdir(exist_ok=True)
(ROOT / "public" / "index.html").write_text(doc)
print("wrote public/index.html")

# Keep the NEA summaries in public/data.json in sync with data/nea.json (the source of truth).
subprocess.run([sys.executable, str(ROOT / "scripts" / "merge.py"), str(ROOT / "public" / "data.json"),
                "--nea", str(ROOT / "data" / "nea.json")], check=True)
