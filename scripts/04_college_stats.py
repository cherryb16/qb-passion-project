"""
Step 4: Pull college stats for cohort QBs from College Football Data API.
        https://collegefootballdata.com — free API key required.

        export CFBD_KEY="your_key_here"

Endpoints used per season year (one call each = very efficient):
  /stats/player/season   — traditional passing + rushing stats
  /ppa/players/season    — PPA (Predicted Points Added) per play
  /player/usage          — usage rates by down, explosiveness

Features engineered per QB (last 2 college seasons combined):
  Traditional:
    cmp_pct, yards_per_att, td_int_ratio, int_rate, sack_rate,
    rush_att_per_game, rush_yds_per_att, games_played, games_started
  Advanced:
    ppa_overall, ppa_pass, ppa_rush (avg predicted pts added per play)
    usage_overall, usage_passing, usage_third_down
    explosiveness (avg PPA on successful plays)
    pass_td_pct, first_down_pct

Input:  data/processed/qb_cohort.csv
Output: data/raw/cfbd_raw_stats.json   (raw API responses, cached)
        data/processed/qb_college_features.csv
"""

import os
import json
import time
import requests
import pandas as pd
from rapidfuzz import process, fuzz

CFBD_KEY = os.environ.get("CFBD_KEY", "Gh0YQadv3zW/jJtWXn2QQ3jSZPaYiBaxLUX5atazB3zUuZqWMZt7Uh3vTiHRO24D")
BASE = "https://api.collegefootballdata.com"
COHORT_PATH = "data/processed/qb_cohort.csv"
RAW_CACHE = "data/raw/cfbd_raw_stats.json"
OUT_PATH = "data/processed/qb_college_features.csv"


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


# ---------------------------------------------------------------------------
# Pull raw data from CFBD (or load from cache)
# ---------------------------------------------------------------------------

def fetch_all_seasons(years: list[int]) -> dict:
    """Fetch all CFBD data for the given years. Cache to avoid re-pulling."""
    if os.path.exists(RAW_CACHE):
        print(f"Loading cached CFBD data from {RAW_CACHE}")
        with open(RAW_CACHE) as f:
            return json.load(f)

    cache = {}
    for year in years:
        print(f"  Fetching {year}...")
        cache[year] = {}

        # 1. Traditional passing stats
        try:
            cache[year]["passing"] = cfbd_get(
                "stats/player/season",
                {"year": year, "seasonType": "regular", "category": "passing"}
            )
            print(f"    passing: {len(cache[year]['passing'])} rows")
        except Exception as e:
            print(f"    passing ERROR: {e}")
            cache[year]["passing"] = []

        # 2. Rushing stats
        try:
            cache[year]["rushing"] = cfbd_get(
                "stats/player/season",
                {"year": year, "seasonType": "regular", "category": "rushing"}
            )
            print(f"    rushing: {len(cache[year]['rushing'])} rows")
        except Exception as e:
            print(f"    rushing ERROR: {e}")
            cache[year]["rushing"] = []

        # 3. PPA (Predicted Points Added)
        try:
            cache[year]["ppa"] = cfbd_get(
                "ppa/players/season",
                {"year": year, "threshold": 100}
            )
            print(f"    ppa: {len(cache[year]['ppa'])} rows")
        except Exception as e:
            print(f"    ppa ERROR: {e}")
            cache[year]["ppa"] = []

        # 4. Player usage (down-by-down, explosiveness)
        try:
            cache[year]["usage"] = cfbd_get(
                "player/usage",
                {"year": year, "position": "QB"}
            )
            print(f"    usage: {len(cache[year]['usage'])} rows")
        except Exception as e:
            print(f"    usage ERROR: {e}")
            cache[year]["usage"] = []

    # 5. Recruiting ratings (pull a wide range to cover all cohort QBs)
    # Recruiting class year is typically draft_year - 3 or - 4
    print("  Fetching recruiting data...")
    recruit_years = list(range(int(min(years)) - 2, int(max(years)) + 1))
    cache["recruiting"] = []
    for ry in recruit_years:
        try:
            rows = cfbd_get("recruiting/players", {"year": ry, "position": "Pro-Style QB"})
            cache["recruiting"].extend(rows)
            rows2 = cfbd_get("recruiting/players", {"year": ry, "position": "Dual Threat QB"})
            cache["recruiting"].extend(rows2)
        except Exception as e:
            print(f"    recruiting {ry} ERROR: {e}")
    print(f"    recruiting: {len(cache['recruiting'])} total recruits")

    with open(RAW_CACHE, "w") as f:
        json.dump(cache, f)
    print(f"\nCached to {RAW_CACHE}")
    return cache


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
        "explosiveness":     row.get("explosiveness"),
        "conference":        row.get("conference"),
        "team":              row.get("team"),
    }


def extract_recruiting(name: str, cache: dict) -> dict:
    rows = cache.get("recruiting", [])
    players = [r.get("name", "") for r in rows]
    matched = match_player(name, players)
    if not matched:
        return {}
    row = next((r for r in rows if r.get("name") == matched), None)
    if not row:
        return {}
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
                "explosiveness"]:
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
            found = bool(passing or ppa or usage)
            print(f"  {yr}: {'found' if found else 'NOT FOUND'} — "
                  f"att={passing.get('att')}, cmp%={passing.get('pct')}, "
                  f"ppa={ppa.get('ppa_overall')}, expl={usage.get('explosiveness')}")
            season_features.append(merged)

        agg = aggregate_college(season_features)
        recruiting = extract_recruiting(name, cache)
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
    df.to_csv(OUT_PATH, index=False)

    found = df["col_seasons_found"].gt(0).sum()
    print(f"\nMatched {found}/{len(df)} QBs to college data")
    print(f"Saved to {OUT_PATH}")
    print(f"\nFeature columns ({len([c for c in df.columns if c.startswith('col_')])}):")
    print([c for c in df.columns if c.startswith("col_")])


if __name__ == "__main__":
    main()
