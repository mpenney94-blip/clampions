"""Load a Sleeper league's season and compute the dashboard's stats."""

import collections
import datetime as dt
import statistics as st

import winprob
from sleeper import SleeperClient

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
FLEX = {"FLEX": ("RB", "WR", "TE"), "SUPER_FLEX": ("QB", "RB", "WR", "TE"),
        "REC_FLEX": ("WR", "TE"), "WRRB_FLEX": ("RB", "WR")}


class League:
    """Everything the dashboard needs about one league, through the last scored week."""

    def __init__(self, league_id, client=None):
        c = self.client = client or SleeperClient()
        self.id = league_id
        self.info = c.league(league_id)
        self.name = self.info["name"]
        self.season = self.info["season"]
        self.scoring = self.info["scoring_settings"]
        self.slots = [s for s in self.info["roster_positions"] if s not in ("BN", "IR", "TAXI")]
        st_ = self.info["settings"]
        last = st_.get("last_scored_leg", 0)
        if st_.get("playoff_week_start"):  # season stats cover the regular season; playoff weeks include teams with no game
            last = min(last, st_["playoff_week_start"] - 1)
        self.weeks = list(range(st_.get("start_week", 1), last + 1))
        self.complete = self.info.get("status") == "complete"
        users = {u["user_id"]: u for u in c.league_users(league_id)}
        self.team, self.roster_now, self.division, self.owner = {}, {}, {}, {}
        for r in c.rosters(league_id):
            self.roster_now[r["roster_id"]] = set(r.get("players") or [])
            self.division[r["roster_id"]] = (r.get("settings") or {}).get("division")
            u = users.get(r["owner_id"]) or {}
            self.owner[r["roster_id"]] = r.get("owner_id") or f"roster-{r['roster_id']}"  # the manager, which outlives team names
            self.team[r["roster_id"]] = (u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Team {r['roster_id']}"
        self.players = c.players()
        self.matchups = {w: c.matchups(league_id, w) for w in self.weeks}
        self.pts = collections.defaultdict(dict)  # player_id -> week -> league-scored points (anyone, rostered or not)
        self.played = collections.defaultdict(set)  # week -> players who were active for a game
        for w in self.weeks:
            rows = winprob._fetch(f"https://api.sleeper.app/stats/nfl/{self.season}/{w}?season_type=regular"
                                  + "".join(f"&position[]={p}" for p in POSITIONS))
            for r in rows:
                s = r.get("stats") or {}
                if s.get("gp") or r["player_id"].isalpha():  # gms_active is set for injured players who sat
                    self.pts[r["player_id"]][w] = round(winprob.score_stats(s, self.scoring), 2)
                    self.played[w].add(r["player_id"])
            for m in self.matchups[w]:  # Sleeper's own numbers win where we have them
                for pid, v in (m.get("players_points") or {}).items():
                    self.pts[pid][w] = v
        self.transactions = []
        for w in self.weeks + [self.weeks[-1] + 1] if self.weeks else []:
            self.transactions += [dict(t, leg=w) for t in c.transactions(league_id, w)]  # includes failed waiver claims
        drafts = c.league_drafts(league_id)
        self.picks = c.draft_picks(drafts[0]["draft_id"]) if drafts else []
        self._kickoffs = {}
        st_ = self.info["settings"]
        self.playoff_teams = st_.get("playoff_teams") or 0
        self.playoff_start = st_.get("playoff_week_start") or 0
        self.reg_weeks = list(range(st_.get("start_week", 1), self.playoff_start)) if self.playoff_start else self.weeks
        self.next_week = self.weeks[-1] + 1 if self.weeks else 1
        self._proj = {}
        self.champion = None
        if self.complete:
            bracket = winprob._fetch(f"https://api.sleeper.app/v1/league/{league_id}/winners_bracket") or []
            final = next((m for m in bracket if m.get("p") == 1 and m.get("w")), None)
            self.champion = self.team.get(final["w"]) if final else None
        sched = winprob._fetch(f"https://api.sleeper.app/schedule/nfl/regular/{self.season}")
        all_teams = {t for g in sched for t in (g["home"], g["away"])}
        self.bye = {w: all_teams - {t for g in sched if g["week"] == w for t in (g["home"], g["away"])} for w in {g["week"] for g in sched}}

    # ---- helpers
    def name_of(self, pid):
        if pid.isalpha():
            return f"{pid} D/ST"
        return (self.players.get(pid) or {}).get("full_name") or pid

    def pos_of(self, pid):
        return "DEF" if pid.isalpha() else (self.players.get(pid) or {}).get("position")

    def scores(self, w):
        return {m["roster_id"]: m["points"] or 0.0 for m in self.matchups[w]}

    def opponent(self, w):
        ms = self.matchups[w]
        by = collections.defaultdict(list)
        for m in ms:
            if m.get("matchup_id") is not None:
                by[m["matchup_id"]].append(m["roster_id"])
        return {a: b for pair in by.values() if len(pair) == 2 for a, b in (pair, pair[::-1])}

    def proj(self, w):
        """(league-scored projection by player, team by player) for week w."""
        if w not in self._proj:
            self._proj[w] = winprob.projections(self.season, w, self.scoring)
        return self._proj[w]

    def matchups_for(self, w):
        if w not in self.matchups:
            self.matchups[w] = self.client.matchups(self.id, w)
        return self.matchups[w]

    def kickoffs(self, w):
        if w not in self._kickoffs:
            g = winprob.espn_games(self.season, w)
            self._kickoffs[w] = (min(x["kickoff"] for x in g), max(x["kickoff"] for x in g)) if g else (0, 0)
        return self._kickoffs[w]

    def first_week_after(self, ts):
        """First week whose games had not all kicked off by unix time ts."""
        for w in self.weeks:
            if ts < self.kickoffs(w)[1]:
                return w
        return (self.weeks[-1] + 1) if self.weeks else 1


def _result(a, b):
    return 0 if a > b else 1 if a < b else 2


def allplay(lg):
    rows = []
    for r, name in lg.team.items():
        ap, real, pf, pa = [0, 0, 0], [0, 0, 0], 0.0, 0.0
        for w in lg.weeks:
            sc, opp = lg.scores(w), lg.opponent(w)
            pf += sc[r]
            for o, v in sc.items():
                if o != r:
                    ap[_result(sc[r], v)] += 1
            if r in opp:
                pa += sc[opp[r]]
                real[_result(sc[r], sc[opp[r]])] += 1
        games = sum(real)
        pct = (ap[0] + ap[2] / 2) / sum(ap) if sum(ap) else 0
        rows.append({"team": name, "roster_id": r, "allplay": ap, "pct": pct, "record": real, "pf": pf, "pa": pa,
                     "luck": real[0] + real[2] / 2 - pct * games})
    rows.sort(key=lambda x: (-x["pct"], -x["pf"]))
    return rows


def schedule_swap(lg, order):
    """grid[i][j] = wins team order[i] would have with order[j]'s schedule."""
    def wins(t, u):
        n = 0
        for w in lg.weeks:
            sc, opp = lg.scores(w), lg.opponent(w)
            o = opp.get(u)
            if o is None:
                continue
            if o == t:
                o = u
            n += sc[t] > sc[o]
        return n
    return [[wins(t, u) for u in order] for t in order]


def _optimal(lg, pp):
    avail = sorted(pp.items(), key=lambda kv: -kv[1])
    used, tot = [], 0.0
    for s in sorted(lg.slots, key=lambda s: s in FLEX):
        ok = FLEX.get(s, (s,))
        for pid, v in avail:
            if pid not in used and lg.pos_of(pid) in ok:
                used.append(pid)
                tot += v
                break
    return tot, used


def bench(lg):
    out = {r: {"team": n, "lost": 0.0, "flips": [], "worst": None} for r, n in lg.team.items()}
    for w in lg.weeks:
        sc, opp = lg.scores(w), lg.opponent(w)
        for m in lg.matchups[w]:
            r = m["roster_id"]
            opt, used = _optimal(lg, m.get("players_points") or {})
            out[r]["lost"] += opt - sc[r]
            if r in opp and sc[r] < sc[opp[r]] < opt:
                out[r]["flips"].append(w)
            for pid in used:
                if pid not in m["starters"]:
                    v = m["players_points"][pid]
                    if not out[r]["worst"] or v > out[r]["worst"]["pts"]:
                        out[r]["worst"] = {"player": lg.name_of(pid), "pts": v, "week": w}
    return sorted(out.values(), key=lambda x: -x["lost"])


def pickups(lg):
    """Waiver and free-agent adds, with points per game while on the adding team's roster."""
    roster = {(m["roster_id"], w): (set(m.get("players") or []), m.get("players_points") or {})
              for w in lg.weeks for m in lg.matchups[w]}
    seen, out = set(), []
    for t in sorted(lg.transactions, key=lambda t: t["status_updated"]):
        if t["type"] not in ("waiver", "free_agent") or t["status"] != "complete":
            continue
        for pid, r in (t.get("adds") or {}).items():
            if (r, pid) in seen or lg.pos_of(pid) not in POSITIONS:
                continue
            seen.add((r, pid))
            weeks = [w for w in lg.weeks if w >= t["leg"] and pid in roster.get((r, w), (set(), {}))[0] and w in lg.pts.get(pid, {})]
            if not weeks:
                continue
            total = sum(roster[(r, w)][1].get(pid, 0) for w in weeks)
            out.append({"player": lg.name_of(pid), "pos": lg.pos_of(pid), "team": lg.team[r],
                        "bid": (t.get("settings") or {}).get("waiver_bid", 0) if t["type"] == "waiver" else 0,
                        "games": len(weeks), "total": total, "ppg": total / len(weeks)})
    return out


def waiver_wars(lg):
    """Waiver claims more than one team made for the same player, and what the losers missed."""
    runs = collections.defaultdict(list)  # (player, waiver run time) -> every claim on him in that run
    for t in lg.transactions:
        if t["type"] == "waiver" and t.get("adds"):
            for pid in t["adds"]:
                runs[(pid, t["status_updated"] // 60000)].append(t)
    out = []
    for (pid, _), ts in runs.items():
        losers = [{"team": lg.team[t["adds"][pid]], "bid": (t.get("settings") or {}).get("waiver_bid", 0)} for t in ts
                  if t["status"] == "failed" and "claimed by another" in ((t.get("metadata") or {}).get("notes") or "")]
        win = next((t for t in ts if t["status"] == "complete"), None)
        if not losers or not win:
            continue
        leg = win["leg"]  # claims made earlier in the week can carry an earlier leg; the run counts from the winner's
        weeks = [w for w in lg.weeks if w >= leg and w in lg.pts.get(pid, {})]
        out.append({"player": lg.name_of(pid), "pos": lg.pos_of(pid), "week": leg,
                    "winner": lg.team[win["adds"][pid]], "win_bid": (win.get("settings") or {}).get("waiver_bid", 0),
                    "losers": sorted(losers, key=lambda x: -x["bid"]), "since": sum(lg.pts[pid][w] for w in weeks), "games": len(weeks)})
    out.sort(key=lambda x: -x["since"])
    per_team = collections.defaultdict(lambda: {"lost": 0, "missed": 0.0, "best": None, "claims": []})
    for c in out:
        for lo in {x["team"]: x for x in c["losers"]}.values():
            t = per_team[lo["team"]]
            t["lost"] += 1
            t["claims"].append({"claim": c, "bid": lo["bid"]})
            t["missed"] += c["since"]
            if not t["best"] or c["since"] > t["best"]["since"]:
                t["best"] = c
    return out, dict(per_team)


def waiver_bids(lg):
    """Every team's waiver claims: how many bids, how many won, and how far each win was over the next-highest bid
    (the whole bid when nobody else claimed him, since the league minimum is $0)."""
    floor = lg.info["settings"].get("waiver_bid_min", 0)
    runs = collections.defaultdict(list)
    for t in lg.transactions:
        if t["type"] == "waiver" and t.get("adds"):
            for pid in t["adds"]:
                runs[(pid, t["status_updated"] // 60000)].append(t)
    out = {r: {"team": n, "bids": 0, "won": 0, "spent": 0, "over": 0, "claims": []} for r, n in lg.team.items()}
    for (pid, _), ts in runs.items():
        bid = lambda t: (t.get("settings") or {}).get("waiver_bid", 0)
        win = next((t for t in ts if t["status"] == "complete"), None)
        for t in ts:
            r = t["adds"][pid]
            others = [bid(o) for o in ts if o is not t and o["adds"][pid] != r]
            note = (t.get("metadata") or {}).get("notes") or ""
            c = {"week": t["leg"], "player": lg.name_of(pid), "pos": lg.pos_of(pid), "bid": bid(t), "won": t["status"] == "complete",
                 "next": max(others, default=None), "dropped": [lg.name_of(d) for d in (t.get("drops") or {})], "over": 0}
            if c["won"]:
                c["over"] = bid(t) - max(others + [floor])
                out[r]["won"] += 1
                out[r]["spent"] += bid(t)
                out[r]["over"] += c["over"]
            elif win is not None and "claimed by another" in note:
                c["why"] = f'{lg.team[win["adds"][pid]]} won at ${bid(win)}'
            else:
                c["why"] = "roster would have been too full" if "too many players" in note else (note.rstrip(".") or "failed")
            out[r]["bids"] += 1
            out[r]["claims"].append(c)
    for x in out.values():
        x["claims"].sort(key=lambda c: (c["week"], -c["bid"]))
    return sorted(out.values(), key=lambda x: -x["over"])


def drop_regrets(lg, top=12, skip=("K", "DEF")):
    """Players a team cut who then scored, ranked by points since the drop. Kickers and defenses are left out:
    streaming them is a plan, not a mistake. A team re-adding the player ends that drop's window."""
    rostered = {(m["roster_id"], w): set(m.get("players") or []) for w in lg.weeks for m in lg.matchups[w]}
    started = {(m["roster_id"], w): set(m.get("starters") or []) for w in lg.weeks for m in lg.matchups[w]}
    adds = collections.defaultdict(list)  # (team, player) -> times the team added him
    for t in lg.transactions:
        if t["status"] == "complete":
            for p, r in (t.get("adds") or {}).items():
                adds[(r, p)].append(t["status_updated"])
    out = []
    for t in sorted(lg.transactions, key=lambda t: t["status_updated"]):
        if t["status"] != "complete" or t["type"] == "trade":
            continue
        for p, r in (t.get("drops") or {}).items():
            if lg.pos_of(p) in skip:
                continue
            eff = lg.first_week_after(t["status_updated"] / 1000)
            back = min((a for a in adds[(r, p)] if a > t["status_updated"]), default=None)
            end = lg.first_week_after(back / 1000) if back else lg.weeks[-1] + 1
            before = [w for w in lg.weeks if w < eff and p in rostered.get((r, w), ()) and p in lg.played[w]]
            after = [w for w in lg.weeks if eff <= w < end and p in lg.played[w]]
            if not after:
                continue
            pts_after = sum(lg.pts[p].get(w, 0) for w in after)
            homes = collections.Counter(next((lg.team[o] for (o, ww), ps in rostered.items() if ww == w and p in ps), "free agent") for w in after)
            now = next((lg.team[o] for o, ps in lg.roster_now.items() if p in ps), None)
            out.append({"player": lg.name_of(p), "pos": lg.pos_of(p), "team": lg.team[r], "week": eff,
                        "before_games": len(before), "before": sum(lg.pts[p].get(w, 0) for w in before),
                        "after_games": len(after), "after": pts_after,
                        "best": max((lg.pts[p].get(w, 0), w) for w in after),
                        "kept_by": [h for h, _ in homes.most_common() if h != "free agent"],
                        "now": now, "readded": bool(back),
                        # points he scored while in another team's starting lineup, ie. the damage done elsewhere
                        "started_elsewhere": sum(lg.pts[p].get(w, 0) for w in after
                                                 if any(p in started.get((o, w), ()) for o in lg.team if o != r))})
    out.sort(key=lambda x: -x["after"])
    return out[:top]


def carry(lg):
    """Where each team's starting-lineup points came from, by position and by player."""
    out = []
    for r, name in lg.team.items():
        by_pos, by_player = collections.Counter(), collections.Counter()
        for w in lg.weeks:
            m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
            for pid, v in zip(m["starters"], m["starters_points"]):
                if pid != "0":
                    by_pos[lg.pos_of(pid) or "?"] += v
                    by_player[pid] += v
        total = sum(by_pos.values()) or 1
        top = by_player.most_common(1)[0] if by_player else (None, 0)
        out.append({"team": name, "total": total, "by_pos": dict(by_pos),
                    "top": {"player": lg.name_of(top[0]) if top[0] else "", "pts": top[1], "share": top[1] / total}})
    return sorted(out, key=lambda x: -x["top"]["share"])


def starts(lg, min_starts=4):
    """Every player started at least min_starts times: average and spread of his started scores."""
    seen = collections.defaultdict(list)  # pid -> [(team, pts)]
    for w in lg.weeks:
        for m in lg.matchups[w]:
            for pid, v in zip(m["starters"], m["starters_points"]):
                if pid != "0":
                    seen[pid].append((lg.team[m["roster_id"]], v))
    out = []
    for pid, xs in seen.items():
        if len(xs) < min_starts:
            continue
        vals = [v for _, v in xs]
        team = collections.Counter(t for t, _ in xs).most_common(1)[0][0]
        keeper = any(p["player_id"] == pid and p.get("is_keeper") and lg.team[p["roster_id"]] == team for p in lg.picks)
        out.append({"player": lg.name_of(pid), "pos": lg.pos_of(pid), "team": team, "starts": len(vals), "keeper": keeper,
                    "avg": st.mean(vals), "sd": st.pstdev(vals), "low": min(vals), "high": max(vals)})
    return out


def team_grid(lg, r):
    """Every player on roster r by week: (points, started?) for weeks he was on the roster and played."""
    rows = collections.defaultdict(dict)
    for w in lg.weeks:
        m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
        pp = m.get("players_points") or {}
        for pid in m.get("players") or []:
            if w in lg.pts.get(pid, {}) or pid in m["starters"]:
                rows[pid][w] = (pp.get(pid, 0.0), pid in m["starters"])
    keepers = {p["player_id"] for p in lg.picks if p.get("is_keeper") and p["roster_id"] == r}
    out = [{"player": lg.name_of(pid), "pos": lg.pos_of(pid), "weeks": wk, "keeper": pid in keepers,
            "started": sum(v for v, s in wk.values() if s), "benched": sum(v for v, s in wk.values() if not s)}
           for pid, wk in rows.items() if any(s for _, s in wk.values()) or sum(v for v, _ in wk.values()) >= 5]
    return sorted(out, key=lambda x: (-x["started"], -x["benched"]))


def week_totals(lg, r):
    """{week: (starting-lineup score, best possible lineup score)} for roster r."""
    out = {}
    for w in lg.weeks:
        m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
        out[w] = (m["points"] or 0.0, _optimal(lg, m.get("players_points") or {})[0])
    return out


def sources(lg):
    """Starting-lineup points per team split by how the player got there: draft (and which round), waiver/free agent, or trade."""
    events = collections.defaultdict(list)  # (roster, player) -> [(effective week, time, kind, round)]
    keepers = {(p["roster_id"], p["player_id"]) for p in lg.picks if p.get("is_keeper")}
    for p in lg.picks:
        events[(p["roster_id"], p["player_id"])].append((0, 0, "draft", p["round"]))
    for t in lg.transactions:
        if t["status"] != "complete" or t["type"] not in ("waiver", "free_agent", "trade"):
            continue
        kind = "trade" if t["type"] == "trade" else "waiver"
        eff = t["leg"] if t["type"] == "waiver" else lg.first_week_after(t["status_updated"] / 1000)
        for pid, r in (t.get("adds") or {}).items():
            events[(r, pid)].append((eff, t["status_updated"], kind, None))
    out = {}
    for r, name in lg.team.items():
        row = {"team": name, "draft": 0.0, "waiver": 0.0, "trade": 0.0, "rounds": collections.Counter(),
               "round_players": collections.defaultdict(collections.Counter), "keeper": 0.0,
               "keeper_round": next((p["round"] for p in lg.picks if p.get("is_keeper") and p["roster_id"] == r), None),
               "players": collections.defaultdict(lambda: [0.0, None, None])}
        for w in lg.weeks:
            m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
            for pid, v in zip(m["starters"], m["starters_points"]):
                if pid == "0":
                    continue
                ev = [e for e in events.get((r, pid), []) if e[0] <= w] or events.get((r, pid), [])
                kind, rnd = (max(ev)[2], max(ev)[3]) if ev else ("waiver", None)
                row[kind] += v
                if kind == "draft":
                    row["rounds"][rnd] += v
                    row["round_players"][rnd][lg.name_of(pid)] += v
                    if (r, pid) in keepers:
                        row["keeper"] += v
                pl = row["players"][pid]
                pl[0] += v
                pl[1], pl[2] = kind, rnd
        row["total"] = row["draft"] + row["waiver"] + row["trade"]
        best = {}
        for pid, (v, kind, _) in row["players"].items():
            if kind and (kind not in best or v > best[kind][1]):
                best[kind] = (lg.name_of(pid), v)
        row["best"] = best
        del row["players"]
        row["round_notes"] = {p["round"]: _pick_note(lg, r, p["player_id"]) for p in lg.picks
                              if p["roster_id"] == r and row["rounds"].get(p["round"], 0) <= 0}
        out[name] = row
    return out


def _departure(lg, r, pid):
    """How a player left roster r and where he is now, e.g. 'traded to X, wk 7' or 'dropped wk 1 · now on Y'."""
    left = None
    for t in sorted(lg.transactions, key=lambda t: t["status_updated"]):
        if t["status"] == "complete" and (t.get("drops") or {}).get(pid) == r:
            left = t
    now = next((lg.team[o] for o, ps in lg.roster_now.items() if pid in ps), None)
    if left and left["type"] == "trade" and pid in (left.get("adds") or {}):
        return f"traded to {lg.team[left['adds'][pid]]}, wk {min(left['leg'], lg.weeks[-1])}" + (f" · now on {now}" if now and now != lg.team[left['adds'][pid]] else "")
    wk = f" wk {min(left['leg'], lg.weeks[-1])}" if left else ""
    return f"dropped{wk} · " + (f"now on {now}" if now else "free agent")


def _pick_note(lg, r, pid):
    """Why a draft pick has no starting-lineup points for the team that drafted him."""
    name = lg.name_of(pid)
    starts = bench = 0
    for w in lg.weeks:
        m = next(m for m in lg.matchups[w] if m["roster_id"] == r)
        if pid in m["starters"]:
            starts += 1
        elif pid in (m.get("players") or []):
            bench += (m.get("players_points") or {}).get(pid, 0)
    if starts:
        return f"{name}: started {starts}× for 0 points"
    left = next((t for t in sorted(lg.transactions, key=lambda t: t["status_updated"])
                 if t["status"] == "complete" and (t.get("drops") or {}).get(pid) == r), None)
    now = next((lg.team[m["roster_id"]] for m in lg.matchups[lg.weeks[-1]] if pid in (m.get("players") or [])), None)
    if left:
        how = f"traded to {lg.team[left['adds'][pid]]}" if left["type"] == "trade" and pid in (left.get("adds") or {}) else "dropped"
        wk = min(left["leg"], lg.weeks[-1])
        if now == lg.team[r]:
            tail = "; picked back up later (those points count as a pickup)"
        elif now:
            tail = f"; now on {now}" if how == "dropped" else ""
        else:
            tail = "; now a free agent"
        return f"{name}: {how} in week {wk} without starting{f' ({bench:.1f} pts on the bench)' if bench else ''}{tail}"
    return f"{name}: on the roster but never started ({bench:.1f} pts on the bench)"


def trades(lg):
    out = []
    for t in sorted((t for t in lg.transactions if t["type"] == "trade" and t["status"] == "complete"), key=lambda t: t["status_updated"]):
        eff = lg.first_week_after(t["status_updated"] / 1000)
        weeks = [w for w in lg.weeks if w >= eff]
        sides = []
        for r in t["roster_ids"]:
            got = [{"player": lg.name_of(p), "pos": lg.pos_of(p), "since": sum(lg.pts.get(p, {}).get(w, 0) for w in weeks)}
                   for p, rr in (t.get("adds") or {}).items() if rr == r]
            picks = [f"{dp['season']} round {dp['round']} pick" for dp in (t.get("draft_picks") or []) if dp.get("owner_id") == r]
            sides.append({"team": lg.team[r], "got": got, "picks": picks, "total": sum(g["since"] for g in got)})
        out.append({"weeks": weeks, "when": dt.datetime.fromtimestamp(t["status_updated"] / 1000, dt.timezone.utc), "sides": sides})
    return out


def draft(lg, window=15):
    rows = []
    for p in lg.picks:
        pid = p["player_id"]
        gone = pid not in lg.roster_now.get(p["roster_id"], set())
        rows.append({"pick": p["pick_no"], "round": p["round"], "player": lg.name_of(pid), "keeper": bool(p.get("is_keeper")),
                     "gone": _departure(lg, p["roster_id"], pid) if gone else None,
                     "pos": lg.pos_of(pid) or (p.get("metadata") or {}).get("position"),
                     "team": lg.team.get(p["roster_id"], "?"), "pts": sum(lg.pts.get(pid, {}).get(w, 0) for w in lg.weeks),
                     "rid": p["roster_id"], "slot": p.get("draft_slot"), "pid": pid})
    for x in rows:
        x["exp"] = st.median(y["pts"] for y in rows if abs(y["pick"] - x["pick"]) <= window)
        x["value"] = x["pts"] - x["exp"]
    return rows


def recap(lg, w):
    sc, opp = lg.scores(w), lg.opponent(w)
    games = sorted({tuple(sorted((a, b))) for a, b in opp.items()})
    gl = [{"a": lg.team[a], "b": lg.team[b], "pa": sc[a], "pb": sc[b], "margin": abs(sc[a] - sc[b])} for a, b in games]
    hi = max(sc, key=sc.get)
    lo = min(sc, key=sc.get)
    return {"week": w, "games": gl, "high": (lg.team[hi], sc[hi]), "low": (lg.team[lo], sc[lo]),
            "closest": min(gl, key=lambda g: g["margin"]), "blowout": max(gl, key=lambda g: g["margin"]),
            "median": st.median(sc.values())}


# ---------------------------------------------------------------- season summary (feeds the all-time page)
def _finishes(lg):
    """roster_id -> final place from Sleeper's winners and consolation brackets.

    The consolation bracket can be a toilet bowl, where the loser of each game moves on and the team that loses
    every game finishes last. Sleeper still records the team that moves on as "w", so the real scores decide
    which way the bracket runs."""
    place, n = {}, len(lg.team)
    for m in winprob._fetch(f"https://api.sleeper.app/v1/league/{lg.id}/winners_bracket") or []:
        if m.get("p") and m.get("w") and m.get("l"):
            place[m["w"]], place[m["l"]] = m["p"], m["p"] + 1
    losers = [m for m in winprob._fetch(f"https://api.sleeper.app/v1/league/{lg.id}/losers_bracket") or [] if m.get("w") and m.get("l")]
    toilet = False
    if losers and lg.playoff_start:
        m = min(losers, key=lambda m: m["r"])
        sc = {x["roster_id"]: x["points"] or 0.0 for x in lg.client.matchups(lg.id, lg.playoff_start + m["r"] - 1)}
        toilet = sc.get(m["w"], 0) < sc.get(m["l"], 0)  # the team that moved on lost the game
    for m in losers:
        if m.get("p"):
            if toilet:  # p=1 is the toilet bowl final: whoever moved on (lost it) is last
                place[m["w"]], place[m["l"]] = n - m["p"] + 1, n - m["p"]
            else:
                place[m["w"]], place[m["l"]] = lg.playoff_teams + m["p"], lg.playoff_teams + m["p"] + 1
    return place


def season_summary(lg):
    """Everything the all-time page needs from one season, keyed by manager (Sleeper owner id), as plain JSON."""
    rec = {r: [0, 0, 0] for r in lg.team}
    pf, pa = collections.Counter(), collections.Counter()
    for w in lg.weeks:
        sc, opp = lg.scores(w), lg.opponent(w)
        for r, o in opp.items():
            rec[r][_result(sc[r], sc[o])] += 1
            pf[r] += sc[r]
            pa[r] += sc[o]
    reg_rank = {r: i for i, r in enumerate(sorted(lg.team, key=lambda r: (-(rec[r][0] + rec[r][2] / 2), -pf[r])), 1)}
    finish = _finishes(lg) if lg.complete else {}
    in_playoffs = set()
    if lg.complete:
        for m in winprob._fetch(f"https://api.sleeper.app/v1/league/{lg.id}/winners_bracket") or []:
            in_playoffs |= {m.get("t1"), m.get("t2")} - {None}
    own = lg.owner
    if lg.complete:  # anyone the brackets didn't place falls back to regular-season standing
        for r in sorted((r for r in lg.team if r not in finish), key=lambda r: reg_rank[r]):
            finish[r] = min(set(range(1, len(lg.team) + 1)) - set(finish.values()))
    teams = {own[r]: {"team": lg.team[r], "wins": rec[r][0], "losses": rec[r][1], "ties": rec[r][2],
                      "pf": round(pf[r], 2), "pa": round(pa[r], 2), "reg_rank": reg_rank[r],
                      "playoffs": (r in in_playoffs) if lg.complete else None,
                      "finish": finish.get(r) if lg.complete else None} for r in lg.team}
    by_name = {n: own[r] for r, n in lg.team.items()}
    keepers = [{"player": z["player"], "pos": z["pos"], "owner": by_name.get(z["team"]), "team": z["team"], "round": z["round"],
                "pick": z["pick"], "pts": round(z["pts"], 1), "value": round(z["value"], 1)} for z in draft(lg) if z["keeper"]]
    trade_rows = []
    for t in trades(lg):
        sides = [{"owner": by_name.get(sd["team"]), "team": sd["team"], "total": round(sd["total"], 1), "picks": sd["picks"],
                  "got": [{"player": g["player"], "pos": g["pos"], "since": round(g["since"], 1)} for g in sd["got"]]} for sd in t["sides"]]
        trade_rows.append({"week": t["weeks"][0] if t["weeks"] else None, "sides": sides})
    games = []  # [week, owner, points, owner, points, playoff?] for head-to-head records
    for w in lg.weeks:
        sc = lg.scores(w)
        for a, b in {tuple(sorted(pair)) for pair in lg.opponent(w).items()}:
            games.append([w, own[a], round(sc[a], 2), own[b], round(sc[b], 2), False])
    if lg.complete and lg.playoff_start:
        for m in winprob._fetch(f"https://api.sleeper.app/v1/league/{lg.id}/winners_bracket") or []:
            a, b, w = m.get("t1"), m.get("t2"), lg.playoff_start + m["r"] - 1
            if a and b and m.get("p") != 5:  # the 5th-place game is two knocked-out teams, often with empty lineups
                sc = {x["roster_id"]: x["points"] or 0.0 for x in lg.client.matchups(lg.id, w)}
                games.append([w, own[a], round(sc.get(a, 0), 2), own[b], round(sc.get(b, 0), 2), True])
    pickups_ = sorted(pickups(lg), key=lambda a: -a["total"])[:15]
    return {
        "season": lg.season, "complete": lg.complete, "weeks": len(lg.weeks), "playoff_teams": lg.playoff_teams, "teams": teams,
        "keepers": keepers, "trades": trade_rows, "games": games,
        "draft": [{"owner": by_name.get(z["team"]), "team": z["team"], "round": z["round"], "pick": z["pick"], "player": z["player"],
                   "pos": z["pos"], "pts": round(z["pts"], 1), "value": round(z["value"], 1), "keeper": z["keeper"]} for z in draft(lg)],
        "faab": {by_name[x["team"]]: {k: x[k] for k in ("bids", "won", "spent", "over")} for x in waiver_bids(lg)},
        "bench": {by_name[x["team"]]: round(x["lost"], 1) for x in bench(lg)},
        "pickups": [{"player": a["player"], "pos": a["pos"], "owner": by_name.get(a["team"]), "team": a["team"], "bid": a["bid"],
                     "games": a["games"], "total": round(a["total"], 1)} for a in pickups_],
        "drops": [{"player": d["player"], "pos": d["pos"], "owner": by_name.get(d["team"]), "team": d["team"], "week": d["week"],
                   "before": round(d["before"], 1), "after": round(d["after"], 1), "after_games": d["after_games"],
                   "started_elsewhere": round(d["started_elsewhere"], 1)} for d in drop_regrets(lg, top=15)],
    }


# ---------------------------------------------------------------- more draft views
def _replacement(lg):
    """Points per game of a replacement-level starter at each position: the Nth best, where N is how many the league starts."""
    teams = len(lg.team)
    need = collections.Counter()
    for sl in lg.slots:
        if sl in FLEX:
            share = {"FLEX": {"RB": .45, "WR": .45, "TE": .1}, "SUPER_FLEX": {"QB": .8, "RB": .1, "WR": .1},
                     "REC_FLEX": {"WR": .8, "TE": .2}, "WRRB_FLEX": {"RB": .5, "WR": .5}}.get(sl, {})
            for pos, f in share.items():
                need[pos] += f
        else:
            need[sl] += 1
    games = {p: [w for w in lg.weeks if p in lg.played[w]] for p in lg.pts}
    ppg = collections.defaultdict(list)
    for p, ws in games.items():
        if len(ws) >= max(1, len(lg.weeks) // 3):
            ppg[lg.pos_of(p)].append(sum(lg.pts[p][w] for w in ws) / len(ws))
    return {pos: (sorted(v, reverse=True)[min(len(v) - 1, max(0, round(need[pos] * teams) - 1))] if v else 0)
            for pos, v in ppg.items() if pos in need}


def draft_extras(lg):
    """Grades, board, redraft and position payoff for this season's draft."""
    rows = draft(lg)
    if not rows:
        return None
    starts = collections.Counter()
    for w in lg.weeks:
        for m in lg.matchups[w]:
            for p in m["starters"]:
                starts[(m["roster_id"], p)] += 1
    for x in rows:
        x["starts"] = starts[(x["rid"], x["pid"])]
    # grades
    by_team = collections.defaultdict(list)
    for x in rows:
        by_team[x["rid"]].append(x)
    tot = {r: sum(x["value"] for x in v) for r, v in by_team.items()}
    mu, sd = st.mean(tot.values()), (st.pstdev(tot.values()) or 1)
    cut = [(1.5, "A+"), (1, "A"), (.6, "A-"), (.3, "B+"), (0, "B"), (-.3, "B-"), (-.6, "C+"), (-1, "C"), (-1.5, "D")]
    grades = []
    for r, v in by_team.items():
        z = (tot[r] - mu) / sd
        grades.append({"team": lg.team[r], "value": tot[r], "grade": next((g for c, g in cut if z >= c), "F"),
                       "pts": sum(x["pts"] for x in v), "picks": len(v),
                       "hits": sum(1 for x in v if x["value"] > 0), "kept": sum(1 for x in v if not x["gone"]),
                       "starts": sum(x["starts"] for x in v),
                       "best": max(v, key=lambda x: x["value"]), "worst": min(v, key=lambda x: x["value"])})
    grades.sort(key=lambda g: -g["value"])
    # redraft: everyone who played, ranked by points per game above a replacement starter at the position, times games
    repl = _replacement(lg)
    taken = {x["pid"]: x for x in rows}
    pool = []
    for p, wk in lg.pts.items():
        pos = lg.pos_of(p)
        ws = [w for w in lg.weeks if p in lg.played[w]]
        if pos not in repl or not ws:
            continue
        total = sum(wk[w] for w in ws)
        pool.append({"player": lg.name_of(p), "pos": pos, "pts": total, "games": len(ws),
                     "var": total - repl[pos] * len(ws), "orig": taken.get(p)})
    pool.sort(key=lambda z: -z["var"])
    redraft = pool[:2 * len(lg.team)]
    # position payoff by round band
    bands = [(1, 2), (3, 5), (6, 9), (10, 99)]
    payoff = {}
    for pos in ("QB", "RB", "WR", "TE"):
        for lo, hi in bands:
            xs = [x for x in rows if x["pos"] == pos and lo <= x["round"] <= hi]
            if xs:
                payoff[(pos, lo)] = {"n": len(xs), "avg": st.mean(x["value"] for x in xs), "hit": sum(1 for x in xs if x["value"] > 0) / len(xs)}
    return {"rows": rows, "grades": grades, "redraft": redraft, "payoff": payoff, "bands": bands,
            "slots": sorted({x["slot"] for x in rows if x["slot"]}), "rounds": max(x["round"] for x in rows)}
