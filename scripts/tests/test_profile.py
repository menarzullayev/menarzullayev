import json
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import profile_data as pd  # noqa: E402
import profile_render as pr  # noqa: E402

FACTS = json.loads((ROOT / "data" / "facts.json").read_text(encoding="utf-8"))
DATA = json.loads((ROOT / "data" / "profile-data.json").read_text(encoding="utf-8"))


def lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Render(unittest.TestCase):
    def setUp(self):
        self.images = pr.render_all(FACTS, DATA)

    def test_eight_valid_xml_files(self):
        self.assertEqual(len(self.images), 8)
        for name, svg in self.images.items():
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"), name)
            self.assertEqual(root.get("width"), "830", name)

    def test_nothing_external_or_executable(self):
        for name, svg in self.images.items():
            low = svg.lower()
            self.assertNotIn("<script", low, name)
            self.assertNotIn("href=", low, name)
            self.assertNotIn("@import", low, name)
            self.assertEqual(low.count("http"), low.count("http://www.w3.org/2000/svg"), name)
            self.assertIn("@font-face", svg, name)
            self.assertLess(len(svg), 60_000, name)

    def test_reduced_motion_is_respected(self):
        for name, svg in self.images.items():
            self.assertIn("prefers-reduced-motion", svg, name)

    def test_text_contrast_meets_aa(self):
        for theme, p in pr.PALETTES.items():
            for fg in ("text", "bright", "mut", "amber", "red"):
                for bg in ("bg", "panel"):
                    self.assertGreaterEqual(ratio(p[fg], p[bg]), 4.5, f"{theme}: {fg} on {bg}")

    def test_contrast_harness_rejects_weak_pairs(self):
        self.assertLess(ratio("#808080", "#888888"), 4.5)
        self.assertGreater(ratio("#000000", "#ffffff"), 20)

    def test_hub_labels_are_readable_on_their_fill(self):
        for theme, p in pr.PALETTES.items():
            for fill in (p["text"], p["amber"], p["bright"], p["red"]):
                self.assertGreaterEqual(ratio(p["hub"], fill), 4.5, f"{theme}: hub label on {fill}")

    def test_unsupported_characters_are_replaced(self):
        self.assertEqual(pr.clean("ok · ж"), "ok · ?")
        self.assertEqual(pr.esc("<b>&"), "&lt;b&gt;&amp;")

    def test_long_text_is_clipped_with_ellipsis(self):
        self.assertEqual(pr.clip("short", 40), "short")
        long = "feat(notifications): part 2 emitters (student left, quiz given)"
        out = pr.clip(long, 40)
        self.assertLessEqual(len(out), 40)
        self.assertTrue(out.endswith("…"))

    def test_hostile_commit_message_cannot_break_xml(self):
        data = json.loads(json.dumps(DATA))
        data["commits"][0]["msg"] = '"><script>alert(1)</script>&‮'
        for svg in pr.render_all(FACTS, data).values():
            ET.fromstring(svg)
            self.assertNotIn("<script", svg.lower())

    def test_ci_failure_is_drawn_as_fail(self):
        self.assertIn("FAIL", self.images["stats-dark.svg"])
        data = json.loads(json.dumps(DATA))
        for row in data["ci"]:
            row["ok"] = True
        self.assertNotIn("FAIL", pr.render_all(FACTS, data)["stats-dark.svg"])


class Validate(unittest.TestCase):
    def test_missing_section_fails(self):
        for key in ("cf", "lc", "activity", "ci", "commits"):
            data = {k: v for k, v in DATA.items() if k != key}
            with self.assertRaises(ValueError):
                pr.validate(data)

    def test_implausible_values_fail(self):
        mutations = (lambda d: d["cf"].update(rating=0), lambda d: d["activity"].update(months=[]),
                     lambda d: d.update(ci=[]), lambda d: d["ci"][0].update(ok="yes"))
        for mutate in mutations:
            data = json.loads(json.dumps(DATA))
            mutate(data)
            with self.assertRaises(ValueError):
                pr.validate(data)


class Parsers(unittest.TestCase):
    def test_cf_ok_and_failure(self):
        info = {"status": "OK", "result": [{"rating": 2013, "maxRating": 2013, "rank": "candidate master"}]}
        rating = {"status": "OK", "result": [{"newRating": r} for r in range(1400, 1500, 10)]}
        got = pd.parse_cf(info, rating, "2026-11-22")
        self.assertEqual((got["rating"], got["contests"], len(got["history"])), (2013, 10, 10))
        with self.assertRaises(ValueError):
            pd.parse_cf({"status": "FAILED"}, rating, "2026-11-22")
        with self.assertRaises(ValueError):
            pd.parse_cf(info, {"status": "OK", "result": []}, "2026-11-22")

    def test_lc_null_ranking_fails(self):
        with self.assertRaises(ValueError):
            pd.parse_lc({"data": {"userContestRanking": None}}, "2026-11-22")
        ok = pd.parse_lc({"data": {"userContestRanking": {"rating": 2281.4, "topPercentage": 0.62}}}, "2026-11-22")
        self.assertEqual((ok["rating"], ok["top"]), (2281, "0.6%"))

    def test_activity_needs_twelve_months(self):
        def week(date, n):
            return {"contributionDays": [{"date": date, "contributionCount": n}]}

        def cal(weeks, total):
            return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": total, "weeks": weeks}}}}}

        full = cal([week(f"2026-{m:02d}-01", m) for m in range(1, 13)], 78)
        got = pd.parse_activity(full, "2026-11-22")
        self.assertEqual(len(got["months"]), 12)
        self.assertEqual(got["months"][0], ["J", 1])
        with self.assertRaises(ValueError):
            pd.parse_activity(cal([week("2026-01-01", 1)], 1), "2026-11-22")


class CiPick(unittest.TestCase):
    RUNS = [
        {"name": "Dependabot Updates", "event": "dynamic", "status": "completed", "conclusion": "failure", "created_at": "2026-11-21T05:00:00Z"},
        {"name": "CI", "event": "pull_request", "status": "completed", "conclusion": "failure", "created_at": "2026-11-21T04:00:00Z"},
        {"name": "CI", "event": "push", "status": "completed", "conclusion": "success", "created_at": "2026-11-14T20:00:00Z"},
        {"name": "Nightly", "event": "schedule", "status": "completed", "conclusion": "failure", "created_at": "2026-11-21T09:00:00Z"},
        {"name": "CI", "event": "push", "status": "in_progress", "conclusion": None, "created_at": "2026-11-22T01:00:00Z"},
    ]

    def test_dependabot_and_unfinished_runs_are_ignored(self):
        runs = [r for r in self.RUNS if r["event"] != "pull_request"]
        self.assertEqual(pd.pick_ci(runs, "CI"), {"ok": True, "asof": "2026-11-14"})

    def test_dependabot_workflow_never_counts_even_without_filter(self):
        only_dependabot = [self.RUNS[0]]
        self.assertIsNone(pd.pick_ci(only_dependabot, None))

    def test_named_workflow_filter(self):
        self.assertEqual(pd.pick_ci(self.RUNS, "Nightly"), {"ok": False, "asof": "2026-11-21"})
        self.assertIsNone(pd.pick_ci(self.RUNS, "Deploy"))


class StaleSafe(unittest.TestCase):
    def test_failure_keeps_previous_and_marks_stale(self):
        def boom():
            raise OSError("network down")

        value, err = pd.keep_or_fail("lc", boom, {"rating": 2281, "top": "0.6%", "asof": "2026-11-07", "stale": False})
        self.assertTrue(value["stale"])
        self.assertEqual(value["rating"], 2281)
        self.assertIn("network down", err)

    def test_failure_without_previous_is_fatal(self):
        def boom():
            raise OSError("network down")

        with self.assertRaises(RuntimeError):
            pd.keep_or_fail("lc", boom, None)

    def test_success_replaces_previous(self):
        value, err = pd.keep_or_fail("x", lambda: {"a": 1}, {"a": 0})
        self.assertEqual((value, err), ({"a": 1}, None))


if __name__ == "__main__":
    unittest.main()
