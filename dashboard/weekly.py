"""Week-to-week stats: playoff odds, power rankings, awards, next-week preview, projections, close games, trends,
plus the season-long position-strength, bye and injury views."""

import collections
import math
import random
import re
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
            # league rules: each division's top two are in, the division winners get the byes, the last spots are wild
            # cards for the best remaining records; every tie goes to points for
            ranked = {d: sorted(m, key=key, reverse=True) for d, m in divs.items()}
            winners = sorted((m[0] for m in ranked.values()), key=key, reverse=True)
            runners = [m[1] for m in ranked.values() if len(m) > 1]
            wild = [r for r in order if r not in winners and r not in runners][:max(0, n_po - len(winners) - len(runners))]
            middle = sorted(runners + wild, key=key, reverse=True)
            seeds = winners + middle + [r for r in order if r not in winners and r not in middle]
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
    clinch = _clinched(lg, wins0, pf0, sched, n_po, divs)
    out = []
    for r in rids:
        t = tally[r]
        out.append({"team": lg.team[r], "rid": r, "wins": wins0[r], "losses": len(played) - wins0[r], "pf": pf0[r], **clinch[r],
                    "playoffs": t["playoffs"] / sims, "bye": t["bye"] / sims, "first": t["first"] / sims,
                    "last": t["last"] / sims, "proj_wins": t["wins"] / sims, "division": lg.division.get(r)})
    return sorted(out, key=lambda x: (-x["playoffs"], -x["bye"], -x["proj_wins"]))


def _misses(d, o, n_po, n_div):
    """Can a team miss the playoffs with d division-mates and o other teams finishing ahead of it?
    The top two in each division are in, then wild cards: to miss, two division-mates must be ahead and the wild cards
    must also go to teams ahead of it, from its own division (beyond the top two) or the other one (beyond that division's top two)."""
    wild = n_po - 2 * n_div
    if d < 2:
        return False
    return any(a + b >= wild for a in range(wild + 1) for b in range(wild + 1) if d - 2 >= a and (b == 0 or o - 2 >= b))


def _clinched(lg, wins0, pf0, sched, n_po, divs):
    """Mathematical clinches and eliminations: worst case (lose out, every rival wins out, ties go against) and best case."""
    left = collections.Counter(r for games in sched.values() for pair in games for r in pair)
    out = {}
    two_divs = len(divs) == 2 and None not in divs
    for r in wins0:
        lo, hi = wins0[r], wins0[r] + left[r]
        mates = [x for x in divs.get(lg.division.get(r), []) if x != r]
        others = [x for x in wins0 if x != r and x not in mates]
        settled = lambda x: not left[r] and not left[x]       # both done: a tie in wins is already decided on points
        can_pass = lambda x: (wins0[x], pf0[x]) > (lo, pf0[r]) if settled(x) else wins0[x] + left[x] >= lo  # could finish ahead
        sure_ahead = lambda x: (wins0[x], pf0[x]) > (hi, pf0[r]) if settled(x) else wins0[x] > hi          # ahead even if it wins out
        if two_divs:
            po = not _misses(sum(map(can_pass, mates)), sum(map(can_pass, others)), n_po, len(divs))
            out_ = _misses(sum(map(sure_ahead, mates)), sum(map(sure_ahead, others)), n_po, len(divs))
            bye = not any(map(can_pass, mates))
        else:
            po = sum(can_pass(x) for x in wins0 if x != r) < n_po
            out_ = sum(sure_ahead(x) for x in wins0 if x != r) >= n_po
            bye = False
        out[r] = {"clinched": po, "clinched_bye": bye, "eliminated": out_}
    return out


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


# ---------------------------------------------------------------- byes and injuries (season)
def _ppg(lg):
    games = collections.Counter(p for w in lg.weeks for p in lg.played[w])
    return {p: sum(lg.pts[p].get(w, 0) for w in lg.weeks if p in lg.played[w]) / n for p, n in games.items()}


def _nfl_team(lg, p, w=None):
    if p.isalpha():
        return p
    return (lg.proj(w)[1].get(p) if w else None) or (lg.players.get(p) or {}).get("team")


def byes(lg, min_ppg=8.0):
    """Season averages of contributors lost to byes so far, and still to come for the current roster."""
    ppg = _ppg(lg)
    out = []
    for r, name in lg.team.items():
        past, future = [], []
        for w in lg.weeks:
            m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
            for p in m.get("players") or []:
                if ppg.get(p, 0) >= min_ppg and p not in lg.played[w] and _nfl_team(lg, p, w) in lg.bye.get(w, set()):
                    past.append((w, lg.name_of(p), ppg[p]))
        for w in (x for x in lg.reg_weeks if x >= lg.next_week):
            for p in lg.roster_now.get(r, ()):
                if ppg.get(p, 0) >= min_ppg and _nfl_team(lg, p) in lg.bye.get(w, set()):
                    future.append((w, lg.name_of(p), ppg[p]))
        out.append({"team": name, "past": sorted(past), "future": sorted(future),
                    "lost": sum(v for *_, v in past), "to_come": sum(v for *_, v in future)})
    return sorted(out, key=lambda x: -(x["lost"] + x["to_come"]))


_INJ = re.compile(r"([A-Z]{2,3})-((?:[A-Z][a-z]?\.)?[A-Z][\w'.-]*(?: [A-Z][\w'.-]+)*) (was injured during the play|has returned to the game)")


def injury_exits(lg, w):
    """{(espn name token like 'E.Arroyo', game's teams)} for players who got hurt during a play in week w and never came back."""
    hurt = set()
    for g in winprob.espn_games(lg.season, w):
        try:
            items, page = [], 1
            while True:
                d = winprob._fetch(winprob.ESPN_PLAYS.format(id=g["id"], page=page))
                items += d["items"]
                if page >= d.get("pageCount", 1):
                    break
                page += 1
        except Exception as e:  # one bad game shouldn't sink the page
            print(f"plays for {g['name']} failed: {e}")
            continue
        state = {}  # name -> still out?  Any later mention in a play (not an injury note) means he came back.
        for pl in sorted(items, key=lambda p: int(p["sequenceNumber"])):
            text = pl.get("text") or ""
            plain = re.sub(r"\*\* Injury Update:.*", "", _INJ.sub("", text))
            for n in [n for n, out in state.items() if out and re.search(rf"(?<![\w.]){re.escape(n)}\b", plain)]:
                state[n] = False
            for m in _INJ.finditer(text):
                state[m.group(2)] = m.group(3).startswith("was")
        hurt |= {(n, tuple(g["teams"])) for n, out in state.items() if out}
    return hurt


def _matches(lg, p, token):
    first, _, last = token.partition(".")
    info = lg.players.get(p) or {}
    norm = lambda x: "".join(ch for ch in x.lower() if ch.isalnum())
    return norm(info.get("last_name") or "") == norm(last) and (info.get("first_name") or "").lower().startswith(first.lower())


HURT = {"IR": "injured reserve", "Out": "out", "PUP": "PUP list", "Doubtful": "doubtful"}


def dropped_hurt(lg, r, ppg, min_ppg=5.0):
    """Players team r cut who are still hurt and haven't played a down since."""
    if lg.complete:  # injury status is today's, which says nothing about a finished season
        return []
    out = {}
    for t in sorted(lg.transactions, key=lambda t: t["status_updated"]):
        if t["status"] != "complete":
            continue
        for p, rr in (t.get("drops") or {}).items():
            info = lg.players.get(p) or {}
            if (rr != r or p in lg.roster_now.get(r, ()) or ppg.get(p, 0) < min_ppg or info.get("injury_status") not in HURT
                    or any(p in lg.played[w] for w in lg.weeks if w >= t["leg"])):
                continue
            now = next((lg.team[o] for o, ps in lg.roster_now.items() if p in ps), None)
            out[p] = {"week": t["leg"], "player": lg.name_of(p), "pos": lg.pos_of(p), "ppg": ppg[p],
                      "status": HURT[info["injury_status"]], "injury": info.get("injury_body_part"), "now": now}
    return sorted(out.values(), key=lambda x: x["week"])


def injuries(lg, min_ppg=8.0):
    """Points lost to injury: games missed while the player's NFL team played, and games he left hurt and never returned to,
    plus starts wasted on players who didn't play at all and injured players the team cut."""
    ppg = _ppg(lg)
    exits = {w: injury_exits(lg, w) for w in lg.weeks}
    out = []
    for r, name in lg.team.items():
        missed, left, dead = [], [], []
        for w in lg.weeks:
            m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
            for p in m.get("players") or []:
                v, team = ppg.get(p, 0), _nfl_team(lg, p, w)
                if p not in lg.played[w]:
                    if p in m["starters"] and p != "0":
                        dead.append((w, lg.name_of(p), lg.pos_of(p), "bye" if team in lg.bye.get(w, set()) else "didn’t play"))
                    if v >= min_ppg and team not in lg.bye.get(w, set()):
                        missed.append((w, lg.name_of(p), v))
                elif v >= min_ppg and not p.isalpha() and any(team in ts and _matches(lg, p, n) for n, ts in exits[w]):
                    got = lg.pts[p].get(w, 0)
                    left.append((w, lg.name_of(p), max(0.0, v - got), got, p in m["starters"]))
        out.append({"team": name, "missed": missed, "left": left, "dead": dead, "cut": dropped_hurt(lg, r, ppg),
                    "out": sum(x[2] for x in missed), "early": sum(x[2] for x in left)})
    return sorted(out, key=lambda x: -(x["out"] + x["early"]))


# ---------------------------------------------------------------- opponents' career days (season)
def opponent_peaks(lg, top=2, min_games=3, floor=15.0):
    """For each team: opposing starters who had one of their `top` best games of the season against it (and at least
    `floor` points, so a scrub's best day doesn't count), versus how many you'd expect by chance. A player with n games,
    k of them qualifying, has a k-in-n chance that any one game is one of them."""
    games = {p: sorted(((lg.pts[p].get(w, 0), w) for w in lg.weeks if p in lg.played[w]), reverse=True) for p in lg.pts}
    out = []
    for r, name in lg.team.items():
        actual, expected, extra, hits = 0, 0.0, 0.0, []
        for w in lg.weeks:
            opp = lg.opponent(w).get(r)
            if opp is None:
                continue
            m = next(m for m in lg.matchups[w] if m["roster_id"] == opp)
            for p in m["starters"]:
                g = games.get(p, [])
                if p == "0" or p not in lg.played[w] or len(g) < min_games:
                    continue
                cut = g[min(top, len(g)) - 1][0]  # ties with the last qualifying game count
                best = [x for x, _ in g if x >= cut and x >= floor]
                expected += len(best) / len(g)
                v = lg.pts[p].get(w, 0)
                if v >= cut and v >= floor:
                    avg = sum(x for x, _ in g) / len(g)
                    actual += 1
                    extra += v - avg
                    hits.append({"week": w, "player": lg.name_of(p), "pos": lg.pos_of(p), "opp": lg.team[opp], "pts": v, "avg": avg,
                                 "rank": 1 + sum(1 for x, _ in g if x > v)})  # 1 = season best, ties share the higher rank
        out.append({"team": name, "actual": actual, "expected": expected, "extra": extra, "hits": sorted(hits, key=lambda h: h["week"])})
    return sorted(out, key=lambda x: -(x["actual"] - x["expected"]))
