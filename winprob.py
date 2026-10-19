"""Reconstruct win probability over the course of a Sleeper fantasy week.

Sleeper doesn't publish its in-app win probability, so this rebuilds an estimate:

1. Each starter's projection comes from Sleeper's projections, scored with the
   league's own scoring settings.
2. ESPN play-by-play (with wall-clock timestamps) tells us when each player's
   points happened. Per-play fantasy points are approximated from yards,
   receptions and TDs, then scaled so each player's curve ends exactly at their
   actual Sleeper score. Kickers/defenses/unmatched players accrue linearly
   over their game.
3. At any moment, a team's expected final = points so far + projection x share
   of the player's game remaining. Uncertainty shrinks the same way, and win
   probability is the normal CDF of the score-difference distribution.

Usage: python3 winprob.py <league_id> [--week N] [--out winprob.json]
"""

import argparse
import bisect
import datetime as dt
import json
import math
import urllib.request

from sleeper import SleeperClient

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={week}"
ESPN_PLAYS = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{id}/competitions/{id}/plays?limit=500&page={page}"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={id}"
ESPN_TO_SLEEPER_TEAM = {"WSH": "WAS"}
GAME_SECONDS = 3600


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "montana60-winprob"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def player_sd(proj, position):
    """Rough standard deviation of a player's weekly fantasy score."""
    if proj <= 0:
        return 0.0
    if position in ("K", "DEF"):
        return 4.5
    return 0.5 * proj + 3.0


def score_stats(stats, scoring):
    return sum(v * scoring.get(k, 0) for k, v in stats.items() if isinstance(v, (int, float)))


def projections(season, week, scoring):
    rows = _fetch(
        f"https://api.sleeper.app/projections/nfl/{season}/{week}?season_type=regular"
        + "".join(f"&position[]={p}" for p in ["QB", "RB", "WR", "TE", "K", "DEF"])
    )
    return {r["player_id"]: max(score_stats(r.get("stats") or {}, scoring), 0.0) for r in rows}


def espn_games(season, week):
    games = []
    for e in _fetch(ESPN_SCOREBOARD.format(season=season, week=week))["events"]:
        comp = e["competitions"][0]
        teams = [ESPN_TO_SLEEPER_TEAM.get(t["team"]["abbreviation"], t["team"]["abbreviation"]) for t in comp["competitors"]]
        games.append({
            "id": e["id"],
            "name": e["shortName"],
            "kickoff": _ts(e["date"]),
            "state": e["status"]["type"]["state"],  # pre / in / post
            "teams": teams,
        })
    return games


def _norm(name):
    name = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ")
    return " ".join(w for w in name.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def espn_roster_ids(game):
    """(sleeper team, normalized name) -> ESPN athlete id, from the game's box score."""
    ids = {}
    for team in _fetch(ESPN_SUMMARY.format(id=game["id"])).get("boxscore", {}).get("players", []):
        abbr = team["team"]["abbreviation"]
        abbr = ESPN_TO_SLEEPER_TEAM.get(abbr, abbr)
        for cat in team.get("statistics", []):
            for a in cat.get("athletes", []):
                ids[(abbr, _norm(a["athlete"]["displayName"]))] = str(a["athlete"]["id"])
    return ids


def _play_points(play):
    """Approximate per-play fantasy points by ESPN athlete id."""
    kind = play["type"]["text"]
    yds = play.get("statYardage") or 0
    pts = {}

    def add(aid, v):
        pts[aid] = pts.get(aid, 0) + v

    for part in play.get("participants", []):
        aid = part["athlete"]["$ref"].split("/athletes/")[1].split("?")[0]
        role = part["type"]
        if kind in ("Pass Reception", "Passing Touchdown"):
            if role == "passer":
                add(aid, yds * 0.04 + (4 if kind == "Passing Touchdown" else 0))
            elif role == "receiver":
                add(aid, 0.5 + yds * 0.1 + (6 if kind == "Passing Touchdown" else 0))
        elif kind == "Pass Interception Return" and role == "passer":
            add(aid, -2)
        elif kind in ("Rush", "Rushing Touchdown") and role == "rusher":
            add(aid, yds * 0.1 + (6 if kind == "Rushing Touchdown" else 0))
        elif kind == "Field Goal Good" and role == "kicker":
            add(aid, 3)
        elif role == "patScorer":
            add(aid, 1)
    return pts


def game_timeline(game):
    """List of (wallclock, fraction_of_game_elapsed, {espn_id: cumulative approx pts})."""
    items, page = [], 1
    while True:
        d = _fetch(ESPN_PLAYS.format(id=game["id"], page=page))
        items += d["items"]
        if page >= d.get("pageCount", 1):
            break
        page += 1
    items.sort(key=lambda p: int(p["sequenceNumber"]))
    timeline, cum, last_ts = [], {}, game["kickoff"]
    for p in items:
        ts = _ts(p["wallclock"]) if p.get("wallclock") else last_ts
        ts = max(ts, last_ts)
        last_ts = ts
        period = p["period"]["number"]
        elapsed = min(((period - 1) * 900 + (900 - p["clock"]["value"])) / GAME_SECONDS, 1.0)
        if p["type"]["text"] == "End of Game":
            elapsed = 1.0
        for aid, v in _play_points(p).items():
            cum[aid] = cum.get(aid, 0) + v
        timeline.append((ts, elapsed, dict(cum)))
    return timeline


class PlayerCurve:
    """Actual points so far and fraction of game remaining, for any wall-clock time."""

    def __init__(self, actual, timeline, espn_id, done):
        self.actual = actual
        self.timeline = timeline or []
        self.times = [t[0] for t in self.timeline]
        self.espn_id = espn_id
        self.done = done
        final = self.timeline[-1][2].get(espn_id, 0) if self.timeline and espn_id else 0
        # Use the play-by-play shape only if it agrees in sign with the real score
        self.recon_final = final if final > 0 and actual > 0 else None

    def at(self, t):
        if not self.timeline or t < self.times[0]:
            return 0.0, 1.0
        i = bisect.bisect_right(self.times, t) - 1
        _, elapsed, cum = self.timeline[i]
        remaining = 0.0 if (self.done and i == len(self.timeline) - 1) else 1.0 - elapsed
        last_elapsed = 1.0 if self.done else self.timeline[-1][1]
        if self.recon_final is not None:
            share = cum.get(self.espn_id, 0) / self.recon_final
        else:
            share = elapsed / last_elapsed if last_elapsed else 0.0
        return self.actual * max(min(share, 1.5), -0.5), remaining


def win_probability(league_id, week=None):
    client = SleeperClient()
    state = client.nfl_state()
    season = state["season"]
    week = week or state["display_week"]
    league = client.league(league_id)
    scoring = league["scoring_settings"]
    players = client.players()
    proj = projections(season, week, scoring)
    teams = {r["roster_id"]: r["team"] for r in client.standings(league_id)}
    matchups = client.matchups(league_id, week)

    games = espn_games(season, week)
    by_team = {team: g for g in games for team in g["teams"]}
    timelines = {g["id"]: game_timeline(g) for g in games if g["state"] != "pre"}
    espn_ids = {}
    for g in games:
        if g["state"] != "pre":
            espn_ids.update(espn_roster_ids(g))

    sides = {}
    for m in matchups:
        curves = []
        for pid, pts in zip(m["starters"], m["starters_points"]):
            if pid == "0":
                continue
            info = players.get(pid, {})
            pos = info.get("position") or ("DEF" if pid.isalpha() else None)
            team = pid if pos == "DEF" else info.get("team")
            game = by_team.get(team)
            tl = timelines.get(game["id"]) if game else None
            espn_id = None
            if pos != "DEF":
                espn_id = espn_ids.get((team, _norm(info.get("full_name") or ""))) or (str(info["espn_id"]) if info.get("espn_id") else None)
            curve = PlayerCurve(pts or 0.0, tl, espn_id, done=bool(game and game["state"] == "post"))
            # Player on bye / no game: their score is final already
            if not game:
                curve.timeline = [(0, 1.0, {})]
                curve.times = [0]
                curve.done = True
            p = proj.get(pid, 0.0)
            curves.append({"pid": pid, "curve": curve, "proj": p, "sd": player_sd(p, pos)})
        sides.setdefault(m["matchup_id"], []).append({"roster_id": m["roster_id"], "team": teams[m["roster_id"]], "points": m["points"], "players": curves})

    # Sample every play across the week, plus a pregame point
    times = sorted({t for tl in timelines.values() for t, _, _ in tl})
    start = min(g["kickoff"] for g in games) - 60
    times = [start] + times

    def team_dist(side, t):
        mean = var = so_far = 0.0
        for pl in side["players"]:
            pts, remaining = pl["curve"].at(t)
            so_far += pts
            mean += pts + pl["proj"] * remaining
            var += (pl["sd"] ** 2) * remaining
        return so_far, mean, var

    result = {
        "league": league["name"], "season": season, "week": week,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "games": [{"name": g["name"], "kickoff": g["kickoff"], "state": g["state"]} for g in sorted(games, key=lambda g: g["kickoff"])],
        "matchups": [],
    }
    for mid, (a, b) in sorted((k, v) for k, v in sides.items() if k is not None and len(v) == 2):
        series = []
        for t in times:
            sa, ma, va = team_dist(a, t)
            sb, mb, vb = team_dist(b, t)
            sd = math.sqrt(va + vb)
            if sd > 1e-9:
                wp = 0.5 * (1 + math.erf((ma - mb) / (sd * math.sqrt(2))))
            else:
                wp = 1.0 if ma > mb else 0.0 if ma < mb else 0.5
            series.append([round(t), round(wp, 4), round(sa, 2), round(sb, 2), round(ma, 2), round(mb, 2)])
        # Drop consecutive duplicates to keep output small
        slim = [series[0]] + [s for prev, s in zip(series, series[1:]) if s[1:] != prev[1:]]
        result["matchups"].append({
            "matchup_id": mid,
            "home": {"team": a["team"], "points": a["points"]},
            "away": {"team": b["team"], "points": b["points"]},
            "series": slim,  # [unix_ts, P(home wins), home pts, away pts, home proj, away proj]
        })
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("league_id")
    ap.add_argument("--week", type=int)
    ap.add_argument("--out", default="winprob.json")
    args = ap.parse_args()
    res = win_probability(args.league_id, args.week)
    with open(args.out, "w") as f:
        json.dump(res, f)
    for m in res["matchups"]:
        first, last = m["series"][0], m["series"][-1]
        print(f"{m['home']['team']:>28} {last[2]:6.2f} - {last[3]:6.2f} {m['away']['team']:<28} "
              f"WP {first[1]:.0%} -> {last[1]:.0%}  (proj {last[4]:.1f}-{last[5]:.1f})")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
