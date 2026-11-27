"""Nemeses: the NFL players who have scored the most fantasy points against each team (started by its opponents), for one
season and all-time. The same file is used by the Clampions and BBLOT dashboards."""
import collections

from dashboard.render import esc

KEEP = 25  # players per manager kept in each season's summary, enough for an all-time top 10


def season(lg):
    """{roster: {pid: [points, games, Counter(opposing roster -> games)]}}: regular-season points opponents' starters
    scored against each team."""
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, collections.Counter()]))
    for w in lg.weeks:
        opp = lg.opponent(w)
        ms = {m["roster_id"]: m for m in lg.matchups[w]}
        for r, o in opp.items():
            m = ms.get(o)
            if not m:
                continue
            for pid, v in zip(m["starters"], m.get("starters_points") or []):
                if pid == "0":
                    continue
                x = out[r][pid]
                x[0] += v or 0
                x[1] += 1
                x[2][o] += 1
    return out


def season_rows(lg):
    data = season(lg)
    rows = []
    for r, name in lg.team.items():
        ps = sorted(data.get(r, {}).items(), key=lambda kv: -kv[1][0])
        rows.append({"team": name, "players": [
            {"name": lg.name_of(p), "pos": lg.pos_of(p), "pts": v[0], "games": v[1],
             "by": ", ".join(f"{lg.team[o]}" + (f" ×{n}" if n > 1 else "") for o, n in v[2].most_common())}
            for p, v in ps[:10]]})
    return rows


def summary(lg):
    """For season_summary: {owner: {pid: [points, games, name, pos]}} (top KEEP per manager)."""
    data = season(lg)
    out = {}
    for r in lg.team:
        ps = sorted(data.get(r, {}).items(), key=lambda kv: -kv[1][0])[:KEEP]
        out[lg.owner[r]] = {p: [round(v[0], 2), v[1], lg.name_of(p), lg.pos_of(p)] for p, v in ps}
    return out


def alltime_rows(sums, name_of_owner):
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, None, None, []]))
    for x in sums:
        for o, ps in (x.get("nemeses") or {}).items():
            for p, (pts, g, n, pos) in ps.items():
                a = agg[o][p]
                a[0] += pts
                a[1] += g
                a[2], a[3] = n, pos
                a[4].append(x["season"])
    rows = []
    for o, ps in agg.items():
        top = sorted(ps.values(), key=lambda a: -a[0])[:10]
        rows.append({"team": name_of_owner(o), "players": [
            {"name": a[2], "pos": a[3], "pts": a[0], "games": a[1], "by": ", ".join(sorted(set(a[4])))} for a in top]})
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
                f' · {p["pts"] / max(1, p["games"]):.1f} a game</span></div></td>')
    trs = []
    for i, r in enumerate(rows):
        ps = r["players"]
        top3 = sum(p["pts"] for p in ps[:3])
        det = "".join(f'<tr><td class="muted">{j}</td><td><b>{esc(p["name"])}</b> <span class="muted">{p["pos"] or ""}</span></td>'
                      f'<td class="n team">{p["pts"]:.1f}</td><td class="n">{p["games"]}</td><td class="n">{p["pts"] / max(1, p["games"]):.1f}</td>'
                      f'<td class="muted" style="font-size:12px">{esc(p["by"])}</td></tr>' for j, p in enumerate(ps, 1))
        trs.append(f'<tr class="xrow" tabindex="0" role="button" aria-expanded="false" aria-controls="{key}-{i}">'
                   f'<td class="team" style="white-space:nowrap" data-v="{esc(r["team"].lower())}"><span class="chev" aria-hidden="true">▸</span> {esc(r["team"])}</td>'
                   + "".join(cell(ps[j] if j < len(ps) else None) for j in range(3))
                   + f'<td class="n team" data-v="{top3:.2f}">{top3:.1f}</td></tr>'
                   f'<tr class="xdetail" id="{key}-{i}" hidden><td colspan="5"><div class="xpin"><table class="picks"><tr><td></td>'
                   f'<td class="muted">Player</td><td class="n muted">Points</td><td class="n muted">Games</td><td class="n muted">Per game</td>'
                   f'<td class="muted">{"Seasons" if alltime else "Started against you by"}</td></tr>{det}</table></div></td></tr>')
    note = ("Regular-season points scored against each manager by players their opponents started, added up over every season "
            "(team names are the current ones)." if alltime else
            "Regular-season points scored against each team by players its opponents started.")
    return ('<div class="panel scroll"><table class="sortable expand"><thead><tr><th>Team</th><th>Worst nemesis</th><th>2nd</th>'
            f'<th>3rd</th><th class="n">Top 3 total</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<p class="note">{note} Click a team for its top ten and who started them. Click a column header to sort.</p>')
