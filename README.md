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
