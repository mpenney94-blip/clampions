# Clampions dashboard

Static site for the "We Are The Clampions" Sleeper fantasy league, rebuilt by GitHub Actions and served on GitHub Pages:
https://mpenney94-blip.github.io/clampions/

## Layout

- `sleeper.py`: Sleeper API client. The players DB is cached in `.cache/` for a day, written atomically because season builds run in parallel.
- `winprob.py`: ESPN scoreboard and play-by-play helpers, projections, and the play-by-play win probability model. `espn_games()` returns ids, teams, home team and ESPN team ids.
- `dashboard/stats.py`: `League` (one season's data) plus season stats, `season_summary()` (feeds the all-time page).
- `dashboard/weekly.py`: playoff odds and clinches, power, awards, preview, trends, byes/injuries, career days, flagged plays, kicking.
- `dashboard/commentary.py`: fact sheets and the Claude-written columns (recap, preview, rivalry), with a built-in fallback writer.
- `dashboard/league_notes.md`: league lore fed to the column writer (duck hunt, "he" for managers, puns, dated real-life news).
- `dashboard/render.py`: all HTML/CSS/JS. `dashboard/build.py`: assembles pages, season tabs and the all-time page.
- `.github/workflows/dashboard.yml`: builds and deploys.

## Building and checking

```
python3 -m dashboard.build 1387868351270760448 --out <dir> --no-winprob --past-cache <dir>   # all seasons
python3 -m dashboard.build 1387868351270760448 --out <dir> --no-winprob --only 2026            # current season only
```

Check pages with Playwright (`PW=$(npm root -g)/playwright node script.js`): screenshot the section, click its controls,
and listen for `pageerror`. Run the build without piping its exit code away; an exception mid-build leaves an empty page.

## Table conventions

- Every sortable table gets both a "Sort by" menu and clickable column headers, kept in sync by the shared sorter in
  `HIGHLIGHT_JS`. Use either `_sort_controls()` inside a `.sortbars` panel (custom sort keys from `data-*` row attributes)
  or `<table class="sortable">` (a menu is built from the headers). Give cells a `data-v` when their text isn't the sort value.
- Expandable rows (`tr.xrow` + `tr.xdetail`, via `_xrows`) stay attached when sorted; tables inside expanded rows are skipped.
  Any `table.expand` with 2+ dropdown rows gets an "Expand all / Collapse all" button automatically.
- Grid/heatmap tables use `.grid-t`, with headers centered over their cells.
- Every `section[id] > h2` gets a "Save image" button (html2canvas from cdnjs, loaded on first use) that captures the
  section as currently shown (sections holding a `[data-nosnap]` element, like the Past weeks tabs, are skipped). html2canvas can't parse `color-mix()`, so use plain colors or the `--t1`..`--t6` tints.

## Workflow conventions

- Each change goes on its own branch, then a PR is opened and merged with `expectedHeadSha`, then the deploy is confirmed
  by polling the live site or the Actions run.
- Commit trailers: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and the `Claude-Session:` link.
- Pushing to `main` under `dashboard/**`, `sleeper.py`, `winprob.py` or the workflow triggers a build. Code changes
  invalidate the finished-season cache (key = hash of the code), so past seasons rebuild in parallel.

## Schedule and pages

- Scheduled runs: Tuesday 4am and Thursday noon Pacific. Both UTC times are listed and a `gate` job lets the one matching
  PDT/PST through. Pushes and manual runs always build.
- Current season at `/`, week pages at `/weeks/N.html` (full "This week" hub for the current season only), finished
  seasons at `/<season>/`, all-time at `/alltime/`. Seasons come from Sleeper's `previous_league_id` chain (2023 on).
- Main page groups: This week, Scoring, Roster, Draft. All-time groups: Standings, Rivalries, Records, Roster moves.

## League rules (encoded)

- 12 teams, 2 divisions. Regular season weeks 1–14; season stats cover the regular season only.
- Playoffs: top 2 in each division are in, division winners get byes, then 2 wild cards from either division. Every tie
  goes to points for. Clinch/eliminated tags are mathematical (worst case/best case), not simulated.
- Final place: 1–6 from the winners bracket, 7–12 from the toilet bowl (losers advance; Sleeper marks the advancing team
  as `w`, so the bracket's direction is read from real scores). Last place = loses every toilet bowl game = duck hunt.
  The 5th-place game is left out of head-to-head and playoff records.
- Scoring: half PPR; kick/punt return yards 0.04, return TD 6. Field goals: made = 0.1/yd − 1; missed = −3 (<30),
  −2 (30–39), −1 (40–49), 0 (50+). XP +1 / −3. Verified against Sleeper's kicker scores.
- Kick distance = yards to the goal line + 18 (measured from this season's field goals).

## Data quirks learned the hard way

- Sleeper `gms_active` is set for injured players who sat; "played" means `gp` only.
- Sleeper is missing `espn_id` for most players. Match ESPN athletes by name and team from the box score, then by the
  abbreviated name in the play text ("R.Rice", "Bi.Robinson") when a player isn't in the box score.
- ESPN `yardsToEndzone` is often from the wrong goal line; compute field position from `possessionText` and possession.
- ESPN play text uses its own team codes (HST, BLT, CLV, ARZ, LA, WSH); see `_ESPN_TEAM` and `ESPN_TO_SLEEPER_TEAM`.
- "No Play" penalties wipe a play; "TOUCHDOWN NULLIFIED" without "No Play" is a spot foul (yards up to the flag count).
- Return-team flags during a return take back the yards after the foul.
- ESPN extra point text can be "Blocked" in mixed case.

## Written columns (Claude)

- Model `claude-sonnet-5-5` with server-side fallbacks, `ANTHROPIC_API_KEY` from the repo secret. Current season only;
  finished seasons use the built-in writer.
- Cached in `.cache/commentary` (Actions cache). A recap, or a preview of a week already played, is written once and
  kept. The live preview and the rivalry column are rewritten only when `COMMENTARY_REFRESH=1` (scheduled and manual
  runs). Expected cost about $0.10–0.15 a week.
- To add real-life news, append a dated line to the "Real-life news" section of `dashboard/league_notes.md`.
- The preview's facts include each team's history in that week number of past seasons (`commentary.week_number_facts`:
  record, average vs. the league, rank among his weeks, and flagged notables like a week he has never won).

## Open options offered to the owner

- Go back to Opus for the columns (or Opus for the recap only) if Sonnet's writing drops off.
- Leave out drops where the player never played for the team that cut him.
- Kicker column for points a miss cost versus making it.
- Flagged away: count partial yards taken back on non-touchdown plays with a spot foul.

## Planned: a dynasty league site

A separate repo and Sleeper league (details to come) will reuse this format, with these changes:
- Rookie draft instead of a full draft: grade rookie classes over several seasons, hit rates by slot, best/worst classes,
  rookie redraft; a startup draft section if one exists in the league history.
- No keeper sections. Add a contention window view and where each team's points come from over the years.
- Carry over "Age, experience and injury history" (`weekly.roster_profile`). It matters even more in dynasty; consider
  adding projected age next season and an age-weighted value of each roster.
- Trades judged across seasons, with traded draft picks valued by who was eventually drafted with them.
- A future draft pick ownership table (Sleeper traded picks).
- Taxi squad and IR players left out of bench and lineup stats.
- Confirm playoff, toilet bowl, scoring and tradition details with the owner, as was done here.
