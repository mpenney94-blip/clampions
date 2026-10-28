"""Week-to-week stats: playoff odds, power rankings, awards, next-week preview, projections, close games, trends,
plus the season-long position-strength and injury/bye views."""

import collections
import math
import random
import statistics as st

import winprob
from dashboard.stats import _optimal

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]


def _scores(lg, weeks):
    return {w: {m["roster_id"]: m["points"] or 0.0 for m in lg.matchups[w]} for w in weeks}


def _pairs(lg, w):
    by = collections.defaultdict(list)
    for m in lg.matchups_for(w):
        if m.get("matchup_id") is not None:
            by[m["matchup_id"]].append(m["roster_id"])
    return [tuple(v) for v in by.values() if len(v) == 2]


# ---------------------------------------------------------------- playoff odds
def playoff_odds(lg, through=None, sims=10000, seed=7):
    """Monte Carlo the rest of the regular season. Through = last week counted as played (default: last scored)."""
    through = through or lg.weeks[-1]
    played = [w for w in lg.weeks if w <= through and w in lg.reg_weeks]
    left = [w for w in lg.reg_weeks if w > through]
    sc = _scores(lg, played)
    rids = list(lg.team)
    wins0 = {r: 0.0 for r in rids}
    pf0 = {r: 0.0 for r in rids}
    for w in played:
        for a, b in _pairs(lg, w):
            wins0[a] += 1 if sc[w][a] > sc[w][b] else .5 if sc[w][a] == sc[w][b] else 0
            wins0[b] += 1 if sc[w][b] > sc[w][a] else .5 if sc[w][a] == sc[w][b] else 0
        for r in rids:
            pf0[r] += sc[w][r]
    allv = [v for w in played for v in sc[w].values()]
    lg_mean, lg_sd = st.mean(allv), st.pstdev(allv)
    mu, sd = {}, {}
    for r in rids:
        v = [sc[w][r] for w in played]
        k = len(v)
        mu[r] = (sum(v) + 3 * lg_mean) / (k + 3)  # shrink toward the league average early in the season
        sd[r] = math.sqrt(((st.pstdev(v) ** 2) * k + lg_sd ** 2 * 3) / (k + 3)) if k else lg_sd
    sched = {w: _pairs(lg, w) for w in left}
    divs = collections.defaultdict(list)
    for r in rids:
        divs[lg.division.get(r)].append(r)
    n_po = lg.playoff_teams
    n_bye = len([d for d in divs if d is not None]) if n_po and len(divs) > 1 else (2 if n_po >= 6 else 0)
    rng = random.Random(seed)
    tally = {r: collections.Counter() for r in rids}
    for _ in range(sims):
        wins, pf = dict(wins0), dict(pf0)
        for w in left:
            draw = {r: rng.gauss(mu[r], sd[r]) for r in rids}
            for a, b in sched[w]:
                wins[a if draw[a] > draw[b] else b] += 1
            for r in rids:
                pf[r] += draw[r]
        key = lambda r: (wins[r], pf[r])
        order = sorted(rids, key=key, reverse=True)
        if len(divs) > 1 and None not in divs:
            winners = sorted((max(m, key=key) for m in divs.values()), key=key, reverse=True)
            rest = [r for r in order if r not in winners]
            seeds = winners + rest
        else:
            seeds = order
        for i, r in enumerate(seeds):
            t = tally[r]
            t["wins"] += wins[r]
            if i < n_po:
                t["playoffs"] += 1
            if i < n_bye:
                t["bye"] += 1
            if i == 0:
                t["first"] += 1
        tally[order[-1]]["last"] += 1
    out = []
    for r in rids:
        t = tally[r]
        out.append({"team": lg.team[r], "rid": r, "wins": wins0[r], "losses": len(played) - wins0[r], "pf": pf0[r],
                    "playoffs": t["playoffs"] / sims, "bye": t["bye"] / sims, "first": t["first"] / sims,
                    "last": t["last"] / sims, "proj_wins": t["wins"] / sims, "division": lg.division.get(r)})
    return sorted(out, key=lambda x: (-x["playoffs"], -x["bye"], -x["proj_wins"]))


# ---------------------------------------------------------------- power rankings
def power(lg, through=None):
    through = through or lg.weeks[-1]
    weeks = [w for w in lg.weeks if w <= through]
    sc = _scores(lg, weeks)
    rows = []
    for r in lg.team:
        ap_w = sum(sum(1 for o, v in sc[w].items() if o != r and sc[w][r] > v) + .5 * sum(1 for o, v in sc[w].items() if o != r and sc[w][r] == v)
                   for w in weeks)
        ap = ap_w / (len(weeks) * (len(lg.team) - 1))
        ppg = st.mean(sc[w][r] for w in weeks)
        recent = st.mean(sc[w][r] for w in weeks[-3:])
        rows.append({"rid": r, "team": lg.team[r], "allplay": ap, "ppg": ppg, "recent": recent})
    def pct(key):
        vals = sorted(x[key] for x in rows)
        return {x["rid"]: (sum(1 for v in vals if v < x[key]) + .5 * (sum(1 for v in vals if v == x[key]) - 1)) / (len(vals) - 1) for x in rows}
    p_ppg, p_rec = pct("ppg"), pct("recent")
    for x in rows:
        x["score"] = 100 * (.5 * x["allplay"] + .25 * p_ppg[x["rid"]] + .25 * p_rec[x["rid"]])
    rows.sort(key=lambda x: -x["score"])
    for i, x in enumerate(rows, 1):
        x["rank"] = i
    return rows


# ---------------------------------------------------------------- weekly awards
def awards(lg, w, wp=None):
    ms = lg.matchups[w]
    sc = {m["roster_id"]: m["points"] or 0.0 for m in ms}
    pairs = _pairs(lg, w)
    res = [(a, b) if sc[a] >= sc[b] else (b, a) for a, b in pairs]  # (winner, loser)
    out = {}
    lw = min(res, key=lambda p: sc[p[0]])
    out["luckiest"] = (lg.team[lw[0]], sc[lw[0]], f"won with the week’s lowest winning score, over {lg.team[lw[1]]} ({sc[lw[1]]:.2f})")
    ul = max(res, key=lambda p: sc[p[1]])
    out["unluckiest"] = (lg.team[ul[1]], sc[ul[1]], f"lost anyway, to {lg.team[ul[0]]} ({sc[ul[0]]:.2f})")
    eff = {}
    for m in ms:
        opt, used = _optimal(lg, m.get("players_points") or {})
        eff[m["roster_id"]] = (sc[m["roster_id"]] / opt if opt else 1, opt - sc[m["roster_id"]], m, used)
    best = max(eff, key=lambda r: (eff[r][0], sc[r]))
    out["best_call"] = (lg.team[best], eff[best][0], "started its best possible lineup" if eff[best][1] < .05
                        else f"left only {eff[best][1]:.1f} points on the bench")
    worst = max(eff, key=lambda r: eff[r][1])
    _, gap, m, used = eff[worst]
    benched = max((p for p in used if p not in m["starters"]), key=lambda p: m["players_points"][p], default=None)
    out["worst_call"] = (lg.team[worst], gap, f"left {gap:.1f} points on the bench"
                         + (f", including {lg.name_of(benched)} ({m['players_points'][benched]:.1f})" if benched else ""))
    top = max(((lg.name_of(p), v, lg.team[m["roster_id"]]) for m in ms for p, v in zip(m["starters"], m["starters_points"]) if p != "0"),
              key=lambda x: x[1])
    out["player"] = (top[0], top[1], f"for {top[2]}")
    bench = max(((lg.name_of(p), v, lg.team[m["roster_id"]]) for m in ms for p, v in (m.get("players_points") or {}).items() if p not in m["starters"]),
                key=lambda x: x[1], default=None)
    if bench:
        out["bench"] = (bench[0], bench[1], f"sat on {bench[2]}’s bench")
    if wp:
        ups = []
        for mm in wp["matchups"]:
            pre, last = mm["series"][0], mm["series"][-1]
            home_won = last[2] >= last[3]
            p_win = pre[1] if home_won else 1 - pre[1]
            ups.append((p_win, mm["home"]["team"] if home_won else mm["away"]["team"], mm["away"]["team"] if home_won else mm["home"]["team"]))
        u = min(ups)
        out["upset"] = (u[1], u[0], f"won after starting with a {u[0]:.0%} chance against {u[2]}")
    return out


# ---------------------------------------------------------------- next week preview
def preview(lg, w):
    if w not in lg.reg_weeks and (not lg.playoff_start or w >= lg.playoff_start + 3):
        return []
    ms = {m["roster_id"]: m for m in lg.matchups_for(w)}
    proj, _ = lg.proj(w)
    games = []
    for a, b in _pairs(lg, w):
        side = []
        for r in (a, b):
            m = ms[r]
            starters = [p for p in (m.get("starters") or []) if p and p != "0"]
            if not starters:  # no lineup set yet: use the best projected lineup
                _, starters = _optimal(lg, {p: proj.get(p, 0) for p in lg.roster_now.get(r, [])})
            pts = sum(proj.get(p, 0) for p in starters)
            var = sum(winprob.player_sd(proj.get(p, 0), lg.pos_of(p)) ** 2 for p in starters)
            key = max(starters, key=lambda p: proj.get(p, 0), default=None)
            out_ = [lg.name_of(p) for p in starters if proj.get(p, 0) <= 0]
            side.append({"team": lg.team[r], "proj": pts, "var": var, "key": (lg.name_of(key), proj.get(key, 0)) if key else None, "empty": out_})
        sd = math.sqrt(side[0]["var"] + side[1]["var"]) or 1
        pa = .5 * (1 + math.erf((side[0]["proj"] - side[1]["proj"]) / (sd * math.sqrt(2))))
        if pa < .5:
            side, pa = side[::-1], 1 - pa
        games.append({"fav": side[0], "dog": side[1], "p": pa, "spread": side[0]["proj"] - side[1]["proj"]})
    return sorted(games, key=lambda g: g["p"])


# ---------------------------------------------------------------- vs projections
def vs_projection(lg):
    teams = {r: {"team": n, "act": 0.0, "proj": 0.0, "last_act": 0.0, "last_proj": 0.0} for r, n in lg.team.items()}
    players = collections.defaultdict(lambda: {"act": 0.0, "proj": 0.0, "starts": 0, "team": None})
    last = lg.weeks[-1]
    for w in lg.weeks:
        proj, _ = lg.proj(w)
        for m in lg.matchups[w]:
            t = teams[m["roster_id"]]
            for p, v in zip(m["starters"], m["starters_points"]):
                if p == "0":
                    continue
                pj = proj.get(p, 0.0)
                t["act"] += v
                t["proj"] += pj
                if w == last:
                    t["last_act"] += v
                    t["last_proj"] += pj
                pl = players[(p, m["roster_id"])]
                pl["act"] += v
                pl["proj"] += pj
                pl["starts"] += 1
                pl["team"] = t["team"]
    rows = sorted(teams.values(), key=lambda t: -(t["act"] - t["proj"]))
    pls = [{"player": lg.name_of(p), "team": v["team"], "starts": v["starts"], "diff": v["act"] - v["proj"], "act": v["act"], "proj": v["proj"]}
           for (p, _), v in players.items() if v["starts"] >= 2]
    pls.sort(key=lambda x: -x["diff"])
    return rows, pls[:6], pls[::-1][:6]


# ---------------------------------------------------------------- close games
def close_games(lg, margin=10):
    rec = {r: [0, 0] for r in lg.team}
    nail = []
    for w in lg.weeks:
        sc = {m["roster_id"]: m["points"] or 0.0 for m in lg.matchups[w]}
        for a, b in _pairs(lg, w):
            d = abs(sc[a] - sc[b])
            if d < margin:
                win, lose = (a, b) if sc[a] > sc[b] else (b, a)
                rec[win][0] += 1
                rec[lose][1] += 1
                nail.append({"week": w, "winner": lg.team[win], "loser": lg.team[lose], "ws": sc[win], "ls": sc[lose], "margin": d})
    rows = sorted(({"team": lg.team[r], "w": v[0], "l": v[1]} for r, v in rec.items()),
                  key=lambda x: (-(x["w"] - x["l"]), -x["w"]))
    return rows, sorted(nail, key=lambda g: g["margin"])


# ---------------------------------------------------------------- scoring trends
def trends(lg, window=3):
    out = []
    for r, name in lg.team.items():
        pts = [next(m["points"] or 0.0 for m in lg.matchups[w] if m["roster_id"] == r) for w in lg.weeks]
        roll = [st.mean(pts[max(0, i - window + 1):i + 1]) for i in range(len(pts))]
        out.append({"team": name, "pts": pts, "roll": roll, "season": st.mean(pts), "recent": roll[-1]})
    league = [st.mean(next(m["points"] or 0.0 for m in lg.matchups[w] if m["roster_id"] == r) for r in lg.team) for w in lg.weeks]
    return sorted(out, key=lambda x: -(x["recent"] - x["season"])), league


# ---------------------------------------------------------------- position strength (season)
def position_strength(lg):
    tot = {r: collections.Counter() for r in lg.team}
    for w in lg.weeks:
        for m in lg.matchups[w]:
            for p, v in zip(m["starters"], m["starters_points"]):
                if p != "0":
                    tot[m["roster_id"]][lg.pos_of(p) or "?"] += v
    n = len(lg.weeks)
    rows = [{"team": lg.team[r], "ppg": {pos: tot[r][pos] / n for pos in POSITIONS}} for r in lg.team]
    for pos in POSITIONS:
        ranked = sorted(rows, key=lambda x: -x["ppg"][pos])
        for i, x in enumerate(ranked, 1):
            x.setdefault("rank", {})[pos] = i
    avg = {pos: st.mean(x["ppg"][pos] for x in rows) for pos in POSITIONS}
    for x in rows:
        x["avg_rank"] = st.mean(x["rank"].values())
    return sorted(rows, key=lambda x: x["avg_rank"]), avg


# ---------------------------------------------------------------- injury and bye damage (season)
def availability(lg, min_ppg=8.0):
    """Points of real contributors who were on the roster but couldn't play, split into byes and injuries/inactives,
    plus starts wasted on players who didn't play at all."""
    games = collections.Counter(p for w in lg.weeks for p in lg.played[w])
    ppg = {p: sum(lg.pts[p].get(w, 0) for w in lg.weeks if p in lg.played[w]) / n for p, n in games.items()}
    out = []
    for r, name in lg.team.items():
        bye = inj = 0.0
        dead, worst = [], collections.Counter()
        for w in lg.weeks:
            m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
            _, teams = lg.proj(w)
            for p in m.get("players") or []:
                if p in lg.played[w]:
                    continue  # he played
                v = ppg.get(p, 0)
                team = p if p.isalpha() else teams.get(p) or (lg.players.get(p) or {}).get("team")
                if p in m["starters"] and p != "0":
                    dead.append((w, lg.name_of(p)))
                if v < min_ppg:
                    continue
                if team in lg.bye.get(w, set()):
                    bye += v
                else:
                    inj += v
                    worst[lg.name_of(p)] += v
        out.append({"team": name, "bye": bye, "inj": inj, "dead": dead, "worst": worst.most_common(2)})
    return sorted(out, key=lambda x: -(x["bye"] + x["inj"]))
