"""
Step 4: Pull college stats for cohort QBs from College Football Data API.
        https://collegefootballdata.com — free API key required.

        export CFBD_KEY="your_key_here"

Endpoints used per season year (one call each = very efficient):
  /stats/player/season   — traditional passing + rushing stats
  /ppa/players/season    — PPA (Predicted Points Added) per play
  /player/usage          — usage rates by down
  /records               — team win/loss records per season

Features engineered per QB (last 2 college seasons combined):
  Traditional:
    cmp_pct, yards_per_att, td_int_ratio, int_rate, sack_rate,
    rush_att_per_game, rush_yds_per_att, games_played, games_started
  Advanced:
    ppa_overall, ppa_pass, ppa_rush (avg predicted pts added per play)
    usage_overall, usage_passing, usage_third_down
    pass_td_pct, first_down_pct
  Team context:
    col_team_win_pct (avg team win % across last 2 seasons)

Input:  data/processed/qb_cohort.csv
Output: data/raw/cfbd_raw_stats.json   (raw API responses, cached)
        data/processed/qb_college_features.csv
"""

import os
import json
import time
from typing import Any, cast
import requests
import pandas as pd
from rapidfuzz import process, fuzz

# Load .env.local if present (keeps key out of source code)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

CFBD_KEY = os.environ.get("CFBD_KEY", "")
BASE = "https://api.collegefootballdata.com"
COHORT_PATH = "data/processed/qb_cohort.csv"
RAW_CACHE = "data/raw/cfbd_raw_stats.json"
OUT_PATH = "data/processed/qb_college_features.csv"
QB_RECRUIT_POSITIONS = {"QB", "PRO", "DUAL"}


def cfbd_get(endpoint: str, params: dict) -> list:
    if not CFBD_KEY:
        raise ValueError("Set CFBD_KEY environment variable. Register free at collegefootballdata.com")
    headers = {"Authorization": f"Bearer {CFBD_KEY}", "accept": "application/json"}
    url = f"{BASE}/{endpoint}"
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    time.sleep(0.3)
    return resp.json()


def normalize_name(name: str) -> str:
    return (str(name).lower().strip()
            .replace(".", "").replace("'", "").replace("-", " ")
            .replace(" jr", "").replace(" sr", "").replace(" ii", "").replace(" iii", ""))


def match_player(target: str, candidates: list[str], threshold: int = 80) -> str | None:
    norm_target = normalize_name(target)
    norm_candidates = [normalize_name(c) for c in candidates]
    result = process.extractOne(norm_target, norm_candidates, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return candidates[norm_candidates.index(result[0])]
    return None


def is_qb_recruit(row: dict[str, Any]) -> bool:
    position = str(row.get("position", "")).strip().upper()
    return position in QB_RECRUIT_POSITIONS or "QB" in position


def load_cache() -> dict[str, Any]:
    if not os.path.exists(RAW_CACHE):
        return {}

    print(f"Loading cached CFBD data from {RAW_CACHE}")
    with open(RAW_CACHE) as f:
        cache = json.load(f)

    if isinstance(cache, dict):
        return cache
    return {}


def save_cache(cache: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    def make_serializable(obj: Any) -> Any:
        if isinstance(obj, dict):
            obj_dict = cast(dict[Any, Any], obj)
            return {
                (int(k) if isinstance(k, np.integer) else k): make_serializable(v)
                for k, v in obj_dict.items()
            }
        if isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return obj

    cache_clean = make_serializable(cache)
    with open(RAW_CACHE, "w") as f:
        json.dump(cache_clean, f)
    print(f"\nCached to {RAW_CACHE}")
    return {str(k): v for k, v in cache_clean.items()}


# ---------------------------------------------------------------------------
# Pull raw data from CFBD (or load from cache)
# ---------------------------------------------------------------------------

def fetch_all_seasons(years: list[int]) -> dict:
    """Fetch all CFBD data for the given years. Cache to avoid re-pulling."""
    cache = load_cache()
    updated = False
    for year in years:
        year_key = str(year)
        year_cache = cache.setdefault(year_key, {})
        year_sections = ("passing", "rushing", "ppa", "usage")
        if all(year_cache.get(key) for key in year_sections):
            continue

        print(f"  Fetching {year}...")

        # 1. Traditional passing stats
        try:
            year_cache["passing"] = cfbd_get(
                "stats/player/season",
                {"year": year, "seasonType": "regular", "category": "passing"}
            )
            updated = True
            print(f"    passing: {len(year_cache['passing'])} rows")
        except Exception as e:
            print(f"    passing ERROR: {e}")
            year_cache["passing"] = []

        # 2. Rushing stats
        try:
            year_cache["rushing"] = cfbd_get(
                "stats/player/season",
                {"year": year, "seasonType": "regular", "category": "rushing"}
            )
            updated = True
            print(f"    rushing: {len(year_cache['rushing'])} rows")
        except Exception as e:
            print(f"    rushing ERROR: {e}")
            year_cache["rushing"] = []

        # 3. PPA (Predicted Points Added)
        try:
            year_cache["ppa"] = cfbd_get(
                "ppa/players/season",
                {"year": year, "threshold": 100}
            )
            updated = True
            print(f"    ppa: {len(year_cache['ppa'])} rows")
        except Exception as e:
            print(f"    ppa ERROR: {e}")
            year_cache["ppa"] = []

        # 4. Player usage (down-by-down)
        try:
            year_cache["usage"] = cfbd_get(
                "player/usage",
                {"year": year, "position": "QB"}
            )
            updated = True
            print(f"    usage: {len(year_cache['usage'])} rows")
        except Exception as e:
            print(f"    usage ERROR: {e}")
            year_cache["usage"] = []

    # 5. Recruiting ratings (pull a wide range to cover all cohort QBs)
    # Recruiting class year is typically draft_year - 3 or - 4
    if cache.get("recruiting"):
        print(f"  Using cached recruiting data ({len(cache['recruiting'])} rows)")
    else:
        print("  Fetching recruiting data...")
        recruit_years = list(range(int(min(years)) - 2, int(max(years)) + 1))
        fetched_recruits: list[dict[str, Any]] = []
        for ry in recruit_years:
            try:
                rows = cfbd_get("recruiting/players", {"year": ry})
                qb_rows = [r for r in rows if is_qb_recruit(r)]
                fetched_recruits.extend(qb_rows)
                updated = True
                print(f"    {ry}: {len(qb_rows)} QB recruits")
            except Exception as e:
                print(f"    recruiting {ry} ERROR: {e}")
        if fetched_recruits:
            cache["recruiting"] = fetched_recruits
        print(f"    recruiting: {len(fetched_recruits)} total recruits")

    if updated:
        return save_cache(cache)

    return {str(k): v for k, v in cache.items()}


# ---------------------------------------------------------------------------
# Parse a single season's stats for a named QB
# ---------------------------------------------------------------------------

def extract_passing_stats(name: str, year_data: dict) -> dict:
    """
    Parse CFBD stats/player/season (passing category) for one QB.
    Returns flat dict of passing stat values.
    """
    rows = year_data.get("passing", [])
    players = [r["player"] for r in rows]
    matched = match_player(name, players)
    if not matched:
        return {}

    player_rows = [r for r in rows if r["player"] == matched]
    stats = {}
    for row in player_rows:
        key = row.get("statType", "").lower().replace(" ", "_")
        try:
            stats[key] = float(row.get("stat", 0))
        except (ValueError, TypeError):
            pass
    return stats


def extract_rushing_stats(name: str, year_data: dict) -> dict:
    rows = year_data.get("rushing", [])
    players = [r["player"] for r in rows]
    matched = match_player(name, players)
    if not matched:
        return {}
    player_rows = [r for r in rows if r["player"] == matched]
    stats = {}
    for row in player_rows:
        key = "rush_" + row.get("statType", "").lower().replace(" ", "_")
        try:
            stats[key] = float(row.get("stat", 0))
        except (ValueError, TypeError):
            pass
    return stats


def extract_ppa(name: str, year_data: dict) -> dict:
    rows = year_data.get("ppa", [])
    players = [r.get("name", "") for r in rows]
    matched = match_player(name, players)
    if not matched:
        return {}
    row = next((r for r in rows if r.get("name") == matched), None)
    if not row:
        return {}
    avg = row.get("averagePPA", {})
    return {
        "ppa_overall": avg.get("all"),
        "ppa_pass":    avg.get("pass"),
        "ppa_rush":    avg.get("rush"),
        "ppa_plays":   row.get("countablePlays"),
    }


def extract_usage(name: str, year_data: dict) -> dict:
    rows = year_data.get("usage", [])
    players = [r.get("name", "") for r in rows]
    matched = match_player(name, players)
    if not matched:
        return {}
    row = next((r for r in rows if r.get("name") == matched), None)
    if not row:
        return {}
    u = row.get("usage", {})
    return {
        "usage_overall":     u.get("overall"),
        "usage_pass":        u.get("pass"),
        "usage_rush":        u.get("rush"),
        "usage_first_down":  u.get("firstDown"),
        "usage_second_down": u.get("secondDown"),
        "usage_third_down":  u.get("thirdDown"),
        "conference":        row.get("conference"),
        "team":              row.get("team"),
    }


def fetch_team_record(team: str, year: int) -> dict | None:
    """
    Fetch win/loss record for a team in a given year from CFBD /records.
    Returns dict with win_pct or None on failure.
    """
    try:
        data = cfbd_get("records", {"year": year, "team": team})
        if not data:
            return None
        record = data[0] if isinstance(data, list) else data
        total = record.get("total", {})
        wins   = total.get("wins", 0)
        losses = total.get("losses", 0)
        games  = total.get("games") or (wins + losses)
        if games and games > 0:
            return {"win_pct": round(wins / games, 4)}
    except Exception as e:
        print(f"    team_record ERROR ({team} {year}): {e}")
    return None


def extract_recruiting(name: str, college: str, draft_year: int, cache: dict) -> dict:
    rows = cache.get("recruiting", [])

    def recruiting_score(row: dict[str, Any]) -> tuple[int, int, int]:
        name_score = int(
            fuzz.token_sort_ratio(normalize_name(name), normalize_name(row.get("name", "")))
        )
        commit_score = int(
            fuzz.token_sort_ratio(str(college).lower(), str(row.get("committedTo", "")).lower())
        )
        recruit_year = row.get("year")
        try:
            year_gap = abs(int(recruit_year) - (draft_year - 4))
        except (TypeError, ValueError):
            year_gap = 99
        return (name_score, commit_score, -year_gap)

    candidates = [row for row in rows if recruiting_score(row)[0] >= 80]
    if not candidates:
        return {}

    college_matched = [row for row in candidates if recruiting_score(row)[1] >= 80]
    pool = college_matched or candidates
    row = max(pool, key=recruiting_score)

    return {
        "recruit_stars":     row.get("stars"),
        "recruit_rating":    row.get("rating"),
        "recruit_ranking":   row.get("ranking"),
        "recruit_position":  row.get("position"),
        "recruit_city":      row.get("city"),
        "recruit_state_prov": row.get("stateProvince"),
    }


# ---------------------------------------------------------------------------
# Aggregate two seasons into one feature row per QB
# ---------------------------------------------------------------------------

def safe_avg(vals: list) -> float | None:
    valid = [v for v in vals if v is not None]
    return sum(valid) / len(valid) if valid else None


def safe_sum(vals: list) -> float | None:
    valid = [v for v in vals if v is not None]
    return sum(valid) if valid else None


def aggregate_college(season_dicts: list[dict]) -> dict:
    """
    Given a list of per-season stat dicts, produce a single aggregated
    feature dict. Counting stats are summed; rate stats are averaged
    (weighted by attempts where possible).
    """
    out = {}

    # Counting stats — sum across seasons
    for key in ["completions", "att", "yds", "td", "int", "sacks", "sack_yds",
                "rush_car", "rush_yds", "rush_td", "ppa_plays"]:
        vals = [s.get(key) for s in season_dicts]
        out[f"col_{key}"] = safe_sum(vals)

    # Derive clean aggregate rates from summed counts
    att = out.get("col_att") or 0
    cmp = out.get("col_completions") or 0
    yds = out.get("col_yds") or 0
    td  = out.get("col_td") or 0
    int_ = out.get("col_int") or 0
    sacks = out.get("col_sacks") or 0
    rush_car = out.get("col_rush_car") or 0
    rush_yds = out.get("col_rush_yds") or 0

    out["col_cmp_pct"]        = round(cmp / att * 100, 2) if att > 0 else None
    out["col_yds_per_att"]    = round(yds / att, 2) if att > 0 else None
    out["col_td_int_ratio"]   = round(td / int_, 2) if int_ > 0 else None
    out["col_int_rate"]       = round(int_ / att * 100, 2) if att > 0 else None
    out["col_sack_rate"]      = round(sacks / (att + sacks) * 100, 2) if (att + sacks) > 0 else None
    out["col_rush_yds_per_att"] = round(rush_yds / rush_car, 2) if rush_car > 0 else None

    # Rate stats — simple average across seasons
    for key in ["ppa_overall", "ppa_pass", "ppa_rush",
                "usage_overall", "usage_pass", "usage_rush",
                "usage_first_down", "usage_second_down", "usage_third_down",
                "team_win_pct"]:
        vals = [s.get(key) for s in season_dicts]
        out[f"col_{key}"] = safe_avg(vals)

    # Metadata — take from most recent season
    for key in ["conference", "team"]:
        for s in reversed(season_dicts):
            if s.get(key):
                out[f"col_{key}"] = s[key]
                break

    out["col_seasons_found"] = len([s for s in season_dicts if s])

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cohort = pd.read_csv(COHORT_PATH)
    print(f"Cohort: {len(cohort)} QBs, draft years {cohort['draft_year'].min()}–{cohort['draft_year'].max()}")

    # Determine college seasons to pull
    # Senior year = draft_year - 1, junior year = draft_year - 2
    draft_years = cohort["draft_year"].unique()
    college_years = sorted(set(
        year for dy in draft_years for year in [dy - 1, dy - 2]
    ))
    print(f"College seasons to fetch: {college_years}")

    # Fetch (or load cache)
    cache = fetch_all_seasons(college_years)

    results = []
    for _, qb in cohort.iterrows():
        name = qb["qb_name"]
        draft_year = int(qb["draft_year"])
        senior_year = str(draft_year - 1)
        junior_year = str(draft_year - 2)

        print(f"\n{name} ({draft_year})...")

        season_features = []
        for yr in [junior_year, senior_year]:
            if yr not in cache:
                print(f"  {yr}: no data in cache")
                season_features.append({})
                continue

            yr_data = cache[yr]
            passing = extract_passing_stats(name, yr_data)
            rushing = extract_rushing_stats(name, yr_data)
            ppa     = extract_ppa(name, yr_data)
            usage   = extract_usage(name, yr_data)

            merged = {**passing, **rushing, **ppa, **usage}

            # Fetch team win rate for the season
            col_team = usage.get("team")
            if col_team:
                rec = fetch_team_record(col_team, int(yr))
                if rec:
                    merged["team_win_pct"] = rec["win_pct"]

            found = bool(passing or ppa or usage)
            print(f"  {yr}: {'found' if found else 'NOT FOUND'} — "
                  f"att={passing.get('att')}, cmp%={passing.get('pct')}, "
                  f"ppa={ppa.get('ppa_overall')}, win_pct={merged.get('team_win_pct')}")
            season_features.append(merged)

        agg = aggregate_college(season_features)
        recruiting = extract_recruiting(name, qb.get("college", ""), draft_year, cache)
        if recruiting:
            print(f"  recruiting: {recruiting.get('recruit_stars')}★ | rating={recruiting.get('recruit_rating')} | rank={recruiting.get('recruit_ranking')}")
        else:
            print(f"  recruiting: NOT FOUND")

        row = {
            "qb_name":    name,
            "draft_year": draft_year,
            "college":    qb.get("college"),
        }
        row.update(recruiting)
        row.update(agg)
        results.append(row)

    df = pd.DataFrame(results)
    found = df["col_seasons_found"].gt(0).sum()
    if found == 0:
        raise RuntimeError(
            "No college data matched. Refusing to overwrite existing output. "
            "Populate the CFBD cache or rerun with network access."
        )

    df.to_csv(OUT_PATH, index=False)
    print(f"\nMatched {found}/{len(df)} QBs to college data")
    print(f"Saved to {OUT_PATH}")
    print(f"\nFeature columns ({len([c for c in df.columns if c.startswith('col_')])}):")
    print([c for c in df.columns if c.startswith("col_")])


if __name__ == "__main__":
    main()
