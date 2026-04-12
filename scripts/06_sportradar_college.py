"""
06_sportradar_college.py

Pull Sportradar NCAAFB v7 player profiles for cohort QBs.

Pipeline:
  1. Load all NCAAFB teams from Sportradar → build college-name → team-ID map
     dynamically (no hardcoded IDs)
  2. For each QB, pull seasonal team statistics to find their Sportradar player ID
  3. Pull each player's profile (career season stats including sacks allowed)
  4. Write data/raw/sportradar_profiles.json

Key stat we get that CFBD lacks: sacks allowed per season.

Usage:
  Set SPORTRADAR_KEY in .env.local (or export it), then:
  python scripts/06_sportradar_college.py
"""

import os
import json
import time
import requests
import pandas as pd
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Config — load key from .env.local so it never touches source control
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

API_KEY = os.environ.get("SPORTRADAR_KEY", "")
BASE    = "https://api.sportradar.com/ncaafb/trial/v7/en"
HEADERS = {"accept": "application/json"}

COHORT_PATH      = "data/processed/qb_cohort.csv"
TEAMS_CACHE_PATH = "data/raw/sportradar_teams.json"
PLAYER_IDS_PATH  = "data/raw/sportradar_player_ids.json"
PROFILES_PATH    = "data/raw/sportradar_profiles.json"


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def get(path: str, pause: float = 1.5) -> dict | None:
    if not API_KEY:
        raise ValueError("Set SPORTRADAR_KEY in .env.local or as an env var")
    url = f"{BASE}/{path}?api_key={API_KEY}"
    print(f"  GET {path}")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 429:
        print("  Rate limited — waiting 10s")
        time.sleep(10)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  Retry status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Error: {resp.text[:300]}")
        return None
    time.sleep(pause)
    return resp.json()


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

def name_match(target: str, candidate: str) -> bool:
    """True if target and candidate refer to the same person."""
    def clean(s):
        return s.lower().replace(".", "").replace("-", " ").split()

    suffixes = {"ii", "iii", "iv", "jr", "sr"}
    t_parts = clean(target)
    c_parts = clean(candidate)

    t_last = [p for p in t_parts if p not in suffixes][-1]
    c_last = [p for p in c_parts if p not in suffixes][-1]
    if t_last != c_last:
        return False

    t_first = t_parts[0]
    c_first = c_parts[0]
    return t_first == c_first or t_first.startswith(c_first) or c_first.startswith(t_first)


def fuzzy_team_match(college: str, team_names: list[str], threshold: int = 75) -> str | None:
    """Find the best Sportradar team name for a college string."""
    result = max(team_names, key=lambda t: fuzz.token_sort_ratio(college.lower(), t.lower()), default=None)
    if result and fuzz.token_sort_ratio(college.lower(), result.lower()) >= threshold:
        return result
    return None


# ---------------------------------------------------------------------------
# Team ID resolution — dynamic, no hardcoding
# ---------------------------------------------------------------------------

def load_team_map() -> dict[str, str]:
    """
    Return {college_name: sportradar_team_id} for all NCAAFB teams.
    Builds from cached hierarchy file if present, otherwise fetches from API.
    Indexes by market name (e.g. "LSU"), team nickname, and "market nickname"
    so fuzzy matching can find any college string.
    """
    # Re-parse from the raw hierarchy file every time (it's local, fast)
    raw_path = TEAMS_CACHE_PATH.replace(".json", "_raw.json")

    if not os.path.exists(raw_path):
        print("Fetching NCAAFB team list from Sportradar...")
        data = get("league/hierarchy.json", pause=1.5)
        if not data:
            print("  WARNING: could not fetch team hierarchy — team IDs unavailable")
            return {}
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2)
    else:
        with open(raw_path) as f:
            data = json.load(f)

    team_map: dict[str, str] = {}

    # The API returns either a nested hierarchy or a flat teams list
    flat_teams = data.get("teams", [])
    nested_confs = data.get("conferences", [])

    if flat_teams:
        # Flat format: {"league": {...}, "teams": [...]}
        for team in flat_teams:
            _index_team(team, team_map)
    elif nested_confs:
        # Nested format: conferences → divisions → teams
        for conf in nested_confs:
            for div in conf.get("divisions", []):
                for team in div.get("teams", []):
                    _index_team(team, team_map)

    # Sportradar NCAAFB hierarchy: divisions → conferences → teams
    for div in data.get("divisions", []):
        for conf in div.get("conferences", []):
            for team in conf.get("teams", []):
                _index_team(team, team_map)

    with open(TEAMS_CACHE_PATH, "w") as f:
        json.dump(team_map, f, indent=2)
    print(f"  Indexed {len(team_map)} team name variants")
    return team_map


def _index_team(team: dict, team_map: dict[str, str]) -> None:
    """Add all useful name variants for a team to team_map."""
    tid    = team.get("id", "")
    name   = team.get("name", "")    # e.g. "Tigers"
    market = team.get("market", "")  # e.g. "LSU"
    alias  = team.get("alias", "")   # e.g. "LSU"
    if not tid:
        return
    for key in [market, name, alias, f"{market} {name}"]:
        if key and key not in team_map:
            team_map[key] = tid


# PFR uses abbreviated names that fuzzy matching may mis-resolve — map them explicitly
_COLLEGE_ALIASES: dict[str, str] = {
    "North Carolina St.": "NC State",
    "North Dakota St.":   "North Dakota State",
    "South Carolina St.": "South Carolina State",
    "Western Kentucky":   "Western Kentucky",
    "Washington St.":     "Washington State",
    "Oklahoma St.":       "Oklahoma State",
    "Iowa St.":           "Iowa State",
    "Ohio St.":           "Ohio State",
    "Mississippi St.":    "Mississippi State",
    "Penn St.":           "Penn State",
    "Florida St.":        "Florida State",
    "Michigan St.":       "Michigan State",
    "Kansas St.":         "Kansas State",
    "Arizona St.":        "Arizona State",
    "Oregon St.":         "Oregon State",
    "Colorado St.":       "Colorado State",
    "San Diego St.":      "San Diego State",
    "Appalachian St.":    "Appalachian State",
    "Boise St.":          "Boise State",
    "Utah St.":           "Utah State",
    "Fresno St.":         "Fresno State",
}


def resolve_team_id(college: str, team_map: dict[str, str]) -> str | None:
    """Return Sportradar team ID for a college name string."""
    # Apply known alias first
    lookup = _COLLEGE_ALIASES.get(college, college)
    # Exact match
    if lookup in team_map:
        return team_map[lookup]
    # Fuzzy match on the resolved name
    matched_name = fuzzy_team_match(lookup, list(team_map.keys()))
    if matched_name:
        print(f"  Fuzzy team match: '{college}' → '{matched_name}'")
        return team_map[matched_name]
    return None


def _find_player_id(qb_name: str, team_id: str, season: int) -> str | None:
    """
    Try two methods to find a Sportradar player ID:
      1. Team season statistics (QB appears if they threw passes)
      2. Team roster (full player list regardless of stats)
    Returns the player ID string or None.
    """
    # Method 1: season statistics
    stats_data = get(f"seasons/{season}/REG/teams/{team_id}/statistics.json")
    if stats_data:
        players = stats_data.get("players", [])
        print(f"  Stats method: {len(players)} players in response")
        for p in players:
            if name_match(qb_name, p.get("name", "")):
                pid = p["id"]
                print(f"  Matched via stats: '{p['name']}' → {pid}")
                return pid
        roster_qbs = [p.get("name") for p in players if p.get("position") == "QB"]
        print(f"  No stats match. QBs listed: {roster_qbs}")

    # Method 2: team roster profile
    roster_data = get(f"teams/{team_id}/profile.json")
    if roster_data:
        players = roster_data.get("players", [])
        print(f"  Roster method: {len(players)} players on roster")
        for p in players:
            if p.get("position") == "QB" and name_match(qb_name, p.get("name", "")):
                pid = p["id"]
                print(f"  Matched via roster: '{p['name']}' → {pid}")
                return pid
        roster_qbs = [p.get("name") for p in players if p.get("position") == "QB"]
        print(f"  No roster match. QBs listed: {roster_qbs}")

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cohort = pd.read_csv(COHORT_PATH)
    qbs = cohort[["qb_name", "college", "draft_year"]].copy()
    qbs["last_col_season"] = qbs["draft_year"] - 1
    print(f"Loaded {len(qbs)} QBs from cohort")

    # Dynamic team map — no hardcoded IDs
    team_map = load_team_map()
    print(f"Team map: {len(team_map)} entries")

    # Load existing caches (resume-friendly)
    try:
        with open(PLAYER_IDS_PATH) as f:
            player_ids: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        player_ids = {}

    try:
        with open(PROFILES_PATH) as f:
            profiles: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        profiles = {}

    print(f"Cached player IDs: {len(player_ids)}  |  Cached profiles: {len(profiles)}")

    # -----------------------------------------------------------------------
    # Step 1: Find player IDs — try team stats first, then roster fallback
    # -----------------------------------------------------------------------
    print("\n=== STEP 1: Find Player IDs ===")

    for _, row in qbs.iterrows():
        qb_name = row["qb_name"]
        college = row["college"]
        season  = int(row["last_col_season"])

        if qb_name in player_ids:
            print(f"  {qb_name} — cached ({player_ids[qb_name]})")
            continue

        team_id = resolve_team_id(college, team_map)
        if not team_id:
            print(f"  {qb_name} ({college}) — no team ID found, skipping")
            continue

        print(f"\n{qb_name} | {college} | season {season}")
        found_id = _find_player_id(qb_name, team_id, season)

        if found_id:
            player_ids[qb_name] = found_id
            with open(PLAYER_IDS_PATH, "w") as f:
                json.dump(player_ids, f, indent=2)
        else:
            print(f"  Could not find player ID via stats or roster")

    print(f"\nPlayer IDs found: {len(player_ids)} / {len(qbs)}")

    # -----------------------------------------------------------------------
    # Step 2: Pull player profiles
    # -----------------------------------------------------------------------
    print("\n=== STEP 2: Pull Player Profiles ===")

    for qb_name, player_id in player_ids.items():
        if qb_name in profiles:
            print(f"  {qb_name} — cached")
            continue

        print(f"\n{qb_name} | {player_id}")
        profile = get(f"players/{player_id}/profile.json")

        if profile:
            profiles[qb_name] = profile
            with open(PROFILES_PATH, "w") as f:
                json.dump(profiles, f, indent=2)
            print(f"  Saved — {len(profile.get('seasons', []))} seasons in profile")
        else:
            print("  Failed")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n=== SUMMARY ===")
    print(f"QBs in cohort:      {len(qbs)}")
    print(f"Player IDs found:   {len(player_ids)}")
    print(f"Profiles fetched:   {len(profiles)}")

    missing_ids = [r["qb_name"] for _, r in qbs.iterrows() if r["qb_name"] not in player_ids]
    if missing_ids:
        print(f"\nMissing IDs ({len(missing_ids)}): {missing_ids}")

    missing_profiles = [n for n in player_ids if n not in profiles]
    if missing_profiles:
        print(f"\nMissing profiles ({len(missing_profiles)}): {missing_profiles}")

    if profiles:
        sample_name = next(iter(profiles))
        sample = profiles[sample_name]
        seasons = sample.get("seasons", [])
        print(f"\nSample — {sample_name} ({len(seasons)} seasons):")
        for s in seasons:
            for t in s.get("teams", []):
                p = t.get("statistics", {}).get("passing", {})
                if p:
                    print(f"  {s['year']}: att={p.get('attempts')} cmp={p.get('completions')} "
                          f"yds={p.get('yards')} td={p.get('touchdowns')} "
                          f"int={p.get('interceptions')} sacks={p.get('sacks')}")


if __name__ == "__main__":
    main()
