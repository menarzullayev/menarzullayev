# Data and tools

What the images on the profile show, where the numbers come from, and what happens when a source fails.

## Sources

| Shown | Source | Notes |
|---|---|---|
| Codeforces rating, rank, contest count, history | Codeforces public API (`user.info`, `user.rating`) | Last 12 contests are drawn; the count is all rated contests. |
| LeetCode contest rating and top percentage | LeetCode public GraphQL (`userContestRanking`) | If it cannot be fetched the last value is kept and shown with its date. |
| Public contributions, last 12 months | GitHub GraphQL contribution calendar, read with the repository's `GITHUB_TOKEN` | Only what is public. Private contributions are switched off on the account, so they are not counted. |
| CI status | GitHub Actions runs of the **default branch** | Dependabot runs and unfinished runs are ignored. A pull-request run never decides the status. |
| Latest commits | GitHub commits API of the public flagship repositories | One latest commit per repository, newest four shown. |
| Flagship counters | Git tree of each public repository (default branch) and the commit count | Rules below. |

## What the flagship counters count

| Counter | Rule |
|---|---|
| commits | Total commits on the default branch (includes bot commits). |
| test files | Files named `test_*.py`, `*_test.py`, `*.test.{ts,tsx,js,jsx}` or `*.spec.{ts,tsx,js,jsx}`. This counts **files by name**, not test functions or coverage. |
| decision records | Markdown files inside a folder named `decisions`, `adr` or `adrs`, excluding `README.md`, `index.md` and `template.md`. |
| markdown files | Used instead of decision records when a repository has none (project-alpha). All `.md` files. |
| workflows | Files in `.github/workflows/` ending in `.yml` or `.yaml`. |

Anything under `node_modules` is skipped. If GitHub truncates a tree the counters are not drawn (the build fails) instead of showing a wrong number.

## What is stated by hand

Some facts are not measured by the build and live in `data/facts.json` with their date:

- the number of camera devices that were live in a 7-day window (about 1,950, counted on 2026-11-06 from the fleet's request logs; approved for publication by the owner);
- the verification study result (36 of 36 injected errors caught, hypothesis not supported), which is reproduced from the public `agent-verification-study` repository;
- ICPC participation years.

## Failure handling

A source that cannot be reached keeps its previous value, marked as stale, and the build prints a warning. A source with no previous value stops the build, so a half-empty image is never committed. Missing or implausible data (a rating of 0, fewer than 12 months, an empty CI list) is rejected by `validate()` in `scripts/profile_render.py`.

## Why numbers can differ from what GitHub shows when you are signed in

The profile page shows contributions that depend on the viewer's access: organisation repositories behind single sign-on are hidden until the viewer signs in to that organisation. The images use the public view, which is also what anonymous visitors see.

## Privacy and fonts

Private repositories are not read, counted or named. Projects that are private appear on the project map only as generic labels. The images embed a subset of JetBrains Mono (SIL Open Font License, text in `scripts/fonts/OFL.txt`) so nothing is loaded from another host.

## Reproduce

```
python scripts/build_profile.py            # needs GITHUB_TOKEN for the GitHub API
python scripts/build_profile.py --offline  # render from the committed data
python -m unittest discover -s scripts/tests
```

The daily workflow (`.github/workflows/profile.yml`) pins its actions to commit SHAs and uses only the repository's `GITHUB_TOKEN`.
