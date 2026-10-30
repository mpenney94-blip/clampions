"""Build the league dashboard as a static site.

Usage: python3 -m dashboard.build <league_id> [--out _site] [--no-winprob] [--past-cache DIR] [--only SEASON ...]
"""

import argparse
import concurrent.futures
import datetime as dt
import json
import math
import os
import random
import shutil

import winprob
from dashboard import commentary, render, stats, weekly
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
            'the line is the chance the first-named team wins. Quiet stretches between game days are squeezed out. Hover or tap a chart to see the odds at that moment. Times are Pacific.</p>')


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
        pts.append({"x": a["bid"], "y": a["ppg"], "r": 3 + 1.3 * min(g, 8), "jitter": random.uniform(-16, 3) if a["bid"] == 0 else 0,
                    "z": -g, "label": a["player"] if lab else None,
                    "sub": f'{a["team"]} · ${a["bid"]} · {a["ppg"]:.1f}/gm · {g} {"game" if g == 1 else "games"}',
                    "priority": (2 if a in top else 1) * a["ppg"], "group": gi[a["team"]], "glabel": a["player"],
                    "gsub": f'${a["bid"]} · {a["ppg"]:.1f}/gm · {g} {"game" if g == 1 else "games"}',
                    "title": f'{a["player"]} ({a["team"]}): ${a["bid"]}, {a["ppg"]:.1f} pts/game over {g} games, {a["total"]:.1f} total'})
    ticks = [v for v in (0, 1, 2, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 1000) if v <= xmax * .9] + [xmax]
    # square-root axis: spreads out the crowd of $0-$10 bids without squashing the big ones
    svg = render.scatter(pts, xmax=xmax, ymax=ymax, ystep=5, xreverse=True, xticks=ticks, xfmt=lambda v: f"${v}", xscale=math.sqrt,
                         xlabel="Waiver bid  ·  cheaper →  (square-root scale)", ylabel="Points per game on that roster",
                         quadrants=[(xmax * .3 ** 2, ymax * .92, "STEALS", "good"), (xmax * .82 ** 2, ymax * .5, "PRICEY", "bad")], groups=groups)
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
    groups = sorted(lg.team.values(), key=str.lower) + ["★ Keepers only"]
    gi = {t: i for i, t in enumerate(groups)}
    kg = len(groups) - 1
    pts = []
    for z in rows:
        good, bad = z in best, z in busts
        pts.append({"x": z["pick"], "y": z["pts"], "r": 5, "z": good or bad, "star": z["keeper"],
                    "ring": "good" if good else "bad" if bad else None,
                    "label": (z["player"] + (" ★" if z["keeper"] else "")) if good or bad else None, "lab_color": "good" if good else "bad" if bad else None,
                    "sub": f'{z["team"]} · pick {z["pick"]} · {z["pts"]:.0f} pts', "priority": abs(z["value"]),
                    "group": [gi[z["team"]]] + ([kg] if z["keeper"] else []),
                    "glabels": {kg: (f'{z["player"]} ★ {z["pts"]:.0f}', f'{z["team"]} · round {z["round"]}')}, "glabel": f'{z["player"]}{" ★" if z["keeper"] else ""} {z["pts"]:.0f}', "gsub": "",
                    "title": f'{z["player"]} ({z["pos"]}), pick {z["pick"]} by {z["team"]}{" (keeper)" if z["keeper"] else ""}: {z["pts"]:.1f} pts'})
    curve = [(z["pick"], z["exp"]) for z in sorted(rows, key=lambda z: z["pick"])]
    n = len(rows)
    svg = render.scatter(pts, xmax=n + 1, ymax=ymax, ystep=30, rounds=(teams, (n + teams - 1) // teams), curve=curve,
                         xlabel="Draft round (pick 1 → %d)" % n, ylabel="Fantasy points this season", groups=groups)
    tot = {}
    for z in rows:
        tot[z["team"]] = tot.get(z["team"], 0) + z["pts"]
    mx = max(tot.values()) or 1
    def picks_detail(t):
        mine = sorted((z for z in rows if z["team"] == t), key=lambda z: z["pick"])
        trs = "".join(f'<tr><td class="muted">R{z["round"]}</td><td class="muted">#{z["pick"]}</td>'
                      f'<td><b{" class=gone" if z["gone"] else ""}>{esc(z["player"])}</b>{"<span class=star>★</span>" if z["keeper"] else ""} '
                      f'<span class="muted">{z["pos"] or ""}</span></td>'
                      f'<td>{"<span class=gone-note>" + esc(z["gone"]) + "</span>" if z["gone"] else ""}</td>'
                      f'<td class="n team">{z["pts"]:.1f}</td></tr>' for z in mine)
        n_gone = sum(1 for z in mine if z["gone"])
        foot = f'<div class="muted" style="margin-top:6px;font-size:13px">{n_gone} of {len(mine)} no longer on the team (struck through)</div>' if n_gone else ""
        return f'<table class="picks">{trs}</table>{foot}'
    haul = "".join(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="haul-{i}">'
                   f'<td class="muted">{i}</td><td class="team"><span class="chev" aria-hidden="true">▸</span> {esc(t)}</td>'
                   f'<td class="barcell"><div class="track"><span style="width:{100 * v / mx:.1f}%"></span></div></td>'
                   f'<td class="n team">{v:.0f}</td></tr>'
                   f'<tr class="xdetail" id="haul-{i}" hidden><td></td><td colspan="3">{picks_detail(t)}</td></tr>'
                   for i, (t, v) in enumerate(sorted(tot.items(), key=lambda kv: -kv[1]), 1))

    def lst(title, items, cls):
        li = "".join(f'<tr><td><b>{esc(z["player"])}</b>{"<span class=star title=keeper>★</span>" if z["keeper"] else ""} '
                     f'<span class="muted">{z["pos"] or ""} · {esc(z["team"])} · pick {z["pick"]}</span></td>'
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
    kept = [z for z in rows if z["keeper"]]
    if kept:
        kb = max(kept, key=lambda z: z["value"])
        sums[groups[kg]] = (f'{len(kept)} keepers · {sum(z["pts"] for z in kept):.0f} pts · best value: {kb["player"]}, '
                            f'{kb["team"]}, round {kb["round"]} ({render.signed(kb["value"], 0)} vs typical)')
    return (render.highlight_box(svg, groups, sums, "draft picks", extra=1) +
            f'<div class="grid2" style="margin-top:14px">{lst("Biggest steals", best, "pos")}{lst("Biggest busts (rounds 1–4)", busts, "neg")}</div>'
            f'<h3 style="margin-top:18px">Draft haul: total points from each team’s picks</h3><p class="lede" style="margin:0 0 8px">Click a team to see its picks.</p>'
            f'<div class="panel scroll"><table class="expand">{haul}</table></div>'
            '<p class="note">Points are each drafted player’s fantasy points in this league’s scoring this season, wherever they ended up. '
            'The dashed line is the typical score for that draft slot (median of picks within 15 spots); steals and busts are measured against it. '
            '★ = keeper: kept from last season using that round’s pick rather than chosen in this year’s draft.</p>')


def boom_bust_chart(lg):
    rows = stats.starts(lg)
    if not rows:
        return '<div class="panel muted">Not enough starts yet.</div>'
    groups = sorted(lg.team.values(), key=str.lower) + ["★ Keepers only"]
    gi = {t: i for i, t in enumerate(groups)}
    kg = len(groups) - 1
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
                    "group": [gi[r["team"]]] + ([kg] if r["keeper"] else []), "star": r["keeper"],
                    "glabels": {kg: (f'{r["player"]} ★', f'{r["team"]} · {r["avg"]:.1f} avg · {r["low"]:.1f}–{r["high"]:.1f}')}, "glabel": r["player"], "gsub": f'{r["avg"]:.1f} avg · {r["low"]:.1f}–{r["high"]:.1f}',
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
    kept = [r for r in rows if r["keeper"]]
    if kept:
        kb = max(kept, key=lambda r: r["avg"])
        sums[groups[kg]] = f'{len(kept)} keepers with 4+ starts · best: {kb["player"]} {kb["avg"]:.1f} avg ({kb["team"]})'
    return (render.highlight_box(svg, groups, sums, "starters", extra=1) +
            '<p class="note">Every player started at least 4 times, by his average when started and how much that score swings week to week. '
            'Right = scores more; higher = less predictable. Bigger dots = more starts. ★ = keeper.</p>')


def week_hub(lg, w, with_winprob, wp_cache, odds, div_names):
    """The week-specific sections for week w: [(key, title, html)], each as things stood right after that week.
    Claude writes the columns for the current season only; finished seasons keep the built-in writer."""
    def po(x):
        if x not in odds:
            odds[x] = weekly.playoff_odds(lg, x) if x in lg.weeks else []
        return odds[x]
    wp = None
    if with_winprob:
        wp_html = winprob_section(lg, w, wp_cache)
        wp = wp_cache.get(w)
    more = lg.reg_weeks and w < lg.reg_weeks[-1]
    pw_prev = {x["team"]: x["rank"] for x in weekly.power(lg, w - 1)} if w - 1 in lg.weeks else {}
    out = [("recap", f"Week {w} recap", render.recap_tiles(stats.recap(lg, w))),
           ("awards", f"Week {w} awards", render.awards_tiles(weekly.awards(lg, w, wp), w)),
           ("column", "The week in review", render.column(*commentary.write("recap", commentary.week_facts(lg, w, wp, po(w), po(w - 1)), not lg.complete)))]
    if with_winprob:
        out.append(("winprob", f"Week {w} win probability", wp_html))
    out.append(("power", "Power rankings", render.power_table(weekly.power(lg, w), pw_prev)))
    if more:
        out += [("playoffs", "Playoff odds", render.playoff_table(po(w), po(w - 1), lg.playoff_teams, div_names)),
                ("preview", f"Week {w + 1} preview", render.preview_cards(weekly.preview(lg, w + 1), w + 1)),
                ("lookahead", f"Week {w + 1} trash talk", render.column(*commentary.write("preview", commentary.preview_facts(lg, w + 1, po(w)), not lg.complete,
                                                                                                   final=w + 1 <= lg.weeks[-1])))]
    return out


def build(league_id, out, with_winprob=True, tabs=""):
    lg = stats.League(league_id)
    now = dt.datetime.now(dt.timezone.utc)
    if not lg.weeks:
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "index.html"), "w").write(render.page(lg.name, f'{tabs}<h1>{esc(lg.name)}</h1><p>No games scored yet this season.</p>'))
        return
    last = lg.weeks[-1]
    ap = stats.allplay(lg)
    order = [r["team"] for r in ap]
    rid = {v: k for k, v in lg.team.items()}
    grid = stats.schedule_swap(lg, [rid[t] for t in order])
    wp_cache = {}
    src = stats.sources(lg)
    week_links = " ".join(f'<a href="weeks/{w}.html">Week {w}</a>' for w in reversed(lg.weeks))

    # week-to-week hub
    meta = lg.info.get("metadata") or {}
    div_names = {int(k.split("_")[1]): v for k, v in meta.items() if k.startswith("division_") and k.split("_")[1].isdigit()}
    odds = {}
    hub = week_hub(lg, last, with_winprob, wp_cache, odds, div_names)
    proj_rows, proj_over, proj_under = weekly.vs_projection(lg)
    tr_rows, tr_league = weekly.trends(lg)
    dx = stats.draft_extras(lg)
    S = {k: (t, h) for k, t, h in hub}
    S.update({
        "history": ("Past weeks", f'<div class="panel">{week_links}</div>'),
        "standings": ("All-play standings", '<p class="lede">How each team would stand if everyone played everyone every week, next to their real record.</p>' + render.allplay_table(ap, lg.weeks)),
        "trends": ("Scoring trends", render.trend_cards(tr_rows, tr_league, lg.weeks)),
        "projections": ("Beating the projections", render.projection_table(proj_rows, proj_over, proj_under, last)),
        "peaks": ("Opponents' career days", '<p class="lede">Did opponents keep having their best game of the year against you?</p>'
                  + render.peaks_switch({k: weekly.opponent_peaks(lg, k) for k in (1, 2, 3)})),
        "flags": ("Flagged away", '<p class="lede">Fantasy points erased when a big play got called back for a penalty.</p>'
                  + render.flagged_section(weekly.flagged_away(lg))),
        "kickers": ("Kicking distance profile", '<p class="lede">Who gets the long kicks, and who makes them.</p>' + render.kicker_table(weekly.kicker_profile(lg))),
        "coaches": ("Coaches who cost kickers", '<p class="lede">Field goal chances in range that coaches passed up, and what they cost kicker owners.</p>'
                    + render.coach_section(weekly.coach_summary(lg))),
        "close": ("Close games", render.close_table(*weekly.close_games(lg))),
        "schedule": ("Schedule swap", '<p class="lede">Every team’s record if it had played each other team’s schedule.</p>' + render.swap_table(order, grid)),
        "carry": ("Who carried each team", render.carry_bars(stats.carry(lg))),
        "boom-bust": ("Boom or bust", boom_bust_chart(lg)),
        "team-grid": ("Team by week", '<p class="lede">Every player on a team’s roster, week by week: what he scored and whether he was in the lineup.</p>'
                      + render.team_grids(lg.name, {n: stats.team_grid(lg, r) for r, n in lg.team.items()}, lg.weeks,
                                          {n: stats.week_totals(lg, r) for r, n in lg.team.items()})),
        "trades": ("Trade scorecard", render.trade_cards(stats.trades(lg))),
        "byes": ("Bye week damage", render.bye_table(weekly.byes(lg))),
        "injuries": ("Injury damage", render.injury_table(weekly.injuries(lg))),
        "bench": ("Points left on the bench", render.bench_table(stats.bench(lg))),
        "waivers": ("Waiver wire", pickups_chart(lg)),
        "waiver-wars": ("Waiver wars", '<p class="lede">Players more than one team put in a claim for, who won them, and what the losing bidders missed out on.</p>'
                        + render.waiver_wars(*stats.waiver_wars(lg), sorted(lg.team.values(), key=str.lower))),
        "overbids": ("Waiver overbids", '<p class="lede">How much FAAB each team spent beyond what it took to win, and how often its claims came through.</p>'
                     + render.overbid_table(stats.waiver_bids(lg), lg.info["settings"].get("waiver_budget", 100))),
        "drops": ("Drops that came back to bite", '<p class="lede">The worst cuts of the season: players who went on to produce after their team let them go.</p>'
                  + render.drop_table(stats.drop_regrets(lg))),
        "position": ("Position strength", render.position_table(*weekly.position_strength(lg))),
        "draft-grades": ("Draft grades", render.draft_grades(dx)) if dx else None,
        "draft-board": ("Draft board", render.draft_board(dx, lg.team)) if dx else None,
        "redraft": ("Redraft", render.redraft_table(dx)) if dx else None,
        "payoff": ("Which positions paid off", render.payoff_table(dx)) if dx else None,
        "sources": ("Drafted vs. picked up", render.source_bars(src)),
        "draft": ("Draft report card", draft_chart(lg)),
        "rounds": ("Points by draft round", render.round_table(src, max((p["round"] for p in lg.picks), default=0))),
    })
    groups = [
        ("this-week", "This week", f"What happened in week {last} and what’s coming next. These change every week.",
         [k for k, _, _ in hub] + ["history"]),
        ("scoring", "Scoring", f"Weeks 1–{last}: how many points every team put up, how lucky it was, and where the points came from.",
         ["standings", "trends", "projections", "close", "peaks", "flags", "kickers", "coaches", "schedule", "carry", "boom-bust", "team-grid"]),
        ("roster", "Roster", "Trades, byes, injuries, lineup calls and the waiver wire.",
         ["trades", "byes", "injuries", "bench", "waivers", "waiver-wars", "overbids", "drops", "position"]),
        ("draft-group", "Draft", "How the draft played out, and how much each team still leans on it.",
         ["draft-grades", "draft", "draft-board", "redraft", "rounds", "payoff", "sources"]),
    ]
    groups = [(gid, name, blurb, [k for k in keys if S.get(k)]) for gid, name, blurb, keys in groups]
    toc = ('<nav class="toc" aria-label="Sections">'
           + "".join(f'<div class="grp"><span><a href="#{gid}" style="all:unset;cursor:pointer">{name}</a></span>'
                     + "".join(f'<a href="#{k}">{esc(S[k][0])}</a>' for k in keys) + '</div>' for gid, name, _, keys in groups)
           + '</nav>')
    when = (f"{lg.season} season · final" + (f" · 🏆 {esc(lg.champion)}" if lg.champion else "")) if lg.complete else f"{lg.season} season · through week {last}"
    body = (f'{tabs}<header class="site"><div><div class="eyebrow">{when}</div><h1>{esc(lg.name)}</h1></div></header>{toc}'
            + "".join(f'<div class="group-head" id="{gid}"><h2>{name}</h2><p>{blurb}</p></div>'
                      + "".join(f'<section id="{k}"><h2>{esc(S[k][0])}</h2>{S[k][1]}</section>' for k in keys) for gid, name, blurb, keys in groups)
            + render.footer(now) + render.HIGHLIGHT_JS)
    os.makedirs(os.path.join(out, "weeks"), exist_ok=True)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(render.page(f"{lg.name} dashboard", body, f"{lg.name} {lg.season}: all-play standings, win probability, schedule swap, bench, waivers, trades and draft."))
    for w in lg.weeks:
        parts = [f'<p><a href="../index.html">← {esc(lg.name)} dashboard</a></p><div class="eyebrow">{lg.season} season</div><h1>Week {w}</h1>']
        if lg.complete:  # finished seasons keep the short week pages
            parts.append(f'<section><h2>Recap</h2>{render.recap_tiles(stats.recap(lg, w))}</section>')
            if with_winprob:
                parts.append(f'<section><h2>Win probability</h2>{winprob_section(lg, w, wp_cache)}</section>')
        else:
            secs = hub if w == last else week_hub(lg, w, with_winprob, wp_cache, odds, div_names)
            nav = " ".join(f'<a href="{w2}.html">Week {w2}</a>' if w2 != w else f'<b>Week {w2}</b>' for w2 in lg.weeks)
            parts.append(f'<nav class="toc" aria-label="Sections"><div class="grp"><span>Week {w}</span>'
                         + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t, _ in secs) + '</div></nav>'
                         + "".join(f'<section id="{k}"><h2>{esc(t)}</h2>{h}</section>' for k, t, h in secs)
                         + f'<section><h2>Other weeks</h2><div class="panel">{nav}</div></section>')
        parts.append(render.footer(now) + render.HIGHLIGHT_JS)
        with open(os.path.join(out, "weeks", f"{w}.html"), "w") as f:
            f.write(render.page(f"{lg.name} · Week {w}", "".join(parts)))
    with open(os.path.join(out, "summary.json"), "w") as f:  # this season's totals, for the all-time page
        json.dump(stats.season_summary(lg), f)
    with open(os.path.join(out, ".nojekyll"), "w"):
        pass
    print(f"built {lg.name} through week {last} -> {out}")


def seasons(league_id):
    """[(league_id, season)] from this league back through Sleeper's previous_league_id chain."""
    out, c = [], stats.SleeperClient()
    while league_id and league_id != "0":
        info = c.league(league_id)
        out.append((league_id, info["season"]))
        league_id = info.get("previous_league_id")
    return out


def alltime_page(name, tabs, sums):
    secs = render.alltime_sections(sums)
    talk = ("rivalries", "Rivalry trash talk", render.column(*commentary.write("rivalry", render.rivalry_facts(sums)), "the league’s head-to-head history"))
    secs.insert(2, talk)  # right after head to head
    S = {k: (t, h) for k, t, h in secs}
    groups = [
        ("at-standings", "Standings", "Who has won, who has lost, and where everyone finished.",
         ["alltime-standings", "finishes", "champions", "playoff-records"]),
        ("at-rivalries", "Rivalries", "Every manager against every other manager.", ["head-to-head", "rivalries", "streaks"]),
        ("at-records", "Records", "The best and worst single games and seasons, and who the schedule has favored.", ["record-book", "luck"]),
        ("at-moves", "Roster moves", "Keepers, drafts, trades and the waiver wire across every season.",
         ["keepers", "draft-history", "alltime-trades", "tendencies", "alltime-overbids", "moves"]),
    ]
    groups = [(gid, g, blurb, [k for k in keys if k in S]) for gid, g, blurb, keys in groups]
    placed = {k for *_, keys in groups for k in keys}
    if any(k not in placed for k in S):  # anything new lands in a catch-all group rather than vanishing
        groups.append(("at-more", "More", "", [k for k in S if k not in placed]))
    toc = ('<nav class="toc" aria-label="Sections">'
           + "".join(f'<div class="grp"><span><a href="#{gid}" style="all:unset;cursor:pointer">{g}</a></span>'
                     + "".join(f'<a href="#{k}">{esc(S[k][0])}</a>' for k in keys) + '</div>' for gid, g, _, keys in groups)
           + '</nav>')
    body = (f'{tabs}<header class="site"><div><div class="eyebrow">{sums[-1]["season"]}–{sums[0]["season"]} on Sleeper</div>'
            f'<h1>{esc(name)}: all-time</h1></div></header>{toc}'
            + "".join(f'<div class="group-head" id="{gid}"><h2>{g}</h2><p>{blurb}</p></div>'
                      + "".join(f'<section id="{k}"><h2>{esc(S[k][0])}</h2>{S[k][1]}</section>' for k in keys) for gid, g, blurb, keys in groups)
            + render.footer(dt.datetime.now(dt.timezone.utc)) + render.HIGHLIGHT_JS)
    return render.page(f"{name} all-time", body, f"{name}: all-time standings, finishes, champions, keepers, trades, pickups and drops.")


def build_all(league_id, out, with_winprob=True, past_cache=None, only=None):
    """The current season at the site root, each earlier season in /<season>/, and an all-time page in /alltime/.
    Finished seasons don't change, so with past_cache they're built once into that folder and copied from it after."""
    chain = seasons(league_id)
    tab_list = [(s, "index.html" if i == 0 else f"{s}/index.html") for i, (_, s) in enumerate(chain)] + [("All-time", "alltime/index.html")]
    jobs = []  # (league_id, folder to build into, tabs, folder to copy to afterwards)
    for i, (lid, season) in enumerate(chain):
        if only and season not in only:
            continue
        if i == 0:
            jobs.append((lid, out, render.season_tabs(tab_list, season, ""), None))
            continue
        tabs, dest = render.season_tabs(tab_list, season, "../"), os.path.join(out, season)
        if not past_cache:
            jobs.append((lid, dest, tabs, None))
        elif os.path.exists(os.path.join(past_cache, season, "index.html")):
            print(f"{season}: using the cached build")
            shutil.copytree(os.path.join(past_cache, season), dest, dirs_exist_ok=True)
        else:
            jobs.append((lid, os.path.join(past_cache, season), tabs, dest))
    stats.SleeperClient().players()  # warm the shared players cache once, before the parallel builds
    # seasons are independent and mostly wait on the network, so build them side by side
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        for f in [pool.submit(build, lid, folder, with_winprob, tabs) for lid, folder, tabs, _ in jobs]:
            f.result()
    for _, folder, _, dest in jobs:
        if dest:
            shutil.copytree(folder, dest, dirs_exist_ok=True)
    name = stats.SleeperClient().league(league_id)["name"]
    os.makedirs(os.path.join(out, "alltime"), exist_ok=True)
    with open(os.path.join(out, "alltime", "index.html"), "w") as f:
        sums = []
        for i, (_, season) in enumerate(chain):
            path = os.path.join(out, "summary.json") if i == 0 else os.path.join(out, season, "summary.json")
            if os.path.exists(path):
                with open(path) as sf:
                    sums.append(json.load(sf))
        f.write(alltime_page(name, render.season_tabs(tab_list, "All-time", "../"), sums))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("league_id", help="the current season's league; earlier seasons are found from it")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--no-winprob", action="store_true", help="skip the slow ESPN play-by-play step")
    ap.add_argument("--past-cache", help="folder that keeps finished seasons' builds between runs")
    ap.add_argument("--only", nargs="*", help="build just these seasons (e.g. 2026 2025)")
    a = ap.parse_args()
    build_all(a.league_id, a.out, not a.no_winprob, a.past_cache, set(a.only) if a.only else None)


if __name__ == "__main__":
    main()
