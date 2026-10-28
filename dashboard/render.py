"""HTML and inline-SVG rendering for the dashboard. No JavaScript needed."""

import datetime as dt
import html
import math
import random

esc = html.escape
ET = dt.timezone(dt.timedelta(hours=-4))  # display times in US Eastern (regular season is EDT until early Nov)

CSS = """
:root{--bg:#f6f7f9;--surface:#fff;--ink:#12151a;--ink2:#4b525c;--ink3:#7a828d;--rule:#e2e5ea;--grid:#eceef2;
--a:#2a78d6;--a-fill:rgba(42,120,214,.14);--b:#eb6834;--b-fill:rgba(235,104,52,.14);--good:#1a7f3c;--bad:#c2410c;--mark:#b4bcc7;
--r0:#f3f6fa;--r1:#dbe8f8;--r2:#b7d3f6;--r3:#86b6ef;--r4:#5598e7;--r5:#2a78d6;--r6:#1c5cab;--r7:#104281;
--display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;--body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#111317;--surface:#1a1d22;--ink:#eef0f3;--ink2:#b9bfc8;--ink3:#8a919b;--rule:#2c3038;--grid:#252930;
--a:#3987e5;--a-fill:rgba(57,135,229,.2);--b:#d95926;--b-fill:rgba(217,89,38,.2);--good:#3fb26a;--bad:#ef7a4a;--mark:#5b636e;
--r0:#1f242c;--r1:#1b3150;--r2:#184f95;--r3:#1c5cab;--r4:#256abf;--r5:#3987e5;--r6:#6da7ec;--r7:#9ec5f4;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.5}
a{color:var(--a)}
.wrap{max-width:1120px;margin:0 auto;padding:24px max(16px,env(safe-area-inset-right)) 64px max(16px,env(safe-area-inset-left))}
header.site{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 24px;margin-bottom:8px}
.eyebrow{font:600 14px var(--display);letter-spacing:.1em;text-transform:uppercase;color:var(--ink3)}
h1{font:700 clamp(32px,6vw,48px)/1.05 var(--display);margin:4px 0}
h2{font:700 28px/1.1 var(--display);margin:0 0 4px;text-wrap:balance}
h3{font:600 20px/1.2 var(--display);margin:0 0 6px}
nav.toc{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 28px}
nav.toc a{font:600 14px var(--display);letter-spacing:.06em;text-transform:uppercase;text-decoration:none;color:var(--ink2);
 border:1px solid var(--rule);background:var(--surface);border-radius:999px;padding:6px 12px}
nav.toc a:hover{border-color:var(--ink3)}
section{margin-top:44px;scroll-margin-top:16px}
.lede{color:var(--ink2);max-width:72ch;margin:0 0 14px}
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:16px 18px}
.note{color:var(--ink3);font-size:14px;max-width:80ch;margin:10px 0 0}
.scroll{overflow-x:auto}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.tile .k{font-size:13px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.tile .v{font:700 28px/1.1 var(--display);font-variant-numeric:tabular-nums}
.tile .s{color:var(--ink2);font-size:14px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);text-align:left;font-weight:600;padding:8px 10px;border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--grid)}
tr:last-child td{border-bottom:0}
.n{text-align:right}
.team{font-weight:700}
.pos{color:var(--good);font-weight:700}.neg{color:var(--bad);font-weight:700}.muted{color:var(--ink3)}
.bar{height:10px;border-radius:5px;background:var(--a);display:inline-block;vertical-align:middle}
.barcell{width:38%;min-width:120px}
.track{background:var(--grid);border-radius:5px;height:10px;position:relative}
.track>span{position:absolute;inset:0 auto 0 0;border-radius:5px;background:var(--mark)}
.swap td.c{text-align:center;font-weight:700;min-width:38px;border:2px solid var(--surface);padding:6px 4px}
.swap td.self{outline:2.5px solid var(--ink);outline-offset:-3px}
.swap th.col{height:130px;vertical-align:bottom;padding:0}
.swap th.col div{transform:translate(14px,-4px) rotate(-50deg);transform-origin:bottom left;width:24px;white-space:nowrap;text-transform:none;letter-spacing:0;font-size:13px;color:var(--ink2)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:14px}
.wp-card{display:grid;gap:4px}
.wp-card .score{display:flex;justify-content:space-between;gap:12px;font-weight:700}
.dot-a{color:var(--a)}.dot-b{color:var(--b)}
svg{display:block;width:100%;height:auto}
svg text{font-family:var(--body);fill:var(--ink3);font-size:12px}
svg .lab{fill:var(--ink);font-weight:700;font-size:14px}
svg .sub{fill:var(--ink3);font-size:11.5px}
svg .lab,svg .sub{paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}
svg .gridl{stroke:var(--grid)}
svg .dot{fill:var(--mark);stroke:var(--surface);stroke-width:1.5}
svg .good{fill:var(--good)}svg .bad{fill:var(--bad)}
svg .ring-good{fill:none;stroke:var(--good);stroke-width:2.5}svg .ring-bad{fill:none;stroke:var(--bad);stroke-width:2.5}
svg .curve{fill:none;stroke:var(--ink3);stroke-width:2;stroke-dasharray:5 4}
svg .lead{stroke:var(--ink3);stroke-width:1}
.hl-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-bottom:8px}
.hl-bar label{font-weight:600}
.hl-bar select{font:inherit;padding:6px 10px;border:1px solid var(--rule);border-radius:8px;background:var(--surface);color:var(--ink);max-width:100%}
.hl-bar select:focus-visible{outline:2px solid var(--a);outline-offset:2px}
svg.hl-on .dot,svg.hl-on [class^="ring-"]{opacity:.15}
svg.hl-on .dot.sel{opacity:1;fill:var(--a)!important;stroke-width:2}
svg.hl-on [class^="ring-"].sel{opacity:1}
footer{margin-top:56px;color:var(--ink3);font-size:14px;border-top:1px solid var(--rule);padding-top:16px}
"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap">'


def page(title, body, desc=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{FONTS}<style>{CSS}</style></head>
<body><div class="wrap">{body}</div></body></html>"""


def pct_s(p):
    s = f"{p:.3f}"
    return s[1:] if s.startswith("0") else s


def fmt_record(r):
    return f"{r[0]}-{r[1]}" + (f"-{r[2]}" if r[2] else "")


def signed(v, digits=1):
    s = f"{abs(v):.{digits}f}"
    return ("+" if v > 0.05 else "−" if v < -0.05 else "") + s


# ---------------------------------------------------------------- tables
def allplay_table(rows, weeks):
    n = len(weeks)
    out = ['<div class="panel scroll"><table><thead><tr><th>#</th><th>Team</th><th class="n">All-play</th><th>Win %</th>'
           '<th class="n">Actual</th><th class="n">Luck</th><th class="n">PF</th><th class="n">PA</th></tr></thead><tbody>']
    for i, r in enumerate(rows, 1):
        luck = r["luck"]
        cls = "pos" if luck >= 0.5 else "neg" if luck <= -0.5 else "muted"
        out.append(f'<tr><td class="muted">{i}</td><td class="team">{esc(r["team"])}</td><td class="n team">{fmt_record(r["allplay"])}</td>'
                   f'<td style="white-space:nowrap">{pct_s(r["pct"])} <span class="bar" style="width:{r["pct"] * 90:.0f}px"></span></td>'
                   f'<td class="n">{fmt_record(r["record"])}</td><td class="n {cls}">{signed(luck)}</td>'
                   f'<td class="n">{r["pf"]:.1f}</td><td class="n muted">{r["pa"]:.1f}</td></tr>')
    out.append('</tbody></table></div>')
    out.append(f'<p class="note">All-play = every team’s weekly score played against every other team that week. '
               f'Luck = actual wins minus expected wins (all-play win % × {n} games): positive means luckier than their scores deserve.</p>')
    return "".join(out)


def swap_table(order, grid):
    k = len(order)
    out = ['<div class="panel scroll"><table class="swap"><thead><tr><th></th>']
    out += [f'<th class="col"><div>{esc(t)}</div></th>' for t in order]
    out.append('<th class="n">Avg</th></tr></thead><tbody>')
    for i, (t, row) in enumerate(zip(order, grid)):
        out.append(f'<tr><th style="text-transform:none;letter-spacing:0;font-size:14px;color:var(--ink)">{esc(t)}</th>')
        for j, v in enumerate(row):
            fg = "#fff" if v >= 5 else "var(--ink)"
            out.append(f'<td class="c{" self" if i == j else ""}" style="background:var(--r{min(v, 7)});color:{fg}" title="{esc(t)} with {esc(order[j])}’s schedule: {v} wins">{v}</td>')
        out.append(f'<td class="n team">{sum(row) / k:.1f}</td></tr>')
    diff = [sum(grid[i][j] for i in range(k) if i != j) / (k - 1) for j in range(k)]
    out.append('<tr><th style="font-size:12px">Schedule difficulty</th>' + "".join(f'<td class="n muted" style="text-align:center">{v:.1f}</td>' for v in diff) + '<td></td></tr>')
    out.append('</tbody></table></div><p class="note">Each row is a team’s own scores; each column is a schedule. Numbers are wins with that schedule; '
               'outlined cells are actual records. When a schedule would pit a team against itself, it plays the schedule’s owner that week. '
               'Schedule difficulty = average wins the other teams would get with it (lower is tougher).</p>')
    return "".join(out)


def bench_table(rows):
    mx = max(r["lost"] for r in rows) or 1
    out = ['<div class="panel scroll"><table><thead><tr><th>Team</th><th class="barcell">Points left on bench</th><th class="n"></th>'
           '<th>Cost</th><th>Biggest benching</th></tr></thead><tbody>']
    for r in rows:
        f = r["flips"]
        cost = f'<span class="neg">{len(f)} {"loss" if len(f) == 1 else "losses"}</span> <span class="muted">(Wk {", ".join(map(str, f))})</span>' if f else ""
        w = r["worst"]
        worst = f'{esc(w["player"])} <span class="muted">{w["pts"]:.1f} · Wk {w["week"]}</span>' if w else ""
        out.append(f'<tr><td class="team">{esc(r["team"])}</td><td class="barcell"><div class="track"><span style="width:{100 * r["lost"] / mx:.1f}%"></span></div></td>'
                   f'<td class="n team">{r["lost"]:.1f}</td><td style="white-space:nowrap">{cost}</td><td>{worst}</td></tr>')
    out.append('</tbody></table></div><p class="note">Best lineup = the highest-scoring legal lineup from that week’s roster, picked after the games. '
               'Cost = losses that lineup would have turned into wins.</p>')
    return "".join(out)


def trade_cards(trades):
    if not trades:
        return '<div class="panel muted">No trades yet.</div>'
    cards = []
    for i, t in enumerate(trades, 1):
        w = t["weeks"]
        span = "no games yet" if not w else (f"Week {w[0]}" if len(w) == 1 else f"Weeks {w[0]}–{w[-1]}")
        lead = max(t["sides"], key=lambda s: s["total"])
        margin = lead["total"] - min(s["total"] for s in t["sides"])
        mx = max(max((g["since"] for s in t["sides"] for g in s["got"]), default=1), 1)
        head = f'{esc(lead["team"])} ahead by {margin:.1f}' if w else "Too early to call"
        body = [f'<div class="panel"><div class="eyebrow">Trade {i} · {t["when"].astimezone(ET):%b %-d} · counts {span}</div><h3>{head}</h3>']
        for s in t["sides"]:
            body.append(f'<div style="margin-top:10px;font-weight:700">{esc(s["team"])} got</div><table>')
            for g in s["got"]:
                body.append(f'<tr><td>{esc(g["player"])} <span class="muted">{g["pos"] or ""}</span></td><td class="barcell"><div class="track">'
                            f'<span style="width:{100 * g["since"] / mx:.1f}%;background:{"var(--good)" if s is lead and w else "var(--mark)"}"></span></div></td>'
                            f'<td class="n team">{g["since"]:.1f}</td></tr>')
            for p in s["picks"]:
                body.append(f'<tr><td colspan="3" class="muted">{esc(p)}</td></tr>')
            body.append(f'</table><div class="n muted" style="font-size:14px">Total <b style="color:var(--ink)">{s["total"]:.1f}</b></div>')
        body.append('</div>')
        cards.append("".join(body))
    return ('<div class="grid2">' + "".join(cards) + '</div><p class="note">Points each player has scored since the trade, wherever they played, '
            'counting from the first week whose games started after it.</p>')


def waiver_wars(claims, per_team, teams):
    if not claims:
        return '<div class="panel muted">No contested waiver claims yet.</div>'
    most = max(claims, key=lambda c: (len(c["losers"]), c["since"]))
    big = max(claims, key=lambda c: c["since"])
    ties = [c for c in claims if c["losers"][0]["bid"] == c["win_bid"]]
    def bids(c):
        return ", ".join(f'{esc(x["team"])} ${x["bid"]}' for x in c["losers"])
    tiles = ('<div class="tiles">'
             f'<div class="panel tile"><div class="k">Most contested</div><div class="v">{len(most["losers"]) + 1} teams</div>'
             f'<div class="s">{esc(most["player"])}, Week {most["week"]}: {esc(most["winner"])} won at ${most["win_bid"]}</div></div>'
             f'<div class="panel tile"><div class="k">Biggest one that got away</div><div class="v">{big["since"]:.1f} pts</div>'
             f'<div class="s">{esc(big["player"])}: {bids(big)} lost to {esc(big["winner"])} ${big["win_bid"]}</div></div>'
             f'<div class="panel tile"><div class="k">Lost on a tie</div><div class="v">{len(ties)}</div>'
             f'<div class="s">{"Same bid as the winner, lost on waiver order" + (": " + ", ".join(esc(c["player"]) for c in ties[:3]) if ties else "")}</div></div>'
             '</div>')
    rows = "".join(f'<tr><td class="muted">{c["week"]}</td><td><b>{esc(c["player"])}</b> <span class="muted">{c["pos"] or ""}</span></td>'
                   f'<td>{esc(c["winner"])} <b>${c["win_bid"]}</b></td><td class="muted">{bids(c)}</td>'
                   f'<td class="n team">{c["since"]:.1f}</td></tr>' for c in claims)
    claims_tbl = ('<h3 style="margin-top:18px">Every contested claim</h3><div class="panel scroll"><table><thead><tr><th>Wk</th><th>Player</th>'
                  f'<th>Won by</th><th>Lost by</th><th class="n">Pts since</th></tr></thead><tbody>{rows}</tbody></table></div>')
    mx = max((v["missed"] for v in per_team.values()), default=1) or 1
    trs = []
    for t in sorted(teams, key=lambda t: -per_team.get(t, {}).get("missed", 0)):
        v = per_team.get(t)
        if not v:
            trs.append(f'<tr><td class="team">{esc(t)}</td><td class="barcell"><div class="track"></div></td><td class="n muted">0</td><td class="n muted">0.0</td><td class="muted">Never outbid</td></tr>')
            continue
        b = v["best"]
        trs.append(f'<tr><td class="team">{esc(t)}</td><td class="barcell"><div class="track"><span style="width:{100 * v["missed"] / mx:.1f}%"></span></div></td>'
                   f'<td class="n">{v["lost"]}</td><td class="n team">{v["missed"]:.1f}</td><td>{esc(b["player"])} <span class="muted">{b["since"]:.1f} pts</span></td></tr>')
    team_tbl = ('<h3 style="margin-top:18px">Points that got away, by team</h3><div class="panel scroll"><table><thead><tr><th>Team</th>'
                '<th class="barcell">Points missed</th><th class="n">Lost claims</th><th class="n">Pts</th><th>Biggest miss</th></tr></thead>'
                f'<tbody>{"".join(trs)}</tbody></table></div>')
    return (tiles + team_tbl + claims_tbl +
            '<p class="note">A contested claim is a waiver run where more than one team put in a claim for the same player. '
            '“Points since” and “points missed” are everything that player has scored from that week on, wherever he played, '
            'so they’re the most the losing teams could have gotten, not what they’d actually have started. '
            'Sleeper doesn’t share trade offers that weren’t accepted, so only waivers show up here.</p>')


def recap_tiles(rc):
    c, b = rc["closest"], rc["blowout"]
    def g(x):
        w, l = (x["a"], x["b"]) if x["pa"] >= x["pb"] else (x["b"], x["a"])
        return f'{esc(w)} {max(x["pa"], x["pb"]):.2f} – {min(x["pa"], x["pb"]):.2f} {esc(l)}'
    return ('<div class="tiles">'
            f'<div class="panel tile"><div class="k">High score</div><div class="v">{rc["high"][1]:.2f}</div><div class="s">{esc(rc["high"][0])}</div></div>'
            f'<div class="panel tile"><div class="k">Low score</div><div class="v">{rc["low"][1]:.2f}</div><div class="s">{esc(rc["low"][0])}</div></div>'
            f'<div class="panel tile"><div class="k">Closest game</div><div class="v">{c["margin"]:.2f}</div><div class="s">{g(c)}</div></div>'
            f'<div class="panel tile"><div class="k">Biggest blowout</div><div class="v">{b["margin"]:.2f}</div><div class="s">{g(b)}</div></div>'
            '</div>')


# ---------------------------------------------------------------- scatter with automatic labels
def _text_w(s, size):
    return len(s) * size * 0.56


def scatter(points, *, xmax, ymax, ystep, xlabel, ylabel, xfmt=str, xreverse=False, xticks=None, rounds=None,
            curve=None, quadrants=(), groups=None, W=1040, H=560):
    """points: dicts with x, y, r, cls ('dot'|'good'|'bad'), label, sub, ring ('good'|'bad'|None), title.

    With groups (a list of names), each point may carry group (an index into it) plus glabel/gsub. Every group gets
    its own hidden label layer naming all of its points, which highlight_box() shows when that group is picked."""
    l, r, t, b = 64, 24, 16, 56
    X = (lambda v: l + (W - l - r) * (xmax - v) / xmax) if xreverse else (lambda v: l + (W - l - r) * v / xmax)
    Y = lambda v: t + (H - t - b) * (1 - v / ymax)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(ylabel)} by {esc(xlabel)}">']
    for v in range(0, int(ymax) + 1, ystep):
        s.append(f'<line class="gridl" x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text x="{l - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    if rounds:
        per, n = rounds
        for i in range(n):
            s.append(f'<text x="{X(i * per + per / 2 + .5):.1f}" y="{H - b + 20}" text-anchor="middle">R{i + 1}</text>')
            if i:
                s.append(f'<line class="gridl" stroke-dasharray="2 4" x1="{X(i * per + .5):.1f}" x2="{X(i * per + .5):.1f}" y1="{t}" y2="{H - b}"/>')
    for v in (xticks or []):
        s.append(f'<text x="{X(v):.1f}" y="{H - b + 20}" text-anchor="middle">{xfmt(v)}</text>')
    s.append(f'<text x="{(l + W - r) / 2}" y="{H - 8}" text-anchor="middle" style="fill:var(--ink2);font-weight:600;font-size:13px">{esc(xlabel)}</text>')
    s.append(f'<text x="14" y="{(t + H - b) / 2}" text-anchor="middle" transform="rotate(-90 14 {(t + H - b) / 2})" style="fill:var(--ink2);font-weight:600;font-size:13px">{esc(ylabel)}</text>')
    for qx, qy, txt, cls in quadrants:
        s.append(f'<text x="{X(qx):.1f}" y="{Y(qy):.1f}" text-anchor="middle" class="{cls}" style="font-weight:700;letter-spacing:2px;opacity:.7">{txt}</text>')
    if curve:
        s.append('<path class="curve" d="' + " ".join(f'{"M" if i == 0 else "L"}{X(x):.1f},{Y(y):.1f}' for i, (x, y) in enumerate(curve)) + '"/>')
    random.seed(7)
    placed = []  # label boxes (x0, y0, x1, y1)
    dots = []
    for p in sorted(points, key=lambda p: p.get("z", 0)):
        cx, cy = X(p["x"]) + p.get("jitter", 0), Y(p["y"])
        p["_c"] = (cx, cy)
        dots.append((cx, cy, p["r"]))
        fill = {"dot": "", "a": ' style="fill:var(--a)"', "good": ' style="fill:var(--good)"', "bad": ' style="fill:var(--bad)"'}[p.get("cls", "dot")]
        g = f' data-g="{p["group"]}"' if p.get("group") is not None else ""
        s.append(f'<circle class="dot" cx="{cx:.1f}" cy="{cy:.1f}" r="{p["r"]:.1f}"{fill}{g}><title>{esc(p.get("title", ""))}</title></circle>')
        if p.get("ring"):
            s.append(f'<circle class="ring-{p["ring"]}" cx="{cx:.1f}" cy="{cy:.1f}" r="{p["r"] + 3:.1f}"{g}/>')

    def hits(box, pts):
        x0, y0, x1, y1 = box
        return sum(1 for cx, cy, rr in pts if x0 - rr < cx < x1 + rr and y0 - rr < cy < y1 + rr)

    def layer(labeled, marked, lab_key="label", sub_key="sub"):
        placed, out = [], []
        for p in sorted(labeled, key=lambda p: -p.get("priority", 0)):
            out += place(p, p[lab_key], p.get(sub_key, ""), placed, marked)
        return out

    def collides(box, placed, marked):
        x0, y0, x1, y1 = box
        if x0 < l or x1 > W - r or y0 < t or y1 > H - b:
            return True
        if any(not (x1 < bx[0] or x0 > bx[2] or y1 < bx[1] or y0 > bx[3]) for bx in placed):
            return True
        return hits(box, marked) > 0

    def place(p, lab, sub, placed, marked):
        cx, cy = p["_c"]
        w = max(_text_w(lab, 14), _text_w(sub, 11.5)) + 4
        h = 30 if sub else 16
        best = None
        spots = sorted(((dy, push) for dy in range(-6, 7) for push in (0, 40, 80, 120)), key=lambda c: abs(c[0]) + c[1] / 40)
        for k, (dy, push) in enumerate(spots):
            for dx, an in ((1, "start"), (-1, "end")):
                lx = cx + dx * (p["r"] + 6 + push)
                ly = cy + 5 + dy * 20
                x0 = lx if an == "start" else lx - w
                box = (x0, ly - 13, x0 + w, ly - 13 + h)
                if collides(box, placed, marked):
                    continue
                score = k * 2 + hits(box, dots)
                if not best or score < best[0]:
                    best = (score, lx, ly, an, box)
        if not best:
            return []
        _, lx, ly, an, box = best
        placed.append(box)
        out = []
        if abs(ly - 5 - cy) > 14 or abs(lx - cx) > p["r"] + 12:
            out.append(f'<line class="lead" x1="{cx:.1f}" y1="{cy:.1f}" x2="{lx:.1f}" y2="{ly - 5:.1f}"/>')
        color = f' style="fill:var(--{p["lab_color"]})"' if p.get("lab_color") else ""
        out.append(f'<text class="lab" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{an}"{color}>{esc(lab)}</text>')
        if sub:
            out.append(f'<text class="sub" x="{lx:.1f}" y="{ly + 15:.1f}" text-anchor="{an}">{esc(sub)}</text>')
        return out

    marked = [p["_c"] + (p["r"] + 4,) for p in points if p.get("label") or p.get("ring") or p.get("cls", "dot") != "dot"]
    s.append('<g class="lay" data-lay="all">' + "".join(layer([p for p in points if p.get("label")], marked)) + '</g>')
    for gi, _ in enumerate(groups or []):
        mine = [p for p in points if p.get("group") == gi]
        s.append(f'<g class="lay" data-lay="{gi}" style="display:none">'
                 + "".join(layer(mine, [p["_c"] + (p["r"] + 4,) for p in mine], "glabel", "gsub")) + '</g>')
    s.append('</svg>')
    return "".join(s)


# ---------------------------------------------------------------- win probability small multiples
def winprob_card(m):
    full = m["series"]
    S = [full[0]]
    for prev, p, nxt in zip(full, full[1:], full[2:] + [None]):  # thin: keep visible moves and both ends of every quiet gap
        if nxt is None or abs(p[1] - S[-1][1]) >= 0.004 or p[0] - prev[0] > 45 * 60 or nxt[0] - p[0] > 45 * 60:
            S.append(p)
    if len(S) < 2:
        return ""
    W, H, l, r, t, b = 520, 170, 34, 34, 8, 22
    gap_s, seg_gap = 45 * 60, 10
    segs = []
    for i, p in enumerate(S):
        if not segs or p[0] - S[i - 1][0] > gap_s:
            segs.append([p[0], p[0], i])
        segs[-1][1] = p[0]
    dur = lambda g: max(g[1] - g[0], 1800)
    total = sum(dur(g) for g in segs)
    plot_w = W - l - r - seg_gap * (len(segs) - 1)
    off, x0s = l, []
    for g in segs:
        x0s.append(off)
        off += plot_w * dur(g) / total + seg_gap

    def X(ts):
        for g, x0 in zip(segs, x0s):
            if ts <= g[1] + 1:
                return x0 + plot_w * dur(g) / total * (ts - g[0]) / dur(g)
        return W - r
    Y = lambda p: t + (H - t - b) * (1 - p)
    cid = f"m{m['matchup_id']}"
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Win probability for {esc(m["home"]["team"])} vs {esc(m["away"]["team"])}">',
         f'<defs><clipPath id="{cid}a"><rect x="0" y="0" width="{W}" height="{Y(.5):.1f}"/></clipPath>'
         f'<clipPath id="{cid}b"><rect x="0" y="{Y(.5):.1f}" width="{W}" height="{H}"/></clipPath></defs>']
    for p in (0, .5, 1):
        dash = ' stroke-dasharray="3 3"' if p == .5 else ""
        s.append(f'<line class="gridl" x1="{l}" x2="{W - r}" y1="{Y(p):.1f}" y2="{Y(p):.1f}"{dash}/>'
                 + f'<text x="{l - 6}" y="{Y(p) + 4:.1f}" text-anchor="end">{int(p * 100)}%</text>')
    last_day, last_x = None, -99
    for k, g in enumerate(segs):
        end = segs[k + 1][2] if k + 1 < len(segs) else len(S)
        pts = S[g[2]:end]
        d = f"M{X(pts[0][0]):.1f},{Y(pts[0][1]):.1f}"
        for a, c in zip(pts, pts[1:]):
            d += f"L{X(c[0]):.1f},{Y(a[1]):.1f}L{X(c[0]):.1f},{Y(c[1]):.1f}"
        area = f"M{X(pts[0][0]):.1f},{Y(.5):.1f}L" + d[1:] + f"L{X(pts[-1][0]):.1f},{Y(.5):.1f}Z"
        s.append(f'<path d="{area}" style="fill:var(--a-fill)" clip-path="url(#{cid}a)"/><path d="{area}" style="fill:var(--b-fill)" clip-path="url(#{cid}b)"/>'
                 f'<path d="{d}" style="fill:none;stroke:var(--a);stroke-width:2" clip-path="url(#{cid}a)"/><path d="{d}" style="fill:none;stroke:var(--b);stroke-width:2" clip-path="url(#{cid}b)"/>')
        day = dt.datetime.fromtimestamp(g[0], ET).strftime("%a")
        if k == 0 or (day != last_day and x0s[k] - last_x > 34):
            s.append(f'<text x="{x0s[k]:.1f}" y="{H - 6}">{day}</text>')
            last_day, last_x = day, x0s[k]
    for k in range(1, len(segs)):
        a, c = S[segs[k][2] - 1], S[segs[k][2]]
        s.append(f'<line class="lead" stroke-dasharray="2 3" x1="{X(a[0]):.1f}" y1="{Y(a[1]):.1f}" x2="{X(c[0]):.1f}" y2="{Y(c[1]):.1f}"/>')
    last = S[-1]
    s.append(f'<circle cx="{X(last[0]):.1f}" cy="{Y(last[1]):.1f}" r="4" style="fill:var({"--a" if last[1] >= .5 else "--b"})"/>')
    peak_a, peak_b = max(S, key=lambda p: p[1]), min(S, key=lambda p: p[1])
    s.append('</svg>')
    h, a = m["home"], m["away"]
    final = not m.get("pending")
    stat = (f'Peak: <span class="dot-a">{esc(h["team"])} {peak_a[1]:.0%}</span> · <span class="dot-b">{esc(a["team"])} {1 - peak_b[1]:.0%}</span>'
            if final else f'Live: {esc(h["team"])} {last[1]:.0%} to win')
    return (f'<div class="panel wp-card"><div class="score"><span class="dot-a">{esc(h["team"])} {last[2]:.2f}</span>'
            f'<span class="dot-b" style="text-align:right">{last[3]:.2f} {esc(a["team"])}</span></div>{"".join(s)}'
            f'<div class="muted" style="font-size:13px">{stat}</div></div>')


def highlight_box(svg, groups, summaries, what):
    """Wrap a grouped scatter with a team picker that dims everyone else and labels the picked team's points."""
    opts = "".join(f'<option value="{i}" data-sum="{esc(summaries.get(g, ""))}">{esc(g)}</option>'
                   for i, g in sorted(enumerate(groups), key=lambda ig: ig[1].lower()))
    uid = f"hl{abs(hash(what)) % 10**6}"
    return (f'<div class="panel hl"><div class="hl-bar"><label for="{uid}">Highlight a team’s {esc(what)}</label>'
            f'<select id="{uid}"><option value="">All teams</option>{opts}</select><span class="hl-sum muted"></span></div>'
            f'<div class="scroll"><div style="min-width:680px">{svg}</div></div></div>')


HIGHLIGHT_JS = """<script>
document.querySelectorAll('.hl').forEach(function (box) {
  var sel = box.querySelector('select'), svg = box.querySelector('svg'), sum = box.querySelector('.hl-sum');
  function apply() {
    var v = sel.value;
    svg.classList.toggle('hl-on', v !== '');
    svg.querySelectorAll('[data-g]').forEach(function (e) { e.classList.toggle('sel', e.getAttribute('data-g') === v); });
    svg.querySelectorAll('.lay').forEach(function (g) { g.style.display = g.getAttribute('data-lay') === (v === '' ? 'all' : v) ? '' : 'none'; });
    sum.textContent = v === '' ? '' : sel.selectedOptions[0].getAttribute('data-sum');
  }
  sel.addEventListener('change', apply);
  apply();
});
</script>"""


def footer(updated, extra=""):
    return (f'<footer>Updated {updated.astimezone(ET):%a %b %-d, %Y at %-I:%M %p} ET. Data from the Sleeper API; win probability is an estimate '
            f'rebuilt from ESPN play-by-play and Sleeper projections, not Sleeper’s in-app number. {extra}</footer>')
