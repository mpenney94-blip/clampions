"""Nemeses: the NFL players who have scored the most fantasy points against each team (started by its opponents), for one
season and all-time. The same file is used by the Clampions and BBLOT dashboards."""
import collections

import winprob
from dashboard.render import esc

KEEP = 25  # players per manager kept in each season's summary, enough for an all-time top 10


def _playoff_games(lg):
    """[(week, roster, roster)] for winners-bracket games played so far (not the 5th-place game, which is left out of
    head-to-head and playoff records)."""
    if not lg.playoff_start:
        return []
    if "_nem_po" in lg.__dict__:
        return lg._nem_po
    last = lg.info["settings"].get("last_scored_leg") or 0
    out = []
    for m in winprob._fetch(f"https://api.sleeper.app/v1/league/{lg.id}/winners_bracket") or []:
        a, b, w = m.get("t1"), m.get("t2"), lg.playoff_start + m["r"] - 1
        if a and b and m.get("p") != 5 and w <= last:
            out.append((w, a, b))
    lg._nem_po = out
    return out


def season(lg, through=None):
    """{roster: {pid: [points, games, Counter(opposing roster -> games), [(week, opposing roster, points) in playoffs]]}}:
    points opponents' starters scored against each team, regular season plus winners-bracket playoff games."""
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, collections.Counter(), []]))
    games = [(w, r, o, False) for w in lg.weeks for r, o in lg.opponent(w).items()]
    for w, a, b in _playoff_games(lg):
        games += [(w, a, b, True), (w, b, a, True)]
    if through is not None:  # as things stood after week `through`
        games = [g for g in games if g[0] <= through]
    ms_by_week = {}
    for w, r, o, po in games:
        if w not in ms_by_week:
            ms_by_week[w] = {m["roster_id"]: m for m in (lg.matchups[w] if w in lg.matchups else lg.client.matchups(lg.id, w))}
        m = ms_by_week[w].get(o)
        if not m:
            continue
        for pid, v in zip(m["starters"], m.get("starters_points") or []):
            if pid == "0":
                continue
            x = out[r][pid]
            x[0] += v or 0
            x[1] += 1
            x[2][o] += 1
            if po:
                x[3].append((w, o, v or 0))
    return out


def week_facts(lg, w, limit=6):
    """For the week-w recap: players who started against a team this week and rank among that team's three worst
    all-time nemeses (earlier seasons' summaries plus this season through week w), with what they did this week."""
    data = season(lg, through=w)
    past = collections.defaultdict(lambda: collections.defaultdict(float))  # owner -> pid -> points before this season
    past_g = collections.defaultdict(collections.Counter)
    for x in getattr(lg, "past_sums", None) or []:
        for o, ps in (x.get("nemeses") or {}).items():
            for p, row in ps.items():
                past[o][p] += row[0]
                past_g[o][p] += row[1]
    ms = {m["roster_id"]: m for m in (lg.matchups[w] if w in lg.matchups else lg.client.matchups(lg.id, w))}
    opp = lg.opponent(w) if w in lg.matchups else {}
    for wk, a, b in _playoff_games(lg):
        if wk == w:
            opp.update({a: b, b: a})
    out = []
    for r, o in opp.items():
        own = lg.owner[r]
        totals = {p: past[own][p] + v[0] for p, v in data.get(r, {}).items()}
        totals.update({p: v for p, v in past[own].items() if p not in totals})
        top = sorted(totals, key=lambda p: -totals[p])[:3]
        before = {p: totals[p] - pts for p, pts in zip(ms[o]["starters"], ms[o].get("starters_points") or []) if p in totals}
        top_before = sorted(totals, key=lambda p: -(before.get(p, totals[p])))[:3]
        for pid, pts in zip(ms[o]["starters"], ms[o].get("starters_points") or []):
            if pid in top:
                games = past_g[own][pid] + data[r][pid][1]
                out.append({"team": lg.team[r], "player": lg.name_of(pid), "pos": lg.pos_of(pid), "started_by": lg.team[o],
                            "points_this_week": round(pts or 0, 1), "all_time_points_against_team": round(totals[pid], 1),
                            "all_time_games_against_team": games, "nemesis_rank_for_team": top.index(pid) + 1,
                            "new_to_top_3": pid not in top_before})
    out.sort(key=lambda x: -x["points_this_week"])
    return out[:limit]


def _po_text(po):
    """'2 · 41.3' style summary of playoff games, or ''."""
    return f'{len(po)} · {sum(v for *_, v in po):.1f}' if po else ""


def season_rows(lg):
    data = season(lg)
    rows = []
    for r, name in lg.team.items():
        ps = sorted(data.get(r, {}).items(), key=lambda kv: -kv[1][0])
        rows.append({"team": name, "players": [
            {"name": lg.name_of(p), "pos": lg.pos_of(p), "pts": v[0], "games": v[1], "po_games": len(v[3]), "po_pts": sum(x[2] for x in v[3]),
             "po_detail": ", ".join(f"wk {w} vs. {lg.team[o]}: {pts:.1f}" for w, o, pts in v[3]),
             "by": ", ".join(f"{lg.team[o]}" + (f" ×{n}" if n > 1 else "") for o, n in v[2].most_common())}
            for p, v in ps[:10]]})
    return rows


def summary(lg):
    """For season_summary: {owner: {pid: [points, games, name, pos, playoff games, playoff points]}} (top KEEP per manager)."""
    data = season(lg)
    out = {}
    for r in lg.team:
        ps = sorted(data.get(r, {}).items(), key=lambda kv: -kv[1][0])[:KEEP]
        out[lg.owner[r]] = {p: [round(v[0], 2), v[1], lg.name_of(p), lg.pos_of(p), len(v[3]), round(sum(x[2] for x in v[3]), 2)] for p, v in ps}
    return out


def alltime_rows(sums, name_of_owner):
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, None, None, [], 0, 0.0, []]))
    for x in sums:
        for o, ps in (x.get("nemeses") or {}).items():
            for p, row in ps.items():
                pts, g, n, pos = row[:4]
                po_g, po_pts = (row[4], row[5]) if len(row) > 5 else (0, 0.0)
                a = agg[o][p]
                a[0] += pts
                a[1] += g
                a[2], a[3] = n, pos
                a[4].append(x["season"])
                a[5] += po_g
                a[6] += po_pts
                if po_g:
                    a[7].append(x["season"])
    rows = []
    for o, ps in agg.items():
        top = sorted(ps.values(), key=lambda a: -a[0])[:10]
        rows.append({"team": name_of_owner(o), "players": [
            {"name": a[2], "pos": a[3], "pts": a[0], "games": a[1], "by": ", ".join(sorted(set(a[4]))), "po_games": a[5], "po_pts": a[6],
             "po_detail": "playoffs " + ", ".join(sorted(set(a[7]))) if a[7] else ""} for a in top]})
    return rows


def html(rows, key, alltime=False):
    """One row per team: its three worst nemeses, with a dropdown of the top ten."""
    rows = [r for r in rows if r["players"]]
    if not rows:
        return '<div class="panel muted">No games yet.</div>'
    rows.sort(key=lambda r: -sum(p["pts"] for p in r["players"][:3]))

    def cell(p):
        if not p:
            return '<td data-v="0"><span class="muted">—</span></td>'
        return (f'<td data-v="{p["pts"]:.2f}" style="white-space:nowrap"><b>{esc(p["name"])}</b> <span class="muted">{p["pos"] or ""}</span>'
                f'<div style="font-size:12px"><b>{p["pts"]:.1f}</b> <span class="muted">in {p["games"]} game{"s" if p["games"] != 1 else ""}'
                + (f' ({p["po_games"]} in playoffs)' if p.get("po_games") else "")
                + f' · {p["pts"] / max(1, p["games"]):.1f} a game</span></div></td>')
    trs = []
    for i, r in enumerate(rows):
        ps = r["players"]
        top3 = sum(p["pts"] for p in ps[:3])
        det = "".join(f'<tr><td class="muted">{j}</td><td><b>{esc(p["name"])}</b> <span class="muted">{p["pos"] or ""}</span></td>'
                      f'<td class="n team">{p["pts"]:.1f}</td><td class="n">{p["games"]}</td><td class="n">{p["pts"] / max(1, p["games"]):.1f}</td>'
                      + (f'<td class="n" style="min-width:170px" title="{esc(p.get("po_detail", ""))}"><b>{p["po_games"]}</b> <span class="muted">· {p["po_pts"]:.1f}</span>'
                         + (f'<div class="muted" style="font-size:11px;white-space:normal">{esc(p["po_detail"])}</div>' if p.get("po_detail") else "")
                         + '</td>' if p.get("po_games") else '<td class="n muted">–</td>')
                      + f'<td class="muted" style="font-size:12px">{esc(p["by"])}</td></tr>' for j, p in enumerate(ps, 1))
        trs.append(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="{key}-{i}">'
                   f'<td class="team" style="white-space:nowrap" data-v="{esc(r["team"].lower())}"><span class="chev" aria-hidden="true">▸</span> {esc(r["team"])}</td>'
                   + "".join(cell(ps[j] if j < len(ps) else None) for j in range(3))
                   + f'<td class="n team" data-v="{top3:.2f}">{top3:.1f}</td></tr>'
                   f'<tr class="xdetail" id="{key}-{i}" hidden><td colspan="5"><div class="xpin"><table class="picks"><tr><td></td>'
                   f'<td class="muted">Player</td><td class="n muted">Points</td><td class="n muted">Games</td><td class="n muted">Per game</td>'
                   f'<td class="n muted">Playoff games · pts</td>'
                   f'<td class="muted">{"Seasons" if alltime else "Started against you by"}</td></tr>{det}</table></div></td></tr>')
    note = ("Points scored against each manager by players their opponents started, regular season and playoffs, added up over "
            "every season (team names are the current ones)." if alltime else
            "Points scored against each team by players its opponents started, regular season and playoffs.")
    note += " Playoffs = winners-bracket games (not the 5th-place game); the dropdown shows how many of the games and points came there."
    return ('<div class="panel scroll"><table class="sortable expand"><thead><tr><th>Team</th><th>Worst nemesis</th><th>2nd</th>'
            f'<th>3rd</th><th class="n">Top 3 total</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<p class="note">{note} Click a team for its top ten and who started them. Click a column header to sort.</p>')
