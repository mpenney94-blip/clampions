"""HTML and inline-SVG rendering for the dashboard. No JavaScript needed."""

import collections
import datetime as dt
import html
import json
import math
import random
import re

esc = html.escape
try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")  # all displayed times are Pacific
except Exception:  # no tz database available
    PT = dt.timezone(dt.timedelta(hours=-8))

CSS = """
:root{--bg:#f6f7f9;--surface:#fff;--ink:#12151a;--ink2:#4b525c;--ink3:#7a828d;--rule:#e2e5ea;--grid:#eceef2;
--a:#2a78d6;--a-fill:rgba(42,120,214,.14);--b:#eb6834;--b-fill:rgba(235,104,52,.14);--good:#1a7f3c;--bad:#c2410c;--mark:#b4bcc7;
--r0:#f3f6fa;--r1:#dbe8f8;--r2:#b7d3f6;--r3:#86b6ef;--r4:#5598e7;--r5:#2a78d6;--r6:#1c5cab;--r7:#104281;
--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--c4:#eda100;--c5:#e87ba4;--c6:#008300;--c4b:#f2d28a;
--display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;--body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#111317;--surface:#1a1d22;--ink:#eef0f3;--ink2:#b9bfc8;--ink3:#8a919b;--rule:#2c3038;--grid:#252930;
--a:#3987e5;--a-fill:rgba(57,135,229,.2);--b:#d95926;--b-fill:rgba(217,89,38,.2);--good:#3fb26a;--bad:#ef7a4a;--mark:#5b636e;
--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;--c5:#d55181;--c6:#008300;--c4b:#6b4f12;
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
nav.toc{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(160px,45%),1fr));gap:10px;margin:14px 0 28px}
@media (max-width:520px){nav.toc .grp{padding:10px 10px 8px}nav.toc .grp>a{font-size:14px;padding:3px 0}}
nav.toc .grp{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:12px 14px 10px}
nav.toc .grp>span{display:block;font:700 13px var(--display);letter-spacing:.1em;text-transform:uppercase;color:var(--a);
 padding-bottom:6px;margin-bottom:6px;border-bottom:1px solid var(--rule)}
nav.toc .grp>a{display:block;font-size:15px;line-height:1.35;color:var(--ink);text-decoration:none;padding:4px 0;break-inside:avoid}
nav.toc .grp>a:hover{color:var(--a);text-decoration:underline;text-underline-offset:3px}
nav.toc .grp:only-child{grid-column:1/-1;columns:200px}
nav.toc .grp:only-child>span{column-span:all}
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
th.ang{height:170px;vertical-align:bottom;padding:0;text-align:left!important}
th.ang div{transform:translate(16px,-6px) rotate(-50deg);transform-origin:bottom left;width:24px;white-space:nowrap;text-transform:none;
 letter-spacing:0;font-size:13px;font-weight:600;color:var(--ink2)}
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
.stack{display:flex;gap:2px;height:22px;border-radius:5px;overflow:hidden;min-width:220px}
.stack span{display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:700;min-width:0;overflow:hidden}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:0 0 10px;font-size:14px;color:var(--ink2)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.grid-t td.w{text-align:center;min-width:44px;font-weight:700;border:2px solid var(--surface);padding:6px 4px}
.grid-t tr.tot td.n,.grid-t th.n,.grid-t td.n{text-align:center}
table.swap th.col{text-align:center}
table.board th,table.board td{text-align:center}
.grid-t tr.tot td{font-weight:700;border-top:2px solid var(--rule);border-bottom:0;white-space:nowrap}
.grid-t td.kept{outline:2.5px solid var(--ink);outline-offset:-3px}
.star{color:var(--c4);margin-left:3px;font-size:.9em}
svg text.star{fill:var(--c4);font-size:19px;paint-order:stroke;stroke:var(--surface);stroke-width:3px;cursor:default}
svg .lay,svg .lab,svg .sub,svg .lead,svg [class^="ring-"]{pointer-events:none}
svg.hl-on text.star{opacity:.2}svg.hl-on text.star.sel{opacity:1}
.grid-t .star{font-size:1.25em;vertical-align:-1px}
.grid-t td.bn{color:var(--ink3);font-weight:400;font-style:italic}
.column p{margin:0 0 12px;font-size:17px;line-height:1.55;max-width:72ch}.column p:last-child{margin-bottom:0}
.column p:first-child::first-letter{font:700 2.6em/0.9 var(--display);float:left;margin:4px 8px 0 0;color:var(--a)}
nav.seasons{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 18px;border-bottom:1px solid var(--rule)}
nav.seasons a{font:600 15px var(--display);letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);text-decoration:none;padding:8px 14px;border-bottom:3px solid transparent;margin-bottom:-1px}
nav.seasons a:hover{color:var(--ink)}
nav.seasons a[aria-current="page"]{color:var(--a);border-bottom-color:var(--a)}
:root{--t1:rgba(42,120,214,.22);--t2:rgba(235,104,52,.22);--t3:rgba(27,175,122,.22);--t4:rgba(237,161,0,.24);--t5:rgba(232,123,164,.24);--t6:rgba(0,131,0,.22)}
.xall{margin-left:auto;font:600 12.5px var(--body);color:var(--ink2);background:var(--surface);border:1px solid var(--rule);border-radius:999px;padding:4px 10px;cursor:pointer}
.xall:hover{border-color:var(--a);color:var(--a)}
.xall-bar{display:flex;justify-content:flex-end;margin-bottom:8px}
.snapping .xall{display:none}
.xpin{position:sticky;left:0;width:min(560px,calc(100vw - 64px))}
h3.h3-xall{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}h3.h3-xall .xall{margin-left:auto}
@media (max-width:520px){.snapbtn{font-size:11.5px;padding:3px 9px}}
section[id]>h2{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px}
.snapbtn{margin-left:auto;flex:none;font:600 12px var(--body);letter-spacing:0;text-transform:none;color:var(--ink2);background:var(--surface);
 border:1px solid var(--rule);border-radius:999px;padding:4px 10px;cursor:pointer}
.snapbtn:hover{border-color:var(--a);color:var(--a)}
.snapping .scroll,.snapping .tippanel{overflow:visible!important}
.snapping{width:max-content;min-width:100%;padding:16px;background:var(--bg)}
.snapping .snapbtn,.snapping .hl-bar select{pointer-events:none}
.snapcap{font:600 12px var(--display);letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px}
.snapview{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:16px}
.snapview .card{background:var(--surface);border-radius:12px;padding:14px;max-width:min(96vw,1100px);max-height:92vh;display:flex;flex-direction:column;gap:10px}
.snapview img{max-width:100%;max-height:70vh;object-fit:contain;border:1px solid var(--rule);border-radius:6px;-webkit-touch-callout:default}
.snapview .row{display:flex;gap:8px;justify-content:space-between;align-items:center;flex-wrap:wrap}
.snapview button,.snapview a{font:600 14px var(--body);border-radius:8px;padding:8px 14px;border:1px solid var(--rule);background:var(--surface);color:var(--ink);cursor:pointer;text-decoration:none}
.snapview .go{background:var(--a);color:#fff;border-color:var(--a)}
th.sorth{cursor:pointer;user-select:none}
th.sorth:hover{color:var(--ink)}
th.sorth[aria-sort]::after{content:" ▼";font-size:.8em;color:var(--a)}
th.sorth[aria-sort="ascending"]::after{content:" ▲"}
.totop{display:none;position:fixed;top:16px;right:16px;z-index:50;align-items:center;gap:4px;font:600 14px var(--display);
 letter-spacing:.06em;text-transform:uppercase;text-decoration:none;color:var(--ink);background:var(--surface);
 border:1px solid var(--rule);border-radius:999px;padding:8px 14px;box-shadow:0 4px 14px rgba(0,0,0,.14)}
.totop:hover{border-color:var(--a);color:var(--a)}
.totop:focus-visible{outline:2px solid var(--a);outline-offset:2px}
@media (min-width:900px) and (hover:hover){.totop.show{display:flex}}
.chip.medal{border:0;color:#3b2f00;padding:1px 7px}
.chip.m1{background:#f2c94c}
.chip.m2{background:#cfd4da;color:#2b3036}
.chip.m3{background:#d9a066;color:#3a2410}
td.pk{cursor:pointer}
td.pk:focus-visible,td.pk.on{outline:2px solid var(--a);outline-offset:-2px}
.pop{position:fixed;z-index:40;width:260px;background:var(--surface);border:1px solid var(--rule);border-radius:10px;
 box-shadow:0 8px 24px rgba(0,0,0,.18);padding:10px 12px;font-size:13.5px;text-align:left}
.pop table td{padding:3px 0;border:0}
.pop .x{position:absolute;top:6px;right:8px;border:0;background:none;color:var(--ink3);font-size:16px;cursor:pointer}
table.expand tr.xrow{cursor:pointer}
table.expand tr.xrow:hover td{background:var(--grid)}
table.expand tr.xrow:focus-visible{outline:2px solid var(--a);outline-offset:-2px}
table.expand tr.xrow[aria-expanded="true"] .track>span{background:var(--a)}
table.expand .chev{display:inline-block;color:var(--ink3);transition:transform .15s;width:12px}
table.expand tr.xrow[aria-expanded="true"] .chev{transform:rotate(90deg)}
table.expand tr.xdetail>td{background:var(--bg);padding:6px 10px 12px}
table.picks td{padding:5px 8px;font-size:14px}
table.picks b.gone{text-decoration:line-through;text-decoration-thickness:1.5px;color:var(--ink3)}
.gone-note{color:var(--bad);font-size:12.5px}
@media (prefers-reduced-motion:reduce){table.expand .chev{transition:none}}
.tip b.gone{text-decoration:line-through;text-decoration-thickness:1.5px;color:var(--ink3)}
.tip .gone-note{color:var(--bad);font-size:11.5px}
.tipwrap{position:relative;padding:8px 0;cursor:help;outline:none}
.tipwrap:hover .track>span,.tipwrap:focus .track>span{background:var(--a)}
.tip{display:none;position:absolute;left:0;top:100%;z-index:5;background:var(--surface);border:1px solid var(--rule);border-radius:8px;
 box-shadow:0 6px 24px rgba(0,0,0,.18);padding:10px 12px;width:max-content;max-width:min(560px,86vw);font-size:13px;white-space:normal}
.tip td{padding:4px 6px;border-bottom:1px solid var(--grid)}
.tip td:first-child,.tip td:nth-child(2){white-space:nowrap}
.tipwrap:hover .tip,.tipwrap:focus .tip{display:block}
.tippanel{overflow:visible}
.tip-close{display:none}
.tipwrap.closed .tip{display:none!important}
@media (max-width:640px){.tippanel{overflow-x:auto}
 .tip-close{display:block;position:sticky;top:0;float:right;margin:-4px -4px 0 8px;width:36px;height:36px;border-radius:50%;
  border:1px solid var(--rule);background:var(--surface);color:var(--ink);font-size:16px;line-height:1;cursor:pointer}
 .tip{position:fixed;left:12px;right:12px;bottom:max(12px,env(safe-area-inset-bottom));top:auto;width:auto;max-width:none;max-height:60vh;overflow:auto}}
.wp-plot{position:relative}
svg .xh{stroke:var(--ink3);stroke-width:1}
svg .xd{stroke:var(--surface);stroke-width:2}
svg .hit{cursor:crosshair}
.wp-tip{position:absolute;top:0;pointer-events:none;background:var(--surface);border:1px solid var(--rule);border-radius:8px;
 box-shadow:0 4px 16px rgba(0,0,0,.16);padding:6px 9px;font-size:12.5px;line-height:1.35;white-space:nowrap;font-variant-numeric:tabular-nums}
.wp-tip .t{color:var(--ink3)}
.chip{display:inline-block;font-size:11px;font-weight:700;border:1px solid currentColor;border-radius:999px;padding:0 6px;margin-left:6px;vertical-align:1px}
.trend-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.group-head{margin-top:56px;padding:14px 0 6px;border-bottom:3px solid var(--ink)}
.group-head h2{font-size:36px;margin:0}
.group-head p{margin:4px 0 0;color:var(--ink2)}
footer{margin-top:56px;color:var(--ink3);font-size:14px;border-top:1px solid var(--rule);padding-top:16px}
"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap">'


TOTOP = """<a href="#" class="totop" aria-label="Back to top">↑ Top</a><script>
(function () {
  var b = document.querySelector('.totop');
  function f() { b.classList.toggle('show', window.scrollY > 600); }
  window.addEventListener('scroll', f, { passive: true }); f();
  b.addEventListener('click', function (e) {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    b.blur();
  });
})();
</script>"""


def page(title, body, desc=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{FONTS}<style>{CSS}</style></head>
<body><div class="wrap">{body}</div>{TOTOP}</body></html>"""


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
           '<th>Cost</th><th>Biggest benching</th><th class="n">Perfect lineups</th></tr></thead><tbody>']
    for r in rows:
        f = r["flips"]
        cost = f'<span class="neg">{len(f)} {"loss" if len(f) == 1 else "losses"}</span> <span class="muted">(Wk {", ".join(map(str, f))})</span>' if f else ""
        w = r["worst"]
        worst = f'{esc(w["player"])} <span class="muted">{w["pts"]:.1f} · Wk {w["week"]}</span>' if w else ""
        out.append(f'<tr><td class="team">{esc(r["team"])}</td><td class="barcell"><div class="track"><span style="width:{100 * r["lost"] / mx:.1f}%"></span></div></td>'
                   f'<td class="n team">{r["lost"]:.1f}</td><td style="white-space:nowrap">{cost}</td><td>{worst}</td>'
                   f'<td class="n" style="white-space:nowrap">' + (f'<b class="pos">{len(r["perfect"])}</b> <span class="muted">(Wk {", ".join(map(str, r["perfect"]))})</span>'
                                                                    if r.get("perfect") else '<span class="muted">0</span>') + '</td></tr>')
    out.append('</tbody></table></div><p class="note">Best lineup = the highest-scoring legal lineup from that week’s roster, picked after the games. '
               'Cost = losses that lineup would have turned into wins. Perfect lineups = weeks with every starter in the best lineup '
               '(ties go to the player started).</p>')
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
        body = [f'<div class="panel"><div class="eyebrow">Trade {i} · {t["when"].astimezone(PT):%b %-d} · counts {span}</div><h3>{head}</h3>']
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
    mx = max((v["missed"] for v in per_team.values()), default=1) or 1
    trs = []
    for i, t in enumerate(sorted(teams, key=lambda t: -per_team.get(t, {}).get("missed", 0))):
        v = per_team.get(t)
        if not v:
            trs.append(f'<tr><td class="team"><span class="chev" aria-hidden="true" style="visibility:hidden">▸</span> {esc(t)}</td>'
                       f'<td class="barcell"><div class="track"></div></td><td class="n muted">0</td><td class="n muted">0.0</td><td class="muted">Never outbid</td></tr>')
            continue
        b = v["best"]
        lost = "".join(f'<tr><td class="muted">Wk {x["claim"]["week"]}</td><td><b>{esc(x["claim"]["player"])}</b> <span class="muted">{x["claim"]["pos"] or ""}</span></td>'
                       f'<td>bid ${x["bid"]} vs {esc(x["claim"]["winner"])} ${x["claim"]["win_bid"]}</td>'
                       f'<td class="n team">{x["claim"]["since"]:.1f}</td></tr>'
                       for x in sorted(v["claims"], key=lambda x: -x["claim"]["since"]))
        trs.append(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="ww-{i}">'
                   f'<td class="team"><span class="chev" aria-hidden="true">▸</span> {esc(t)}</td>'
                   f'<td class="barcell"><div class="track"><span style="width:{100 * v["missed"] / mx:.1f}%"></span></div></td>'
                   f'<td class="n">{v["lost"]}</td><td class="n team">{v["missed"]:.1f}</td><td>{esc(b["player"])} <span class="muted">{b["since"]:.1f} pts</span></td></tr>'
                   f'<tr class="xdetail" id="ww-{i}" hidden><td colspan="5"><table class="picks">{lost}</table></td></tr>')
    team_tbl = ('<h3 style="margin-top:18px">Points that got away, by team</h3><p class="lede" style="margin:0 0 8px">Click a team to see who they lost out on.</p>'
                '<div class="panel scroll"><table class="expand"><thead><tr><th>Team</th>'
                '<th class="barcell">Points missed</th><th class="n">Lost claims</th><th class="n">Pts</th><th>Biggest miss</th></tr></thead>'
                f'<tbody>{"".join(trs)}</tbody></table></div>')
    return (tiles + team_tbl +
            '<p class="note">A contested claim is a waiver run where more than one team put in a claim for the same player. '
            '“Points missed” is everything that player has scored from that week on, wherever he played, '
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
            curve=None, quadrants=(), groups=None, xscale=None, W=1040, H=560):
    """points: dicts with x, y, r, cls ('dot'|'good'|'bad'), label, sub, ring ('good'|'bad'|None), title.

    With groups (a list of names), each point may carry group (an index into it) plus glabel/gsub. Every group gets
    its own hidden label layer naming all of its points, which highlight_box() shows when that group is picked.
    xscale (e.g. math.sqrt) stretches the x axis; ticks then get vertical gridlines so the spacing reads."""
    l, r, t, b = 64, 24, 16, 56
    f = xscale or (lambda v: v)
    frac = lambda v: f(max(v, 0)) / f(xmax)
    X = (lambda v: l + (W - l - r) * (1 - frac(v))) if xreverse else (lambda v: l + (W - l - r) * frac(v))
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
        if xscale:
            s.append(f'<line class="gridl" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{H - b}"/>')
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
        gs = p.get("group")
        gs = [gs] if isinstance(gs, int) else (gs or [])
        p["_groups"] = gs
        g = f' data-g="{" ".join(map(str, gs))}"' if gs else ""
        if p.get("star"):  # starred points (keepers) are drawn as the star itself instead of a dot
            s.append(f'<text class="star" x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" dominant-baseline="central"{g}>★'
                     f'<title>{esc(p.get("title", ""))}</title></text>')
        else:
            s.append(f'<circle class="dot" cx="{cx:.1f}" cy="{cy:.1f}" r="{p["r"]:.1f}"{fill}{g}><title>{esc(p.get("title", ""))}</title></circle>')
        if p.get("ring"):
            s.append(f'<circle class="ring-{p["ring"]}" cx="{cx:.1f}" cy="{cy:.1f}" r="{p["r"] + (5 if p.get("star") else 3):.1f}"{g}/>')

    def hits(box, pts):
        x0, y0, x1, y1 = box
        return sum(1 for cx, cy, rr in pts if x0 - rr < cx < x1 + rr and y0 - rr < cy < y1 + rr)

    def layer(labeled, marked, gi=None):
        placed, out = [], []
        for p in sorted(labeled, key=lambda p: -p.get("priority", 0)):
            if gi is None:
                lab, sub = p["label"], p.get("sub", "")
            else:
                lab, sub = (p.get("glabels") or {}).get(gi, (p.get("glabel"), p.get("gsub", "")))
            out += place(p, lab, sub, placed, marked)
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

    marked = [p["_c"] + (p["r"] + (12 if p.get("star") else 4),) for p in points
              if p.get("label") or p.get("ring") or p.get("star") or p.get("cls", "dot") != "dot"]
    s.append('<g class="lay" data-lay="all">' + "".join(layer([p for p in points if p.get("label")], marked)) + '</g>')
    for gi, _ in enumerate(groups or []):
        mine = [p for p in points if gi in p["_groups"]]
        s.append(f'<g class="lay" data-lay="{gi}" style="display:none">'
                 + "".join(layer(mine, [p["_c"] + (p["r"] + (12 if p.get("star") else 4),) for p in mine], gi)) + '</g>')
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
        day = dt.datetime.fromtimestamp(g[0], PT).strftime("%a")
        if k == 0 or (day != last_day and x0s[k] - last_x > 34):
            s.append(f'<text x="{x0s[k]:.1f}" y="{H - 6}">{day}</text>')
            last_day, last_x = day, x0s[k]
    for k in range(1, len(segs)):
        a, c = S[segs[k][2] - 1], S[segs[k][2]]
        s.append(f'<line class="lead" stroke-dasharray="2 3" x1="{X(a[0]):.1f}" y1="{Y(a[1]):.1f}" x2="{X(c[0]):.1f}" y2="{Y(c[1]):.1f}"/>')
    last = S[-1]
    s.append(f'<circle cx="{X(last[0]):.1f}" cy="{Y(last[1]):.1f}" r="4" style="fill:var({"--a" if last[1] >= .5 else "--b"})"/>')
    peak_a, peak_b = max(S, key=lambda p: p[1]), min(S, key=lambda p: p[1])
    # hover layer: crosshair + dot, driven by WP_JS from the points in data-pts
    s.append(f'<line class="xh" x1="0" x2="0" y1="{t}" y2="{H - b}" style="display:none"/><circle class="xd" r="4.5" style="display:none"/>'
             f'<rect class="hit" x="{l}" y="0" width="{W - l - r}" height="{H}" fill="transparent"/>')
    s.append('</svg>')
    hover = json.dumps([[round(X(p[0]), 1), round(Y(p[1]), 1), int(p[0]), round(p[1] * 100), round(p[2], 1), round(p[3], 1)] for p in S],
                       separators=(",", ":"))
    h, a = m["home"], m["away"]
    final = not m.get("pending")
    stat = (f'Peak: <span class="dot-a">{esc(h["team"])} {peak_a[1]:.0%}</span> · <span class="dot-b">{esc(a["team"])} {1 - peak_b[1]:.0%}</span>'
            if final else f'Live: {esc(h["team"])} {last[1]:.0%} to win')
    return (f'<div class="panel wp-card" data-pts="{esc(hover)}" data-w="{W}" data-a="{esc(h["team"])}" data-b="{esc(a["team"])}">'
            f'<div class="score"><span class="dot-a">{esc(h["team"])} {last[2]:.2f}</span>'
            f'<span class="dot-b" style="text-align:right">{last[3]:.2f} {esc(a["team"])}</span></div>'
            f'<div class="wp-plot">{"".join(s)}<div class="wp-tip" hidden></div></div>'
            f'<div class="muted" style="font-size:13px">{stat}</div></div>')


def highlight_box(svg, groups, summaries, what, extra=0):
    """Wrap a grouped scatter with a team picker that dims everyone else and labels the picked team's points.

    The last `extra` groups are special views (like "Keepers only") listed right after "All teams"."""
    teams = list(enumerate(groups))[:len(groups) - extra]
    special = list(enumerate(groups))[len(groups) - extra:]
    opts = "".join(f'<option value="{i}" data-sum="{esc(summaries.get(g, ""))}">{esc(g)}</option>'
                   for i, g in special + sorted(teams, key=lambda ig: ig[1].lower()))
    uid = "hl-" + re.sub(r"[^a-z0-9]+", "-", what.lower()).strip("-")
    return (f'<div class="panel hl"><div class="hl-bar"><label for="{uid}">Highlight a team’s {esc(what)}</label>'
            f'<select id="{uid}" autocomplete="off"><option value="">All teams</option>{opts}</select><span class="hl-sum muted"></span></div>'
            f'<div class="scroll"><div style="min-width:680px">{svg}</div></div></div>')


POS_ORDER = ["QB", "RB", "WR", "TE", "K", "DEF"]


def carry_bars(rows):
    legend = '<div class="legend">' + "".join(f'<span><i style="background:var(--c{i})"></i>{p}</span>' for i, p in enumerate(POS_ORDER, 1)) + '</div>'
    opts = ('<option value="top" data-plain data-hint="Most reliant on one player first">Top player’s share</option>'
            '<option value="total" data-plain data-hint="Most starting-lineup points first">Total points</option>'
            + "".join(f'<option value="{p}">{p} share</option>' for p in POS_ORDER))
    controls = (f'<div class="hl-bar"><label for="carry-sort">Sort by</label><select id="carry-sort" autocomplete="off">{opts}</select>'
                f'<span class="muted sort-hint"></span></div>')
    trs = []
    for r in rows:
        segs, data = [], [f'data-top="{r["top"]["share"]:.4f}" data-total="{r["total"]:.1f}"']
        for i, p in enumerate(POS_ORDER, 1):
            v = r["by_pos"].get(p, 0)
            share = v / r["total"]
            data.append(f'data-{p.lower()}="{share:.4f}" data-{p.lower()}-pts="{v:.1f}"')
            if share <= 0:
                continue
            txt = f"{share:.0%}" if share >= .09 else ""
            segs.append(f'<span data-pos="{p}" style="flex:{share:.4f};background:var(--c{i})" title="{p}: {v:.1f} pts ({share:.0%})">{txt}</span>')
        t = r["top"]
        trs.append(f'<tr {" ".join(data)}><td class="muted rank"></td><td class="team" style="white-space:nowrap">{esc(r["team"])}</td><td style="width:40%"><div class="stack">{"".join(segs)}</div></td>'
                   f'<td class="n team sort-col" hidden></td><td class="n team">{r["total"]:.1f}</td>'
                   f'<td style="white-space:nowrap">{esc(t["player"])} <b>{t["share"]:.0%}</b> <span class="muted">{t["pts"]:.0f} pts</span></td></tr>')
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table><thead><tr><th></th><th>Team</th><th>Share of starting-lineup points, by position</th>'
            f'<th class="n sort-col" hidden></th><th class="n">Total</th><th>Top player’s share</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Only points scored by players in the starting lineup count. Flex points go to the player’s own position. '
            'Pick a position to rank teams by how much of their scoring came from it, or Total points to rank by starting-lineup points.</p>')


def source_bars(src):
    kinds = [("draft", "Drafted", 1), ("waiver", "Waiver / free agent", 2), ("trade", "Trade", 3)]
    legend = '<div class="legend">' + "".join(f'<span><i style="background:var(--c{c})"></i>{lab}</span>' for _, lab, c in kinds) + '</div>'
    opts = ('<option value="total" data-plain data-hint="Most starting-lineup points first" selected>Total points</option>'
            + "".join(f'<option value="{k}" data-label="{lab}">{lab} share</option>' for k, lab, _ in kinds))
    controls = (f'<div class="hl-bar"><label for="sources-sort">Sort by</label><select id="sources-sort" autocomplete="off">{opts}</select>'
                f'<span class="muted sort-hint"></span></div>')
    trs = []
    for r in sorted(src.values(), key=lambda r: -r["total"]):
        segs, data = [], [f'data-total="{r["total"]:.1f}"']
        for k, lab, c in kinds:
            share = r[k] / (r["total"] or 1)
            data.append(f'data-{k}="{share:.4f}" data-{k}-pts="{r[k]:.1f}"')
            if share > 0:
                segs.append(f'<span data-pos="{k}" style="flex:{share:.4f};background:var(--c{c})" title="{lab}: {r[k]:.1f} pts ({share:.0%})">'
                            f'{f"{share:.0%}" if share >= .08 else ""}</span>')
        best = r["best"].get("waiver")
        trs.append(f'<tr {" ".join(data)}><td class="muted rank"></td><td class="team" style="white-space:nowrap">{esc(r["team"])}</td>'
                   f'<td style="width:34%"><div class="stack">{"".join(segs)}</div></td>'
                   f'<td class="n">{r["draft"]:.1f}</td><td class="n">{r["waiver"]:.1f}</td><td class="n">{r["trade"]:.1f}</td>'
                   f'<td class="n team">{r["total"]:.1f}</td>'
                   f'<td style="white-space:nowrap">{esc(best[0]) + f" <span class=muted>{best[1]:.1f}</span>" if best else "<span class=muted>—</span>"}</td></tr>')
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table><thead><tr><th></th><th>Team</th><th>Share of starting-lineup points</th>'
            f'<th class="n">Drafted</th><th class="n">Waiver/FA</th><th class="n">Trade</th><th class="n">Total</th><th>Best pickup</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Starting-lineup points only, credited to how that team got the player at the time: drafted it, picked it up '
            '(waiver claim or free agent) or traded for it. A drafted player who was dropped and picked back up counts as a pickup. '
            'Pick a source to rank teams by how much of their scoring came from it, or Total points to rank by starting-lineup points.</p>')


def round_table(src, rounds):
    mx = max((v for r in src.values() for v in r["rounds"].values()), default=1) or 1
    head = "".join(f'<th class="n">R{i}</th>' for i in range(1, rounds + 1))
    trs = []
    for r in sorted(src.values(), key=lambda r: -r["draft"]):
        cells = []
        for i in range(1, rounds + 1):
            v = r["rounds"].get(i, 0)
            if v <= 0:
                note = r["round_notes"].get(i)
                cells.append(f'<td class="w muted"{f" title={chr(34)}{esc(note)}{chr(34)}" if note else ""}>–</td>')
                continue
            step = max(1, min(7, round(7 * v / mx)))
            fg = "#fff" if step >= 5 else "var(--ink)"
            who = ", ".join(f"{n} {p:.1f}" for n, p in r["round_players"][i].most_common())
            kept = r["keeper_round"] == i
            if kept:
                who = "Keeper: " + who
            badge = '<span class="star" aria-label="keeper">★</span>' if kept else ""
            cells.append(f'<td class="w{" kept" if kept else ""}" style="background:var(--r{step});color:{fg}" title="{esc(who)}">{v:.0f}{badge}</td>')
        trs.append(f'<tr><td class="team" style="white-space:nowrap">{esc(r["team"])}</td>{"".join(cells)}'
                   f'<td class="n">{r["keeper"]:.0f}</td><td class="n">{r["draft"] - r["keeper"]:.0f}</td><td class="n team">{r["draft"]:.0f}</td></tr>')
    return (f'<div class="panel scroll"><table class="grid-t"><thead><tr><th>Team</th>{head}<th class="n">Keeper</th><th class="n">New picks</th>'
            f'<th class="n">Total</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Starting-lineup points from each team’s own draft picks, by the round they were taken. Darker = more points; '
            'hover a cell to see the players (on a “–”, what happened to that pick). Outlined cells with a ★ are each team’s keeper, taken in that round’s slot; '
            '“New picks” is everything else from this year’s draft. Picks that were traded away, dropped or never started count as –.</p>')


def team_grids(lg_name, grids, weeks, totals):
    """grids: {team: rows from stats.team_grid}; totals: {team: stats.week_totals}. One table per team behind a team picker."""
    teams = sorted(grids, key=str.lower)
    opts = "".join(f'<option value="{i}">{esc(t)}</option>' for i, t in enumerate(teams))
    panels = []
    for i, t in enumerate(teams):
        head = "".join(f'<th class="n">Wk {w}</th>' for w in weeks)
        body = []
        for r in grids[t]:
            cells = []
            for w in weeks:
                if w not in r["weeks"]:
                    cells.append('<td class="w"></td>')
                    continue
                v, started = r["weeks"][w]
                if started:
                    step = max(1, min(7, int(v // 5) + 1)) if v > 0 else 0
                    fg = "#fff" if step >= 5 else "var(--ink)"
                    cells.append(f'<td class="w" style="background:var(--r{step});color:{fg}" title="Week {w}: {v:.2f}">{v:.1f}</td>')
                else:
                    cells.append(f'<td class="w bn" title="Week {w}: {v:.2f} on the bench">{v:.1f}</td>')
            star = '<span class="star" title="Keeper">★</span>' if r.get("keeper") else ""
            body.append(f'<tr><td><b>{esc(r["player"])}</b>{star} <span class="muted">{r["pos"] or ""}</span></td>{"".join(cells)}'
                        f'<td class="n team">{r["started"]:.1f}</td><td class="n muted">{r["benched"]:.1f}</td></tr>')
        tot = totals[t]
        act, best = sum(a for a, _ in tot.values()), sum(b for _, b in tot.values())
        def gap(d):
            return f' <span class="neg" style="font-size:11px">+{d:.1f}</span>' if d > 0.05 else ""
        foot = (f'<tr class="tot"><td>Starters total</td>' + "".join(f'<td class="n">{tot[w][0]:.1f}</td>' for w in weeks)
                + f'<td class="n">{act:.1f}</td><td></td></tr>'
                + f'<tr class="tot"><td>Best possible <span class="muted" style="font-weight:400">(+ left on bench)</span></td>'
                + "".join(f'<td class="n">{tot[w][1]:.1f}{gap(tot[w][1] - tot[w][0])}</td>' for w in weeks)
                + f'<td class="n">{best:.1f}{gap(best - act)}</td><td></td></tr>')
        panels.append(f'<div data-panel="{i}"{"" if i == 0 else " hidden"}><table class="grid-t"><thead><tr><th>Player</th>{head}'
                      f'<th class="n">Started</th><th class="n">Bench</th></tr></thead><tbody>{"".join(body)}</tbody><tfoot>{foot}</tfoot></table></div>')
    return (f'<div class="panel switch"><div class="hl-bar"><label for="grid-pick">Team</label><select id="grid-pick" autocomplete="off">{opts}</select></div>'
            f'<div class="scroll">{"".join(panels)}</div></div>'
            '<p class="note">Colored cells are starting-lineup scores (darker = more points, in 5-point steps). Gray italic numbers are points '
            'scored on the bench. Blank cells are weeks the player wasn’t on the roster or didn’t play. ★ = the team’s keeper. Best possible = the highest-scoring '
            'legal lineup from that week’s roster, picked after the games; the red number is how much more it would have scored.</p>')


HIGHLIGHT_JS = """<script>
document.querySelectorAll('.tipwrap').forEach(function (w) {
  function close(e) { e.preventDefault(); e.stopPropagation(); w.classList.add('closed'); w.blur(); }
  w.addEventListener('pointerdown', function (e) { if (!e.target.closest('.tip-close')) w.classList.remove('closed'); });
  w.addEventListener('focus', function () { w.classList.remove('closed'); });
  var b = w.querySelector('.tip-close');
  if (b) { b.addEventListener('pointerdown', close); b.addEventListener('click', close); }
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && document.activeElement && document.activeElement.classList.contains('tipwrap')) document.activeElement.blur();
});
document.querySelectorAll('table.expand tr.xrow').forEach(function (row) {
  function toggle() {
    var open = row.getAttribute('aria-expanded') !== 'true', d = document.getElementById(row.getAttribute('aria-controls'));
    row.setAttribute('aria-expanded', open); d.hidden = !open;
  }
  row.addEventListener('click', toggle);
  row.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
});
document.querySelectorAll('.sortbars').forEach(function (box) {
  var sel = box.querySelector('select'), body = box.querySelector('tbody'), hint = box.querySelector('.sort-hint');
  var th = box.querySelector('th.sort-col');
  function apply() {
    if (sel.value.indexOf('col:') === 0) return;  // a column-header sort; the shared sorter below handles it
    var o = sel.selectedOptions[0], v = sel.value, k = v.toLowerCase(), plain = o.hasAttribute('data-plain'), lab = o.getAttribute('data-label') || v;
    var rows = Array.prototype.slice.call(body.rows).filter(function (r) { return !r.classList.contains('xdetail'); });
    rows.sort(function (a, b) { return +b.getAttribute('data-' + k) - +a.getAttribute('data-' + k); });
    rows.forEach(function (r, i) {
      body.appendChild(r);
      var d = r.getAttribute('aria-controls') && document.getElementById(r.getAttribute('aria-controls'));
      if (d) body.appendChild(d);
      r.querySelector('.rank').textContent = i + 1;
      var c = r.querySelector('td.sort-col');
      if (c) { c.hidden = plain; if (!plain) c.textContent = Math.round(+r.getAttribute('data-' + k) * 100) + '% · ' + r.getAttribute('data-' + k + '-pts'); }
      r.querySelectorAll('.stack span').forEach(function (s) { s.style.opacity = (plain && !o.hasAttribute('data-dim')) || v === 'total' || s.getAttribute('data-pos') === v ? '' : '.3'; });
    });
    if (th) { th.hidden = plain; th.textContent = plain ? '' : lab + ' share · pts'; }
    hint.textContent = o.getAttribute('data-hint') || ('Highest ' + lab + ' share first');
  }
  sel.addEventListener('change', apply);
  apply();
});
document.querySelectorAll('.wp-card').forEach(function (card) {
  var pts = JSON.parse(card.getAttribute('data-pts')), W = +card.getAttribute('data-w');
  var svg = card.querySelector('svg'), tip = card.querySelector('.wp-tip'), plot = card.querySelector('.wp-plot');
  var xh = svg.querySelector('.xh'), xd = svg.querySelector('.xd'), hit = svg.querySelector('.hit');
  var a = card.getAttribute('data-a'), b = card.getAttribute('data-b');
  var fmt = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', weekday: 'short', hour: 'numeric', minute: '2-digit' });
  function row(cls, name, v) { var d = document.createElement('div'); var s = document.createElement('span'); s.className = cls; s.textContent = name; d.append(s, ' ' + v); return d; }
  function show(ev) {
    var r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) * W / r.width;
    var lo = 0, hi = pts.length - 1;
    while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (pts[mid][0] <= x) lo = mid; else hi = mid - 1; }
    if (lo + 1 < pts.length && Math.abs(pts[lo + 1][0] - x) < Math.abs(pts[lo][0] - x)) lo++;
    var p = pts[lo];
    xh.setAttribute('x1', p[0]); xh.setAttribute('x2', p[0]); xh.style.display = '';
    xd.setAttribute('cx', p[0]); xd.setAttribute('cy', p[1]); xd.style.fill = p[3] >= 50 ? 'var(--a)' : 'var(--b)'; xd.style.display = '';
    tip.textContent = '';
    var t = document.createElement('div'); t.className = 't'; t.textContent = fmt.format(new Date(p[2] * 1000)) + ' PT'; tip.append(t);
    tip.append(row('dot-a', a, p[3] + '%'), row('dot-b', b, (100 - p[3]) + '%'));
    var sc = document.createElement('div'); sc.className = 't'; sc.textContent = 'Score ' + p[4].toFixed(1) + ' – ' + p[5].toFixed(1); tip.append(sc);
    tip.hidden = false;
    var px = p[0] * r.width / W, tw = tip.offsetWidth;
    tip.style.left = Math.max(0, Math.min(px + 12 + tw > r.width ? px - tw - 12 : px + 12, r.width - tw)) + 'px';
  }
  function hide() { xh.style.display = 'none'; xd.style.display = 'none'; tip.hidden = true; }
  hit.addEventListener('pointermove', show); hit.addEventListener('pointerdown', show); hit.addEventListener('pointerleave', hide);
});
document.querySelectorAll('.trend-card').forEach(function (card) {
  var pts = JSON.parse(card.getAttribute('data-pts')), W = +card.getAttribute('data-w'), season = +card.getAttribute('data-season');
  var svg = card.querySelector('svg'), tip = card.querySelector('.wp-tip');
  var xh = svg.querySelector('.xh'), xd = svg.querySelector('.xd'), hit = svg.querySelector('.hit');
  function signed(v) { return (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1); }
  function row(label, v, d) {
    var r = document.createElement('div'); r.append(label + ' ');
    if (v) { var b = document.createElement('b'); b.textContent = v; r.append(b); }
    if (d !== undefined) { var s = document.createElement('b'); s.className = d >= 0 ? 'pos' : 'neg'; s.textContent = signed(d); r.append(s); }
    return r;
  }
  function show(ev) {
    var r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) * W / r.width, i = 0;
    pts.forEach(function (p, j) { if (Math.abs(p[0] - x) < Math.abs(pts[i][0] - x)) i = j; });
    var p = pts[i];
    xh.setAttribute('x1', p[0]); xh.setAttribute('x2', p[0]); xh.style.display = '';
    xd.setAttribute('cx', p[0]); xd.setAttribute('cy', p[1]); xd.style.fill = p[3] >= season ? 'var(--good)' : 'var(--bad)'; xd.style.display = '';
    tip.textContent = '';
    var t = document.createElement('div'); t.className = 't'; t.textContent = 'Week ' + p[2]; tip.append(t);
    tip.append(row('Score', p[3].toFixed(1)), row('vs. its season avg (' + season.toFixed(1) + ')', '', p[3] - season),
               row('vs. league avg (' + p[5].toFixed(1) + ')', '', p[3] - p[5]), row('3-week avg', p[4].toFixed(1)));
    tip.hidden = false;
    var px = p[0] * r.width / W, tw = tip.offsetWidth;
    tip.style.left = Math.max(0, Math.min(px + 12 + tw > r.width ? px - tw - 12 : px + 12, r.width - tw)) + 'px';
  }
  function hide() { xh.style.display = 'none'; xd.style.display = 'none'; tip.hidden = true; }
  hit.addEventListener('pointermove', show); hit.addEventListener('pointerdown', show); hit.addEventListener('pointerleave', hide);
});
// Every sortable table gets both a Sort by menu and clickable column headers, kept in sync.
// Tables with their own menu (.sortbars) keep their custom options; plain table.sortable ones get a menu built from the headers.
(function () {
  function heads(t) { var r = t.tHead && t.tHead.rows[t.tHead.rows.length - 1]; return r ? Array.prototype.slice.call(r.cells) : []; }
  function rowsOf(t) { return Array.prototype.slice.call(t.tBodies[0].rows).filter(function (r) { return !r.classList.contains('xdetail'); }); }
  function place(t, rows) {
    var body = t.tBodies[0];
    rows.forEach(function (r, i) {
      body.appendChild(r);
      var id = r.getAttribute('aria-controls'), d = id && document.getElementById(id);
      if (d) body.appendChild(d);
      var rk = r.querySelector('.rank'); if (rk) rk.textContent = i + 1;
    });
  }
  function val(r, i) {
    var c = r.cells[i]; if (!c) return '';
    var v = c.hasAttribute('data-v') ? c.getAttribute('data-v') : c.textContent.replace(/[$,%▸▾]/g, '').replace(/−/g, '-').trim();
    var n = parseFloat(v);
    return isNaN(n) || !/^[-+]?[0-9.]/.test(v) ? v.toLowerCase() : n;
  }
  function norm(x) { return x.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }
  function setup(t) {
    if (!t.tHead || !t.tBodies[0] || t.dataset.sortReady || t.closest('tr.xdetail')) return;  // skip tables inside expanded rows
    t.dataset.sortReady = '1';
    var hs = heads(t), box = t.closest('.sortbars'), sel = box && box.querySelector('select'), hint = box && box.querySelector('.sort-hint');
    var original = rowsOf(t);
    var cols = [];
    hs.forEach(function (h, i) {
      var vals = original.map(function (r) { return val(r, i); });
      var name = h.textContent.trim();
      if (name && name !== '#' && vals.some(function (v) { return v !== '' && v !== vals[0]; })) cols.push(i);
    });
    if (!sel) {  // build a menu from the headers
      var bar = document.createElement('div'); bar.className = 'hl-bar';
      var lab = document.createElement('label'); lab.textContent = 'Sort by';
      sel = document.createElement('select'); sel.setAttribute('autocomplete', 'off');
      sel.id = 'sort-' + Math.random().toString(36).slice(2, 8); lab.htmlFor = sel.id;
      var o0 = document.createElement('option'); o0.value = ''; o0.textContent = 'Default order'; sel.appendChild(o0);
      cols.forEach(function (i) { var o = document.createElement('option'); o.value = 'col:' + i; o.textContent = hs[i].textContent.trim(); sel.appendChild(o); });
      hint = document.createElement('span'); hint.className = 'muted sort-hint';
      bar.append(lab, sel, hint);
      var host = t.closest('.panel') || t.parentNode;
      host.insertBefore(bar, host.firstChild);
      var pre = hs.findIndex(function (h) { return h.getAttribute('aria-sort'); });
      if (pre >= 0 && cols.indexOf(pre) >= 0) sel.value = 'col:' + pre;
    }
    function sortBy(i, dir) {
      var rows = rowsOf(t), text = typeof val(rows[0], i) === 'string';
      dir = dir || (text ? 'ascending' : 'descending');
      rows.sort(function (a, b) { var x = val(a, i), y = val(b, i); return (x < y ? -1 : x > y ? 1 : 0) * (dir === 'ascending' ? 1 : -1); });
      place(t, rows);
      t.querySelectorAll('.stack span').forEach(function (s) { s.style.opacity = ''; });
      hs.forEach(function (h, j) { if (j === i) h.setAttribute('aria-sort', dir); else h.removeAttribute('aria-sort'); });
      if (hint) hint.textContent = text ? (dir === 'ascending' ? 'A to Z' : 'Z to A') : (dir === 'descending' ? 'Highest first' : 'Lowest first');
    }
    cols.forEach(function (i) {
      var h = hs[i];
      h.classList.add('sorth'); h.setAttribute('tabindex', '0');
      function go() {
        var text = typeof val(rowsOf(t)[0], i) === 'string', first = text ? 'ascending' : 'descending';
        var dir = h.getAttribute('aria-sort') === first ? (first === 'ascending' ? 'descending' : 'ascending') : first;
        sortBy(i, dir);
        // show the matching menu choice: one of the table's own options if it names this column, else a column option
        var label = norm(h.textContent), match = Array.prototype.find.call(sel.options, function (o) {
          var ot = norm(o.textContent); return o.value && o.value.indexOf('col:') !== 0 && ot && (ot === label || ot.indexOf(label) === 0 || label.indexOf(ot) === 0);
        });
        var colOpt = sel.querySelector('option[value="col:' + i + '"]');
        if (!match && !colOpt) {
          Array.prototype.forEach.call(sel.querySelectorAll('option.tmp'), function (o) { o.remove(); });
          colOpt = document.createElement('option'); colOpt.className = 'tmp'; colOpt.value = 'col:' + i; colOpt.textContent = h.textContent.trim(); sel.appendChild(colOpt);
        }
        sel.value = (match || colOpt).value;
      }
      h.addEventListener('click', go);
      h.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
    sel.addEventListener('change', function () {
      var v = sel.value;
      if (v.indexOf('col:') === 0) { sortBy(+v.slice(4)); return; }
      if (v === '' && !box) { place(t, original); hs.forEach(function (h) { h.removeAttribute('aria-sort'); }); if (hint) hint.textContent = ''; return; }
      // one of the table's own options (already applied by its own handler): mark the header it matches, if any
      var label = norm(sel.selectedOptions[0].textContent);
      hs.forEach(function (h) { var ht = norm(h.textContent); if (ht && (ht === label || label.indexOf(ht) === 0 || ht.indexOf(label) === 0)) h.setAttribute('aria-sort', 'descending'); else h.removeAttribute('aria-sort'); });
    });
  }
  document.querySelectorAll('.sortbars table, table.sortable').forEach(setup);
})();
// Expand all / collapse all for every table with dropdown rows.
(function () {
  document.querySelectorAll('table.expand').forEach(function (t) {
    if (t.closest('tr.xdetail')) return;
    var rows = Array.prototype.slice.call(t.querySelectorAll('tr.xrow')).filter(function (r) { return r.closest('table') === t; });
    if (rows.length < 2) return;
    var b = document.createElement('button'); b.type = 'button'; b.className = 'xall';
    function sync() { var open = rows.every(function (r) { return r.getAttribute('aria-expanded') === 'true'; }); b.textContent = open ? '▾ Collapse all' : '▸ Expand all'; return open; }
    b.addEventListener('click', function () {
      var open = !sync();
      rows.forEach(function (r) { r.setAttribute('aria-expanded', open); var d = document.getElementById(r.getAttribute('aria-controls')); if (d) d.hidden = !open; });
      sync();
    });
    rows.forEach(function (r) { r.addEventListener('click', function () { setTimeout(sync, 0); }); });
    sync();
    var box = t.closest('.panel') || t.parentNode, bar = box.querySelector('.hl-bar');
    var h3 = box.firstElementChild;
    if (bar && bar.closest('.panel') === box) bar.appendChild(b);
    else if (h3 && h3.tagName === 'H3' && box.classList.contains('panel')) { h3.classList.add('h3-xall'); h3.appendChild(b); }
    else { var w = document.createElement('div'); w.className = 'xall-bar'; w.appendChild(b); box.insertBefore(w, t.closest('.panel') === box ? box.firstChild : t); }
  });
})();
// Save image: a button on every section heading turns the section, exactly as it looks now (sort, expanded rows,
// toggles), into a PNG. On a phone the share sheet saves it to Photos; pressing and holding the preview works too.
(function () {
  var lib = null;
  function load() {
    if (window.html2canvas) return Promise.resolve();
    if (!lib) lib = new Promise(function (ok, bad) {
      var sc = document.createElement('script');
      sc.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
      sc.onload = ok; sc.onerror = bad; document.head.appendChild(sc);
    });
    return lib;
  }
  function slug(x) { return x.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  function show(blob, name) {
    var url = URL.createObjectURL(blob), file = new File([blob], name, { type: 'image/png' });
    var v = document.createElement('div'); v.className = 'snapview';
    v.innerHTML = '<div class="card"><img alt="Saved table"><div class="row"><span class="muted" style="font-size:13px">On iPhone: Share, then Save Image. Or press and hold the picture.</span>' +
      '<span style="display:flex;gap:8px"><button type="button" class="close">Close</button><a class="dl">Download</a><button type="button" class="go">Share / Save</button></span></div></div>';
    v.querySelector('img').src = url;
    var dl = v.querySelector('.dl'); dl.href = url; dl.download = name;
    var go = v.querySelector('.go');
    if (!(navigator.canShare && navigator.canShare({ files: [file] }))) go.remove();
    else go.addEventListener('click', function () { navigator.share({ files: [file], title: name }).catch(function () {}); });
    function close() { v.remove(); URL.revokeObjectURL(url); }
    v.querySelector('.close').addEventListener('click', close);
    v.addEventListener('click', function (e) { if (e.target === v) close(); });
    document.body.appendChild(v);
  }
  function snap(sec, btn) {
    btn.disabled = true; var label = btn.textContent; btn.textContent = 'Saving…';
    load().then(function () {
      var title = (sec.querySelector('h2') || {}).childNodes ? sec.querySelector('h2').childNodes[0].textContent.trim() : 'table';
      var cap = document.createElement('div'); cap.className = 'snapcap';
      var league = (document.querySelector('header.site h1') || { textContent: '' }).textContent.replace(/: all-time$/, '').trim() || 'We Are The Clampions';
      var brow = (document.querySelector('.eyebrow') || { textContent: '' }).textContent;
      var when = /\/alltime\//.test(location.pathname) ? 'All-time' + ((brow.match(/(\d{4}–\d{4})/) || [])[1] ? ' ' + brow.match(/(\d{4}–\d{4})/)[1] : '')
        : ((brow.match(/(\d{4}) season/) || [])[1] ? brow.match(/(\d{4}) season/)[1] + ' season' : '');
      var wk = /\/weeks\//.test(location.pathname) && document.querySelector('h1') ? document.querySelector('h1').textContent.trim() : '';
      cap.textContent = [league, when, wk, title, new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })]
        .filter(Boolean).join(' · ');
      sec.insertBefore(cap, sec.firstChild); sec.classList.add('snapping');
      var bg = getComputedStyle(document.body).backgroundColor;
      return window.html2canvas(sec, { backgroundColor: bg, scale: Math.min(2, window.devicePixelRatio || 2), useCORS: true,
        windowWidth: Math.max(document.documentElement.clientWidth, sec.scrollWidth + 40),
        ignoreElements: function (el) { return el.classList && (el.classList.contains('snapbtn') || el.classList.contains('totop')); } })
        .then(function (canvas) {
          cap.remove(); sec.classList.remove('snapping');
          return new Promise(function (ok) { canvas.toBlob(ok, 'image/png'); }).then(function (blob) { show(blob, slug(title) + '.png'); });
        }, function (err) { cap.remove(); sec.classList.remove('snapping'); throw err; });
    }).catch(function (e) { alert('Couldn’t make the image: ' + e); })
      .then(function () { btn.disabled = false; btn.textContent = label; });
  }
  document.querySelectorAll('section[id] > h2').forEach(function (h) {
    var b = document.createElement('button'); b.type = 'button'; b.className = 'snapbtn'; b.textContent = '📷 Save image';
    b.setAttribute('aria-label', 'Save ' + h.textContent.trim() + ' as an image');
    b.addEventListener('click', function () { snap(h.parentNode, b); });
    h.appendChild(b);
  });
})();
(function () {
  var pop = null, cur = null;
  function close() { if (pop) { pop.remove(); pop = null; } if (cur) { cur.classList.remove('on'); cur = null; } }
  function open(td) {
    close(); cur = td; td.classList.add('on');
    pop = document.createElement('div'); pop.className = 'pop'; pop.setAttribute('role', 'dialog');
    pop.appendChild(td.querySelector('template').content.cloneNode(true));
    var x = document.createElement('button'); x.className = 'x'; x.type = 'button'; x.setAttribute('aria-label', 'Close'); x.textContent = '✕';
    x.addEventListener('click', close); pop.appendChild(x);
    document.body.appendChild(pop);
    var r = td.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    var left = Math.min(Math.max(8, r.left), window.innerWidth - w - 8);
    var top = r.bottom + 6 + h > window.innerHeight - 8 ? r.top - h - 6 : r.bottom + 6;
    pop.style.left = left + 'px'; pop.style.top = Math.max(8, top) + 'px';
  }
  document.querySelectorAll('td.pk').forEach(function (td) {
    td.addEventListener('click', function (e) { e.stopPropagation(); if (cur === td) close(); else open(td); });
    td.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (cur === td) close(); else open(td); } });
  });
  document.addEventListener('click', function (e) { if (pop && !pop.contains(e.target)) close(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  window.addEventListener('scroll', close, { passive: true });
})();
document.querySelectorAll('.switch').forEach(function (box) {
  var sel = box.querySelector('select');
  function apply() { box.querySelectorAll('[data-panel]').forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== sel.value; }); }
  sel.addEventListener('change', apply);
  apply();
});
document.querySelectorAll('.hl').forEach(function (box) {
  var sel = box.querySelector('select'), svg = box.querySelector('svg'), sum = box.querySelector('.hl-sum');
  function apply() {
    var v = sel.value;
    svg.classList.toggle('hl-on', v !== '');
    svg.querySelectorAll('[data-g]').forEach(function (e) { e.classList.toggle('sel', v !== '' && e.getAttribute('data-g').split(' ').indexOf(v) >= 0); });
    svg.querySelectorAll('.lay').forEach(function (g) { g.style.display = g.getAttribute('data-lay') === (v === '' ? 'all' : v) ? '' : 'none'; });
    sum.textContent = v === '' ? '' : sel.selectedOptions[0].getAttribute('data-sum');
  }
  sel.addEventListener('change', apply);
  apply();
});
</script>"""


def footer(updated, extra=""):
    return (f'<footer>Updated {updated.astimezone(PT):%a %b %-d, %Y at %-I:%M %p} PT. Data from the Sleeper API; win probability is an estimate '
            f'rebuilt from ESPN play-by-play and Sleeper projections, not Sleeper’s in-app number. {extra}</footer>')


# ================================================================ week-to-week hub
def _pct(p):
    return "<1%" if 0 < p < .005 else ">99%" if .995 <= p < 1 else f"{p:.0%}"


def _move(delta, fmt="{:+.0%}", eps=.005):
    if delta > eps:
        return f'<span class="pos" style="font-size:12px">▲ {fmt.format(delta).lstrip("+")}</span>'
    if delta < -eps:
        return f'<span class="neg" style="font-size:12px">▼ {fmt.format(-delta).lstrip("+")}</span>'
    return '<span class="muted" style="font-size:12px">–</span>'


def playoff_table(rows, prev, n_playoff, div_names):
    pv = {x["team"]: x for x in prev}
    trs = []
    for x in rows:
        p0 = pv.get(x["team"], {}).get("playoffs", x["playoffs"])
        status = (' <span class="chip pos" title="Clinched a first-round bye">Clinched bye</span>' if x.get("clinched_bye")
                  else ' <span class="chip pos" title="Clinched a playoff spot">Clinched playoffs</span>' if x.get("clinched")
                  else ' <span class="chip neg" title="Eliminated from playoff contention">Eliminated</span>' if x.get("eliminated") else "")
        trs.append(f'<tr><td class="team" style="white-space:nowrap">{esc(x["team"])}{status}</td>'
                   f'<td class="muted" style="white-space:nowrap">{esc(div_names.get(x["division"], ""))}</td>'
                   f'<td class="n">{x["wins"]:.0f}-{x["losses"]:.0f}</td>'
                   f'<td class="barcell"><div style="display:flex;align-items:center;gap:8px"><div class="track" style="flex:1"><span style="width:{100 * x["playoffs"]:.1f}%;background:var(--a)"></span></div>'
                   f'<b style="min-width:42px;text-align:right">{_pct(x["playoffs"])}</b></div></td>'
                   f'<td class="n">{_move(x["playoffs"] - p0)}</td><td class="n">{_pct(x["bye"])}</td><td class="n">{_pct(x["first"])}</td>'
                   f'<td class="n">{_pct(x["last"])}</td><td class="n">{x["proj_wins"]:.1f}</td></tr>')
    return (f'<div class="panel scroll"><table><thead><tr><th>Team</th><th>Division</th><th class="n">Record</th><th>Make playoffs</th>'
            f'<th class="n">This week</th><th class="n">Bye</th><th class="n">#1 seed</th><th class="n">Worst record</th><th class="n">Proj. wins</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            f'<p class="note">10,000 simulations of the rest of the regular season using the real remaining schedule. Each team’s weekly score is drawn '
            f'from its own scoring so far, pulled toward the league average early in the year. {n_playoff} teams make the playoffs: the top two '
            'in each division are in, the division winners get the byes, and the last spots go to the best remaining records as wild cards. '
            'Every tie goes to points for. “Worst record” is the chance of finishing with the league’s worst regular-season record. '
            '“This week” is the change since last week’s results. Clinched and eliminated tags are mathematical, not simulated: '
            'a clinch holds even if the team loses out, every rival wins out and every tie goes against it on points.</p>')


def power_table(rows, prev_rank):
    mx = max(x["score"] for x in rows) or 1
    trs = []
    for x in rows:
        was = prev_rank.get(x["team"])
        mv = (f'<span class="pos">▲{was - x["rank"]}</span>' if was and was > x["rank"] else
              f'<span class="neg">▼{x["rank"] - was}</span>' if was and was < x["rank"] else '<span class="muted">–</span>')
        trs.append(f'<tr><td class="team">{x["rank"]}</td><td class="n" style="font-size:13px">{mv}</td><td class="team" style="white-space:nowrap">{esc(x["team"])}</td>'
                   f'<td class="barcell"><div class="track"><span style="width:{100 * x["score"] / mx:.1f}%;background:var(--a)"></span></div></td>'
                   f'<td class="n team">{x["score"]:.0f}</td><td class="n">{pct_s(x["allplay"])}</td><td class="n">{x["ppg"]:.1f}</td><td class="n">{x["recent"]:.1f}</td></tr>')
    return (f'<div class="panel scroll"><table><thead><tr><th>#</th><th class="n">Move</th><th>Team</th><th class="barcell">Power score</th><th class="n"></th>'
            f'<th class="n">All-play</th><th class="n">PPG</th><th class="n">Last 3</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Power score (0–100) = 50% all-play win rate + 25% season points per game + 25% last three weeks’ points per game '
            '(both as a rank against the league). Move = change from last week’s ranking.</p>')


def awards_tiles(aw, week):
    spec = [("upset", "Upset of the week", lambda v: f"{v:.0%}"), ("luckiest", "Luckiest win", lambda v: f"{v:.2f}"),
            ("unluckiest", "Unluckiest loss", lambda v: f"{v:.2f}"), ("best_call", "Best lineup call", lambda v: f"{v:.0%}"),
            ("worst_call", "Worst lineup call", lambda v: f"−{v:.1f}"), ("player", "Player of the week", lambda v: f"{v:.1f}"),
            ("bench", "Bench disaster", lambda v: f"{v:.1f}"), ("perfect", "Perfect lineups", lambda v: f"{v}")]
    tiles = []
    for k, label, f in spec:
        if k not in aw:
            continue
        who, v, why = aw[k]
        tiles.append(f'<div class="panel tile"><div class="k">{label}</div><div class="v">{f(v)}</div>'
                     f'<div class="s"><b style="color:var(--ink)">{esc(who)}</b> {esc(why)}</div></div>')
    return (f'<div class="tiles">{"".join(tiles)}</div><p class="note">Week {week}. Best lineup call = highest share of its best possible lineup; '
            'upset = the winner with the lowest pregame win probability. Perfect lineup = every starter belonged in the best possible '
            'lineup from that week’s roster.</p>')


def preview_cards(games, week):
    if not games:
        return '<div class="panel muted">No more regular-season games to preview.</div>'
    cards = []
    for g in games:
        f, d = g["fav"], g["dog"]
        def side(x, cls):
            key = f'{esc(x["key"][0])} {x["key"][1]:.1f}' if x["key"] else ""
            empty = (f'<div class="neg" style="font-size:12px">No projection (bye/out): {esc(", ".join(x["empty"]))}</div>' if x["empty"] else "")
            return (f'<div><div class="team {cls}">{esc(x["team"])}</div><div style="font:700 26px/1.1 var(--display)">{x["proj"]:.1f}</div>'
                    f'<div class="muted" style="font-size:13px">Key player: {key}</div>{empty}</div>')
        cards.append(f'<div class="panel" style="display:grid;gap:8px">'
                     f'<div style="display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:start">{side(f, "dot-a")}'
                     f'<div class="muted" style="padding-top:22px">vs</div><div style="text-align:right">{side(d, "dot-b")}</div></div>'
                     f'<div class="stack" style="height:10px"><span style="flex:{g["p"]:.3f};background:var(--a)"></span><span style="flex:{1 - g["p"]:.3f};background:var(--b)"></span></div>'
                     f'<div style="display:flex;justify-content:space-between;font-size:13px"><b class="dot-a">{_pct(g["p"])}</b>'
                     f'<span class="muted">projected margin {g["spread"]:.1f}</span><b class="dot-b">{_pct(1 - g["p"])}</b></div></div>')
    close = games[0]
    tile = (f'<p class="lede">Closest projected game: <b>{esc(close["fav"]["team"])}</b> vs <b>{esc(close["dog"]["team"])}</b> '
            f'({_pct(close["p"])}–{_pct(1 - close["p"])}). Biggest favorite: <b>{esc(games[-1]["fav"]["team"])}</b> at {_pct(games[-1]["p"])}.</p>')
    return (tile + f'<div class="grid2">{"".join(cards)}</div><p class="note">Week {week} odds from Sleeper projections (in this league’s scoring) for each team’s '
            'current starting lineup, as of the last site update. Lineups and projections change before kickoff.</p>')


def projection_table(rows, over, under, week):
    mx = max(abs(r["act"] - r["proj"]) for r in rows) or 1
    trs = []
    for r in rows:
        d = r["act"] - r["proj"]
        ld = r["last_act"] - r["last_proj"]
        w = 50 * abs(d) / mx
        bar = (f'<div style="position:relative;height:10px;background:var(--grid);border-radius:5px">'
               f'<span style="position:absolute;top:0;bottom:0;{"left:50%" if d >= 0 else f"right:50%"};width:{w:.1f}%;'
               f'background:var({"--good" if d >= 0 else "--bad"});border-radius:5px"></span>'
               f'<span style="position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--ink3)"></span></div>')
        trs.append(f'<tr><td class="team" style="white-space:nowrap">{esc(r["team"])}</td><td class="barcell">{bar}</td>'
                   f'<td class="n {"pos" if d >= 0 else "neg"}">{d:+.1f}</td><td class="n">{r["act"]:.1f}</td><td class="n muted">{r["proj"]:.1f}</td>'
                   f'<td class="n {"pos" if ld >= 0 else "neg"}">{ld:+.1f}</td></tr>')
    def plist(title, items, cls):
        li = "".join(f'<tr><td><b>{esc(x["player"])}</b> <span class="muted">{esc(x["team"])} · {x["starts"]} starts</span></td>'
                     f'<td class="n {cls}">{x["diff"]:+.1f}</td></tr>' for x in items)
        return f'<div class="panel"><h3 class="{cls}">{title}</h3><table>{li}</table></div>'
    return (f'<div class="panel scroll"><table><thead><tr><th>Team</th><th class="barcell">Season vs. projection</th><th class="n">+/−</th>'
            f'<th class="n">Scored</th><th class="n">Projected</th><th class="n">Wk {week}</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<div class="grid2" style="margin-top:14px">{plist("Beat their projections most", over, "pos")}{plist("Missed their projections most", under, "neg")}</div>'
            '<p class="note">Starting-lineup points against Sleeper’s pregame projections, scored with this league’s settings. Players need 2+ starts.</p>')


def close_table(rows, nail, margin=10):
    trs = "".join(f'<tr><td class="team">{esc(x["team"])}</td><td class="n team">{x["w"]}-{x["l"]}</td>'
                  f'<td class="n {"pos" if x["w"] > x["l"] else "neg" if x["w"] < x["l"] else "muted"}">{x["w"] - x["l"]:+d}</td></tr>' for x in rows)
    ng = "".join(f'<tr><td class="muted" style="white-space:nowrap">Wk {g["week"]}</td><td><b>{esc(g["winner"])}</b> {g["ws"]:.2f} – {g["ls"]:.2f} {esc(g["loser"])}</td>'
                 f'<td class="n team">{g["margin"]:.2f}</td></tr>' for g in nail[:8])
    n5 = sum(1 for g in nail if g["margin"] < 5)
    return (f'<p class="lede">{len(nail)} games decided by less than {margin} points so far, {n5} by less than 5.</p>'
            f'<div class="grid2"><div class="panel"><h3>Record in games decided by &lt;{margin}</h3><table>{trs}</table></div>'
            f'<div class="panel"><h3>Closest games</h3><table>{ng}</table></div></div>')


def trend_cards(rows, league, weeks):
    lo = min(min(r["pts"]) for r in rows + [{"pts": league}])
    hi = max(max(r["pts"]) for r in rows + [{"pts": league}])
    lo, hi = math.floor(lo / 10) * 10, math.ceil(hi / 10) * 10
    W, H, l, r_, t, b = 240, 90, 6, 6, 8, 16
    X = lambda i: l + (W - l - r_) * (i / max(1, len(weeks) - 1))
    Y = lambda v: t + (H - t - b) * (1 - (v - lo) / (hi - lo or 1))
    cards = []
    for x in rows:
        diff = x["recent"] - x["season"]
        pts = " ".join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(x["roll"]))
        lgp = " ".join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(league))
        dots = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="2.5" class="dot"><title>Week {weeks[i]}: {v:.1f}</title></circle>' for i, v in enumerate(x["pts"]))
        hover = json.dumps([[round(X(i), 1), round(Y(v), 1), weeks[i], round(v, 1), round(x["roll"][i], 1), round(league[i], 1)]
                            for i, v in enumerate(x["pts"])])
        svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(x["team"])} scoring trend">'
               f'<polyline points="{lgp}" fill="none" style="stroke:var(--ink3);stroke-dasharray:3 3;stroke-width:1.2"/>{dots}'
               f'<polyline points="{pts}" fill="none" style="stroke:var({"--good" if diff >= 0 else "--bad"});stroke-width:2.2"/>'
               f'<text x="{l}" y="{H - 3}">Wk {weeks[0]}</text><text x="{W - r_}" y="{H - 3}" text-anchor="end">Wk {weeks[-1]}</text>'
               f'<line class="xh" y1="{t}" y2="{H - b}" style="display:none"/><circle class="xd" r="4" style="display:none"/>'
               f'<rect class="hit" x="0" y="0" width="{W}" height="{H}" fill="transparent"/></svg>')
        cards.append(f'<div class="panel trend-card" style="padding:12px 14px" data-pts="{esc(hover)}" data-w="{W}" data-season="{x["season"]:.1f}">'
                     f'<div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline">'
                     f'<b style="font-size:14px">{esc(x["team"])}</b><span class="{"pos" if diff >= 0 else "neg"}" style="font-size:13px">{"▲" if diff >= 0 else "▼"} {abs(diff):.1f}</span></div>'
                     f'<div class="wp-plot">{svg}<div class="wp-tip" hidden></div></div>'
                     f'<div class="muted" style="font-size:12px">Last 3: <b style="color:var(--ink)">{x["recent"]:.1f}</b> · season {x["season"]:.1f}</div></div>')
    return (f'<div class="trend-grid">{"".join(cards)}</div><p class="note">Colored line = 3-week rolling average (green if the last three weeks beat the season '
            'average, red if not); dots = each week’s score; dashed line = league average. Covers every week played so far; ▲/▼ is the last three weeks against the season average. '
            'Hover or tap a chart for each week’s numbers. Sorted from hottest to coldest.</p>')


def position_table(rows, avg):
    n = len(rows)
    head = "".join(f'<th class="n">{p}</th>' for p in avg)
    trs = []
    for x in rows:
        cells = []
        for p in avg:
            rk = x["rank"][p]
            step = max(1, min(7, round(7 - 6 * (rk - 1) / max(1, n - 1))))
            fg = "#fff" if step >= 5 else "var(--ink)"
            cells.append(f'<td class="w" style="background:var(--r{step});color:{fg}" title="{p}: {x["ppg"][p]:.1f} per week (#{rk})">{x["ppg"][p]:.1f}'
                         f'<div style="font-size:10px;font-weight:400;opacity:.85">#{rk}</div></td>')
        trs.append(f'<tr><td class="team" style="white-space:nowrap">{esc(x["team"])}</td>{"".join(cells)}<td class="n team">{x["avg_rank"]:.1f}</td></tr>')
    foot = '<tr class="tot"><td>League average</td>' + "".join(f'<td class="n">{v:.1f}</td>' for v in avg.values()) + '<td></td></tr>'
    return (f'<div class="panel scroll"><table class="grid-t"><thead><tr><th>Team</th>{head}<th class="n">Avg rank</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody><tfoot>{foot}</tfoot></table></div>'
            '<p class="note">Starting-lineup points per week from each position (flex points go to the player’s position), with the league rank underneath. '
            'Darker = better rank. Sorted by average rank across positions.</p>')


def _xrows(key, rows, cells, detail, ncols, data):
    return "".join(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="{key}-{i}" '
                   + " ".join(f'data-{k}="{v:.2f}"' for k, v in data(x).items()) + '>'
                   f'<td class="muted rank"></td><td class="team" style="white-space:nowrap"><span class="chev" aria-hidden="true">▸</span> {esc(x["team"])}</td>{cells(x)}</tr>'
                   f'<tr class="xdetail" id="{key}-{i}" hidden><td colspan="{ncols}">{detail(x)}</td></tr>' for i, x in enumerate(rows))


def _plist(items, empty):
    if not items:
        return f'<span class="muted">{empty}</span>'
    return '<table class="picks">' + "".join(f'<tr><td class="muted">Wk {w}</td><td><b>{esc(n)}</b>{extra}</td><td class="n team">{v:.1f}</td></tr>'
                                             for w, n, v, extra in items) + '</table>'


def _sort_controls(key, opts):
    """Sort-by select for a .sortbars table; opts are (value, label, hint) with the default first."""
    return (f'<div class="hl-bar"><label for="{key}-sort">Sort by</label><select id="{key}-sort" autocomplete="off">'
            + "".join(f'<option value="{v}" data-plain data-dim data-hint="{esc(h)}"{" selected" if i == 0 else ""}>{esc(lab)}</option>'
                      for i, (v, lab, h) in enumerate(opts))
            + '</select><span class="muted sort-hint"></span></div>')


def bye_table(rows, min_ppg=8):
    mx = max(x["lost"] + x["to_come"] for x in rows) or 1

    def cells(x):
        return (f'<td class="barcell"><div class="stack" style="height:12px;min-width:120px;background:var(--grid)">'
                f'<span data-pos="lost" style="flex:{x["lost"] / mx:.4f};background:var(--c4)" title="Lost so far: {x["lost"]:.1f}"></span>'
                f'<span data-pos="future" style="flex:{x["to_come"] / mx:.4f};background:var(--c4b)" title="Still to come: {x["to_come"]:.1f}"></span>'
                f'<span style="flex:{max(0, 1 - (x["lost"] + x["to_come"]) / mx):.4f};background:transparent"></span></div></td>'
                f'<td class="n">{x["lost"]:.0f}</td><td class="n">{x["to_come"]:.0f}</td><td class="n team">{x["lost"] + x["to_come"]:.0f}</td>')

    def detail(x):
        return (f'<div class="grid2"><div><h3>Lost so far</h3>{_plist([(w, n, v, "") for w, n, v in x["past"]], "No byes yet")}</div>'
                f'<div><h3>Still to come (current roster)</h3>{_plist([(w, n, v, "") for w, n, v in x["future"]], "None left")}</div></div>')
    legend = ('<div class="legend"><span><i style="background:var(--c4)"></i>Lost so far</span>'
              '<span><i style="background:var(--c4b)"></i>Still to come</span></div>')
    controls = _sort_controls("byes", [("total", "Season total", "Most points lost to byes, past and future, first"),
                                       ("lost", "Lost so far", "Most bye points already lost first"),
                                       ("future", "Still to come", "Most bye points still ahead first")])
    data = lambda x: {"total": x["lost"] + x["to_come"], "lost": x["lost"], "future": x["to_come"]}
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table class="expand"><thead><tr><th></th><th>Team</th><th class="barcell">Points lost to byes</th>'
            f'<th class="n">So far</th><th class="n">To come</th><th class="n">Total</th></tr></thead>'
            f'<tbody>{_xrows("bye", rows, cells, detail, 6, data)}</tbody></table></div>'
            f'<p class="note">Each bye week of a player who averages {min_ppg}+ points a game counts his season average as points lost. '
            '“So far” uses the roster each team had that week; “To come” uses today’s roster and the rest of the regular season’s bye weeks, '
            'so it will move with trades and pickups. Click a team for the players.</p>')


INJURY_NOTES = {"Josh Jacobs": "abuse"}  # league editor's notes on why a player was out


def _inj_note(name):
    return f' <span class="muted">*{esc(INJURY_NOTES[name])}</span>' if name in INJURY_NOTES else ""


def injury_table(rows, min_ppg=8):
    mx = max(x["out"] + x["early"] for x in rows) or 1

    def cells(x):
        dead = (f'<span class="neg">{len(x["dead"])}</span>' if x["dead"] else '<span class="muted">0</span>')
        cut = (f'<span class="neg">{len(x["cut"])}</span>' if x["cut"] else '<span class="muted">0</span>')
        return (f'<td class="barcell"><div class="stack" style="height:12px;min-width:120px;background:var(--grid)">'
                f'<span data-pos="missed" style="flex:{x["out"] / mx:.4f};background:var(--bad)" title="Missed games: {x["out"]:.1f}"></span>'
                f'<span data-pos="left" style="flex:{x["early"] / mx:.4f};background:var(--c1)" title="Left hurt: {x["early"]:.1f}"></span>'
                f'<span style="flex:{max(0, 1 - (x["out"] + x["early"]) / mx):.4f};background:transparent"></span></div></td>'
                f'<td class="n">{x["out"]:.0f}</td><td class="n">{x["early"]:.0f}</td><td class="n team">{x["out"] + x["early"]:.0f}</td><td class="n">{dead}</td>'
                f'<td class="n">{cut}</td>')

    def detail(x):
        missed = _plist([(w, n, v, _inj_note(n)) for w, n, v in x["missed"]], "No missed games")
        left = _plist([(w, n, v, f' <span class="muted">scored {got:.1f}{"" if st else " · bench"}</span>') for w, n, v, got, st in x["left"]],
                      "Nobody left a game hurt")
        dead = ('<table class="picks">' + "".join(f'<tr><td class="muted">Wk {w}</td><td><b>{esc(n)}</b> <span class="muted">{pos or ""}</span></td>'
                                                  f'<td class="neg">{why}</td><td class="n team">0.0</td></tr>' for w, n, pos, why in x["dead"]) + '</table>'
                if x["dead"] else '<span class="muted">None — every starter played</span>')
        cut = ('<table class="picks">' + "".join(
            f'<tr><td class="muted">Wk {c["week"]}</td><td><b>{esc(c["player"])}</b> <span class="muted">{c["pos"] or ""}</span></td>'
            f'<td><span class="neg">{esc(c["status"])}{" · " + esc(c["injury"]) if c["injury"] else ""}</span></td>'
            f'<td class="muted">{"now on " + esc(c["now"]) if c["now"] else "free agent"}</td><td class="n team">{c["ppg"]:.1f}/gm</td></tr>'
            for c in x["cut"]) + '</table>') if x["cut"] else '<span class="muted">None</span>'
        return (f'<div class="grid2"><div><h3>Missed games</h3>{missed}</div><div><h3>Left a game hurt</h3>{left}</div></div>'
                f'<div class="grid2" style="margin-top:12px"><div><h3>Dead starts</h3>{dead}</div><div><h3>Dropped while hurt</h3>{cut}</div></div>')
    legend = ('<div class="legend"><span><i style="background:var(--bad)"></i>Missed games</span>'
              '<span><i style="background:var(--c1)"></i>Left a game hurt</span></div>')
    controls = _sort_controls("injuries", [("total", "Total", "Most points lost to injury first"),
                                           ("missed", "Missed games", "Most points lost to missed games first"),
                                           ("left", "Left hurt", "Most points lost to in-game injuries first"),
                                           ("dead", "Dead starts", "Most starters who didn’t play first"),
                                           ("cut", "Dropped while hurt", "Most injured players cut first")])
    data = lambda x: {"total": x["out"] + x["early"], "missed": x["out"], "left": x["early"], "dead": len(x["dead"]) + (x["out"] + x["early"]) / 1e4,
                      "cut": len(x["cut"]) + sum(c["ppg"] for c in x["cut"]) / 1e3}
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table class="expand"><thead><tr><th></th><th>Team</th><th class="barcell">Points lost to injury</th>'
            f'<th class="n">Missed</th><th class="n">Left hurt</th><th class="n">Total</th><th class="n">Dead starts</th><th class="n">Dropped hurt</th></tr></thead>'
            f'<tbody>{_xrows("inj", rows, cells, detail, 8, data)}</tbody></table></div>'
            f'<p class="note">Only players averaging {min_ppg}+ points a game count. <b>Missed</b>: he was on the roster but didn’t play while his NFL team did '
            '(injury, illness, inactive or suspension), costing his season average. <b>Left hurt</b>: ESPN’s play-by-play logged him '
            '“injured during the play” and he never showed up in a play again or got a “returned to the game” note; the cost is his season average '
            'minus what he’d scored when he went down. <b>Dead starts</b>: players left in the lineup who didn’t play at all (on bye or out). <b>Dropped hurt</b>: players averaging 5+ a game the team cut who are still listed injured (IR, PUP, out or doubtful) and haven’t played since; Sleeper doesn’t say whether an injury is season-ending, so the listed status and injury are shown instead. Click a team for the players.</p>')


def _biggest_cell(b, season=None):
    if not b or not b.get("player"):
        return '<td class="muted" data-v="0">—</td>'
    when = f'{season} wk {b["week"]}' if season else f'wk {b["week"]}'
    return (f'<td data-v="{b["bid"]}" style="white-space:nowrap"><b>${b["bid"]}</b> {esc(b["player"])}'
            f'<div class="muted" style="font-size:12px">{when}</div></td>')


def overbid_table(rows, budget=100):
    mx = max(x["spent"] for x in rows) or 1

    def cells(x):
        need = x["spent"] - x["over"]
        rate = f'{x["won"] / x["bids"]:.0%}' if x["bids"] else "—"
        return (f'<td class="barcell"><div class="stack" style="height:12px;min-width:120px;background:var(--grid)">'
                f'<span data-pos="need" style="flex:{need / mx:.4f};background:var(--c1)" title="Needed to win: ${need}"></span>'
                f'<span data-pos="over" style="flex:{x["over"] / mx:.4f};background:var(--bad)" title="Overbid: ${x["over"]}"></span>'
                f'<span style="flex:{max(0, 1 - x["spent"] / mx):.4f};background:transparent"></span></div></td>'
                f'<td class="n team">${x["over"]}</td><td class="n">${x["spent"]}</td><td class="n">{x["bids"]}</td><td class="n">{x["won"]}</td>'
                f'<td class="n muted">{rate}</td><td class="n">{x["moves"]}<div class="muted" style="font-size:11px">{x["fa"]} FA</div></td>'
                + _biggest_cell(x["biggest"]))

    def detail(x):
        if not x["claims"]:
            return '<span class="muted">No waiver claims yet</span>'
        trs = []
        for c in x["claims"]:
            if c["won"]:
                vs = f'next bid ${c["next"]}' if c["next"] is not None else "uncontested"
                res = (f'<span class="pos">Won</span> <span class="muted">· {vs}</span>'
                       + (f' · <span class="neg">${c["over"]} over</span>' if c["over"] else ""))
            else:
                res = f'<span class="muted">Lost · {esc(c["why"])}</span>'
            drop = f'<span class="muted">dropped {esc(", ".join(c["dropped"]))}</span>' if c["dropped"] and c["won"] else ""
            trs.append(f'<tr><td class="muted">Wk {c["week"]}</td><td><b>{esc(c["player"])}</b> <span class="muted">{c["pos"] or ""}</span></td>'
                       f'<td class="n team">${c["bid"]}</td><td>{res}</td><td>{drop}</td></tr>')
        return f'<table class="picks">{"".join(trs)}</table>'
    legend = ('<div class="legend"><span><i style="background:var(--c1)"></i>Needed to win</span>'
              '<span><i style="background:var(--bad)"></i>Overbid</span></div>')
    controls = _sort_controls("overbids", [("over", "Overbid $", "Most money left on the table first"),
                                           ("spent", "Spent $", "Biggest spenders first"),
                                           ("bids", "Total bids", "Most claims put in first"),
                                           ("won", "Successful bids", "Most claims won first"),
                                           ("rate", "Win rate", "Highest share of claims won first"),
                                           ("big", "Biggest spend", "Biggest single winning bid first"),
                                           ("moves", "Roster moves", "Most players added (waiver wins plus free agents) first")])
    data = lambda x: {"over": x["over"] + x["spent"] / 1e4, "spent": x["spent"] + x["over"] / 1e4, "bids": x["bids"] + x["won"] / 100,
                      "won": x["won"] + x["bids"] / 100, "rate": (x["won"] / x["bids"] if x["bids"] else -1) + x["bids"] / 1e4,
                      "big": x["biggest"]["bid"] + x["spent"] / 1e4, "moves": x["moves"] + x["won"] / 1000, "need": 0}
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table class="expand"><thead><tr><th></th><th>Team</th><th class="barcell">FAAB spent on wins</th>'
            f'<th class="n">Overbid</th><th class="n">Spent</th><th class="n">Bids</th><th class="n">Won</th><th class="n">Win %</th><th class="n">Roster moves</th><th>Biggest spend</th></tr></thead>'
            f'<tbody>{_xrows("ob", rows, cells, detail, 10, data)}</tbody></table></div>'
            f'<p class="note">Overbid is how much a winning claim beat the next-highest bid on the same player by; when nobody else put in a claim, '
            f'the whole bid counts, since the minimum bid is $0. Ties won on waiver priority count as $0 over. Bids count every waiver claim, '
            f'including $0 claims and ones that lost or failed because the roster would have been too full. Roster moves = players actually added: waiver claims won plus free agent adds (FA). Budget is ${budget}. Click a team for every claim.</p>')


def column(paras, by, source="this week’s stats"):
    if not paras:
        return '<div class="panel muted">Nothing to say this week. Enjoy it while it lasts.</div>'
    who = f"Written by {'Claude' if by == 'Claude' else 'the dashboard'} from {source}."
    return (f'<div class="panel column">{"".join(f"<p>{p}</p>" for p in paras)}</div>'
            f'<p class="note">{who} All in good fun; complaints can be filed with your waiver wire.</p>')


def season_tabs(tabs, current, root):
    """tabs: (label, path from the site root); root: relative path from this page to the site root."""
    return ('<nav class="seasons" aria-label="Seasons">'
            + "".join(f'<a href="{root}{path}"{" aria-current=page" if label == current else ""}>{esc(label)}</a>' for label, path in tabs)
            + '</nav>')


def drop_table(rows):
    if not rows:
        return '<div class="panel muted">No regrettable drops yet. Give it time.</div>'
    mx = max(x["gain"] for x in rows) or 1
    ppg = lambda pts, g: f"{pts / g:.1f}" if g else "—"
    trs = []
    for i, x in enumerate(rows, 1):
        went = x["now"] or (x["kept_by"][-1] if x["kept_by"] else None)
        where = (f'now on <b>{esc(x["now"])}</b>' if x["now"] else f'was on {esc(went)}, now a free agent' if went else "still a free agent")
        if x["readded"]:
            where += ' · <span class="muted">re-added later</span>'
        hurt = f'<div class="neg" style="font-size:12px">{x["started_elsewhere"]:.1f} pts in other teams’ lineups</div>' if x["started_elsewhere"] >= 1 else ""
        trs.append(f'<tr><td class="n muted">{i}</td><td data-v="{esc(x["player"].lower())}"><b>{esc(x["player"])}</b> <span class="muted">{x["pos"] or ""}</span>'
                   f'<div style="font-size:12.5px">{where}</div></td>'
                   f'<td class="team" style="white-space:nowrap" data-v="{esc(x["team"].lower())}">{esc(x["team"])}<div class="muted" style="font-size:12px;font-weight:400">before week {x["week"]}</div></td>'
                   f'<td class="n" data-v="{x["before_ppg"]:.2f}">{ppg(x["before"], x["before_games"])}<div class="muted" style="font-size:12px;white-space:nowrap">{x["before_games"]} wk{"" if x["before_games"] == 1 else "s"} · {x["before"]:.1f} pts</div></td>'
                   f'<td class="n muted" data-v="{x["repl"]:.2f}">{x["repl"]:.1f}<div style="font-size:12px">{x["pos"]}</div></td>'
                   f'<td class="n team" data-v="{x["after_ppg"]:.2f}">{x["after_ppg"]:.1f}<div class="muted" style="font-size:12px;font-weight:400;white-space:nowrap">{x["after_games"]} g · {x["after"]:.1f} pts</div></td>'
                   f'<td class="barcell" data-v="{x["gain"]:.2f}"><div style="display:flex;align-items:center;gap:8px"><div class="track" style="flex:1"><span style="width:{100 * x["gain"] / mx:.1f}%;background:var(--bad)"></span></div>'
                   f'<b class="neg">+{x["gain"]:.1f}</b></div>{hurt}</td>'
                   f'<td class="n" data-v="{x["best"][0]:.1f}">{x["best"][0]:.1f}<div class="muted" style="font-size:12px">wk {x["best"][1]}</div></td></tr>')
    return (f'<div class="panel scroll"><table class="sortable"><thead><tr><th class="n">#</th><th>Player</th><th>Dropped by</th><th class="n">Avg with them</th><th class="n">Replacement</th>'
            f'<th class="n">Avg since</th><th class="barcell" aria-sort="descending">Regret per game</th><th class="n">Best game</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">The players whose drops have aged worst. Regret per game = what he’s averaged since the drop (games he played, wherever he '
            'landed) minus the higher of what he averaged for that team (every week on the roster, bench and did-not-play weeks counting as 0, '
            'byes skipped) and a replacement-level starter at his position (roughly the worst starter in the league there: about 18 for a QB, '
            '11 for a WR, 10 for an RB, 8 for a TE). So a drop only counts if he’s been better than both what he gave the team and what was easy to '
            'find anyway, which keeps quarterbacks’ big numbers from crowding out everyone else. At least 2 games since the drop. '
            'If the team picked him back up, the count stops there. Kickers and defenses are left out, since streaming them is the plan. Click a column header to sort.</p>')


# ---------------------------------------------------------------- all-time page
def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def alltime_sections(sums):
    """sums: season summaries, newest first. Returns [(key, title, html)]."""
    seasons = [x["season"] for x in sums]
    done = [x for x in sums if x["complete"]]
    owners = []
    for x in sums:
        owners += [o for o in x["teams"] if o not in owners]
    name = {o: next(x["teams"][o]["team"] for x in sums if o in x["teams"]) for o in owners}  # latest team name
    aka = {o: list(dict.fromkeys(x["teams"][o]["team"] for x in sums if o in x["teams"] and x["teams"][o]["team"] != name[o])) for o in owners}
    n_teams = max(len(x["teams"]) for x in sums)

    def who(o, team=None):
        t = team or name.get(o, "?")
        alias = f' title="also: {esc(", ".join(aka[o]))}"' if o in aka and aka[o] and not team else ""
        sub = f' <span class="muted" style="font-size:12px">(now {esc(name[o])})</span>' if team and o in name and team != name[o] else ""
        return f'<span class="team"{alias}>{esc(t)}</span>{sub}'

    # standings
    rows = []
    for o in owners:
        ts = [x["teams"][o] for x in sums if o in x["teams"]]
        cs = [x["teams"][o] for x in done if o in x["teams"]]
        w, l, t = (sum(z[k] for z in ts) for k in ("wins", "losses", "ties"))
        g = w + l + t
        rows.append({"o": o, "seasons": len(ts), "w": w, "l": l, "t": t, "pct": (w + t / 2) / g if g else 0,
                     "pf": sum(z["pf"] for z in ts), "pa": sum(z["pa"] for z in ts), "ppg": sum(z["pf"] for z in ts) / g if g else 0,
                     "po": sum(1 for z in cs if z["playoffs"]), "done": len(cs),
                     "titles": sum(1 for z in cs if z["finish"] == 1), "last": sum(1 for z in cs if z["finish"] == n_teams),
                     "best": min((z["finish"] for z in cs if z["finish"]), default=None)})
    rows.sort(key=lambda r: (-r["pct"], -r["pf"]))
    trs = []
    for r in rows:
        po_pct = r["po"] / r["done"] if r["done"] else 0
        trs.append(f'<tr><td data-v="{esc(name[r["o"]].lower())}">{who(r["o"])}</td><td class="n">{r["seasons"]}</td>'
                   f'<td class="n team" data-v="{r["w"] + r["t"] / 2 - r["l"] / 1000}">{r["w"]}-{r["l"]}{f"-{r["t"]}" if r["t"] else ""}</td>'
                   f'<td class="n">{r["pct"]:.3f}</td>'
                   f'<td class="n">{r["pf"]:,.1f}</td><td class="n">{r["pa"]:,.1f}</td><td class="n">{r["ppg"]:.1f}</td>'
                   f'<td class="n" data-v="{po_pct + r["po"] / 100:.4f}">{r["po"]}/{r["done"]} <span class="muted">({po_pct:.0%})</span></td>'
                   f'<td class="n" data-v="{r["titles"]}">{"🏆" * r["titles"] or "<span class=muted>0</span>"}</td>'
                   f'<td class="n" data-v="{r["last"]}">{"💩" * r["last"] or "<span class=muted>0</span>"}</td>'
                   f'<td class="n" data-v="{-(r["best"] or 99)}">{_ordinal(r["best"]) if r["best"] else "—"}</td></tr>')
    cur = [x for x in sums if not x["complete"]]
    standings = (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>Manager (current team)</th><th class="n">Seasons</th>'
                 '<th class="n">Record</th><th class="n" aria-sort="descending">Win %</th><th class="n">Points for</th><th class="n">Points against</th><th class="n">PPG</th>'
                 '<th class="n">Playoffs</th><th class="n">Titles</th><th class="n">Last place</th><th class="n">Best finish</th></tr></thead>'
                 f'<tbody>{"".join(trs)}</tbody></table></div>'
                 f'<p class="note">Regular-season games only, {seasons[-1]}–{seasons[0]}'
                 + (f' ({cur[0]["season"]} so far, through week {cur[0]["weeks"]})' if cur else "")
                 + '. Playoffs, titles, last places and best finish count finished seasons only. Last place = finished '
                 f'{_ordinal(n_teams)}: lost every game in the toilet bowl. Managers are tracked by Sleeper account, so team renames stay together; '
                 'hover a name for its old team names. Click a column header to sort.</p>')

    # finishes by year
    head = "".join(f'<th class="n">{x["season"]}</th>' for x in sums)
    ftrs = []
    for r in sorted(rows, key=lambda r: st_mean([x["teams"][r["o"]]["finish"] or x["teams"][r["o"]]["reg_rank"] for x in sums if r["o"] in x["teams"]])):
        cells = []
        for x in sums:
            z = x["teams"].get(r["o"])
            if not z:
                cells.append('<td class="n muted">—</td>')
                continue
            place = z["finish"] or z["reg_rank"]
            step = max(1, min(7, round(7 - 6 * (place - 1) / max(1, n_teams - 1))))
            fg = "#fff" if step >= 5 else "var(--ink)"
            mark = " 🏆" if z["finish"] == 1 else " 💩" if z["finish"] == n_teams else ""
            tip = (f'{esc(z["team"])}: {z["wins"]}-{z["losses"]}, {z["pf"]:.1f} PF, {_ordinal(z["reg_rank"])} in the regular season'
                   + (f', finished {_ordinal(z["finish"])}' if z["finish"] else " (in progress)"))
            label = _ordinal(place) + mark if z["finish"] else f'<i>{_ordinal(place)}</i>'
            cells.append(f'<td class="w" style="background:var(--r{step});color:{fg};white-space:nowrap" title="{tip}">{label}</td>')
        ftrs.append(f'<tr><td>{who(r["o"])}</td>{"".join(cells)}</tr>')
    finishes = (f'<div class="panel scroll"><table class="grid-t"><thead><tr><th>Manager</th>{head}</tr></thead><tbody>{"".join(ftrs)}</tbody></table></div>'
                '<p class="note">Final place each season: 1st–6th from the playoff bracket, 7th–12th from the toilet bowl (lose every game there and you finish last); darker = better. The current season shows '
                'its regular-season standing in italics. Hover a cell for the record and that year’s team name.</p>')

    # champions and last places
    ctrs = []
    for x in done:
        by = {z["finish"]: (o, z) for o, z in x["teams"].items() if z["finish"]}
        cell = lambda k: (f'{who(by[k][0], by[k][1]["team"])} <span class="muted">{by[k][1]["wins"]}-{by[k][1]["losses"]}</span>' if k in by else "—")
        ctrs.append(f'<tr><td class="team">{x["season"]}</td><td>🏆 {cell(1)}</td><td>{cell(2)}</td><td>💩 {cell(n_teams)}</td></tr>')
    champs = (f'<div class="panel scroll"><table><thead><tr><th>Season</th><th>Champion</th><th>Runner-up</th><th>Last place</th></tr></thead>'
              f'<tbody>{"".join(ctrs)}</tbody></table></div>'
              '<p class="note">Team names as they were that season. Last place = lost every game in the toilet bowl.</p>') if ctrs else '<div class="panel muted">No finished seasons yet.</div>'

    # keepers
    keepers = sorted((dict(k, season=x["season"]) for x in sums for k in x["keepers"]), key=lambda k: -k["value"])
    def ktable(items):
        return "".join(f'<tr><td class="muted">{k["season"]}</td><td><b>{esc(k["player"])}</b> <span class="muted">{k["pos"] or ""}</span></td>'
                       f'<td>{who(k["owner"], k["team"])}</td><td class="n muted">R{k["round"]}</td><td class="n team">{k["pts"]:.1f}</td>'
                       f'<td class="n {"pos" if k["value"] >= 0 else "neg"}">{signed(k["value"], 1)}</td></tr>' for k in items)
    kown = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for k in keepers:
        if k["owner"]:
            kown[k["owner"]][0] += 1
            kown[k["owner"]][1] += k["pts"]
            kown[k["owner"]][2] += k["value"]
    kh = '<thead><tr><th>Season</th><th>Keeper</th><th>Kept by</th><th class="n">Round</th><th class="n">Points</th><th class="n">vs. slot</th></tr></thead>'
    keep_html = (f'<div class="grid2"><div class="panel scroll"><h3 class="pos">Best keepers</h3><table>{kh}{ktable(keepers[:8])}</table></div>'
                 f'<div class="panel scroll"><h3 class="neg">Worst keepers</h3><table>{kh}{ktable(keepers[::-1][:8])}</table></div></div>'
                 '<h3 style="margin-top:18px">Keeper record by manager</h3><div class="panel scroll"><table><thead><tr><th>Manager</th><th class="n">Keepers</th>'
                 '<th class="n">Points</th><th class="n">vs. slot</th></tr></thead><tbody>'
                 + "".join(f'<tr><td>{who(o)}</td><td class="n">{v[0]}</td><td class="n">{v[1]:.1f}</td>'
                           f'<td class="n {"pos" if v[2] >= 0 else "neg"}">{signed(v[2], 1)}</td></tr>'
                           for o, v in sorted(kown.items(), key=lambda kv: -kv[1][2]))
                 + '</tbody></table></div><p class="note">Each keeper’s regular-season points that year, and how that compares with what a '
                   'pick in the same draft slot usually scored (median of picks within 15 spots). Round = the draft slot the keeper used.</p>') if keepers else '<div class="panel muted">No keepers found.</div>'

    # trades
    trades_ = []
    for x in sums:
        for t in x["trades"]:
            if len(t["sides"]) == 2:
                a, b = sorted(t["sides"], key=lambda sd: -sd["total"])
                trades_.append((a["total"] - b["total"], x["season"], t["week"], a, b))
    trades_.sort(key=lambda z: -z[0])
    def side(sd, cls):
        got = ", ".join(f'{esc(g["player"])} <span class="muted">{g["since"]:.0f}</span>' for g in sd["got"]) or '<span class="muted">nothing</span>'
        picks = (" + " + esc(", ".join(sd["picks"]))) if sd["picks"] else ""
        return f'<div><b class="{cls}">{who(sd["owner"], sd["team"])}</b> <span class="muted">got</span> {got}{picks} <b>= {sd["total"]:.1f}</b></div>'
    trade_html = ("".join(f'<div class="panel" style="margin-bottom:10px"><div class="muted" style="font-size:13px;margin-bottom:4px">'
                          f'{season}{f", week {wk}" if wk else ""} · decided by <b class="neg">{gap:.1f}</b> points</div>'
                          f'{side(a, "pos")}{side(b, "neg")}</div>' for gap, season, wk, a, b in trades_[:8])
                  + '<p class="note">The most lopsided trades: points each side’s players scored for the rest of that regular season. '
                    'Draft picks are listed but not scored.</p>') if trades_ else '<div class="panel muted">No trades yet.</div>'

    # pickups and drops
    picks_ = sorted((dict(a, season=x["season"]) for x in sums for a in x["pickups"]), key=lambda a: -a["total"])[:10]
    drops_ = sorted((dict(d, season=x["season"]) for x in sums for d in x["drops"]), key=lambda d: -d.get("gain", 0))[:10]
    ph = "".join(f'<tr><td class="muted">{a["season"]}</td><td><b>{esc(a["player"])}</b> <span class="muted">{a["pos"] or ""}</span></td>'
                 f'<td>{who(a["owner"], a["team"])}</td><td class="n muted">${a["bid"]}</td><td class="n">{a["games"]}</td>'
                 f'<td class="n team">{a["total"]:.1f}</td></tr>' for a in picks_)
    def dppg(pts, g):
        return pts / g if g else 0.0
    dh = "".join(f'<tr><td class="muted">{d["season"]}</td><td><b>{esc(d["player"])}</b> <span class="muted">{d["pos"] or ""}</span></td>'
                 f'<td>{who(d["owner"], d["team"])}</td><td class="n muted">wk {d["week"]}</td>'
                 f'<td class="n">{dppg(d["before"], d.get("before_games", 0)):.1f}</td>'
                 f'<td class="n">{dppg(d["after"], d["after_games"]):.1f}</td>'
                 f'<td class="n team neg">+{d.get("gain", 0):.1f}</td></tr>' for d in drops_)
    moves = (f'<div class="panel scroll"><h3 class="pos">Best waiver pickups</h3><table><thead><tr><th>Season</th><th>Player</th><th>Picked up by</th>'
             f'<th class="n">Bid</th><th class="n">Games</th><th class="n">Points</th></tr></thead><tbody>{ph}</tbody></table></div>'
             f'<div class="panel scroll" style="margin-top:14px"><h3 class="neg">Worst drops</h3><table><thead><tr><th>Season</th><th>Player</th><th>Dropped by</th>'
             f'<th class="n">Dropped</th><th class="n">Avg with them</th><th class="n">Avg since</th><th class="n">Regret per game</th></tr></thead><tbody>{dh}</tbody></table></div>'
             '<p class="note">Pickups: points scored for the team that picked him up (waiver or free agent), that season. '
             'Drops: ranked by regret per game, what he averaged after the drop minus the higher of his average for that team and a '
             'replacement-level starter at his position; at least 2 games after, kickers and defenses left out.</p>')
    # head to head
    h2h = collections.defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "pw": 0, "pl": 0})
    for x in sums:
        for w, a, sa, b, sb, playoff in x.get("games", []):
            for me, mine, them, theirs in ((a, sa, b, sb), (b, sb, a, sa)):
                c = h2h[(me, them)]
                c["w" if mine > theirs else "l" if mine < theirs else "t"] += 1
                c["pf"] += mine
                c["pa"] += theirs
                if playoff:
                    c["pw" if mine > theirs else "pl"] += 1
    order = [r["o"] for r in rows]
    hhead = "".join(f'<th class="ang" title="{esc(name[o])}"><div>{esc(name[o])}</div></th>' for o in order)
    htrs = []
    for me in order:
        cells = []
        for them in order:
            if me == them:
                cells.append('<td style="background:var(--grid)"></td>')
                continue
            c = h2h.get((me, them))
            if not c or not (c["w"] + c["l"] + c["t"]):
                cells.append('<td class="n muted">—</td>')
                continue
            g = c["w"] + c["l"] + c["t"]
            pct = (c["w"] + c["t"] / 2) / g
            bg = ("var(--good)" if pct > .5 else "var(--bad)" if pct < .5 else "var(--grid)")
            alpha = 0 if pct == .5 else min(1, abs(pct - .5) * 2) * .55 + .12
            po = f', playoffs {c["pw"]}-{c["pl"]}' if c["pw"] + c["pl"] else ""
            tip = f'{esc(name[me])} vs {esc(name[them])}: {c["w"]}-{c["l"]}{f"-{c["t"]}" if c["t"] else ""}{po}; avg score {c["pf"] / g:.1f}–{c["pa"] / g:.1f}'
            star = "*" if c["pw"] + c["pl"] else ""
            cells.append(f'<td class="n h2h" title="{tip}" style="position:relative;white-space:nowrap">'
                         f'<span style="position:absolute;inset:0;background:{bg};opacity:{alpha:.2f}"></span>'
                         f'<span style="position:relative">{c["w"]}-{c["l"]}{f"-{c["t"]}" if c["t"] else ""}{star}</span></td>')
        tot = [h2h[(me, o)] for o in order if (me, o) in h2h]
        htrs.append(f'<tr><td style="white-space:nowrap">{who(me)}</td>{"".join(cells)}'
                    f'<td class="n team" style="padding-left:56px">{sum(c["w"] for c in tot)}-{sum(c["l"] for c in tot)}</td></tr>')
    # rivalries worth calling out
    pairs = []
    for (a, b), c in h2h.items():
        if a < b:
            g = c["w"] + c["l"] + c["t"]
            pairs.append((a, b, c, g))
    lop = max(pairs, key=lambda p: (abs(p[2]["w"] - p[2]["l"]), p[3]), default=None)
    most = max(pairs, key=lambda p: (p[3], -abs(p[2]["w"] - p[2]["l"])), default=None)
    closest = min((p for p in pairs if p[3] >= 3), key=lambda p: abs(p[2]["pf"] - p[2]["pa"]) / p[3], default=None)
    def rival(label, p, why):
        a, b, c, g = p
        if c["l"] > c["w"]:
            a, b = b, a
            c = h2h[(a, b)]
        return (f'<div class="panel tile"><div class="k">{label}</div><div class="v">{c["w"]}-{c["l"]}{f"-{c["t"]}" if c["t"] else ""}</div>'
                f'<div class="s"><b style="color:var(--ink)">{esc(name[a])}</b> over <b style="color:var(--ink)">{esc(name[b])}</b> · {why(c, g)}</div></div>')
    tiles = ""
    if pairs:
        tiles = ('<div class="tiles" style="margin-bottom:14px">'
                 + rival("Most one-sided", lop, lambda c, g: f"{g} meetings")
                 + rival("Most meetings", most, lambda c, g: f"{g} games, avg {c['pf'] / g:.1f}–{c['pa'] / g:.1f}")
                 + (rival("Closest rivalry", closest, lambda c, g: f"{(c['pf'] - c['pa']) / g:+.1f} points a game") if closest else "")
                 + '</div>')
    headtohead = (tiles + f'<div class="panel scroll"><table class="grid-t" style="font-size:13px"><thead><tr><th>Manager ↓ vs →</th>{hhead}<th class="n" style="padding-left:56px;vertical-align:bottom">Total</th></tr></thead>'
                  f'<tbody>{"".join(htrs)}</tbody></table></div>'
                  '<p class="note">Each row is that manager’s record against the column manager: regular season plus playoff games '
                  '(consolation and 5th-place games left out). Green = winning record, red = losing; * = includes playoff meetings. Hover a cell for the playoff '
                  'record and average score.</p>')

    seas_order = {x["season"]: i for i, x in enumerate(reversed(sums))}  # oldest = 0
    def rec_s(w, l, t=0):
        return f"{w}-{l}" + (f"-{t}" if t else "")

    # playoff records
    po = collections.defaultdict(lambda: {"w": 0, "l": 0, "apps": 0, "finals": 0, "titles": 0})
    for x in sums:
        for w, a, sa, b, sb, playoff in x.get("games", []):
            if playoff:
                po[a]["w" if sa > sb else "l"] += 1
                po[b]["w" if sb > sa else "l"] += 1
        for o, z in x["teams"].items():
            if z["playoffs"]:
                po[o]["apps"] += 1
            if z["finish"] in (1, 2):
                po[o]["finals"] += 1
            if z["finish"] == 1:
                po[o]["titles"] += 1
    reg = {r["o"]: r for r in rows}
    ptrs = "".join(
        f'<tr><td data-v="{esc(name[o].lower())}">{who(o)}</td><td class="n">{c["apps"]}</td>'
        f'<td class="n team" data-v="{c["w"] - c["l"] / 100}">{rec_s(c["w"], c["l"])}</td>'
        f'<td class="n" data-v="{c["w"] / (c["w"] + c["l"]) if c["w"] + c["l"] else -1}">{f"{c["w"] / (c["w"] + c["l"]):.3f}" if c["w"] + c["l"] else "<span class=muted>—</span>"}</td>'
        f'<td class="n muted">{reg[o]["pct"]:.3f}</td>'
        f'<td class="n">{c["finals"]}</td><td class="n" data-v="{c["titles"]}">{"🏆" * c["titles"] or "<span class=muted>0</span>"}</td></tr>'
        for o, c in sorted(((o, po[o]) for o in owners), key=lambda kv: (-kv[1]["titles"], -kv[1]["w"], kv[1]["l"], -kv[1]["apps"])))
    playoffs_html = (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>Manager</th><th class="n">Trips</th><th class="n">Playoff record</th>'
                     f'<th class="n">Playoff win %</th><th class="n">Regular-season win %</th><th class="n">Finals</th><th class="n">Titles</th></tr></thead>'
                     f'<tbody>{ptrs}</tbody></table></div><p class="note">Winners-bracket games only, including the 3rd-place game (the 5th-place game is left out). '
                     'Compare the two win % columns to find the regular-season bullies and the playoff closers. Click a column header to sort.</p>')

    # record book
    allg = [(x["season"], w, a, sa, b, sb, pl) for x in sums for w, a, sa, b, sb, pl in x.get("games", [])]
    scores = [(sa, x, w, a, pl) for x, w, a, sa, b, sb, pl in allg] + [(sb, x, w, b, pl) for x, w, a, sa, b, sb, pl in allg]
    def wk(x, w, pl):
        return f'{x} wk {w}{" (playoffs)" if pl else ""}'
    def lst(title, items, fmt, cls=""):
        return (f'<div class="panel"><h3 class="{cls}">{title}</h3><table>'
                + "".join(f'<tr><td class="muted">{i}</td>{fmt(it)}</tr>' for i, it in enumerate(items, 1)) + '</table></div>')
    hi = sorted(scores, key=lambda z: -z[0])[:5]
    lo = sorted(scores, key=lambda z: z[0])[:5]
    blow = sorted(allg, key=lambda g: -abs(g[3] - g[5]))[:5]
    close = sorted(allg, key=lambda g: abs(g[3] - g[5]))[:5]
    def game_fmt(g):
        x, w, a, sa, b, sb, pl = g
        (wo, ws), (lo_, ls) = ((a, sa), (b, sb)) if sa >= sb else ((b, sb), (a, sa))
        return (f'<td>{who(wo)} <b>{ws:.1f}</b> – {ls:.1f} {who(lo_)}<div class="muted" style="font-size:12px">{wk(x, w, pl)}</div></td>'
                f'<td class="n team">{abs(sa - sb):.2f}</td>')
    seasons_ = [(x["season"], o, z) for x in sums if x["complete"] for o, z in x["teams"].items()]
    best_pf = sorted(seasons_, key=lambda t: -t[2]["pf"])[:5]
    worst_pf = sorted(seasons_, key=lambda t: t[2]["pf"])[:5]
    season_fmt = lambda t: (f'<td>{who(t[1], t[2]["team"])}<div class="muted" style="font-size:12px">{t[0]} · {rec_s(t[2]["wins"], t[2]["losses"], t[2]["ties"])}'
                            f' · finished {_ordinal(t[2]["finish"])}</div></td><td class="n team">{t[2]["pf"]:,.1f}</td>')
    lineups = {(x["season"], k): v for x in sums for k, v in x.get("lineups", {}).items()}
    def score_lst(title, items, cls, key):
        trs = []
        for i, z in enumerate(items, 1):
            lu = lineups.get((z[1], f"{z[2]}:{z[3]}"))
            head = (f'<td class="muted">{i}</td><td>{"<span class=chev aria-hidden=true>▸</span> " if lu else ""}{who(z[3])}'
                    f'<div class="muted" style="font-size:12px">{wk(z[1], z[2], z[4])}</div></td><td class="n team">{z[0]:.2f}</td>')
            if not lu:
                trs.append(f'<tr>{head}</tr>')
                continue
            det = "".join(f'<tr><td class="muted">{esc(sl)}</td><td>' + (f'<b>{esc(n)}</b> <span class="muted">{p_ or ""}</span>' if n else '<span class="neg">empty slot</span>')
                          + f'</td><td class="n team">{v:.1f}</td></tr>' for sl, n, p_, v in lu["starters"])
            det += "".join(f'<tr><td class="muted">BN</td><td><b>{esc(n)}</b> <span class="muted">{p_ or ""}</span></td>'
                           f'<td class="n muted">{v:.1f}</td></tr>' for n, p_, v in lu["bench"])
            trs.append(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="{key}-{i}">{head}</tr>'
                       f'<tr class="xdetail" id="{key}-{i}" hidden><td colspan="3"><table class="picks">{det}</table></td></tr>')
        return f'<div class="panel"><h3 class="{cls}">{title}</h3><table class="expand">{"".join(trs)}</table></div>'
    record_book = (
        '<div class="grid2">'
        + score_lst("Highest scores", hi, "pos", "rb-hi") + score_lst("Lowest scores", lo, "neg", "rb-lo")
        + lst("Biggest blowouts", blow, game_fmt) + lst("Closest games", close, game_fmt)
        + lst("Most points in a season", best_pf, season_fmt, "pos") + lst("Fewest points in a season", worst_pf, season_fmt, "neg")
        + '</div><p class="note">Regular season and playoff games. Season totals are regular season, finished seasons only. '
          'Names are each manager’s current team. Click a high or low score for that week’s full roster: starters, then the bench.</p>')

    # all-time luck (regular season)
    exp = collections.Counter()
    act = collections.Counter()
    per = collections.defaultdict(dict)
    for x in sums:
        byw = collections.defaultdict(dict)
        for w, a, sa, b, sb, pl in x.get("games", []):
            if not pl:
                byw[w][a], byw[w][b] = sa, sb
                act[a] += 1 if sa > sb else .5 if sa == sb else 0
                act[b] += 1 if sb > sa else .5 if sa == sb else 0
        e = collections.Counter()
        for w, sc in byw.items():
            for o, v in sc.items():
                others = [u for p, u in sc.items() if p != o]
                e[o] += (sum(1 for u in others if v > u) + .5 * sum(1 for u in others if v == u)) / len(others)
        for o in e:
            exp[o] += e[o]
            per[o][x["season"]] = (x["teams"][o]["wins"] + x["teams"][o]["ties"] / 2) - e[o]
    luck_rows = sorted(owners, key=lambda o: -(act[o] - exp[o]))
    lmx = max((abs(act[o] - exp[o]) for o in owners), default=1) or 1
    ltrs = []
    for o in luck_rows:
        d = act[o] - exp[o]
        bar = (f'<div style="display:flex;align-items:center;height:12px"><div style="flex:1;display:flex;justify-content:flex-end">'
               + (f'<span style="height:12px;width:{100 * -d / lmx:.1f}%;background:var(--bad);border-radius:3px 0 0 3px"></span>' if d < 0 else "")
               + '</div><div style="width:1px;height:16px;background:var(--ink3)"></div><div style="flex:1">'
               + (f'<span style="display:block;height:12px;width:{100 * d / lmx:.1f}%;background:var(--good);border-radius:0 3px 3px 0"></span>' if d > 0 else "")
               + '</div></div>')
        tip = ", ".join(f"{y}: {v:+.1f}" for y, v in sorted(per[o].items()))
        ltrs.append(f'<tr title="{tip}"><td>{who(o)}</td><td class="n">{act[o]:g}</td><td class="n">{exp[o]:.1f}</td>'
                    f'<td class="barcell" style="min-width:160px">{bar}</td><td class="n team {"pos" if d >= 0 else "neg"}">{d:+.1f}</td></tr>')
    luck_html = (f'<div class="panel scroll"><table><thead><tr><th>Manager</th><th class="n">Wins</th><th class="n">Expected</th>'
                 f'<th class="barcell">Unlucky ← → Lucky</th><th class="n">Luck</th></tr></thead><tbody>{"".join(ltrs)}</tbody></table></div>'
                 '<p class="note">Expected wins = each week’s share of the league you outscored (the all-play win rate), added up over every '
                 'regular-season week. Luck = real wins minus expected: positive means the schedule did you favors. Hover a row for each season.</p>')

    # streaks (regular season + playoffs, carried across seasons)
    seq = collections.defaultdict(list)
    for x, w, a, sa, b, sb, pl in sorted(allg, key=lambda g: (seas_order[g[0]], g[1])):
        if sa != sb:
            seq[a].append(("W" if sa > sb else "L", x, w))
            seq[b].append(("W" if sb > sa else "L", x, w))
    def runs(v, kind):
        best, cur, start = (0, None, None), 0, None
        for i, (r, x, w) in enumerate(v):
            if r == kind:
                cur, start = (cur + 1, start if cur else (x, w))
                if cur > best[0]:
                    best = (cur, start, (x, w))
            else:
                cur = 0
        return best
    span = lambda b: (f'{b[1][0]} wk {b[1][1]} – {b[2][0]} wk {b[2][1]}' if b[1] else "")
    strs = []
    for o in sorted(owners, key=lambda o: -runs(seq[o], "W")[0]):
        v = seq[o]
        bw, bl = runs(v, "W"), runs(v, "L")
        cur = 0
        for r, *_ in reversed(v):
            if r != v[-1][0]:
                break
            cur += 1
        curs = f'<span class="{"pos" if v[-1][0] == "W" else "neg"}">{v[-1][0]}{cur}</span>' if v else "—"
        strs.append(f'<tr><td>{who(o)}</td><td class="n team pos">{bw[0]}</td><td class="muted" style="font-size:12px">{span(bw)}</td>'
                    f'<td class="n team neg">{bl[0]}</td><td class="muted" style="font-size:12px">{span(bl)}</td><td class="n team">{curs}</td></tr>')
    streak_html = (f'<div class="panel scroll"><table><thead><tr><th>Manager</th><th class="n">Longest win streak</th><th></th>'
                   f'<th class="n">Longest losing streak</th><th></th><th class="n">Current</th></tr></thead><tbody>{"".join(strs)}</tbody></table></div>'
                   '<p class="note">Regular season and playoff games in order, carrying over from one season to the next.</p>')

    # draft history
    drafts = [(x["season"], d) for x in sums for d in x.get("draft", [])]
    firsts = collections.defaultdict(list)
    for y, d in drafts:
        if d["round"] == 1 and d["owner"]:
            firsts[d["owner"]].append((y, d))
    classes = collections.defaultdict(float)
    for y, d in drafts:
        if d["owner"] and not d["keeper"]:
            classes[(y, d["owner"])] += d["value"]
    ftr = []
    for o in sorted(owners, key=lambda o: -sum(d["value"] for _, d in firsts[o])):
        cells = []
        for x in sums:
            ds = [d for y, d in firsts[o] if y == x["season"]]
            cells.append("<td>" + ("".join(f'<div><b>{esc(d["player"])}</b>{" <span class=star title=keeper>★</span>" if d["keeper"] else ""} '
                                           f'<span class="muted">#{d["pick"]}</span> <span class="{"pos" if d["value"] >= 0 else "neg"}" style="font-size:12px">'
                                           f'{signed(d["value"], 0)}</span></div>' for d in ds) or '<span class="muted">—</span>') + "</td>")
        tot = sum(d["value"] for _, d in firsts[o])
        ftr.append(f'<tr><td>{who(o)}</td>{"".join(cells)}<td class="n team {"pos" if tot >= 0 else "neg"}">{signed(tot, 0)}</td></tr>')
    best_cls = sorted(classes.items(), key=lambda kv: -kv[1])[:5]
    worst_cls = sorted(classes.items(), key=lambda kv: kv[1])[:5]
    cls_fmt = lambda kv: f'<td>{who(kv[0][1])}<div class="muted" style="font-size:12px">{kv[0][0]} draft</div></td><td class="n team {"pos" if kv[1] >= 0 else "neg"}">{signed(kv[1], 0)}</td>'
    draft_html = (f'<div class="panel scroll"><table style="font-size:14px"><thead><tr><th>Manager</th>'
                  + "".join(f'<th>{x["season"]} 1st round</th>' for x in sums) + '<th class="n">Total vs. slot</th></tr></thead>'
                  f'<tbody>{"".join(ftr)}</tbody></table></div>'
                  f'<div class="grid2" style="margin-top:14px">{lst("Best draft classes", best_cls, cls_fmt, "pos")}{lst("Worst draft classes", worst_cls, cls_fmt, "neg")}</div>'
                  '<p class="note">Value = a pick’s regular-season points that year minus what picks in the same draft slot usually score. '
                  'Draft classes add up every non-keeper pick. ★ = keeper using a first-round slot. The current season counts points so far.</p>')

    # manager tendencies
    tcount, partners, tnet = collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    for x in sums:
        for t in x["trades"]:
            os_ = [sd["owner"] for sd in t["sides"] if sd["owner"]]
            for sd in t["sides"]:
                others = [o["total"] for o in t["sides"] if o is not sd]
                if sd["owner"] and others:
                    tnet[sd["owner"]] += sd["total"] - sum(others) / len(others)
            for o in os_:
                tcount[o] += 1
                for p in os_:
                    if p != o:
                        partners[o][p] += 1
    faab = collections.defaultdict(collections.Counter)
    bench_ = collections.Counter()
    ss = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for x in sums:
        for o, v in x.get("startsit", {}).items():
            ss[o] = [a + b for a, b in zip(ss[o], list(v) + [0] * (6 - len(v)))]
        for o, f in x.get("faab", {}).items():
            faab[o].update({k: v for k, v in f.items() if isinstance(v, (int, float))})
        for o, v in x.get("bench", {}).items():
            bench_[o] += v
    ttrs = []
    for o in sorted(owners, key=lambda o: -tcount[o]):
        fav = partners[o].most_common(1)
        f = faab[o]
        nseas = reg[o]["seasons"]
        net = tnet[o]
        ttrs.append(f'<tr><td data-v="{esc(name[o].lower())}">{who(o)}</td><td class="n">{tcount[o]}</td>'
                    f'<td class="n team {"pos" if net > 0 else "neg" if net < 0 else "muted"}" data-v="{net:.1f}">{signed(net, 0) if tcount[o] else "—"}</td>'
                    f'<td data-v="{esc(name[fav[0][0]].lower()) if fav else "~"}">{(who(fav[0][0]) + f" <span class=muted>×{fav[0][1]}</span>") if fav else "<span class=muted>—</span>"}</td>'
                    f'<td class="n">{f["bids"]}</td><td class="n">{f["won"]}</td><td class="n" data-v="{f["spent"]}">${f["spent"]}</td><td class="n neg" data-v="{f["over"]}">${f["over"]}</td>'
                    f'<td class="n team" data-v="{bench_[o]:.1f}">{bench_[o]:,.0f}</td><td class="n muted" data-v="{bench_[o] / nseas:.1f}">{bench_[o] / nseas:,.0f}</td>'
                    + (f'<td class="n team" data-v="{ss[o][0] / ss[o][1]:.4f}">{ss[o][0] / ss[o][1]:.1%}</td>'
                       f'<td class="n" data-v="{ss[o][2] + ss[o][4]}" title="{ss[o][2]} of {ss[o][3]} regular season, {ss[o][4]} of {ss[o][5]} playoffs">'
                       f'{ss[o][2] + ss[o][4]} <span class="muted">of {ss[o][3] + ss[o][5]}</span>'
                       + (f'<div class="muted" style="font-size:12px">{ss[o][4]} in playoffs</div>' if ss[o][4] else '') + '</td>' if ss[o][1] else
                       '<td class="n muted" data-v="0">—</td><td class="n muted" data-v="0">—</td>') + '</tr>')
    tendencies = (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>Manager</th><th class="n">Trades</th><th class="n">Trade net</th><th>Favorite trade partner</th>'
                  f'<th class="n">Waiver bids</th><th class="n">Won</th><th class="n">FAAB spent</th><th class="n">Overbid</th>'
                  f'<th class="n">Points left on bench</th><th class="n">Per season</th><th class="n">Start/sit</th><th class="n">Perfect lineups</th></tr></thead><tbody>{"".join(ttrs)}</tbody></table></div>'
                  '<p class="note">All seasons, including this one so far. Overbid = how much winning claims beat the next-highest bid by '
                  '(the whole bid when nobody else claimed the player). Trade net = points the players a manager got scored for the rest of that season, minus what the other side got, over every trade. '
                  'Bench points = the best possible lineup minus the one actually started, every week. Start/sit = the share of lineup spots filled '
                  'with a player who belongs in that week’s best possible lineup (empty spots count as misses; ties go to the player started), '
                  'regular season. Perfect lineups = games with every spot right, out of every game played: regular season plus all playoff '
                  'games (winners bracket, toilet bowl and placement games). Click a column header to sort.</p>')

    # waiver overbids, every season
    ob = collections.defaultdict(lambda: {"bids": 0, "won": 0, "spent": 0, "over": 0, "fa": 0, "moves": 0, "biggest": None})
    for x in sums:
        for o, f in x.get("faab", {}).items():
            c = ob[o]
            for k in ("bids", "won", "spent", "over", "fa", "moves"):
                c[k] += f.get(k, 0)
            b = f.get("biggest") or {}
            if b.get("player") and (not c["biggest"] or b["bid"] > c["biggest"]["bid"]):
                c["biggest"] = dict(b, season=x["season"])
    omx = max((c["spent"] for c in ob.values()), default=0) or 1
    otrs = []
    for o in sorted(ob, key=lambda o: -ob[o]["over"]):
        c = ob[o]
        need = c["spent"] - c["over"]
        rate = c["won"] / c["bids"] if c["bids"] else 0
        bar = (f'<div class="stack" style="height:12px;min-width:120px;background:var(--grid)">'
               f'<span style="flex:{need / omx:.4f};background:var(--c1)" title="Needed to win: ${need}"></span>'
               f'<span style="flex:{c["over"] / omx:.4f};background:var(--bad)" title="Overbid: ${c["over"]}"></span>'
               f'<span style="flex:{max(0, 1 - c["spent"] / omx):.4f};background:transparent"></span></div>')
        b = c["biggest"]
        otrs.append(f'<tr><td data-v="{esc(name[o].lower())}">{who(o)}</td><td class="barcell" data-v="{c["spent"]}">{bar}</td>'
                    f'<td class="n team" data-v="{c["over"]}">${c["over"]}</td><td class="n" data-v="{c["spent"]}">${c["spent"]}</td>'
                    f'<td class="n">{c["bids"]}</td><td class="n">{c["won"]}</td><td class="n muted" data-v="{rate:.3f}">{rate:.0%}</td>'
                    f'<td class="n" data-v="{c["moves"]}">{c["moves"]}<div class="muted" style="font-size:11px">{c["fa"]} FA</div></td>'
                    + _biggest_cell(b, b.get("season") if b else None) + '</tr>')
    overbids = (f'<div class="panel scroll"><div class="legend"><span><i style="background:var(--c1)"></i>Needed to win</span>'
                f'<span><i style="background:var(--bad)"></i>Overbid</span></div><table class="sortable"><thead><tr><th>Manager</th>'
                f'<th class="barcell">FAAB spent on wins</th><th class="n" aria-sort="descending">Overbid</th><th class="n">Spent</th><th class="n">Bids</th>'
                f'<th class="n">Won</th><th class="n">Win %</th><th class="n">Roster moves</th><th>Biggest spend</th></tr></thead><tbody>{"".join(otrs)}</tbody></table></div>'
                '<p class="note">Every season added up, including this one so far. Overbid = how much winning claims beat the next-highest bid on the '
                'same player (the whole bid when nobody else claimed him). Bids include $0 claims. Roster moves = players actually added: waiver claims won plus free agent adds (FA). Biggest spend = the largest single winning bid. Click a column header to sort.</p>')

    # loyalty: players a manager has kept around, season after season
    possible = collections.Counter()  # owner -> regular-season weeks he's been in the league
    held = collections.defaultdict(lambda: collections.defaultdict(lambda: {"weeks": 0, "seasons": [], "name": "", "pos": "", "started": 0, "pts": 0.0}))
    kept = collections.defaultdict(set)  # (owner, player) -> seasons kept
    for x in sums:
        for o in x["teams"]:
            possible[o] += x["weeks"]
        for o, ps in x.get("rostered", {}).items():
            for pid, row in ps.items():
                n, nm, pos = row[:3]
                h = held[o][pid]
                h["weeks"] += n
                if len(row) > 4:  # weeks started and points while starting (older summaries don't have them)
                    h["started"] += row[3]
                    h["pts"] += row[4]
                h["seasons"].append(x["season"])
                h["name"], h["pos"] = nm, pos
        for k in x["keepers"]:
            if k.get("pid") and k["owner"]:
                kept[(k["owner"], k["pid"])].add(x["season"])
    ltrs = []
    rows_l = []
    for o in owners:
        ps = held.get(o, {})
        multi = {pid: h for pid, h in ps.items() if len(h["seasons"]) >= 2}
        total = sum(h["weeks"] for h in ps.values()) or 1
        rows_l.append((o, ps, multi, sum(h["weeks"] for h in multi.values()) / total))
    for i, (o, ps, multi, share) in enumerate(sorted(rows_l, key=lambda r: (-len(r[2]), -r[3]))):
        top = sorted(multi.items(), key=lambda kv: (-kv[1]["weeks"], kv[1]["name"]))
        longest = top[0][1] if top else None
        nkept = len({pid for (oo, pid) in kept if oo == o})
        long_txt = (f'{esc(longest["name"])} <span class="muted">{longest["weeks"]}/{possible[o]} wks</span>' if longest else "—")

        def tag(pid):
            ss = sorted(kept.get((o, pid), ()))
            return "".join(f' <span class="chip medal m1" title="kept in {s_}">★ kept {s_}</span>' for s_ in ss)
        det = "".join(f'<tr><td><b>{esc(h["name"])}</b> <span class="muted">{h["pos"] or ""}</span>{tag(pid)}</td>'
                      f'<td class="n team">{h["weeks"]}/{possible[o]}</td><td class="n muted">{h["weeks"] / possible[o]:.0%}</td>'
                      f'<td class="n">{h["started"]}</td><td class="n team">{h["pts"]:.1f}</td>'
                      f'<td class="muted">{", ".join(h["seasons"])}</td></tr>' for pid, h in top) or \
            '<tr><td class="muted">Nobody has stuck around for two seasons yet.</td></tr>'
        ltrs.append(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="loy-{i}" '
                    f'data-n="{len(multi)}" data-share="{share:.4f}" data-kept="{nkept}" data-long="{longest["weeks"] if longest else 0}">'
                    f'<td class="muted rank"></td><td><span class="chev" aria-hidden="true">▸</span> {who(o)}</td>'
                    f'<td class="n team">{len(multi)}</td><td class="n">{share:.0%}</td><td class="n">{nkept}</td>'
                    f'<td style="white-space:nowrap">{long_txt}</td></tr>'
                    f'<tr class="xdetail" id="loy-{i}" hidden><td colspan="6"><table class="picks"><tr><td class="muted">Player</td>'
                    f'<td class="n muted">Weeks on roster</td><td class="n muted">Share</td><td class="n muted">Weeks started</td>'
                    f'<td class="n muted">Pts as a starter</td><td class="muted">Seasons</td></tr>{det}</table></td></tr>')
    lcontrols = _sort_controls("loyal", [("n", "Repeat players", "Most players carried across seasons first"),
                                         ("share", "Share of roster weeks", "Most roster time from repeat players first"),
                                         ("long", "Longest tenure", "Longest-held player first"),
                                         ("kept", "Keepers used", "Most keepers first")])
    loyalty = (f'<div class="panel scroll sortbars">{lcontrols}<table class="expand"><thead><tr><th></th><th>Manager</th>'
               f'<th class="n">Repeat players</th><th class="n">Roster weeks from them</th><th class="n">Keepers used</th>'
               f'<th>Longest-held player</th></tr></thead><tbody>{"".join(ltrs)}</tbody></table></div>')
    every = sorted(((o, pid, h) for o, ps in held.items() for pid, h in ps.items() if len(h["seasons"]) >= 2),
                   key=lambda t: -t[2]["weeks"])[:15]
    btrs = "".join(f'<tr><td class="muted">{i}</td><td><b>{esc(h["name"])}</b> <span class="muted">{h["pos"] or ""}</span>'
                   + "".join(f' <span class="chip medal m1">★ kept {s_}</span>' for s_ in sorted(kept.get((o, pid), ())))
                   + f'</td><td>{who(o)}</td><td class="n team">{h["weeks"]}/{possible[o]}</td><td class="muted">{", ".join(h["seasons"])}</td></tr>'
                   for i, (o, pid, h) in enumerate(every, 1))
    loyalty += (f'<div class="panel scroll" style="margin-top:14px"><h3>Longest-held players</h3><table><thead><tr><th></th><th>Player</th>'
                f'<th>Manager</th><th class="n">Weeks on roster</th><th>Seasons</th></tr></thead><tbody>{btrs}</tbody></table></div>'
                '<p class="note">Regular-season weeks a player spent on a manager’s roster, starting or on the bench, out of all the regular-season weeks '
                'that manager has played since 2023 (this season so far included). Repeat players = on the same manager’s roster in at least two '
                'seasons; team defenses count too. ★ marks the seasons a player was a keeper for that manager. Weeks started and points as a starter count only weeks he was in that '
                'manager’s starting lineup. Click a manager for his players.</p>')

    # best single-game player scores and worst bench weeks
    def res(me, them):
        if them is None:
            return '<span class="muted">–</span>'
        d = me - them
        return (f'<span class="pos">W</span> <span class="muted">by {d:.1f}</span>' if d > 0 else
                f'<span class="neg">L</span> <span class="muted">by {-d:.1f}</span>' if d < 0 else '<span class="muted">T</span>')
    def when(x, g):
        return f'{x} wk {g["week"]}{" (playoffs)" if g["playoff"] else ""}'
    def wsort(x, g):
        return int(x) * 100 + g["week"]
    bg = sorted(((x["season"], g) for x in sums for g in x.get("big_games", [])), key=lambda t: -t[1]["pts"])[:25]
    def line_html(g):
        rows = g.get("line") or []
        if not rows:
            return '<span class="muted">No stat line found for this game.</span>'
        body = "".join(f'<tr><td class="muted">{esc(k)}</td><td>{esc(t) or "<span class=muted>–</span>"}</td>'
                       f'<td class="n team {"neg" if v < 0 else ""}">{v:+.2f}</td></tr>' for k, t, v in rows)
        tot = sum(v for _, _, v in rows)
        note = "" if abs(tot - g["pts"]) < .05 else f"Sleeper scored it {g['pts']:.2f}"
        foot = (f'<tr><td class="muted">Total</td><td class="muted">{note}</td>'
                f'<td class="n team">{tot:.2f}</td></tr>')
        return f'<div class="xpin"><table class="picks">{body}{foot}</table></div>'
    def games_table(items, key, share):
        trs = "".join(
            f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="{key}-{i}"><td class="muted rank">{i}</td>'
            f'<td style="white-space:nowrap"><span class="chev" aria-hidden="true">▸</span> <b>{esc(g["player"])}</b> <span class="muted">{g["pos"] or ""}</span></td>'
            f'<td class="n team{"" if share else " neg"}" data-v="{g["pts"]}">{g["pts"]:.2f}</td><td>{who(g["owner"], g["team"])}</td>'
            f'<td data-v="{wsort(x, g)}" style="white-space:nowrap">{when(x, g)}</td>'
            f'<td data-v="{g["score"] - (g["opp"] if g["opp"] is not None else g["score"]):.2f}" style="white-space:nowrap">{res(g["score"], g["opp"])}</td>'
            + (f'<td class="n" data-v="{g["pts"] / g["score"] if g["score"] else 0:.4f}">{g["pts"] / g["score"] if g["score"] else 0:.0%}</td>' if share else '')
            + f'</tr><tr class="xdetail" id="{key}-{i}" hidden><td colspan="{7 if share else 6}">{line_html(g)}</td></tr>'
            for i, (x, g) in enumerate(items, 1))
        return (f'<div class="panel scroll"><table class="sortable expand"><thead><tr><th>#</th><th>Player</th><th class="n">Points</th>'
                f'<th>Team</th><th>When</th><th>Result</th>{"<th class=n>Share of team score</th>" if share else ""}</tr></thead>'
                f'<tbody>{trs}</tbody></table></div>')
    big_games_html = (games_table(bg, "bg", True)
                      + '<p class="note">The highest single-game scores by a player in a starting lineup, since 2023. Regular season and '
                      'winners-bracket playoff games (not the 5th-place game). Team = that season’s team name. Share = his points as a share of '
                      'the team’s score that week. Click a player for his stat line and what each part was worth under league scoring. '
                      'Click a column header to sort.</p>')
    bw = sorted(((x["season"], b) for x in sums for b in x.get("bench_weeks", [])), key=lambda t: -t[1]["gap"])[:25]
    def flipped(b):
        return b["opp"] is not None and b["score"] < b["opp"] < b["best"]
    bw_trs = "".join(
        f'<tr><td class="muted rank">{i}</td><td>{who(b["owner"], b["team"])}</td><td data-v="{wsort(x, b)}" style="white-space:nowrap">{when(x, b)}</td>'
        f'<td class="n team neg" data-v="{b["gap"]}">{b["gap"]:.2f}</td>'
        f'<td class="n" data-v="{b["score"]}" style="white-space:nowrap">{b["score"]:.1f} <span class="muted">of {b["best"]:.1f}</span></td>'
        f'<td data-v="{b["score"] - (b["opp"] if b["opp"] is not None else b["score"]):.2f}" style="white-space:nowrap">{res(b["score"], b["opp"])}'
        + (' <span class="chip neg">cost the game</span>' if flipped(b) else '') + '</td>'
        f'<td>{", ".join(f"<b>{esc(n)}</b> <span class=muted>{p_ or ''} {v:.1f}</span>" for n, p_, v in b["benched"])}</td></tr>'
        for i, (x, b) in enumerate(bw, 1))
    bench_html = (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>#</th><th>Team</th><th>When</th>'
                  f'<th class="n">Left on bench</th><th class="n">Scored</th><th>Result</th><th>Should have started</th></tr></thead>'
                  f'<tbody>{bw_trs}</tbody></table></div>'
                  '<p class="note">The weeks with the most points left on the bench: the best possible lineup from that week’s roster '
                  'minus the lineup actually started. “Scored … of …” = actual score of the best possible. Cost the game = lost, but the best '
                  'lineup would have won. Should have started = the bench players the best lineup would have used. Regular season and '
                  'winners-bracket playoff games. Click a column header to sort.</p>')

    return [("alltime-standings", "All-time standings", standings), ("head-to-head", "Head to head", headtohead),
            ("finishes", "Where everyone finished", finishes), ("champions", "Champions and last places", champs),
            ("playoff-records", "Playoff records", playoffs_html), ("record-book", "Record book", record_book),
            ("big-games", "Best single-game performances", big_games_html), ("bench-disasters", "Biggest bench disasters", bench_html),
            ("luck", "All-time luck", luck_html), ("streaks", "Streaks", streak_html), ("keepers", "Keepers", keep_html),
            ("draft-history", "Draft history", draft_html), ("alltime-trades", "Most lopsided trades", trade_html),
            ("tendencies", "Manager tendencies", tendencies), ("alltime-overbids", "Waiver overbids", overbids),
            ("loyalty", "Who sticks with their guys", loyalty),
            ("moves", "Best pickups and worst drops", moves)]


def rivalry_facts(sums):
    """The biggest head-to-head rivalries, as facts for the rivalry column."""
    owners, name = [], {}
    for x in sums:
        for o, z in x["teams"].items():
            if o not in name:
                owners.append(o)
                name[o] = z["team"]
    h = collections.defaultdict(lambda: [0, 0, 0, 0, 0.0, 0.0])  # w, l, playoff w, playoff l, pf, pa
    for x in sums:
        for w, a, sa, b, sb, pl in x.get("games", []):
            for me, m, them, t in ((a, sa, b, sb), (b, sb, a, sa)):
                c = h[(me, them)]
                c[0 if m > t else 1] += 1 if m != t else 0
                if pl:
                    c[2 if m > t else 3] += 1
                c[4] += m
                c[5] += t
    titles = collections.Counter(o for x in sums if x["complete"] for o, z in x["teams"].items() if z["finish"] == 1)
    out = []
    for (a, b), c in h.items():
        if a < b and c[0] + c[1] >= 3:
            lead, trail, (w, l, pw, pl, pf, pa) = (a, b, c) if c[0] >= c[1] else (b, a, h[(b, a)])
            out.append({"leader": name[lead], "trailer": name[trail], "record": f"{w}-{l}", "leader_wins": w, "trailer_wins": l,
                        "games": w + l, "playoff_record": f"{pw}-{pl}" if pw + pl else None,
                        "avg_score": f"{pf / (w + l):.1f}-{pa / (w + l):.1f}",
                        "leader_titles": titles[lead], "trailer_titles": titles[trail]})
    lopsided = sorted(out, key=lambda r: (-(r["leader_wins"] - r["trailer_wins"]), -r["games"]))[:5]
    even = sorted((r for r in out if r["games"] >= 5), key=lambda r: (r["leader_wins"] - r["trailer_wins"], -r["games"]))[:3]
    seen, picks = set(), []
    for r in lopsided + even:
        k = (r["leader"], r["trailer"])
        if k not in seen:
            seen.add(k)
            picks.append(r)
    return {"week": "alltime", "seasons": f'{sums[-1]["season"]}-{sums[0]["season"]}', "rivalries": picks}


def st_mean(v):
    v = list(v)
    return sum(v) / len(v) if v else 0


# ---------------------------------------------------------------- more draft views
def draft_grades(d):
    trs = []
    for g in d["grades"]:
        cls = "pos" if g["grade"][0] in "AB" else "neg" if g["grade"][0] in "DF" else ""
        b, w = g["best"], g["worst"]
        trs.append(f'<tr><td data-v="{esc(g["team"].lower())}" class="team" style="white-space:nowrap">{esc(g["team"])}</td>'
                   f'<td class="n" data-v="{g["value"]:.1f}"><b class="{cls}" style="font:700 20px var(--display)">{g["grade"]}</b></td>'
                   f'<td class="n {"pos" if g["value"] >= 0 else "neg"}" data-v="{g["value"]:.1f}">{signed(g["value"], 0)}</td>'
                   f'<td class="n" data-v="{g["pts"]:.1f}">{g["pts"]:,.0f}</td>'
                   f'<td class="n" data-v="{g["hits"] / g["picks"]:.3f}">{g["hits"]}/{g["picks"]}</td>'
                   f'<td class="n" data-v="{g["kept"]}">{g["kept"]}</td><td class="n">{g["starts"]}</td>'
                   f'<td data-v="{b["value"]:.1f}"><b>{esc(b["player"])}</b> <span class="muted">#{b["pick"]}</span> <span class="pos" style="font-size:12px">{signed(b["value"], 0)}</span></td>'
                   f'<td data-v="{w["value"]:.1f}"><b>{esc(w["player"])}</b> <span class="muted">#{w["pick"]}</span> <span class="neg" style="font-size:12px">{signed(w["value"], 0)}</span></td></tr>')
    return (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>Team</th><th class="n" aria-sort="descending">Grade</th><th class="n">vs. slot</th>'
            f'<th class="n">Points</th><th class="n">Hits</th><th class="n">Still rostered</th><th class="n">Lineup starts</th><th>Best pick</th><th>Worst pick</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Every pick (keepers included) scored against what picks in that draft slot usually produce; the grade curves each team’s total '
            'against the league. Hits = picks that beat their slot. Lineup starts = weeks the team’s draftees spent in its own starting lineup. '
            'Click a column header to sort.</p>')


def draft_board(d, teams):
    pos_i = {p: i for i, p in enumerate(POS_ORDER, 1)}
    cell = {(x["round"], x["slot"]): x for x in d["rows"]}
    first = {x["slot"]: x["team"] for x in d["rows"] if x["round"] == 1}
    head = "".join(f'<th class="n" style="font-size:11px;white-space:normal;min-width:98px">{esc(first.get(sl, ""))}</th>' for sl in d["slots"])
    trs = []
    for rd in range(1, d["rounds"] + 1):
        tds = []
        for sl in d["slots"]:
            x = cell.get((rd, sl))
            if not x:
                tds.append("<td></td>")
                continue
            c = pos_i.get(x["pos"], 0)
            bg = f"background:var(--t{c})" if c else ""
            card = (f'<div class="eyebrow">Round {x["round"]} · pick {x["pick"]}{" · keeper" if x["keeper"] else ""}</div>'
                    f'<div style="font-weight:700;font-size:15px">{esc(x["player"])} <span class="muted" style="font-weight:400">{x["pos"] or ""}</span></div>'
                    f'<div class="muted" style="font-size:12.5px;margin-bottom:6px">Drafted by {esc(x["team"])}</div>'
                    f'<table><tr><td>Expected for this pick</td><td class="n">{x["exp"]:.1f}</td></tr>'
                    f'<tr><td>Actual points</td><td class="n team">{x["pts"]:.1f}</td></tr>'
                    f'<tr><td>vs. expected</td><td class="n team {"pos" if x["value"] >= 0 else "neg"}">{signed(x["value"], 1)}</td></tr></table>'
                    + (f'<div class="gone-note" style="margin-top:6px">{esc(x["gone"][0].upper() + x["gone"][1:])}</div>' if x["gone"]
                       else '<div class="muted" style="margin-top:6px;font-size:12.5px">Still on the team</div>'))
            tds.append(f'<td class="pk" tabindex="0" role="button" aria-label="{esc(x["player"])} details" style="{bg};font-size:12px;line-height:1.25;padding:5px 6px">'
                       f'<b{" class=gone" if x["gone"] else ""}>{esc(x["player"])}</b>{"<span class=star>★</span>" if x["keeper"] else ""}'
                       f'<div class="{"pos" if x["value"] >= 0 else "neg"}" style="font-size:11px">{x["pts"]:.0f}</div><template>{card}</template></td>')
        trs.append(f'<tr><td class="muted" style="font-size:12px">R{rd}</td>{"".join(tds)}</tr>')
    legend = '<div class="legend">' + "".join(f'<span><i style="background:var(--c{i})"></i>{p}</span>' for p, i in pos_i.items()) + '</div>'
    return (f'<div class="panel scroll">{legend}<table class="picks board" style="min-width:{104 * len(d["slots"])}px"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">The whole draft, by round and draft slot (columns are named for the team that picked first in that slot). '
            'Colors = position; the number is the player’s points this season, green if he beat his slot and red if not. '
            'Struck through = no longer on the team that drafted him; ★ = keeper. Click a pick for its expected points and how it’s gone.</p>')


def redraft_table(d):
    trs = []
    for i, z in enumerate(d["redraft"], 1):
        o = z["orig"]
        if o:
            move = o["pick"] - i
            was = f'#{o["pick"]} <span class="muted">({esc(o["team"])})</span>'
        else:
            was = '<span class="pos">Undrafted</span>'
        trs.append(f'<tr><td class="n muted">{i}</td><td data-v="{esc(z["player"].lower())}"><b>{esc(z["player"])}</b> <span class="muted">{z["pos"]}</span></td>'
                   f'<td data-v="{z["pos"].lower()}">{z["pos"]}</td>'
                   f'<td class="n">{z["pts"]:.1f}</td><td class="n muted">{z["games"]}</td><td class="n team" data-v="{z["var"]:.1f}">{z["var"]:+.0f}</td>'
                   f'<td data-v="{-(o["pick"] if o else 999)}">{was}</td>'
                   f'<td class="n {"pos" if not o or o["pick"] > i else "neg" if o["pick"] < i else "muted"}" data-v="{(o["pick"] - i) if o else 999}">'
                   f'{"new" if not o else f"{o["pick"] - i:+d}" if o["pick"] != i else "="}</td></tr>')
    return (f'<div class="panel scroll"><table class="sortable"><thead><tr><th class="n">Redraft</th><th>Player</th><th>Pos</th><th class="n">Points</th><th class="n">Games</th>'
            f'<th class="n">Above replacement</th><th>Actually went</th><th class="n">Spots gained</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">The first two rounds if the draft were redone knowing this season’s results. Players are ranked by points above a '
            'replacement-level starter at their position (the last starter the league would field there), so quarterbacks don’t take over the board. '
            'Kickers and defenses are left out. Spots gained = how far up the board he’d go now. Click a column header to sort.</p>')


def payoff_table(d):
    labels = {1: "Rounds 1–2", 3: "Rounds 3–5", 6: "Rounds 6–9", 10: "Rounds 10+"}
    head = "".join(f'<th class="n">{labels[lo]}</th>' for lo, _ in d["bands"])
    trs = []
    for pos in ("QB", "RB", "WR", "TE"):
        tds = []
        for lo, _ in d["bands"]:
            c = d["payoff"].get((pos, lo))
            if not c:
                tds.append('<td class="n muted">—</td>')
                continue
            step = max(1, min(7, round(1 + 6 * c["hit"])))
            fg = "#fff" if step >= 5 else "var(--ink)"
            tds.append(f'<td class="w" style="background:var(--r{step});color:{fg}" title="{c["n"]} picks, average {c["avg"]:+.1f} vs. slot">'
                       f'{c["hit"]:.0%}<div style="font-size:10px;font-weight:400;opacity:.85">{c["avg"]:+.0f} avg · {c["n"]}</div></td>')
        trs.append(f'<tr><td class="team">{pos}</td>{"".join(tds)}</tr>')
    return (f'<div class="panel scroll"><table class="grid-t"><thead><tr><th>Position</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">League-wide: the share of picks at each position and stage of the draft that beat their slot (darker = more hits), '
            'with the average points vs. slot and the number of picks underneath.</p>')


def _medal(rank):
    label = {1: "season best", 2: "2nd best", 3: "3rd best"}.get(rank)
    return f' <span class="chip medal m{rank}">{label}</span>' if label else ""


def peaks_table(rows, top=2):
    key = f"pk{top}"
    which = {1: "best game", 2: "best or second-best game", 3: "best, second- or third-best game"}[top]
    mx = max(abs(x["actual"] - x["expected"]) for x in rows) or 1

    def cells(x):
        d = x["actual"] - x["expected"]
        bar = (f'<div style="display:flex;align-items:center;height:12px;min-width:150px"><div style="flex:1;display:flex;justify-content:flex-end">'
               + (f'<span style="height:12px;width:{100 * -d / mx:.1f}%;background:var(--good);border-radius:3px 0 0 3px"></span>' if d < 0 else "")
               + '</div><div style="width:1px;height:16px;background:var(--ink3)"></div><div style="flex:1">'
               + (f'<span style="display:block;height:12px;width:{100 * d / mx:.1f}%;background:var(--bad);border-radius:0 3px 3px 0"></span>' if d > 0 else "")
               + '</div></div>')
        return (f'<td class="barcell">{bar}</td><td class="n team">{x["actual"]}</td><td class="n">{x["expected"]:.1f}</td>'
                f'<td class="n team {"neg" if d > 0 else "pos" if d < 0 else ""}">{d:+.1f}</td><td class="n">{x["extra"]:.0f}</td>')

    def detail(x):
        if not x["hits"]:
            return '<span class="muted">No opponent has had a career day against this team yet.</span>'
        return ('<table class="picks">' + "".join(
            f'<tr><td class="muted">Wk {h["week"]}</td><td><b>{esc(h["player"])}</b> <span class="muted">{h["pos"] or ""}</span>'
            f'{_medal(h["rank"])}</td><td class="muted">for {esc(h["opp"])}</td>'
            f'<td class="n team">{h["pts"]:.1f}</td><td class="n muted">avg {h["avg"]:.1f}</td>'
            f'<td class="n neg">+{h["pts"] - h["avg"]:.1f}</td></tr>' for h in x["hits"]) + '</table>')
    controls = _sort_controls(f"peaks{top}", [("diff", "Above expected", "Most victimized by career days first"),
                                        ("actual", "Career days faced", "Most career days faced first"),
                                        ("extra", "Extra points", "Most points allowed above those players' averages first")])
    data = lambda x: {"diff": x["actual"] - x["expected"], "actual": x["actual"] + x["expected"] / 100, "extra": x["extra"]}
    legend = ('<div class="legend"><span><i style="background:var(--bad)"></i>Faced more than expected (unlucky)</span>'
              '<span><i style="background:var(--good)"></i>Fewer than expected (lucky)</span></div>')
    return (f'<div class="panel scroll sortbars">{controls}{legend}<table class="expand"><thead><tr><th></th><th>Team</th>'
            f'<th class="barcell">vs. expected</th><th class="n">Faced</th><th class="n">Expected</th><th class="n">Difference</th>'
            f'<th class="n">Extra points</th></tr></thead><tbody>{_xrows(key, rows, cells, detail, 7, data)}</tbody></table></div>'
            f'<p class="note">A career day = an opposing starter’s {which} of the season so far, and at least 15 points. '
            f'Expected = how many you’d expect by chance: a player with 7 games, {top} of them career days, has a {top}-in-7 chance any given game is one. '
            'Extra points = how far those games beat each player’s season average. Players with fewer than 3 games don’t count. '
            'These shift as the season goes on and players set new highs. Click a team for the games.</p>')


def peaks_switch(by_top):
    """by_top: {1: rows, 2: rows, 3: rows}; a toggle between counting best games only, top two or top three."""
    labels = {1: "Best game only", 2: "Top 2 games", 3: "Top 3 games"}
    opts = "".join(f'<option value="{k}"{" selected" if k == 2 else ""}>{labels[k]}</option>' for k in by_top)
    panels = "".join(f'<div data-panel="{k}"{"" if k == 2 else " hidden"}>{peaks_table(rows, k)}</div>' for k, rows in by_top.items())
    return (f'<div class="switch"><div class="hl-bar" style="margin-bottom:10px"><label for="peaks-top">Count</label>'
            f'<select id="peaks-top" autocomplete="off">{opts}</select>'
            f'<span class="muted sort-hint">which of each opposing player’s best games count as a career day</span></div>{panels}</div>')


def _flag_play(p):
    what = {"run": f"{p['yards']}-yd {'TD run' if p['td'] else 'run'}",
            "catch": f"{p['yards']}-yd {'TD catch' if p['td'] else 'catch'}",
            "pass": f"{p['yards']}-yd {'TD pass' if p['td'] else 'completion'}",
            "kick return": f"{p['yards']}-yd {'TD kick return' if p['td'] else 'kick return'}",
            "punt return": f"{p['yards']}-yd {'TD punt return' if p['td'] else 'punt return'}"}[p["kind"]]
    if p.get("spot"):
        what += (f' <span class="muted">({"TD and the " if p["td"] else ""}last {p["lost_yards"]} yds called back)</span>')
    tag = ('<span class="chip" style="color:var(--bad)">own team’s flag</span>' if p["own"]
           else '<span class="chip" style="color:var(--ink3)">defense’s flag</span>')
    return what, f'{esc(p["penalty"])} on {esc(p["flagged"])} {tag}'


def flagged_section(d):
    rows = d["teams"]
    mx = max((t["total"] for t in rows), default=0) or 1

    def cells(t):
        return (f'<td class="barcell"><div class="stack" style="height:12px;min-width:120px;background:var(--grid)">'
                f'<span data-pos="own" style="flex:{t["own"] / mx:.4f};background:var(--bad)" title="Own team’s flags: {t["own"]:.1f}"></span>'
                f'<span data-pos="theirs" style="flex:{t["theirs"] / mx:.4f};background:var(--c1)" title="Defense’s flags: {t["theirs"]:.1f}"></span>'
                f'<span style="flex:{max(0, 1 - t["total"] / mx):.4f};background:transparent"></span></div></td>'
                f'<td class="n team">{t["total"]:.1f}</td><td class="n">{t["own"]:.1f}</td><td class="n">{t["theirs"]:.1f}</td>'
                f'<td class="n muted">{len(t["plays"])}</td>')

    def detail(t):
        if not t["plays"]:
            return '<span class="muted">No starter has had a play called back yet.</span>'
        trs = []
        for p in t["plays"]:
            what, why = _flag_play(p)
            trs.append(f'<tr><td class="muted">Wk {p["week"]}</td><td><b>{esc(p["player"])}</b> <span class="muted">{p["pos"] or ""}</span></td>'
                       f'<td>{what}</td><td style="font-size:13px">{why}</td><td class="n team neg">−{p["pts"]:.1f}</td></tr>')
        return f'<table class="picks">{"".join(trs)}</table>'
    controls = _sort_controls("flags", [("total", "All flags", "Most points wiped out first"),
                                        ("own", "Own team’s flags", "Most points lost to their players’ own teammates first"),
                                        ("theirs", "Defense’s flags", "Most points lost to the other side’s flags first")])
    data = lambda t: {"total": t["total"] + len(t["plays"]) / 1000, "own": t["own"], "theirs": t["theirs"]}
    legend = ('<div class="legend"><span><i style="background:var(--bad)"></i>Flag on the player’s own team</span>'
              '<span><i style="background:var(--c1)"></i>Flag on the defense</span></div>')
    table = (f'<div class="panel scroll sortbars">{controls}{legend}<table class="expand"><thead><tr><th></th><th>Team</th>'
             f'<th class="barcell">Starters’ points wiped out</th><th class="n">Total</th><th class="n">Own team’s flags</th>'
             f'<th class="n">Defense’s flags</th><th class="n">Plays</th></tr></thead><tbody>{_xrows("fl", rows, cells, detail, 7, data)}</tbody></table></div>')

    def big(p):
        what, why = _flag_play(p)
        by = f'<div class="muted" style="font-size:12px">Wk {p["week"]} · {esc(p["game"])}</div>'
        return (f'<td><b>{esc(p["player"])}</b> {what}<div style="font-size:13px">started for <b class="team">{esc(p["fantasy"])}</b></div>{by}'
                f'<div style="font-size:12.5px">{why}</div></td><td class="n team neg">−{p["pts"]:.1f}</td>')
    bl = "".join(f'<tr><td class="muted">{i}</td>{big(p)}</tr>' for i, p in enumerate(d["biggest"], 1)) or \
        '<tr><td class="muted">No starter has lost a play yet.</td></tr>'

    def pdetail(x):
        trs = []
        for p in x["plays"]:
            what, why = _flag_play(p)
            role = ('<span class="chip pos">starter</span>' if p["started"] else '<span class="chip" style="color:var(--ink3)">bench</span>')
            trs.append(f'<tr><td class="muted">Wk {p["week"]}</td><td>{what}<div style="font-size:12px">{why}</div></td>'
                       f'<td style="white-space:nowrap"><span class="team">{esc(p["fantasy"])}</span> {role}</td><td class="n neg">−{p["pts"]:.1f}</td></tr>')
        return f'<table class="picks">{"".join(trs)}</table>'
    pl = "".join(
        f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="flp-{i}"><td class="muted">{i}</td>'
        f'<td><span class="chev" aria-hidden="true">▸</span> <b>{esc(x["player"])}</b> <span class="muted">{x["pos"] or ""}</span>'
        f'<div class="muted" style="font-size:12px">{esc(" → ".join(x["teams"]))}</div></td>'
        f'<td class="n muted">{x["n"]} play{"" if x["n"] == 1 else "s"}</td><td class="n team neg">−{x["pts"]:.1f}'
        f'<div class="muted" style="font-size:11px;font-weight:400">{x["started_pts"]:.1f} while starting</div></td></tr>'
        f'<tr class="xdetail" id="flp-{i}" hidden><td colspan="4">{pdetail(x)}</td></tr>' for i, x in enumerate(d["players"], 1))
    lists = (f'<div class="grid2" style="margin-top:14px"><div class="panel"><h3>Biggest plays wiped out</h3>'
             f'<p class="muted" style="font-size:13px;margin:0 0 6px">Only plays by a player in a fantasy starting lineup that week.</p><table>{bl}</table></div>'
             f'<div class="panel"><h3>Players who lost the most</h3>'
             f'<p class="muted" style="font-size:13px;margin:0 0 6px">Plays while on a fantasy roster, starting or on the bench. Click a player for the plays.</p>'
             f'<table class="expand">{pl}</table></div></div>')
    return (table + lists +
            '<p class="note">Runs and completions that were called back by an accepted penalty (“No Play”), plus touchdowns taken away by a '
            'flag during the play (the yards up to the flag still count, so only the score and the yards after it are lost). Scored with this league’s settings: '
            'rushing, receiving and kick/punt return yards, the half point per catch, passing yards and any touchdown that came off the board. Returns count when the whole return was wiped out, or when the return team’s own flag took back the yards after the foul. The team table and the biggest plays count only players in a fantasy starting lineup that week; the player list counts plays while on any fantasy roster. A flag on the defense usually gave the '
            'offense yards back, so it’s shown separately. Penalties enforced after a play that still counted, sacks, incompletions and kicks are left out. '
            'From ESPN’s play-by-play. Click a team for its plays.</p>')


def kicker_table(rows):
    if not rows:
        return '<div class="panel muted">No kickers yet.</div>'
    trs = []
    for k in rows:
        cells = []
        for label, made, att in k["bands"]:
            pct = made / att if att else -1
            cells.append(f'<td class="n" data-v="{att + pct / 10:.3f}">{made:.0f}/{att:.0f}' + (f'<div class="muted" style="font-size:11px">{made / att:.0%}</div>' if att else "") + '</td>')
        xm, xa = k["xp"]
        trs.append(f'<tr><td data-v="{esc(k["player"].lower())}"><b>{esc(k["player"])}</b> <span class="muted">{k["nfl"] or ""}</span>'
                   f'<div class="muted" style="font-size:12px">{esc(" → ".join(k["owners"]))}</div></td>{"".join(cells)}'
                   f'<td class="n" data-v="{xa and xm / xa:.3f}">{xm:.0f}/{xa:.0f}</td>'
                   f'<td class="n team">{k["made"]:.0f}</td><td class="n">{k["missed"]:.0f}</td>'
                   f'<td class="n {"neg" if k["lost"] < 0 else "muted"}" data-v="{-k["lost"]:.1f}">{k["lost"]:.1f}</td>'
                   f'<td class="n" data-v="{k["long_share"]:.3f}">{k["long_share"]:.0%}</td>'
                   f'<td class="n" data-v="{k["season_long"]}">{k["season_long"]:.0f}</td><td class="n" data-v="{k["career_long"] or 0}">{k["career_long"] or "—"}</td>'
                   f'<td class="n team" data-v="{k["ppg"]:.2f}">{k["ppg"]:.1f}</td></tr>')
    head = "".join(f'<th class="n">{label}</th>' for label, *_ in rows[0]["bands"])
    return (f'<div class="panel scroll"><table class="sortable"><thead><tr><th>Kicker</th>{head}<th class="n">XP</th><th class="n">FG made</th><th class="n">FG missed</th><th class="n">Pts lost to misses</th><th class="n">50+ share</th>'
            f'<th class="n">Season long</th><th class="n">Career long</th><th class="n" aria-sort="descending">Pts/game</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>'
            '<p class="note">Every kicker who has spent time on a fantasy roster this season (teams that had him underneath). Field goals made/attempted '
            'by distance, from Sleeper’s stats. In this league a made field goal is worth 0.1 per yard minus 1 (a 30-yarder is 2, a 50-yarder 4), and misses cost '
            'more the shorter the kick: −3 under 30 yards, −2 from 30–39, −1 from 40–49 and nothing from 50+. Long attempts are pure upside, '
            'so 50+ share is the part of a kicker’s attempts that came from there. Points lost to misses = what his missed field goals and missed extra points (−3 each) cost under those rules. Career long is from ESPN. '
            'Click a column header to sort.</p>')


def coach_section(d):
    rows = d["teams"]
    mx = max((t["total"] for t in rows), default=0) or 1

    def cells(t):
        return (f'<td class="barcell"><div class="track"><span style="width:{100 * t["total"] / mx:.1f}%;background:var(--bad)"></span></div></td>'
                f'<td class="n team">{t["total"]:.1f}</td><td class="n muted">{len(t["plays"])}</td>')

    def detail(t):
        if not t["plays"]:
            return '<span class="muted">No coach has passed up a kick for this team’s kickers yet.</span>'
        return ('<table class="picks">' + "".join(
            f'<tr><td class="muted">Wk {p["week"]}</td><td><b>{esc(p["kicker"])}</b> <span class="muted">{p["team"]}</span></td>'
            f'<td>{p["distance"]}-yd try <span class="muted">(career long {p["career_long"]})</span></td>'
            f'<td>{esc(p["coach"] or p["team"])} {p["call"]}'
            f'{f" on <b>{esc(p["dd"])}</b>" if p["dd"] and p["call"] != "punted" else ""} <span class="muted">· {esc(p["dd"]) + " · " if p["dd"] and p["call"] == "punted" else ""}Q{p["q"]} {p["clock"]}</span></td>'
            f'<td class="n neg">−{p["value"]:.1f}</td></tr>' for p in t["plays"]) + '</table>')
    data = lambda t: {"total": t["total"], "n": len(t["plays"]) + t["total"] / 1000}
    controls = _sort_controls("coach", [("total", "Expected points", "Most kicker points passed up first"),
                                        ("n", "Kicks passed up", "Most kicks passed up first")])
    table = (f'<div class="panel scroll sortbars">{controls}<table class="expand"><thead><tr><th></th><th>Team</th>'
             f'<th class="barcell">Kicker points passed up</th><th class="n">Expected points</th><th class="n">Kicks</th></tr></thead>'
             f'<tbody>{_xrows("co", rows, cells, detail, 5, data)}</tbody></table></div>')
    crs = "".join(f'<tr><td class="muted">{i}</td><td><b>{esc(c["coach"] or c["team"])}</b> <span class="muted">{c["team"]}</span></td>'
                  f'<td class="n muted">{c["punts"]} punt{"" if c["punts"] == 1 else "s"}, {c["n"] - c["punts"]} failed {"try" if c["n"] - c["punts"] == 1 else "tries"}</td><td class="n team neg">−{c["value"]:.1f}</td></tr>'
                  for i, c in enumerate(d["coaches"], 1))
    return (table + f'<div class="panel" style="margin-top:14px"><h3>Most kicker-unfriendly coaches</h3><table>{crs}</table></div>'
            '<p class="note">Every 4th down where a field goal would have been within the kicker’s career long, but the coach punted or went for it and '
            'didn’t convert (successful tries are left out, since that drive kept going or scored). Kick distance = yards to the goal line + 18 (the end zone plus the hold, which is how this season’s field goals measured out). Each passed-up kick is valued at what it was worth under '
            'this league’s scoring before it was tried, using typical NFL make rates by distance and this league’s scoring: a make is 0.1 per yard minus 1, and a miss is −3 under 30 yards, '
            '−2 from 30–39, −1 from 40–49 and 0 from 50+. So a 55-yarder (made about 62% of the time for 4.5 points, free to miss) is worth +2.8, '
            'while a 25-yarder (98.5% for 1.5 points, −3 if missed) is worth about +1.4. Plays in the last two minutes when the team trailed by 4 or more are skipped. The team table counts kickers '
            'in that fantasy team’s starting lineup that week; the coach list counts every team. Click a team for the plays.</p>')


def roster_profile_table(rows, vet=8):
    def who(p):
        return f'{esc(p["player"])} <span class="muted">{p["age"]}</span>' if p else "—"

    def cells(t):
        return (f'<td class="n team">{t["core_age"]:.1f}</td><td class="n">{t["age"]:.1f}</td><td class="n">{t["exp"]:.1f}</td>'
                f'<td class="n">{t["rookies"]}</td><td class="n">{t["vets"]}</td>'
                f'<td class="n {"neg" if t["miss17"] >= 3 else ""}">{t["miss17"]:.1f}</td>'
                f'<td class="n {"neg" if t["hurt"] else "muted"}">{t["hurt"]}</td>'
                f'<td style="white-space:nowrap;font-size:13px">{who(t["oldest"])}<div class="muted">{who(t["youngest"])}</div></td>')

    def detail(t):
        trs = []
        for p in t["players"]:
            if p["possible"]:
                rate = p["played"] / p["possible"]
                hist = (f'{p["played"]}/{p["possible"]} <span class="{"neg" if rate < .8 else "muted"}">({p["missed"]} missed)</span>')
            else:
                hist = '<span class="muted">—</span>'
            status = (f'<span class="chip" style="color:var(--bad)">{esc(p["status"])}{" · " + esc(p["body"]) if p["body"] else ""}</span>'
                      if p["status"] else "")
            exp = "rookie" if p["exp"] == 0 else f'{p["exp"]} yr{"s" if p["exp"] != 1 else ""}'
            trs.append(f'<tr><td><b>{esc(p["player"])}</b> <span class="muted">{p["pos"]}</span> {status}</td>'
                       f'<td class="n">{p["age"]}</td><td class="n muted">{exp}</td><td class="n muted">{p["starts"]} start{"" if p["starts"] == 1 else "s"}</td>'
                       f'<td class="n">{hist}</td></tr>')
        return ('<table class="picks"><tr><td class="muted">Player</td><td class="n muted">Age</td><td class="n muted">NFL exp.</td>'
                '<td class="n muted">For this team</td><td class="n muted">Games since 2023</td></tr>' + "".join(trs) + '</table>')
    controls = _sort_controls("ages", [("core", "Starters’ age", "Oldest regular starters first"),
                                       ("age", "Roster age", "Oldest roster first"),
                                       ("young", "Youngest", "Youngest regular starters first"),
                                       ("exp", "NFL experience", "Most experienced roster first"),
                                       ("rookies", "Rookies", "Most rookies first"),
                                       ("vets", f"Veterans ({vet}+ yrs)", "Most veterans first"),
                                       ("miss", "Injury history", "Starters who have missed the most games first"),
                                       ("hurt", "Hurt now", "Most players currently out first")])
    data = lambda t: {"core": t["core_age"], "age": t["age"], "young": -t["core_age"], "exp": t["exp"],
                      "rookies": t["rookies"] + t["exp"] / 100, "vets": t["vets"] + t["exp"] / 100,
                      "miss": t["miss17"], "hurt": t["hurt"] + t["miss17"] / 100}
    return (f'<div class="panel scroll sortbars">{controls}<table class="expand"><thead><tr><th></th><th>Team</th>'
            f'<th class="n">Starters’ age</th><th class="n">Roster age</th><th class="n">Avg NFL yrs</th><th class="n">Rookies</th>'
            f'<th class="n">Vets ({vet}+)</th><th class="n">Missed / 17</th><th class="n">Hurt now</th><th>Oldest / youngest</th></tr></thead>'
            f'<tbody>{_xrows("rp", rows, cells, detail, 10, data)}</tbody></table></div>'
            '<p class="note">Current rosters, kickers included; team defenses are left out since they have no age or experience. Starters = the players who have started the most for that team this '
            f'season (as many as there are lineup spots other than defense). Veterans have {vet}+ NFL seasons. Missed / 17 = games the team’s regular starters have missed '
            'per 17 their NFL teams played, across every season since 2023 (Sleeper’s game logs start there), counting only seasons a player was a '
            'real contributor (6+ points a game when he played), so backups who never get in aren’t counted as hurt. It can’t tell an injury from a '
            'suspension or a benching. Hurt now = currently listed out, doubtful, IR or PUP. Click a team for its players.</p>')
