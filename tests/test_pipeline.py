"""Offline tests for the data pipeline. Run: python3 -m unittest discover tests"""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch  # noqa: E402

# Trimmed copy of a real data.gov.sg v2 PSI response (28 Sep 2026, 11pm and 10pm).
SAMPLE = {
    "code": 0,
    "data": {
        "regionMetadata": [],
        "items": [
            {"timestamp": "2026-09-28T23:00:00+08:00", "readings": {
                "psi_twenty_four_hourly": {"north": 79, "west": 107, "south": 111, "east": 98, "central": 117},
                "pm25_twenty_four_hourly": {"north": 37, "west": 61, "south": 65, "east": 54, "central": 71}}},
            {"timestamp": "2026-09-28T22:00:00+08:00", "readings": {
                "psi_twenty_four_hourly": {"west": 104, "north": 77, "south": 108, "central": 112, "east": 93},
                "pm25_twenty_four_hourly": {"north": 35, "central": 66, "east": 49, "south": 62, "west": 58}}},
            {"timestamp": "2026-09-28T21:00:00+08:00", "readings": {"psi_twenty_four_hourly": {"north": 75}}},
        ],
    },
    "errorMsg": "",
}

import datetime as dt
# Weather reports carry only day/hour/minute (UTC); build them around "now" so the month is unambiguous.
_T0 = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)).replace(minute=0, second=0, microsecond=0)
def _z(t): return t.strftime("%d%H%MZ")
METAR = "\n".join([
    f"METAR WSSS {_z(_T0 + dt.timedelta(hours=1))} 24006KT 210V270 1500 +TSRA HZ FEW008 FEW014CB SCT016TCU 24/23 Q1013",
    f"SPECI WSSS {_z(_T0 + dt.timedelta(minutes=37))} 16013KT 0800 +TSRA HZ FEW008 25/24 Q1013",
    f"METAR WSSS {_z(_T0 + dt.timedelta(minutes=30))} 16012KT 3000 -TSRA HZ FEW014 FEW016CB SCT017TCU 26/23 Q1013",
    f"METAR WSSS {_z(_T0)} 33006KT 300V360 2000 HZ FEW014 SCT017TCU FEW018CB 30/25 Q1013",
])
_KEY0 = (_T0 + dt.timedelta(hours=8)).strftime("%Y-%m-%dT%H")
_KEY1 = (_T0 + dt.timedelta(hours=9)).strftime("%Y-%m-%dT%H")


class FetchParsing(unittest.TestCase):
    def test_psi_lines_use_region_order_and_sgt_hour(self):
        lines = fetch.psi_items_to_lines(SAMPLE)
        self.assertEqual(lines, [
            "2026-09-28T23|79,111,98,107,117|37,65,54,61,71",
            "2026-09-28T22|77,108,93,104,112|35,62,49,58,66",
        ])  # incomplete 9pm item is skipped


class Merge(unittest.TestCase):
    def run_merge(self, data, *args):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "merge.py"), str(data), *args],
                       check=True, capture_output=True)
        return json.loads(data.read_text())

    def test_merge_psi_metar_and_no_change_keeps_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            data, psi, met = tmp / "data.json", tmp / "psi.txt", tmp / "metar.txt"
            psi.write_text("\n".join(fetch.psi_items_to_lines(SAMPLE)))
            met.write_text(METAR)
            d = self.run_merge(data, "--psi", str(psi), "--metar", str(met))
            self.assertEqual(d["latest"], "2026-09-28T23")
            self.assertEqual(d["psi"]["2026-09-28T23"], [[79, 111, 98, 107, 117], [37, 65, 54, 61, 71]])
            # first hour: dry at :00, light thundery rain at :30 -> the :30 report is folded into the hour
            self.assertEqual(d["wx"][_KEY0][5], 1)
            self.assertEqual(d["wx"][_KEY0][6], 1)
            # next hour: heavy thunderstorm rain, visibility 1500 m; SPECI reports are ignored
            self.assertEqual(d["wx"][_KEY1][5], 3)
            self.assertEqual(d["wx"][_KEY1][4], 1500)
            first = d["updated"]
            d2 = self.run_merge(data, "--psi", str(psi))
            self.assertEqual(d2["updated"], first)  # nothing new, so the timestamp stays put


class Build(unittest.TestCase):
    def test_built_page_is_a_full_document(self):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True, capture_output=True)
        html = (ROOT / "public" / "index.html").read_text()
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("<title>Haze Check SG</title>", html)
        self.assertNotIn("/*SHAPES*/", html)
        self.assertIn('fetch("data.json"', html)


if __name__ == "__main__":
    unittest.main()
