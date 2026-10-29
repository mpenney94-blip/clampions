"""Minimal client for the Sleeper fantasy football API.

Sleeper's API is public and read-only: no API key or auth is needed.
Docs: https://docs.sleeper.com/  (keep it under ~1000 calls/minute)
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.sleeper.app/v1"
PLAYERS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "players_nfl.json")
PLAYERS_CACHE_MAX_AGE = 24 * 60 * 60  # Sleeper asks that /players/nfl be fetched at most once a day


class SleeperError(Exception):
    pass


class SleeperClient:
    def __init__(self, base_url=BASE_URL, timeout=30):
        self.base_url = base_url
        self.timeout = timeout

    def _get(self, path, **params):
        url = f"{self.base_url}/{path.lstrip('/')}"
        params = {k: v for k, v in params.items() if v is not None}
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "montana60-sleeper-client"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise SleeperError(f"GET {url} failed: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise SleeperError(f"GET {url} failed: {e.reason}") from e
        # Sleeper returns a literal `null` for unknown users/leagues
        return json.loads(body) if body else None

    # --- State ---
    def nfl_state(self):
        return self._get("state/nfl")

    # --- Users ---
    def user(self, username_or_id):
        user = self._get(f"user/{username_or_id}")
        if user is None:
            raise SleeperError(f"No Sleeper user found for {username_or_id!r}")
        return user

    def user_leagues(self, user_id, season, sport="nfl"):
        return self._get(f"user/{user_id}/leagues/{sport}/{season}")

    def user_drafts(self, user_id, season, sport="nfl"):
        return self._get(f"user/{user_id}/drafts/{sport}/{season}")

    # --- Leagues ---
    def league(self, league_id):
        return self._get(f"league/{league_id}")

    def rosters(self, league_id):
        return self._get(f"league/{league_id}/rosters")

    def league_users(self, league_id):
        return self._get(f"league/{league_id}/users")

    def matchups(self, league_id, week):
        return self._get(f"league/{league_id}/matchups/{week}")

    def winners_bracket(self, league_id):
        return self._get(f"league/{league_id}/winners_bracket")

    def losers_bracket(self, league_id):
        return self._get(f"league/{league_id}/losers_bracket")

    def transactions(self, league_id, week):
        return self._get(f"league/{league_id}/transactions/{week}")

    def traded_picks(self, league_id):
        return self._get(f"league/{league_id}/traded_picks")

    def league_drafts(self, league_id):
        return self._get(f"league/{league_id}/drafts")

    # --- Drafts ---
    def draft(self, draft_id):
        return self._get(f"draft/{draft_id}")

    def draft_picks(self, draft_id):
        return self._get(f"draft/{draft_id}/picks")

    def draft_traded_picks(self, draft_id):
        return self._get(f"draft/{draft_id}/traded_picks")

    # --- Players ---
    def players(self, sport="nfl", cache_path=PLAYERS_CACHE, max_age=PLAYERS_CACHE_MAX_AGE):
        """All players keyed by player_id (~5MB). Cached on disk for a day."""
        if cache_path and os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < max_age:
            with open(cache_path) as f:
                return json.load(f)
        data = self._get(f"players/{sport}")
        if cache_path:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            tmp = f"{cache_path}.{os.getpid()}.tmp"  # write then rename, so a parallel reader never sees half a file
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, cache_path)
        return data

    def trending_players(self, kind="add", lookback_hours=24, limit=25, sport="nfl"):
        """kind is 'add' or 'drop'."""
        return self._get(f"players/{sport}/trending/{kind}", lookback_hours=lookback_hours, limit=limit)

    # --- Helpers ---
    def standings(self, league_id):
        """Rosters joined with owner display names, sorted by wins then points for."""
        owners = {u["user_id"]: u for u in self.league_users(league_id)}
        rows = []
        for r in self.rosters(league_id):
            s = r.get("settings", {})
            owner = owners.get(r.get("owner_id"), {})
            team = (owner.get("metadata") or {}).get("team_name") or owner.get("display_name") or "(unowned)"
            rows.append({
                "roster_id": r["roster_id"],
                "team": team,
                "owner": owner.get("display_name"),
                "wins": s.get("wins", 0),
                "losses": s.get("losses", 0),
                "ties": s.get("ties", 0),
                "fpts": s.get("fpts", 0) + s.get("fpts_decimal", 0) / 100,
                "fpts_against": s.get("fpts_against", 0) + s.get("fpts_against_decimal", 0) / 100,
            })
        rows.sort(key=lambda x: (x["wins"], x["fpts"]), reverse=True)
        return rows


def _print_json(data):
    json.dump(data, sys.stdout, indent=2)
    print()


def main(argv=None):
    p = argparse.ArgumentParser(description="Query the Sleeper fantasy football API")
    p.add_argument("--json", action="store_true", help="print raw JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("state", help="current NFL season/week")

    sp = sub.add_parser("leagues", help="list a user's leagues")
    sp.add_argument("username")
    sp.add_argument("--season", help="defaults to the current season")

    sp = sub.add_parser("standings", help="league standings")
    sp.add_argument("league_id")

    sp = sub.add_parser("matchups", help="matchups for a week")
    sp.add_argument("league_id")
    sp.add_argument("--week", type=int, help="defaults to the current week")

    sp = sub.add_parser("trending", help="trending adds/drops")
    sp.add_argument("kind", choices=["add", "drop"], nargs="?", default="add")
    sp.add_argument("--limit", type=int, default=10)

    args = p.parse_args(argv)
    client = SleeperClient()

    try:
        if args.cmd == "state":
            data = client.nfl_state()
            if args.json:
                return _print_json(data)
            print(f"Season {data['season']} ({data['season_type']}), week {data['week']}")

        elif args.cmd == "leagues":
            user = client.user(args.username)
            season = args.season or client.nfl_state()["season"]
            leagues = client.user_leagues(user["user_id"], season)
            if args.json:
                return _print_json(leagues)
            print(f"{user['display_name']} ({user['user_id']}) - {len(leagues)} league(s) in {season}")
            for lg in leagues:
                print(f"  {lg['league_id']}  {lg['name']}  [{lg['total_rosters']} teams, {lg['status']}]")

        elif args.cmd == "standings":
            rows = client.standings(args.league_id)
            if args.json:
                return _print_json(rows)
            for i, r in enumerate(rows, 1):
                record = f"{r['wins']}-{r['losses']}" + (f"-{r['ties']}" if r["ties"] else "")
                print(f"{i:>2}. {r['team']:<30} {record:>7}  PF {r['fpts']:>8.2f}  PA {r['fpts_against']:>8.2f}")

        elif args.cmd == "matchups":
            week = args.week or client.nfl_state()["display_week"]
            data = client.matchups(args.league_id, week)
            if args.json:
                return _print_json(data)
            teams = {r["roster_id"]: r["team"] for r in client.standings(args.league_id)}
            pairs = {}
            for m in data:
                pairs.setdefault(m.get("matchup_id"), []).append(m)
            print(f"Week {week}")
            for mid, side in sorted(pairs.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
                line = "  vs  ".join(f"{teams.get(s['roster_id'], s['roster_id'])} {s.get('points') or 0:.2f}" for s in side)
                print(f"  {line}")

        elif args.cmd == "trending":
            trending = client.trending_players(args.kind, limit=args.limit)
            if args.json:
                return _print_json(trending)
            players = client.players()
            for t in trending:
                pl = players.get(t["player_id"], {})
                name = pl.get("full_name") or f"{pl.get('first_name', '')} {pl.get('last_name', '')}".strip() or t["player_id"]
                print(f"  {name:<28} {pl.get('position') or '':<4} {pl.get('team') or 'FA':<4} {t['count']:>7,}")
    except SleeperError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
