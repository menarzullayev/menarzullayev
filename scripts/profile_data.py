"""Collect the live numbers shown on the profile.

Every source is public. A failed source never invents a value: the previous
value is kept and marked stale; with no previous value the build fails.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

OWNER = "menarzullayev"
CF_HANDLE = "meNarzullayev"
LC_USER = "NarzullayevMe"
UA = "menarzullayev-profile-builder"
MONTH_LETTERS = "JFMAMJJASOND"


def http_json(url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 20):
    h = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https hosts only)
        return json.load(r)


def gh_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


# ---- parsers (pure, unit-tested) -------------------------------------------------
def parse_cf(info: dict, rating: dict, today: str) -> dict:
    if info.get("status") != "OK" or rating.get("status") != "OK":
        raise ValueError("codeforces api returned a failure status")
    user = info["result"][0]
    hist = [int(r["newRating"]) for r in rating["result"]]
    if "rating" not in user or not hist:
        raise ValueError("codeforces user has no rating")
    return {"rating": int(user["rating"]), "max": int(user["maxRating"]), "rank": str(user["rank"]),
            "contests": len(hist), "history": hist[-12:], "asof": today, "stale": False}


def parse_lc(payload: dict, today: str) -> dict:
    ranking = payload["data"]["userContestRanking"]
    if ranking is None:
        raise ValueError("leetcode has no contest ranking")
    top = float(ranking["topPercentage"])
    return {"rating": int(round(float(ranking["rating"]))), "top": f"{top:.1f}%", "asof": today, "stale": False}


def parse_activity(payload: dict, today: str) -> dict:
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    per_month: dict[str, int] = {}
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            ym = day["date"][:7]
            per_month[ym] = per_month.get(ym, 0) + int(day["contributionCount"])
    months = sorted(per_month)[-12:]
    if len(months) != 12:
        raise ValueError(f"need 12 months, got {len(months)}")
    return {"total": int(cal["totalContributions"]), "asof": today, "stale": False,
            "months": [[MONTH_LETTERS[int(m[5:7]) - 1], per_month[m]] for m in months]}


def pick_ci(runs: list[dict], workflow: str | None) -> dict | None:
    """Latest completed run on the default branch; Dependabot and dynamic runs never count."""
    best = None
    for r in runs:
        name = r.get("name") or ""
        if name.lower().startswith("dependabot") or r.get("event") == "dynamic":
            continue
        if r.get("status") != "completed" or not r.get("conclusion"):
            continue
        if workflow and name.lower() != workflow.lower():
            continue
        if best is None or r["created_at"] > best["created_at"]:
            best = r
    if best is None:
        return None
    return {"ok": best["conclusion"] == "success", "asof": best["created_at"][:10]}



# ---- evidence counters (counted from the public tree, never claimed) -----------------
TEST_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py|[^/]+\.(test|spec)\.(ts|tsx|js|jsx))$")
DECISION_RE = re.compile(r"(^|/)(decisions|adr|adrs)/[^/]+\.md$", re.IGNORECASE)
DECISION_SKIP = {"readme.md", "index.md", "template.md"}


def count_tree(paths: list[str]) -> dict:
    """Count files by name rule. Test files are counted by file name only (not test functions)."""
    tests = decisions = workflows = docs = 0
    for p in paths:
        if "/node_modules/" in f"/{p}":
            continue
        if TEST_RE.search(p):
            tests += 1
        if DECISION_RE.search(p) and p.rsplit("/", 1)[-1].lower() not in DECISION_SKIP:
            decisions += 1
        if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")):
            workflows += 1
        if p.lower().endswith(".md"):
            docs += 1
    return {"tests": tests, "decisions": decisions, "workflows": workflows, "docs": docs}


def parse_tree(payload: dict) -> list[str]:
    if payload.get("truncated"):
        raise ValueError("git tree was truncated; the counts would be wrong")
    return [n["path"] for n in payload["tree"] if n.get("type") == "blob"]


def parse_commit_count(payload: dict) -> int:
    repo = payload["data"]["repository"]
    if repo is None or repo["defaultBranchRef"] is None:
        raise ValueError("repository or default branch not found")
    return int(repo["defaultBranchRef"]["target"]["history"]["totalCount"])


# ---- fetchers ---------------------------------------------------------------------
def fetch_cf(today: str) -> dict:
    q = urllib.parse.quote(CF_HANDLE)
    return parse_cf(http_json(f"https://codeforces.com/api/user.info?handles={q}"),
                    http_json(f"https://codeforces.com/api/user.rating?handle={q}"), today)


def fetch_lc(today: str) -> dict:
    query = "query($u:String!){userContestRanking(username:$u){rating topPercentage}}"
    return parse_lc(http_json("https://leetcode.com/graphql", {"query": query, "variables": {"u": LC_USER}}), today)


def fetch_activity(today: str) -> dict:
    query = ("query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions "
             "weeks{contributionDays{date contributionCount}}}}}}")
    return parse_activity(http_json("https://api.github.com/graphql", {"query": query, "variables": {"l": OWNER}}, gh_headers()), today)


def fetch_ci(target: dict) -> dict:
    url = f"https://api.github.com/repos/{OWNER}/{target['repo']}/actions/runs?branch=main&status=completed&per_page=50"
    runs = http_json(url, headers=gh_headers())["workflow_runs"]
    found = pick_ci(runs, target.get("workflow"))
    if found is None:
        raise ValueError(f"no completed run for {target['label']}")
    return {"label": target["label"], **found}


def fetch_commits(repos: list[str], limit: int = 4) -> list[dict]:
    items = []
    for repo in repos:
        c = http_json(f"https://api.github.com/repos/{OWNER}/{repo}/commits?per_page=1", headers=gh_headers())[0]
        items.append({"date": c["commit"]["author"]["date"][:10], "repo": repo, "msg": c["commit"]["message"].split("\n")[0]})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]


def fetch_evidence(repo: str, today: str) -> dict:
    tree = http_json(f"https://api.github.com/repos/{OWNER}/{repo}/git/trees/HEAD?recursive=1", headers=gh_headers(), timeout=40)
    counts = count_tree(parse_tree(tree))
    q = "query($o:String!,$n:String!){repository(owner:$o,name:$n){defaultBranchRef{target{... on Commit{history{totalCount}}}}}}"
    commits = parse_commit_count(http_json("https://api.github.com/graphql", {"query": q, "variables": {"o": OWNER, "n": repo}}, gh_headers()))
    return {"repo": repo, "commits": commits, **counts, "asof": today, "stale": False}


# ---- stale-safe collection ----------------------------------------------------------
def keep_or_fail(name: str, fetch, previous):
    """Return (value, error). On failure keep `previous` marked stale; no previous: re-raise."""
    try:
        return fetch(), None
    except Exception as exc:  # noqa: BLE001 - any source failure is handled the same way
        if previous is None:
            raise RuntimeError(f"{name}: no data and no previous value ({exc})") from exc
        kept = json.loads(json.dumps(previous))
        if isinstance(kept, dict):
            kept["stale"] = True
        return kept, f"{name}: {exc}"


def collect(facts: dict, previous: dict, today: str | None = None) -> tuple[dict, list[str]]:
    today = today or dt.date.today().isoformat()
    warnings: list[str] = []

    def run(name, fetch, prev):
        value, err = keep_or_fail(name, fetch, prev)
        if err:
            warnings.append(err)
        return value

    data = {"generated": today}
    data["cf"] = run("codeforces", lambda: fetch_cf(today), previous.get("cf"))
    data["lc"] = run("leetcode", lambda: fetch_lc(today), previous.get("lc"))
    data["activity"] = run("activity", lambda: fetch_activity(today), previous.get("activity"))
    prev_ci = {row["label"]: row for row in previous.get("ci", [])}
    ci = []
    for target in facts["ci_targets"]:
        row = run(f"ci {target['label']}", lambda t=target: fetch_ci(t), prev_ci.get(target["label"]))
        ci.append(row)
    data["ci"] = ci
    prev_ev = {row["repo"]: row for row in previous.get("evidence", [])}
    data["evidence"] = [run(f"evidence {f['repo']}", lambda r=f["repo"]: fetch_evidence(r, today), prev_ev.get(f["repo"])) for f in facts.get("flagships", [])]
    data["commits"] = run("commits", lambda: fetch_commits(facts["commit_repos"]), previous.get("commits"))
    if isinstance(data["commits"], dict):  # defensive: stale marker only applies to dict values
        data["commits"] = previous.get("commits", [])
    return data, warnings
