"""Render the profile README images (Terminal style, dark and light) from data.

Pure functions: no network, no clock. Output is plain SVG that GitHub shows
through <img>: inline CSS and SMIL only, fonts embedded as base64 WOFF, no
script, no external reference.
"""
from __future__ import annotations

import base64
import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
W = 830

# Characters the embedded font subset covers (see scripts/fonts/).
ALLOWED_EXTRA = "·×’“”—–…→▸"

PALETTES = {
    "dark": dict(bg="#050805", panel="#0a110a", line="#1f6b34", text="#46f072", bright="#8cffa8", amber="#ffb000",
                 mut="#2fa854", red="#ff5f56", scan="#000000", scan_o=".28", hub="#04210f"),
    "light": dict(bg="#f4f1e6", panel="#fbf9f0", line="#2f6b3f", text="#1d5c33", bright="#0f3d22", amber="#a15c00",
                  mut="#3f6b4c", red="#b42318", scan="#2f6b3f", scan_o=".03", hub="#ffffff"),
}
MODULES = ("hero", "worlds", "stats", "graph")
RANK_ABBR = {"newbie": "N", "pupil": "P", "specialist": "S", "expert": "E", "candidate master": "CM", "master": "M",
             "international master": "IM", "grandmaster": "GM", "international grandmaster": "IGM", "legendary grandmaster": "LGM"}


def clean(text: object) -> str:
    """Keep only characters the embedded font can draw; replace the rest with '?'."""
    out = []
    for ch in str(text):
        if 0x20 <= ord(ch) <= 0x7E or ch in ALLOWED_EXTRA:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def clip(text: object, limit: int) -> str:
    """Shorten with an ellipsis instead of cutting mid-word."""
    t = str(text).strip()
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def esc(text: object) -> str:
    return html.escape(clean(text), quote=True)


def _font_css() -> str:
    faces = []
    for weight in (400, 700):
        raw = (HERE / "fonts" / f"jbm-{weight}.woff").read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        faces.append(f"@font-face{{font-family:'JB';font-weight:{weight};src:url(data:font/woff;base64,{b64}) format('woff')}}")
    return "".join(faces)


class Theme:
    def __init__(self, name: str):
        self.name = name
        self.P = PALETTES[name]
        self.key = f"t{name[0]}"  # td / tl: unique ids per variant
        P = self.P
        k = self.key
        m = "JB,'JetBrains Mono',Consolas,monospace"
        self.css = (
            _font_css()
            + f".{k} text{{font-family:{m}}}"
            + f".{k} .eb{{font:400 11px {m};fill:{P['mut']};letter-spacing:.06em}}.{k} .nm{{font:700 36px {m};fill:{P['bright']}}}"
            + f".{k} .tg{{font:400 13px {m};fill:{P['text']}}}.{k} .lb{{font:700 12px {m};fill:{P['amber']}}}"
            + f".{k} .big{{font:700 36px {m};fill:{P['bright']}}}.{k} .sb{{font:400 12px {m};fill:{P['text']}}}"
            + f".{k} .nt{{font:400 11px {m};fill:{P['mut']}}}.{k} .mn{{font:400 10px {m};fill:{P['mut']}}}"
            + f".{k} .ok{{fill:{P['text']}}}.{k} .bad{{fill:{P['red']}}}"
            + f"@keyframes {k}r{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:none}}}}"
            + f"@keyframes {k}b{{50%{{opacity:0}}}}.{k} .cur{{animation:{k}b 1s steps(1) infinite}}"
            + f".{k} .pn{{opacity:0;animation:{k}r .9s cubic-bezier(.2,1.3,.4,1) both}}"
            + f"@media (prefers-reduced-motion:reduce){{.{k} *{{animation:none!important}}.{k} .pn{{opacity:1}}}}"
        )
        self.defs = (f'<pattern id="sc{k}" width="4" height="4" patternUnits="userSpaceOnUse">'
                     f'<rect width="4" height="1.4" fill="{P["scan"]}" opacity="{P["scan_o"]}"/></pattern>')
        self.accent = [P["text"], P["amber"], P["bright"], P["red"]]

    def wrap(self, h: int, body: str, label: str) -> str:
        return (f'<svg class="{self.key}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
                f'role="img" aria-label="{esc(label)}"><style>{self.css}</style><defs>{self.defs}</defs>{body}</svg>')

    def bg(self, h: int) -> str:
        return (f'<rect width="{W}" height="{h}" fill="{self.P["bg"]}"/>'
                f'<rect width="{W}" height="{h}" fill="url(#sc{self.key})"/>')

    def panel(self, x, y, w, h) -> str:
        P = self.P
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{P["panel"]}" stroke="{P["line"]}"/>'
                f'<rect x="{x+4}" y="{y+4}" width="{w-8}" height="{h-8}" fill="none" stroke="{P["line"]}"/>')

    def pn(self, i: int, inner: str) -> str:
        return f'<g class="pn" style="animation-delay:{0.15*i:.2f}s">{inner}</g>'


def T(cls: str, x, y, txt, extra: str = "") -> str:
    return f'<text class="{cls}" x="{x}" y="{y}" {extra}>{esc(txt)}</text>'


def validate(data: dict) -> None:
    """Fail loudly on missing or impossible values instead of drawing nonsense."""
    for key in ("cf", "lc", "activity", "ci", "commits"):
        if key not in data:
            raise ValueError(f"missing data section: {key}")
    cf = data["cf"]
    if not (0 < int(cf["rating"]) < 4500) or len(cf["history"]) < 2:
        raise ValueError("implausible Codeforces data")
    if int(data["activity"]["total"]) < 0 or len(data["activity"]["months"]) != 12:
        raise ValueError("activity needs 12 months and a non-negative total")
    if not data["ci"]:
        raise ValueError("ci list is empty")
    for row in data["ci"]:
        if not isinstance(row["ok"], bool):
            raise ValueError("ci status must be boolean")


def _fmt(template: str, data: dict) -> str:
    return template.format(cf_rating=data["cf"]["rating"], cf_rank=data["cf"]["rank"].title(),
                           lc_rating=data["lc"]["rating"], lc_top=data["lc"]["top"])


def hero(t: Theme, facts: dict, data: dict) -> str:
    h = 250
    P = t.P
    b = t.bg(h)
    b += T("lb", 32, 40, "$ whoami") + T("nm", 32, 84, facts["name"])
    b += f'<text class="cur" x="{32 + len(facts["name"]) * 21.6:.0f}" y="84" style="font:700 36px JB,monospace;fill:{P["bright"]}">_</text>'
    b += T("eb", 32, 110, "> " + facts["eyebrow"])
    b += T("tg", 32, 132, "> " + facts["tagline"][0]) + T("tg", 48, 150, facts["tagline"][1])
    chips = [facts["chips"][0], f"CF {data['cf']['rating']} · {RANK_ABBR.get(data['cf']['rank'].lower(), 'CF')}", f"LC {data['lc']['rating']} · top {data['lc']['top']}"]
    for i, c in enumerate(chips):
        b += T("lb", 590, 60 + i * 36, f"[ {c} ]")
    cols = t.accent[0], t.accent[1], t.accent[3]
    b += (f'<defs><linearGradient id="tg{t.key}" x1="0" x2="1"><stop offset="0" stop-color="{cols[0]}"/><stop offset=".5" stop-color="{cols[1]}"/><stop offset="1" stop-color="{cols[2]}"/></linearGradient></defs>'
          f'<g transform="translate(32 168)"><path d="M0 52 C70 52,90 14,170 20 S290 62,370 40 S500 6,590 24 S700 52,766 14" fill="none" stroke="url(#tg{t.key})" stroke-width="3" stroke-linecap="round" stroke-dasharray="900" stroke-dashoffset="900">'
          f'<animate attributeName="stroke-dashoffset" values="900;0;0;900" keyTimes="0;.45;.92;1" dur="8s" repeatCount="indefinite"/></path>')
    for xx, yy, lab, col, d in ((170, 20, "BUILD", cols[0], 0.1), (370, 40, "MEASURE", cols[1], 1.1), (590, 24, "VERIFY", cols[2], 2.1)):
        b += (f'<circle cx="{xx}" cy="{yy}" r="6" fill="{col}"><animate attributeName="r" values="0;6;6;0" keyTimes="0;.12;.9;1" dur="8s" begin="{d}s" repeatCount="indefinite"/></circle>'
              f'<text class="mn" x="{xx-18}" y="{yy-12}">{lab}</text>')
    b += "</g>"
    return t.wrap(h, b, f"{facts['name']}, {facts['eyebrow']}")


def worlds(t: Theme, facts: dict, data: dict) -> str:
    h = 200
    b = t.bg(h)
    for i, w_ in enumerate(facts["worlds"]):
        x, y, w, hh = 32 + i * 259, 14, 248, 172
        col = t.accent[i]
        inner = t.panel(x, y, w, hh)
        inner += f'<circle cx="{x+24}" cy="{y+28}" r="5" fill="{col}"/>' + T("lb", x + 38, y + 32, w_["label"])
        inner += T("big", x + 20, y + 84, _fmt(w_["big"], data)) + T("sb", x + 22, y + 108, _fmt(w_["sub"], data))
        for li, line in enumerate(w_["note"]):
            inner += T("nt", x + 22, y + 142 + li * 14, _fmt(line, data), 'style="font-size:10.5px"')
        if i == 0:
            for j, hg in enumerate((16, 24, 34, 28)):
                inner += f'<rect x="{x+w-92+j*18}" y="{y+98-hg}" width="12" height="{hg}" rx="2" fill="{col}" opacity="{.5+j*.15:.2f}"/>'
        elif i == 1:
            inner += f'<polyline points="{x+w-100},{y+40} {x+w-80},{y+32} {x+w-62},{y+36} {x+w-44},{y+24} {x+w-26},{y+28}" fill="none" stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>'
        else:
            cx_, cy_ = x + w - 40, y + 40
            inner += (f'<circle cx="{cx_}" cy="{cy_}" r="16" fill="none" stroke="{t.P["line"]}" stroke-opacity=".6" stroke-width="5"/>'
                      f'<circle cx="{cx_}" cy="{cy_}" r="16" fill="none" stroke="{col}" stroke-width="5" stroke-linecap="round" stroke-dasharray="80" stroke-dashoffset="22" transform="rotate(-90 {cx_} {cy_})"/>')
        b += t.pn(i, inner)
    return t.wrap(h, b, "Three areas of work: research, engineering, competitive programming")


def stats(t: Theme, facts: dict, data: dict) -> str:
    h = 360
    b = t.bg(h)
    act, cf, lc = data["activity"], data["cf"], data["lc"]
    p = t.panel(32, 14, 438, 160)
    p += T("lb", 52, 40, "PUBLIC ACTIVITY · LAST 12 MONTHS") + T("big", 52, 88, f"{act['total']:,}", 'style="font-size:30px"')
    p += T("nt", 52 + 19 * len(f"{act['total']:,}") + 14, 86, "public contributions (private not counted)")
    mx = max(2000, max(v for _, v in act["months"]))
    for j, (m, v) in enumerate(act["months"]):
        bh = max(2.0, v / mx * 52)
        p += f'<rect x="{52+j*33}" y="{150-bh:.1f}" width="22" height="{bh:.1f}" rx="3" fill="{t.accent[0]}" opacity="{.45+.5*v/mx:.2f}"/>' + T("mn", 52 + j * 33 + 5, 166, m)
    b += t.pn(0, p)
    hist = cf["history"][-12:]
    lo, hi = min(hist), max(hist)
    span = max(1, hi - lo)
    p = t.panel(488, 14, 310, 160)
    pts = " ".join(f"{510+j*22.5:.0f},{150-(v-lo)/span*44:.0f}" for j, v in enumerate(hist))
    p += T("lb", 508, 40, "CODEFORCES RATING") + T("big", 508, 82, str(cf["rating"]), 'style="font-size:32px"')
    p += T("nt", 508, 100, f"{cf['rank'].title()} · {cf['contests']} contests")
    p += f'<polyline points="{pts}" fill="none" stroke="{t.accent[1]}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
    p += f'<circle cx="{510+(len(hist)-1)*22.5:.0f}" cy="{150-(hist[-1]-lo)/span*44:.0f}" r="4.5" fill="{t.accent[1]}"/>'
    lc_note = f"LeetCode {lc['rating']} (top {lc['top']})" + (f" · as of {lc['asof']}" if lc.get("stale") else "")
    p += T("mn", 508, 166, "last 12 contests · " + lc_note)
    b += t.pn(1, p)
    p = t.panel(32, 188, 438, 158)
    p += T("lb", 52, 214, "CI · PUBLIC REPOS · DEFAULT BRANCH")
    for j, row in enumerate(data["ci"][:8]):
        col, y = j // 4, 238 + (j % 4) * 24
        x0 = 52 + col * 214
        p += f'<circle cx="{x0+5}" cy="{y-4}" r="5" class="{"ok" if row["ok"] else "bad"}"/>' + T("sb", x0 + 18, y, row["label"][:26], 'style="font-size:12px"')
        if not row["ok"]:
            p += T("mn bad", x0 + 162, y, "FAIL")
    b += t.pn(2, p)
    p = t.panel(488, 188, 310, 158)
    p += T("lb", 508, 214, "LATEST PUBLIC COMMITS")
    for j, c in enumerate(data["commits"][:4]):
        y = 238 + j * 24
        p += T("mn", 508, y, c["date"][5:]) + T("sb", 548, y, clip(c["repo"], 26), 'style="font-size:11px;font-weight:700"') + T("nt", 548, y + 11, clip(c["msg"], 40), 'style="font-size:9px"')
    b += t.pn(3, p)
    return t.wrap(h, b, f"Live public statistics: {act['total']} public contributions, Codeforces {cf['rating']}, CI status, latest commits")


def graph(t: Theme, facts: dict, data: dict) -> str:
    h = 510
    b = t.bg(h)
    cx, cy = 415, 255
    ln, lo = t.P["line"], ".6"
    b += T("lb", 32, 38, "EVERYTHING I BUILD, GROUPED BY WHAT IT PROVES")
    edges = nodes = labels = pulses = ""
    for idx, hub in enumerate(facts["graph"]["hubs"]):
        x, y, col = hub["x"], hub["y"], t.accent[idx]
        edges += (f'<path d="M{cx} {cy} L{x} {y}" stroke="{ln}" stroke-opacity="{lo}" stroke-width="1.6" fill="none" stroke-dasharray="5 6">'
                  f'<animate attributeName="stroke-dashoffset" values="0;-22" dur="1.8s" repeatCount="indefinite"/></path>')
        for lab, dx, dy, pub in hub["leaves"]:
            lx, ly = x + dx, y + dy
            edges += f'<path d="M{x} {y} L{lx} {ly}" stroke="{ln}" stroke-opacity="{lo}" stroke-width="1.2" fill="none"/>'
            if pub:
                nodes += f'<circle cx="{lx}" cy="{ly}" r="8" fill="{col}"/>'
            else:
                nodes += f'<circle cx="{lx}" cy="{ly}" r="8" fill="{t.P["bg"]}" stroke="{col}" stroke-width="2" stroke-dasharray="3 3"/>'
            labels += T("sb", lx, ly + (-14 if dy < 0 else 24), lab, 'text-anchor="middle" style="font-size:11.5px"')
        nodes += (f'<circle cx="{x}" cy="{y}" r="27" fill="{col}"><animate attributeName="r" values="27;30;27" dur="3.4s" begin="{idx*.6}s" repeatCount="indefinite"/></circle>'
                  + T("mn", x, y + 4, hub["name"], f'text-anchor="middle" style="font-weight:700;fill:{t.P["hub"]}"'))
        pulses += f'<circle r="4" fill="{t.P["text"]}"><animateMotion dur="3.4s" begin="-{idx*.85}s" repeatCount="indefinite" path="M{cx} {cy} L{x} {y}"/></circle>'
    b += f"<g>{edges}</g><g>{pulses}</g>"
    b += f'<circle cx="{cx}" cy="{cy}" r="42" fill="{t.P["bg"]}" stroke="{t.accent[0]}" stroke-width="2.5"/>' + T("mn", cx, cy + 4, "S.N.", f'text-anchor="middle" style="font-weight:700;fill:{t.accent[0]}"')
    b += nodes + labels
    b += (f'<g transform="translate(32 488)"><circle cx="6" cy="0" r="6" fill="{t.P["mut"]}"/>' + T("nt", 18, 4, "public repo")
          + f'<circle cx="124" cy="0" r="6" fill="none" stroke="{t.P["mut"]}" stroke-width="2" stroke-dasharray="3 3"/>' + T("nt", 136, 4, "private: described, not shown") + "</g>")
    return t.wrap(h, b, "Project map: edge AI, platforms, verification and competitive programming clusters")


RENDERERS = {"hero": hero, "worlds": worlds, "stats": stats, "graph": graph}


def render_all(facts: dict, data: dict) -> dict[str, str]:
    """Return {filename: svg} for every module in both themes."""
    validate(data)
    out = {}
    for name in ("dark", "light"):
        theme = Theme(name)
        for mod in MODULES:
            out[f"{mod}-{name}.svg"] = RENDERERS[mod](theme, facts, data)
    return out
