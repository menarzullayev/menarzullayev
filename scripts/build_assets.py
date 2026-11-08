"""Generate the profile's SVG assets in light and dark variants (stdlib only).

    python scripts/build_assets.py   # rewrites ./assets/*.svg

Every claim in an asset is a verified fact from the repositories or the public APIs (see README.md).
Fonts are system fonts: SVGs shown through <img> on GitHub cannot load web fonts.
"""
import random
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "assets"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Segoe UI, system-ui, -apple-system, Arial, sans-serif"

THEMES = {
    "light": dict(bg="#F7F8FA", card="#FFFFFF", ink="#101828", mute="#3B455A", faint="#667085", line="#CBD2DC",
                  grid="#E6E9F0", blue="#2347D6", blue_tab_text="#FFFFFF", matrix_off="#C9CFDD", ok="#1B7F4B",
                  warn="#9A5B00"),
    "dark": dict(bg="#0D1117", card="#161B22", ink="#E6EDF3", mute="#B4BDC9", faint="#8B949E", line="#30363D",
                 grid="#171C24", blue="#6E8BFF", blue_tab_text="#0D1117", matrix_off="#2A3140", ok="#56D364",
                 warn="#E3B341"),
}
BALLOON = {"A": "#E4442F", "B": "#2B6CF0", "C": "#1FA463", "D": "#7A4DD8"}


def svg(w, h, label, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(label)}">\n{body}\n</svg>\n')


def banner(t):
    c = THEMES[t]
    body = f'''<defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{c['grid']}" stroke-width="1"/></pattern></defs>
<rect width="1200" height="300" fill="{c['bg']}"/><rect width="1200" height="300" fill="url(#g)"/>
<g stroke="{c['blue']}" stroke-width="3" fill="none" stroke-linecap="square"><path d="M96 92V64H124"/><path d="M1076 64H1104V92"/><path d="M96 208V236H124"/><path d="M1076 236H1104V208"/></g>
<rect x="96" y="38" width="96" height="24" fill="{c['blue']}"/><text x="106" y="55" font-family="{SANS}" font-size="13" font-weight="600" fill="{c['blue_tab_text']}">engineer</text>
<text x="600" y="150" text-anchor="middle" font-family="{SERIF}" font-size="66" font-weight="700" fill="{c['ink']}">Saidakbar Narzullayev</text>
<text x="600" y="198" text-anchor="middle" font-family="{SANS}" font-size="26" fill="{c['mute']}">Software Engineer · Edge AI and platforms</text>'''
    return svg(1200, 300, "Saidakbar Narzullayev, Software Engineer, Edge AI and platforms", body)


def divider(t):
    """A thin device-by-hour matrix strip: decoration only, it encodes no data."""
    c = THEMES[t]
    rnd = random.Random(7)
    cells = []
    cw, gap, cols, rows = 14, 4, 60, 2
    x0 = (1200 - (cols * (cw + gap) - gap)) // 2
    for col in range(cols):
        for row in range(rows):
            v = rnd.random()
            fill = c["blue"] if v > 0.18 else c["matrix_off"]
            op = 0.10 + 0.75 * (v if v > 0.18 else 0.6)
            cells.append(f'<rect x="{x0 + col * (cw + gap)}" y="{8 + row * (cw + gap)}" width="{cw}" height="{cw}" '
                         f'rx="3" fill="{fill}" fill-opacity="{op:.2f}"/>')
    return svg(1200, 44, "", "\n".join(cells).replace('role="img" aria-label=""', 'aria-hidden="true"'))


def badge(t, color, title, line1, line2):
    c = THEMES[t]
    # sizes are chosen for a 400-unit canvas shown at about 70% width: nothing below 14 units
    body = f'''<rect x="1" y="1" width="398" height="98" rx="8" fill="{c['card']}" stroke="{c['line']}" stroke-width="1.5"/>
<circle cx="38" cy="50" r="16" fill="{color}"/>
<text x="68" y="36" font-family="{SANS}" font-size="16" fill="{c['faint']}">{escape(title)}</text>
<text x="68" y="66" font-family="{SANS}" font-size="27" font-weight="700" fill="{c['ink']}">{escape(line1)}</text>
<text x="68" y="88" font-family="{SANS}" font-size="14.5" fill="{c['faint']}">{escape(line2)}</text>'''
    return svg(400, 100, f"{title}: {line1}. {line2}", body)


def card(t, letter, name, tagline, stack, evidence, status, status_kind):
    c = THEMES[t]
    sc = c["warn"] if status_kind == "dev" else c["ok"]
    body = f'''<rect x="1" y="1" width="398" height="248" rx="10" fill="{c['card']}" stroke="{c['line']}" stroke-width="1.5"/>
<circle cx="38" cy="44" r="17" fill="{BALLOON[letter]}"/>
<text x="38" y="50" text-anchor="middle" font-family="{SANS}" font-size="17" font-weight="700" fill="#FFFFFF">{letter}</text>
<text x="68" y="55" font-family="{SERIF}" font-size="30" font-weight="700" fill="{c['ink']}">{escape(name)}</text>
<text x="24" y="102" font-family="{SANS}" font-size="19" fill="{c['mute']}">{escape(tagline[0])}</text>
<text x="24" y="128" font-family="{SANS}" font-size="19" fill="{c['mute']}">{escape(tagline[1])}</text>
<text x="24" y="164" font-family="{SANS}" font-size="16" fill="{c['faint']}">{escape(stack)}</text>
<line x1="24" y1="182" x2="376" y2="182" stroke="{c['line']}"/>
<text x="24" y="208" font-family="{SANS}" font-size="16" fill="{c['ink']}">{escape(evidence)}</text>
<circle cx="31" cy="231" r="5.5" fill="{sc}"/>
<text x="44" y="237" font-family="{SANS}" font-size="16" font-weight="600" fill="{sc}">{escape(status)}</text>'''
    return svg(400, 250, f"{name}: {tagline[0]} {tagline[1]}. {status}.", body)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for t in THEMES:
        files = {
            f"banner-{t}.svg": banner(t),
            f"divider-{t}.svg": divider(t),
            f"badge-icpc-{t}.svg": badge(t, BALLOON["A"], "ICPC Northern Eurasia Finals", "3× participant", "2021, 2022, 2023"),
            f"badge-codeforces-{t}.svg": badge(t, BALLOON["B"], "Codeforces", "Candidate Master", "rating 2013 · checked 2026-11-07"),
            f"badge-leetcode-{t}.svg": badge(t, "#F2B800", "LeetCode", "Contest rating 2281", "top 0.6% · checked 2026-11-07"),
            f"card-rankwant-{t}.svg": card(t, "A", "RankWant", ("Competitive-programming", "platform for Uzbekistan"),
                                           "Django · Next.js · sandboxed judge", "872 commits, sole author · 6 CI workflows",
                                           "in development", "dev"),
            f"card-project-alpha-{t}.svg": card(t, "B", "Project Alpha", ("Documentation OS: idea to", "production-ready docs"),
                                                "10 stages · human approval", "evidence-backed claims · event history",
                                                "used in my projects", "ok"),
            f"card-hisobox-{t}.svg": card(t, "C", "HisoBox", ("Credit ledger for mahalla", "grocery shops"),
                                          "FastAPI · aiogram · React", "108 migrations · about 380 test files",
                                          "in development, not deployed", "dev"),
        }
        for name, text in files.items():
            (OUT / name).write_text(text, encoding="utf-8")
            made.append(name)
    print(f"{len(made)} assets -> {OUT}")


if __name__ == "__main__":
    main()
