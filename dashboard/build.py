"""Build the league dashboard as a static site.

Usage: python3 -m dashboard.build <league_id> [--out _site] [--no-winprob]
"""

import argparse
import datetime as dt
import os
import random

import winprob
from dashboard import render, stats
from dashboard.render import esc


def winprob_section(lg, week, cache):
    if week not in cache:
        try:
            cache[week] = winprob.win_probability(lg.id, week)
        except Exception as e:  # ESPN hiccups shouldn't take the whole site down
            print(f"win probability for week {week} failed: {e}")
            cache[week] = None
    wp = cache[week]
    if not wp:
        return '<div class="panel muted">Win probability isn’t available for this week.</div>'
    cards = [render.winprob_card(m) for m in sorted(wp["matchups"], key=lambda m: -max(m["series"][-1][2], m["series"][-1][3]))]
    return ('<div class="grid2">' + "".join(cards) + '</div><p class="note">Each team starts at its projection. As every play happens '
            '(ESPN play-by-play), players bank their points and keep their projection for the share of their game still left; '
            'the line is the chance the first-named team wins. Quiet stretches between game days are squeezed out. Times are Eastern.</p>')


def pickups_chart(lg):
    adds = stats.pickups(lg)
    if not adds:
        return '<div class="panel muted">No pickups yet.</div>'
    random.seed(3)
    ymax = max(10, (int(max(a["ppg"] for a in adds)) // 5 + 1) * 5)
    xmax = max(10, (int(max(a["bid"] for a in adds)) // 10 + 1) * 10)
    top = sorted(adds, key=lambda a: -(a["ppg"] * min(a["games"], 4) - a["bid"] * 0.15))[:9]
    pricey = sorted(adds, key=lambda a: -a["bid"])[:3]
    groups = sorted(lg.team.values(), key=str.lower)
    gi = {t: i for i, t in enumerate(groups)}
    pts = []
    for a in adds:
        lab = a in top or a in pricey
        g = a["games"]
        pts.append({"x": a["bid"], "y": a["ppg"], "r": 3 + 1.3 * min(g, 8), "jitter": random.uniform(-4, 4) if a["bid"] <= 1 else 0,
                    "z": -g, "label": a["player"] if lab else None,
                    "sub": f'{a["team"]} · ${a["bid"]} · {a["ppg"]:.1f}/gm · {g} {"game" if g == 1 else "games"}',
                    "priority": (2 if a in top else 1) * a["ppg"], "group": gi[a["team"]], "glabel": a["player"],
                    "gsub": f'${a["bid"]} · {a["ppg"]:.1f}/gm · {g} {"game" if g == 1 else "games"}',
                    "title": f'{a["player"]} ({a["team"]}): ${a["bid"]}, {a["ppg"]:.1f} pts/game over {g} games, {a["total"]:.1f} total'})
    svg = render.scatter(pts, xmax=xmax, ymax=ymax, ystep=5, xreverse=True, xticks=range(0, xmax + 1, 10), xfmt=lambda v: f"${v}",
                         xlabel="Waiver bid  ·  cheaper →", ylabel="Points per game on that roster",
                         quadrants=[(xmax * .3, ymax * .92, "STEALS", "good"), (xmax * .82, ymax * .5, "PRICEY", "bad")], groups=groups)
    sums = {}
    for t in groups:
        mine = [a for a in adds if a["team"] == t]
        if mine:
            b = max(mine, key=lambda a: (a["ppg"] * min(a["games"], 4)))
            sums[t] = (f'{len(mine)} {"pickup" if len(mine) == 1 else "pickups"} that played for them · ${sum(a["bid"] for a in mine)} in bids · '
                       f'best: {b["player"]} ({b["ppg"]:.1f}/gm over {b["games"]})')
        else:
            sums[t] = "No pickups have played for them yet."
    return (render.highlight_box(svg, groups, sums, "pickups") + '<p class="note">Every pickup that has played for the team that grabbed it. '
            'Points per game count weeks on that roster (bench included) when the player actually played. Bigger dots = more games, so the average means more. '
            'Free-agent adds count as $0. Hover a dot for details.</p>')


def draft_chart(lg):
    rows = stats.draft(lg)
    if not rows:
        return '<div class="panel muted">No draft found.</div>'
    teams = len(lg.team)
    best = sorted(rows, key=lambda z: -z["value"])[:6]
    busts = sorted([z for z in rows if z["round"] <= 4], key=lambda z: z["value"])[:5]
    ymax = max(30, (int(max(z["pts"] for z in rows)) // 30 + 1) * 30)
    groups = sorted(lg.team.values(), key=str.lower)
    gi = {t: i for i, t in enumerate(groups)}
    pts = []
    for z in rows:
        good, bad = z in best, z in busts
        pts.append({"x": z["pick"], "y": z["pts"], "r": 5, "z": good or bad,
                    "ring": "good" if good else "bad" if bad else None,
                    "label": z["player"] if good or bad else None, "lab_color": "good" if good else "bad" if bad else None,
                    "sub": f'{z["team"]} · pick {z["pick"]} · {z["pts"]:.0f} pts', "priority": abs(z["value"]),
                    "group": gi.get(z["team"]), "glabel": f'{z["player"]} {z["pts"]:.0f}', "gsub": "",
                    "title": f'{z["player"]} ({z["pos"]}), pick {z["pick"]} by {z["team"]}: {z["pts"]:.1f} pts'})
    curve = [(z["pick"], z["exp"]) for z in sorted(rows, key=lambda z: z["pick"])]
    n = len(rows)
    svg = render.scatter(pts, xmax=n + 1, ymax=ymax, ystep=30, rounds=(teams, (n + teams - 1) // teams), curve=curve,
                         xlabel="Draft round (pick 1 → %d)" % n, ylabel="Fantasy points this season", groups=groups)
    tot = {}
    for z in rows:
        tot[z["team"]] = tot.get(z["team"], 0) + z["pts"]
    mx = max(tot.values()) or 1
    haul = "".join(f'<tr><td class="muted">{i}</td><td class="team">{esc(t)}</td><td class="barcell"><div class="track"><span style="width:{100 * v / mx:.1f}%"></span></div></td>'
                   f'<td class="n team">{v:.0f}</td></tr>' for i, (t, v) in enumerate(sorted(tot.items(), key=lambda kv: -kv[1]), 1))

    def lst(title, items, cls):
        li = "".join(f'<tr><td><b>{esc(z["player"])}</b> <span class="muted">{z["pos"] or ""} · {esc(z["team"])} · pick {z["pick"]}</span></td>'
                     f'<td class="n team">{z["pts"]:.0f}</td><td class="n {cls}">{render.signed(z["value"], 0)}</td></tr>' for z in items)
        return f'<div class="panel"><h3 class="{cls}">{title}</h3><table>{li}</table></div>'
    rank = {t: i for i, (t, _) in enumerate(sorted(tot.items(), key=lambda kv: -kv[1]), 1)}
    sums = {}
    for t in groups:
        mine = [z for z in rows if z["team"] == t]
        if mine:
            b = max(mine, key=lambda z: z["value"])
            sums[t] = (f'{len(mine)} picks · {tot[t]:.0f} pts (#{rank[t]} of {len(tot)}) · '
                       f'best value: {b["player"]}, pick {b["pick"]} ({render.signed(b["value"], 0)} vs typical)')
    return (render.highlight_box(svg, groups, sums, "draft picks") +
            f'<div class="grid2" style="margin-top:14px">{lst("Biggest steals", best, "pos")}{lst("Biggest busts (rounds 1–4)", busts, "neg")}</div>'
            f'<h3 style="margin-top:18px">Draft haul: total points from each team’s picks</h3><div class="panel scroll"><table>{haul}</table></div>'
            '<p class="note">Points are each drafted player’s fantasy points in this league’s scoring this season, wherever they ended up. '
            'The dashed line is the typical score for that draft slot (median of picks within 15 spots); steals and busts are measured against it.</p>')


def boom_bust_chart(lg):
    rows = stats.starts(lg)
    if not rows:
        return '<div class="panel muted">Not enough starts yet.</div>'
    groups = sorted(lg.team.values(), key=str.lower)
    gi = {t: i for i, t in enumerate(groups)}
    xmax = max(10, (int(max(r["avg"] for r in rows)) // 5 + 1) * 5)
    ymax = max(10, (int(max(r["sd"] for r in rows)) // 2 + 1) * 2)
    studs = sorted(rows, key=lambda r: -r["avg"])[:5]
    wild = sorted(rows, key=lambda r: -r["sd"])[:4]
    steady = sorted([r for r in rows if r["avg"] >= 12], key=lambda r: r["sd"] / r["avg"])[:3]
    duds = sorted([r for r in rows if r["starts"] >= 5], key=lambda r: r["avg"])[:3]
    pts = []
    for r in rows:
        lab = r in studs or r in wild or r in steady or r in duds
        pts.append({"x": r["avg"], "y": r["sd"], "r": 2 + 1.1 * r["starts"], "label": r["player"] if lab else None,
                    "sub": f'{r["team"]} · {r["avg"]:.1f} avg · {r["low"]:.1f}–{r["high"]:.1f}', "priority": r["avg"] + r["sd"],
                    "group": gi[r["team"]], "glabel": r["player"], "gsub": f'{r["avg"]:.1f} avg · {r["low"]:.1f}–{r["high"]:.1f}',
                    "title": f'{r["player"]} ({r["pos"]}, {r["team"]}): {r["avg"]:.1f} avg over {r["starts"]} starts, range {r["low"]:.1f}–{r["high"]:.1f}'})
    svg = render.scatter(pts, xmax=xmax, ymax=ymax, ystep=2, xticks=range(0, xmax + 1, 5),
                         xlabel="Average points when started", ylabel="Week-to-week swing (std. dev.)", groups=groups,
                         quadrants=[(xmax * .82, ymax * .08, "STEADY STUDS", "good"), (xmax * .5, ymax * .93, "BOOM OR BUST", "bad"),
                                    (xmax * .1, ymax * .08, "DUDS", "muted")])
    sums = {}
    for t in groups:
        mine = [r for r in rows if r["team"] == t]
        if mine:
            a, b = max(mine, key=lambda r: r["avg"]), max(mine, key=lambda r: r["sd"])
            sums[t] = f'{len(mine)} regular starters · best: {a["player"]} {a["avg"]:.1f} avg · wildest: {b["player"]} ({b["low"]:.1f} to {b["high"]:.1f})'
    return (render.highlight_box(svg, groups, sums, "starters") +
            '<p class="note">Every player started at least 4 times, by his average when started and how much that score swings week to week. '
            'Right = scores more; higher = less predictable. Bigger dots = more starts.</p>')


def build(league_id, out, with_winprob=True):
    lg = stats.League(league_id)
    now = dt.datetime.now(dt.timezone.utc)
    if not lg.weeks:
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "index.html"), "w").write(render.page(lg.name, f'<h1>{esc(lg.name)}</h1><p>No games scored yet this season.</p>'))
        return
    last = lg.weeks[-1]
    ap = stats.allplay(lg)
    order = [r["team"] for r in ap]
    rid = {v: k for k, v in lg.team.items()}
    grid = stats.schedule_swap(lg, [rid[t] for t in order])
    wp_cache = {}
    src = stats.sources(lg)
    week_links = " ".join(f'<a href="weeks/{w}.html">Week {w}</a>' for w in reversed(lg.weeks))

    sections = [
        ("recap", f"Week {last} recap", render.recap_tiles(stats.recap(lg, last))),
        ("standings", "All-play standings", '<p class="lede">How each team would stand if everyone played everyone every week, next to their real record.</p>' + render.allplay_table(ap, lg.weeks)),
    ]
    if with_winprob:
        sections.append(("winprob", f"Week {last} win probability", winprob_section(lg, last, wp_cache)))
    sections += [
        ("schedule", "Schedule swap", '<p class="lede">Every team’s record if it had played each other team’s schedule.</p>' + render.swap_table(order, grid)),
        ("bench", "Points left on the bench", render.bench_table(stats.bench(lg))),
        ("waivers", "Waiver wire", pickups_chart(lg)),
        ("waiver-wars", "Waiver wars", '<p class="lede">Players more than one team put in a claim for, who won them, and what the losing bidders missed out on.</p>'
         + render.waiver_wars(*stats.waiver_wars(lg), sorted(lg.team.values(), key=str.lower))),
        ("trades", "Trade scorecard", render.trade_cards(stats.trades(lg))),
        ("carry", "Who carried each team", render.carry_bars(stats.carry(lg))),
        ("sources", "Drafted vs. picked up", render.source_bars(src)),
        ("rounds", "Points by draft round", render.round_table(src, max((p["round"] for p in lg.picks), default=0))),
        ("boom-bust", "Boom or bust", boom_bust_chart(lg)),
        ("team-grid", "Team by week", '<p class="lede">Every player on a team’s roster, week by week: what he scored and whether he was in the lineup.</p>'
         + render.team_grids(lg.name, {n: stats.team_grid(lg, r) for r, n in lg.team.items()}, lg.weeks,
                             {n: stats.week_totals(lg, r) for r, n in lg.team.items()})),
        ("draft", "Draft report card", draft_chart(lg)),
    ]
    toc = '<nav class="toc">' + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t, _ in sections) + '<a href="#history">Past weeks</a></nav>'
    body = (f'<header class="site"><div><div class="eyebrow">{lg.season} season · through week {last}</div><h1>{esc(lg.name)}</h1></div></header>{toc}'
            + "".join(f'<section id="{k}"><h2>{esc(t)}</h2>{h}</section>' for k, t, h in sections)
            + f'<section id="history"><h2>Past weeks</h2><div class="panel">{week_links}</div></section>' + render.footer(now) + render.HIGHLIGHT_JS)
    os.makedirs(os.path.join(out, "weeks"), exist_ok=True)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(render.page(f"{lg.name} dashboard", body, f"{lg.name} {lg.season}: all-play standings, win probability, schedule swap, bench, waivers, trades and draft."))
    for w in lg.weeks:
        parts = [f'<p><a href="../index.html">← {esc(lg.name)} dashboard</a></p><div class="eyebrow">{lg.season} season</div><h1>Week {w}</h1>',
                 f'<section><h2>Recap</h2>{render.recap_tiles(stats.recap(lg, w))}</section>']
        if with_winprob:
            parts.append(f'<section><h2>Win probability</h2>{winprob_section(lg, w, wp_cache)}</section>')
        parts.append(render.footer(now))
        with open(os.path.join(out, "weeks", f"{w}.html"), "w") as f:
            f.write(render.page(f"{lg.name} · Week {w}", "".join(parts)))
    with open(os.path.join(out, ".nojekyll"), "w"):
        pass
    print(f"built {lg.name} through week {last} -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("league_id")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--no-winprob", action="store_true", help="skip the slow ESPN play-by-play step")
    a = ap.parse_args()
    build(a.league_id, a.out, not a.no_winprob)


if __name__ == "__main__":
    main()
