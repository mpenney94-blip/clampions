# Montana60

## Sleeper fantasy football API

`sleeper.py` is a small Python client for the [Sleeper API](https://docs.sleeper.com/), using only the standard library (Python 3.8+).
Sleeper's API is public and read-only, so you don't need an API key. Just use your username or a league ID.

```sh
python3 sleeper.py state                       # current season / week
python3 sleeper.py leagues <username>          # your leagues + league IDs
python3 sleeper.py standings <league_id>
python3 sleeper.py matchups <league_id> [--week N]
python3 sleeper.py trending [add|drop] [--limit N]
python3 sleeper.py --json standings <league_id>   # raw JSON
```

From Python:

```python
from sleeper import SleeperClient

c = SleeperClient()
user = c.user("your_username")
leagues = c.user_leagues(user["user_id"], "2026")
rosters = c.rosters(leagues[0]["league_id"])
players = c.players()  # full player DB, cached in .cache/ for 24h
```

Sleeper can't do write operations through the API (no lineup changes, trades or waivers). Keep usage under about 1000 calls per minute.

## Win probability

`winprob.py` estimates how each matchup's win probability changed over a week. Sleeper doesn't publish its in-app odds, so the script rebuilds them from ESPN play-by-play data and Sleeper projections scored with your league's settings.

```sh
python3 winprob.py <league_id> [--week N] [--out winprob.json]
```

## League dashboard

`dashboard/` builds a static website for a Sleeper league in two parts. **This week**: recap, awards, power rankings, playoff odds (simulated), next week's preview, play-by-play win probability, results vs. projections, close games and scoring trends. **Season so far**: all-play standings, schedule swap, position strength, injury and bye damage, bench points, waivers and waiver wars, trades, who carried each team, drafted vs. picked up, points by draft round, boom or bust, team by week and the draft report card. There's also a page for every past week.

```sh
python3 -m dashboard.build <league_id> --out _site          # full build (about 2 minutes)
python3 -m dashboard.build <league_id> --out _site --no-winprob   # quick build without win probability
python3 -m dashboard.build <league_id> --out _site --only 2026      # just one season
```

`.github/workflows/dashboard.yml` rebuilds and publishes it to GitHub Pages every Tuesday and Thursday, on pushes that change the dashboard code, and on demand from the Actions tab ("Run workflow"). Change `LEAGUE_ID` in that file to point it at a different league.

`<league_id>` is the current season's league. Earlier seasons are found through Sleeper's `previous_league_id` chain and
get their own tab (`/2025/`, `/2024/`, ...), next to an all-time tab (`/alltime/`). Finished seasons never change, so the
workflow keeps their builds in the Actions cache and rebuilds them only when the dashboard code changes.

### Written columns

The "week in review" and next-week "trash talk" sections are written from a fact sheet of each week's stats
(`dashboard/commentary.py`). If the repository has an `ANTHROPIC_API_KEY` Actions secret, Claude writes them;
otherwise a built-in writer fills in from canned lines.
