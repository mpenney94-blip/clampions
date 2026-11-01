"""Written trash talk for the dashboard: a recap of the week just played and a look ahead at the next one.

The stats are boiled down to a fact sheet first. If ANTHROPIC_API_KEY is set, Claude writes the column from it;
otherwise (or if the call fails) a built-in writer does, picking from canned lines.
"""

import collections
import statistics
import glob
import hashlib
import html
import json
import os
import random
import re

from dashboard import weekly
from dashboard.stats import _optimal

MODEL = "claude-sonnet-5-5"
CACHE = os.environ.get("COMMENTARY_CACHE", os.path.join(".cache", "commentary"))  # Claude's columns, keyed by their facts


# ---------------------------------------------------------------- fact sheets
def _records(lg, through):
    rec = collections.defaultdict(lambda: [0, 0, 0])
    seq = collections.defaultdict(list)
    for w in lg.weeks:
        if w > through or w not in lg.reg_weeks:
            continue
        sc = lg.scores(w)
        for a, b in weekly._pairs(lg, w):
            for x, y in ((a, b), (b, a)):
                r = 0 if sc[x] > sc[y] else 1 if sc[x] < sc[y] else 2
                rec[x][r] += 1
                seq[x].append("WLT"[r])
    streak = {}
    for r, s in seq.items():
        n = len(s) - len("".join(s).rstrip(s[-1])) if s else 0
        streak[r] = f"{s[-1]}{n}" if s else ""
    return {r: "-".join(map(str, v[:2])) + (f"-{v[2]}" if v[2] else "") for r, v in rec.items()}, streak


def _p(x):
    return round(x * 100)


def week_facts(lg, w, wp=None, odds_now=None, odds_prev=None):
    proj, _ = lg.proj(w)
    sc = lg.scores(w)
    rec, streak = _records(lg, w)
    ms = {m["roster_id"]: m for m in lg.matchups[w]}
    wpm = {}
    for mm in (wp or {}).get("matchups", []):
        series = mm["series"]
        for side, i in ((mm["home"]["team"], 1), (mm["away"]["team"], None)):
            vals = [s[1] if i else 1 - s[1] for s in series]
            wpm[side] = {"pregame": _p(vals[0]), "low": _p(min(vals)), "high": _p(max(vals))}

    def side(r):
        m = ms[r]
        st = [(p, v) for p, v in zip(m["starters"], m["starters_points"]) if p != "0"]
        opt, used = _optimal(lg, m.get("players_points") or {})
        benched = sorted(((p, m["players_points"][p]) for p in used if p not in m["starters"]), key=lambda x: -x[1])
        flops = sorted(st, key=lambda x: x[1] - proj.get(x[0], 0))[:2]
        empty = [lg.name_of(p) for p in m["starters"] if p == "0"] + [lg.name_of(p) for p, _ in st if p not in lg.played[w]]
        return {
            "team": lg.team[r], "score": round(sc[r], 1), "projected": round(sum(proj.get(p, 0) for p, _ in st), 1),
            "record_after": rec.get(r), "streak": streak.get(r),
            "best_possible_lineup": round(opt, 1), "left_on_bench": round(opt - sc[r], 1),
            "should_have_started": [f"{lg.name_of(p)} ({v:.1f})" for p, v in benched[:2]],
            "top_starters": [{"player": lg.name_of(p), "points": v, "projected": round(proj.get(p, 0), 1)} for p, v in sorted(st, key=lambda x: -x[1])[:2]],
            "biggest_flops": [{"player": lg.name_of(p), "points": v, "projected": round(proj.get(p, 0), 1)} for p, v in flops if proj.get(p, 0) - v > 4],
            "started_players_who_did_not_play": empty,
            "win_probability": wpm.get(lg.team[r]),
        }

    games = []
    for a, b in weekly._pairs(lg, w):
        x, y = side(a), side(b)
        win, lose = (x, y) if x["score"] >= y["score"] else (y, x)
        games.append({"winner": win, "loser": lose, "margin": round(win["score"] - lose["score"], 1),
                      "bench_would_have_flipped_it": lose["best_possible_lineup"] > win["score"]})
    games.sort(key=lambda g: g["margin"])
    aw = weekly.awards(lg, w, wp)
    facts = {
        "week": w, "league": lg.name, "median_score": round(sorted(sc.values())[len(sc) // 2], 1),
        "high_score": [lg.team[max(sc, key=sc.get)], round(max(sc.values()), 1)],
        "low_score": [lg.team[min(sc, key=sc.get)], round(min(sc.values()), 1)],
        "games_closest_first": games,
        "awards": {k: [v[0], round(v[1], 2) if isinstance(v[1], float) else v[1], v[2]] for k, v in aw.items()},
    }
    if odds_now and odds_prev:
        prev = {x["team"]: x["playoffs"] for x in odds_prev}
        moves = sorted(((x["team"], _p(prev.get(x["team"], 0)), _p(x["playoffs"])) for x in odds_now), key=lambda t: t[2] - t[1])
        facts["playoff_odds_moves"] = {"biggest_drop": moves[0], "biggest_rise": moves[-1]}
    return facts


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def week_history(lg):
    """Every regular-season game since 2023 by week of the season, keyed by manager:
    {owner: {week: [(season, won 1/0/0.5, points, opponent's points, opponent owner)]}}, plus {week: [all scores]}."""
    if "_week_hist" in lg.__dict__:
        return lg._week_hist
    games = collections.defaultdict(lambda: collections.defaultdict(list))
    scores = collections.defaultdict(list)
    lid = lg.id
    while lid and lid != "0":
        info = lg.client.league(lid)
        own = {r["roster_id"]: r.get("owner_id") or f"roster-{r['roster_id']}" for r in lg.client.rosters(lid)}
        if lid == lg.id:
            weeks = [x for x in lg.reg_weeks if x < lg.next_week]
        else:
            start = (info.get("settings") or {}).get("playoff_week_start") or 15
            weeks = range(1, start)
        for w in weeks:
            ms = lg.matchups[w] if lid == lg.id and w in lg.matchups else lg.client.matchups(lid, w)
            by_mid = collections.defaultdict(list)
            for m in ms or []:
                if m.get("matchup_id"):
                    by_mid[m["matchup_id"]].append(m)
            for pair in by_mid.values():
                if len(pair) != 2:
                    continue
                for me, them in (pair, pair[::-1]):
                    a, b = me.get("points") or 0.0, them.get("points") or 0.0
                    if not a and not b:
                        continue  # not played yet
                    games[own[me["roster_id"]]][w].append((info["season"], 1 if a > b else 0 if a < b else .5, a, b, own[them["roster_id"]]))
                    scores[w].append(a)
        lid = info.get("previous_league_id")
    lg._week_hist = (games, scores)
    return lg._week_hist


def week_number_facts(lg, w, rid):
    """How this team's manager has done in week w of past seasons, with the notable bits spelled out for the writer."""
    games, _ = week_history(lg)
    # only what was known before week w: this season's games from week w on haven't happened yet as far as the preview knows
    seen = {o_: {x: [g for g in gs if g[0] != lg.season or x < w] for x, gs in by_w.items()} for o_, by_w in games.items()}
    scores = collections.defaultdict(list)
    for by_w in seen.values():
        for x, gs in by_w.items():
            scores[x] += [g[2] for g in gs]
    o = lg.owner[rid]
    mine = {x: gs for x, gs in seen.get(o, {}).items() if gs}
    here = mine.get(w) or []
    if not here:
        return None
    lavg = {x: statistics.mean(v) for x, v in scores.items() if v}
    diff = {x: statistics.mean(p for _, _, p, _, _ in g) - lavg[x] for x, g in mine.items() if g}
    order = sorted(diff, key=lambda x: -diff[x])
    rank = order.index(w) + 1
    wins = sum(r for _, r, _, _, _ in here)
    losses = sum(1 for _, r, _, _, _ in here if r == 0)
    ties = sum(1 for _, r, _, _, _ in here if r == .5)
    avg = statistics.mean(p for _, _, p, _, _ in here)
    rate = {x: sum(r for _, r, _, _, _ in g) / len(g) for x, g in mine.items() if g}
    notable = []
    if len(here) >= 2 and losses == len(here):
        notable.append(f"has never won a week {w} game ({len(here)} tries)")
    if len(here) >= 2 and losses == 0 and not ties:
        notable.append(f"has never lost a week {w} game ({len(here)}-0)")
    if rank == 1:
        notable.append(f"week {w} is his best-scoring week of the season relative to the league ({diff[w]:+.1f} vs. the league average)")
    elif rank == len(order):
        notable.append(f"week {w} is his worst-scoring week of the season relative to the league ({diff[w]:+.1f} vs. the league average)")
    if len(here) >= 2 and 0 < losses < len(here) and rate[w] == min(rate.values()):
        notable.append(f"week {w} is tied for his worst record of any week of the season")
    return {"record_in_this_week_of_past_seasons": f"{int(wins - ties / 2)}-{losses}" + (f"-{ties}" if ties else ""),
            "avg_points_in_this_week": round(avg, 1), "vs_league_avg_in_this_week": round(diff[w], 1),
            "this_week_rank_among_his_weeks": f"{_ordinal(rank)} of {len(order)} weeks, best first (by points vs. the league average)",
            "past_games_this_week": [f"{season}: {'W' if r == 1 else 'L' if r == 0 else 'T'} {a:.1f}-{b:.1f}"
                                     for season, r, a, b, _ in sorted(here, reverse=True)],
            "notable": notable}


def preview_facts(lg, w, odds=None, min_ppg=8.0):
    """Facts for week w's look-ahead, as things stood after week w - 1 (rosters that week; injury news only for the real next week)."""
    games = weekly.preview(lg, w)
    if not games:
        return None
    ppg = weekly._ppg(lg)
    rec, streak = _records(lg, w - 1)
    upcoming = w >= lg.next_week
    roster = (lg.roster_now if upcoming else {m["roster_id"]: set(m.get("players") or []) for m in lg.matchups_for(w)})
    rid = {n: r for r, n in lg.team.items()}
    od = {x["team"]: x for x in odds or []}
    standing = {x["team"]: i for i, x in enumerate(sorted(odds or [], key=lambda x: (-x["wins"], -x["pf"])), 1)}

    def trouble(team):
        r = rid[team]
        byes, hurt = [], []
        for p in roster.get(r, ()):
            if ppg.get(p, 0) < min_ppg:
                continue
            if weekly._nfl_team(lg, p, None if upcoming else w) in lg.bye.get(w, set()):
                byes.append(f"{lg.name_of(p)} ({ppg[p]:.1f}/gm)")
            st = (lg.players.get(p) or {}).get("injury_status") if upcoming else None  # today's injury report means nothing for old weeks
            if st in ("Out", "IR", "Doubtful", "Questionable", "PUP", "Sus"):
                hurt.append(f"{lg.name_of(p)} ({st}, {ppg[p]:.1f}/gm)")
        return byes, hurt

    out = []
    for g in games:
        sides = []
        for s in (g["fav"], g["dog"]):
            byes, hurt = trouble(s["team"])
            o = od.get(s["team"]) or {}
            sides.append({"team": s["team"], "record": rec.get(rid[s["team"]]), "streak": streak.get(rid[s["team"]]),
                          "standing": standing.get(s["team"]), "projected": round(s["proj"], 1),
                          "key_player": f"{s['key'][0]} (proj {s['key'][1]:.1f})" if s["key"] else None,
                          "on_bye": byes, "injured": hurt, "empty_lineup_slots": s["empty"],
                          "playoff_odds": _p(o.get("playoffs", 0)), "first_round_bye_odds": _p(o.get("bye", 0)),
                          "last_place_odds": _p(o.get("last", 0)),
                          "division": lg.division.get(rid[s["team"]]),
                          "history_in_week_number": week_number_facts(lg, w, rid[s["team"]])})
        same_div = sides[0]["division"] is not None and sides[0]["division"] == sides[1]["division"]
        out.append({"favorite": sides[0], "underdog": sides[1], "favorite_win_chance": _p(g["p"]),
                    "spread": round(g["spread"], 1), "division_game": same_div})
    left = [x for x in lg.reg_weeks if x >= w]
    return {"week": w, "league": lg.name, "regular_season_weeks_left_including_this_one": len(left),
            "playoff_teams": lg.playoff_teams, "games_closest_first": out}


# ---------------------------------------------------------------- Claude writer
SYSTEM = """You are the resident trash-talk columnist for a fantasy football league's weekly dashboard. The managers are friends who
roast each other all season, and they asked for this column specifically because they want to be roasted. Be genuinely funny,
savage and specific: mock bad lineup decisions, players who flopped, teams that got lucky, managers who left points on the bench,
blown leads, and whoever is circling the drain. Give credit where it's due too, but backhanded compliments are encouraged.
Don't hold back. Profanity is fine in moderation. Keep it about fantasy football and the decisions people made - no jokes about
real players' personal lives, health or off-field legal troubles, and nothing hateful.

Use only the facts and league notes you're given; never invent stats, scores, players or events. Team names are the managers' identities - roast the
team/manager by team name. Write 5 to 7 short paragraphs, each 1-3 sentences, punchy, with no headings, no bullet points, no emoji,
and no preamble or sign-off. Wrap each team name in **double asterisks** the first time it appears in a paragraph."""
NOTES_PATH = os.path.join(os.path.dirname(__file__), "league_notes.md")
if os.path.exists(NOTES_PATH):  # league lore and real-life news the managers want worked in now and then
    with open(NOTES_PATH) as _f:
        SYSTEM += "\n\nLeague notes (traditions, style and news to draw on when they fit):\n" + _f.read()


def _claude(kind, facts):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        ask = {"recap": "Write this week's recap column. Hit the best and worst performances, lineup blunders, flops, lucky and unlucky "
                        "results and anything that collapsed late.",
               "preview": "Write the look-ahead column for next week. Hype the big games, flag teams wrecked by byes or injuries, and spell out "
                          "the playoff stakes (who is desperate, who is coasting, who is cooked). Each team's history_in_week_number is how its "
                          "manager has done in this same week of past seasons; work in a couple of its notable items (a week he has never "
                          "won, his best or worst scoring week of the year) where they add to the trash talk.",
               "rivalry": "Write an all-time rivalries column for the league's history page. Roast the managers who keep losing to the same "
                          "person, rub in the most one-sided head-to-head records, hype the dead-even rivalries, and work in playoff "
                          "meetings and titles where they make it sting. Team names in the facts are each manager's current team name.",
               }[kind]
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=16000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "medium"}, system=SYSTEM,
            messages=[{"role": "user", "content": f"{ask}\n\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False)}"}])
        if resp.stop_reason not in ("end_turn", "max_tokens"):
            print(f"commentary: Claude stopped with {resp.stop_reason}")
            return None
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()] or None
    except Exception as e:  # never let the column take the site down
        print(f"commentary: Claude call failed ({e}); using the built-in writer")
        return None


# ---------------------------------------------------------------- built-in writer
def _b(team):
    return f"**{team}**"


def _recap_lines(f, rnd):
    g = f["games_closest_first"]
    pick = rnd.choice
    out = []
    blow = g[-1]
    out.append(pick([
        f"{_b(blow['winner']['team'])} dropped {blow['winner']['score']} on {_b(blow['loser']['team'])} and won by {blow['margin']}. "
        f"That wasn't a matchup, it was a public service announcement.",
        f"{_b(blow['loser']['team'])} got beaten by {blow['margin']} by {_b(blow['winner']['team'])}. Somebody check on them; "
        f"actually, don't, they need to sit with this.",
    ]))
    lo, hi = f["low_score"], f["high_score"]
    out.append(f"{_b(hi[0])} led the league with {hi[1]}, while {_b(lo[0])} put up {lo[1]}, which is technically a score in the "
               f"same way a participation trophy is technically a trophy.")
    close = g[0]
    out.append(f"Closest game: {_b(close['winner']['team'])} edged {_b(close['loser']['team'])} by {close['margin']}"
               + (f", and {_b(close['loser']['team'])} had a lineup on its bench that would have won. Read that twice." if close["bench_would_have_flipped_it"] else
                  ". Heartbreak by a rounding error."))
    flipped = [x for x in g[1:] if x["bench_would_have_flipped_it"]]
    for x in flipped[:1]:
        l = x["loser"]
        out.append(f"{_b(l['team'])} lost to {_b(x['winner']['team'])} while {' and '.join(l['should_have_started']) or 'a pile of points'} "
                   f"sat on the bench. The best lineup would have scored {l['best_possible_lineup']}. The actual one scored {l['score']}. Incredible stuff.")
    aw = f["awards"]
    if "worst_call" in aw and not flipped:
        t, gap, why = aw["worst_call"]
        out.append(f"Lineup-setter of the week goes, sadly, to {_b(t)}, who {why}. Autodraft has better instincts.")
    flops = [(x[s]["team"], fl) for x in g for s in ("winner", "loser") for fl in x[s]["biggest_flops"][:1]]
    if flops:
        t, fl = max(flops, key=lambda x: x[1]["projected"] - x[1]["points"])
        out.append(f"Flop of the week: {fl['player']} was projected for {fl['projected']} and gave {_b(t)} {fl['points']}. "
                   f"Projections are a suggestion, apparently.")
    if "player" in aw:
        p, v, why = aw["player"]
        out.append(f"{p} went off for {v} for {_b(why.removeprefix('for '))}, single-handedly carrying a roster that did not deserve it.")
    lucky = min(g, key=lambda x: x["winner"]["score"])
    if lucky["winner"]["score"] < f["median_score"]:
        out.append(f"{_b(lucky['winner']['team'])} scored a below-median {lucky['winner']['score']} and still won, because "
                   f"{_b(lucky['loser']['team'])} somehow managed only {lucky['loser']['score']}. Buy a lottery ticket, then hide it from your league mates.")
    mv = f.get("playoff_odds_moves")
    if mv and mv["biggest_drop"][1] - mv["biggest_drop"][2] >= 8:
        t, a, b = mv["biggest_drop"]
        out.append(f"{_b(t)}'s playoff odds fell from {a}% to {b}%. Start practicing your ‘it's a rebuilding year’ speech.")
    return out


def _preview_lines(f, rnd):
    g = f["games_closest_first"]
    out = []
    top = g[0]
    a, b = top["favorite"], top["underdog"]
    out.append(f"Game of the week: {_b(a['team'])} ({a['record']}) vs. {_b(b['team'])} ({b['record']}), a {top['favorite_win_chance']}–"
               f"{100 - top['favorite_win_chance']} coin flip" + (" between division rivals" if top["division_game"] else "")
               + ". Somebody's group chat is about to get very quiet.")
    big = g[-1]
    out.append(f"{_b(big['favorite']['team'])} is a {big['favorite_win_chance']}% favorite over {_b(big['underdog']['team'])}, "
               f"projected to win by {big['spread']}. {_b(big['underdog']['team'])}, the good news is nobody expects anything.")
    sides = [s for x in g for s in (x["favorite"], x["underdog"])]
    worst = max(sides, key=lambda s: len(s["on_bye"]) + len(s["injured"]))
    if worst["on_bye"] or worst["injured"]:
        bits = []
        if worst["on_bye"]:
            bits.append(f"{', '.join(x.split(' (')[0] for x in worst['on_bye'][:3])} on bye")
        if worst["injured"]:
            bits.append(f"{', '.join(x.split(' (')[0] for x in worst['injured'][:3])} on the injury report")
        out.append(f"{_b(worst['team'])} has {' and '.join(bits)}. Hope you like digging through the waiver wire at midnight.")
    empty = [s for s in sides if s["empty_lineup_slots"]]
    if empty:
        s = empty[0]
        who = s["empty_lineup_slots"][:2]
        out.append(f"{_b(s['team'])} has {' and '.join(who)} in the starting lineup, projected for zero. Bold strategy.")
    hist = [(s, n) for s in sides for n in ((s.get("history_in_week_number") or {}).get("notable") or [])]
    if hist:
        s, n = hist[0]
        out.append(f"History lesson: {_b(s['team'])} {n}. Calendars don't lie.")
    bubble = sorted((s for s in sides if 25 <= s["playoff_odds"] <= 75), key=lambda s: abs(s["playoff_odds"] - 50))
    if bubble:
        s = bubble[0]
        out.append(f"{_b(s['team'])} sits at {s['playoff_odds']}% to make the playoffs, which in fantasy terms means ‘one bad Sunday from irrelevance’.")
    cooked = [s for s in sides if s["playoff_odds"] <= 10]
    if cooked:
        s = min(cooked, key=lambda s: s["playoff_odds"])
        out.append(f"And {_b(s['team'])}: {s['playoff_odds']}% playoff odds. Time to start pricing out duck costumes, because the toilet bowl "
                   f"is calling and the paintball guns are already loaded.")
    return out


def _rivalry_lines(f, rnd):
    out = []
    for r in f["rivalries"][:6]:
        a, b, rec = r["leader"], r["trailer"], r["record"]
        if r["leader_wins"] == r["trailer_wins"]:
            out.append(f"{_b(a)} and {_b(b)} are dead even at {rec} after {r['games']} meetings. Somebody please break the tie before Thanksgiving.")
        elif r["trailer_wins"] == 0:
            out.append(f"{_b(a)} is {rec} all-time against {_b(b)}. That's not a rivalry, that's a subscription.")
        else:
            out.append(f"{_b(a)} leads {_b(b)} {rec} all-time" + (f", including {r['playoff_record']} in the playoffs" if r.get("playoff_record") else "")
                       + ". The scoreboard has spoken.")
    return out


def write(kind, facts, use_claude=True, final=False):
    """Paragraphs of HTML for 'recap', 'preview' or 'rivalry', plus who wrote them. use_claude=False sticks to the built-in writer.

    Columns cost money to write, so once one exists it is reused unless there's a reason to redo it: a recap, or a
    preview whose week has been played (final=True), never changes again; the live preview and the rivalry column are
    rewritten only when COMMENTARY_REFRESH=1 (the scheduled Tuesday/Thursday runs and manual runs), not on code pushes."""
    if not facts:
        return None, None
    key = hashlib.sha256(json.dumps([MODEL, SYSTEM, kind, facts], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    path = os.path.join(CACHE, f"{kind}-{facts['week']}-{key}.json")
    paras = None
    keep = kind == "recap" or final or os.environ.get("COMMENTARY_REFRESH") != "1"
    if use_claude and keep and not os.path.exists(path):
        # reuse the latest column written for this week, even if the stats behind it have shifted since.
        # Only Claude-written seasons are cached, so no other season matches.
        done = sorted(glob.glob(os.path.join(CACHE, f"{kind}-{facts['week']}-*.json")), key=os.path.getmtime)
        if done:
            path = done[-1]
    if os.path.exists(path):
        with open(path) as f:
            paras = json.load(f)
    else:
        paras = _claude(kind, facts) if use_claude else None
        if paras:
            os.makedirs(CACHE, exist_ok=True)
            with open(path, "w") as f:
                json.dump(paras, f)
    by = "Claude"
    if not paras:
        rnd = random.Random(f"{kind}-{facts['week']}")
        paras, by = {"recap": _recap_lines, "preview": _preview_lines, "rivalry": _rivalry_lines}[kind](facts, rnd), "the robot"
    out = []
    for p in paras:
        p = html.escape(p)
        out.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p))
    return out, by
