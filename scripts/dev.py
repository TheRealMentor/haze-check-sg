#!/usr/bin/env python3
"""Dev server: serves public/ continuously, rebuilding automatically whenever
src/page.html, src/regions.json or data/nea.json change, so the server never
needs to be restarted by hand.

Usage: python3 scripts/dev.py [port]   # default port 8000
"""
import pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
WATCH = [ROOT / "src" / "page.html", ROOT / "src" / "regions.json", ROOT / "data" / "nea.json"]


def build():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


build()
server = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(ROOT / "public"), PORT])
print(f"\nServing http://localhost:{PORT} — watching for changes. Ctrl+C to stop.\n")

mtimes = {p: p.stat().st_mtime for p in WATCH if p.exists()}
try:
    while True:
        time.sleep(0.5)
        for p in WATCH:
            if not p.exists():
                continue
            m = p.stat().st_mtime
            if mtimes.get(p) != m:
                mtimes[p] = m
                print(f"Change detected in {p.name}, rebuilding…")
                try:
                    build()
                    print("Rebuilt.\n")
                except subprocess.CalledProcessError as e:
                    print(f"Build failed: {e}\n")
except KeyboardInterrupt:
    pass
finally:
    server.terminate()
    server.wait()
