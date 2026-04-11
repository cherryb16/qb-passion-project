"""
07_sportradar_college.py

Pull Sportradar NCAAFB v7 player profiles for our 31 cohort QBs.

Pipeline:
  1. For each QB, pull the team's seasonal statistics for their last college year
     → finds Sportradar player ID by name match
     → saves to data/raw/sportradar_player_ids.json
  2. Pull each player's profile (career season-by-season stats including sacks)
     → saves to data/raw/sportradar_profiles.json

Key stat we get that CFBD lacks: sacks allowed per season.

Usage:
  export SPORTRADAR_KEY="your key here"
  python scripts/07_sportradar_college.py
"""

import os
import json
import time
import requests
import pandas as pd

API_KEY = os.environ.get("SPORTRADAR_KEY", "MqMm72mkE1Wtm9mTbsqOoCkb7yrYI90vZp8oCKgW")
BASE    = "https://api.sportradar.com/ncaafb/trial/v7/en"
HEADERS = {"accept": "application/json"}

PLAYER_IDS_PATH = "data/raw/sportradar_player_ids.json"
PROFILES_PATH   = "data/raw/sportradar_profiles.json"

# ---------------------------------------------------------------------------
# Team IDs for our 23 unique colleges (confirmed from sportradar_teams.json)
# ---------------------------------------------------------------------------
COLLEGE_TEAM_IDS = {
    "North Carolina":  "79368b86-8bb0-4c66-8189-b836d039c207",  # UNC Tar Heels
    "Texas Tech":      "22083fa4-8d9c-4ccc-8c33-cda772954099",  # TTU Red Raiders
    "Clemson":         "95404613-f4f0-4280-ac27-85419215f8d1",  # CLEM Tigers
    "Notre Dame":      "d7f19bff-74e7-4b71-a221-12dfeb144fd8",  # ND Fighting Irish
    "Oklahoma":        "242f21d8-7372-4359-a04f-4d467ead22d6",  # OKLA Sooners
    "USC":             "8f496f34-14e3-4ca7-958b-53f6da0b74d6",  # USC Trojans
    "Wyoming":         "a62b2dda-d22c-47bf-ad2c-60c66e64d8c7",  # WYO Cowboys
    "UCLA":            "398eda2b-ba77-469f-94df-18fd1d9087d8",  # UCLA Bruins
    "Louisville":      "1e8edb90-ea5e-4663-9a65-a30e51583711",  # LOU Cardinals
    "Duke":            "deb0920f-c4ca-414d-be4b-ca779e353bf0",  # DUKE Blue Devils
    "Ohio St.":        "9a6d6f3f-021e-4ddd-8fac-ac4766239d87",  # OSU Buckeyes
    "Missouri":        "772536c7-c3e8-40d1-ac6e-232d719dc052",  # MIZZ Tigers
    "Washington St.":  "1ff5428d-2e8c-4b0f-a5a6-ebff126111a2",  # WSU Cougars (Washington State)
    "LSU":             "ffca4209-dbfa-4597-b25a-ed19bb351037",  # LSU Tigers
    "Alabama":         "19775492-f1eb-4bc5-9e15-078ebd689c0f",  # ALA Crimson Tide
    "Oregon":          "5c218a3b-a013-4037-97b6-603c9502b701",  # ORE Ducks
    "BYU":             "627b2e5c-3ba5-496e-9f9b-1c620247c1b7",  # BYU Cougars
    "Stanford":        "7cea6bcb-8ecd-4c92-9b13-31345051ab82",  # STAN Cardinal
    "Pittsburgh":      "a5ef8db1-5d26-4d7e-af22-b21e380c16d2",  # PITT Panthers
    "Cincinnati":      "42a9a18b-b59a-408b-8cab-4e49cbe2c23a",  # CIN Bearcats
    "Iowa St.":        "d335c726-44aa-4b69-8271-59d42d691cba",  # ISU Cyclones
    "Kentucky":        "5941ffa3-cdd5-459b-ab61-fef120b929b2",  # UK Wildcats
    "Purdue":          "485dd62f-108c-4e32-b171-27f5d493552d",  # PUR Boilermakers
}


def get(path: str, pause: float = 1.5) -> dict | None:
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


def name_match(target: str, candidate: str) -> bool:
    """
    Return True if target and candidate refer to the same person.
    Requires both first AND last name to match (handles Tua vs Taulia, etc.)
    Also handles suffixes like 'II' and nickname variants.
    """
    def clean(s):
        return s.lower().replace(".", "").replace("-", " ").split()

    t_parts = clean(target)
    c_parts = clean(candidate)
    suffixes = {"ii", "iii", "iv", "jr", "sr"}

    # Must match last name exactly
    t_last = [p for p in t_parts if p not in suffixes][-1]
    c_last = [p for p in c_parts if p not in suffixes][-1]
    if t_last != c_last:
        return False

    # First name: target first must be a prefix of candidate first (or exact)
    t_first = t_parts[0]
    c_first = c_parts[0]
    return t_first == c_first or t_first.startswith(c_first) or c_first.startswith(t_first)


# ---------------------------------------------------------------------------
# Load QBs from cohort
# ---------------------------------------------------------------------------
cohort = pd.read_csv("data/processed/qb_cohort.csv")
qbs = cohort[["qb_name", "college", "draft_year"]].copy()
qbs["last_col_season"] = qbs["draft_year"] - 1

print(f"Loaded {len(qbs)} QBs from cohort")

# ---------------------------------------------------------------------------
# Load existing caches (resume-friendly)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Step 1: Find player IDs via seasonal team statistics
# ---------------------------------------------------------------------------
print("\n=== STEP 1: Find Player IDs via Seasonal Team Statistics ===")

for _, row in qbs.iterrows():
    qb_name = row["qb_name"]
    college = row["college"]
    season  = int(row["last_col_season"])

    if qb_name in player_ids:
        print(f"  {qb_name} — cached ({player_ids[qb_name]})")
        continue

    team_id = COLLEGE_TEAM_IDS.get(college)
    if not team_id:
        print(f"  {qb_name} ({college}) — NO TEAM ID, skipping")
        continue

    print(f"\n{qb_name} | {college} | season {season}")
    stats_data = get(f"seasons/{season}/REG/teams/{team_id}/statistics.json")
    if stats_data is None:
        print(f"  Failed to get team statistics")
        continue

    players = stats_data.get("players", [])
    print(f"  Players in response: {len(players)}")

    # Find the QB by name
    found_id = None
    for p in players:
        p_name = p.get("name", "")
        if name_match(qb_name, p_name):
            found_id = p["id"]
            print(f"  Matched '{p_name}' → {found_id}")
            break

    if found_id:
        player_ids[qb_name] = found_id
        with open(PLAYER_IDS_PATH, "w") as f:
            json.dump(player_ids, f, indent=2)
    else:
        # Print all QBs on the roster to help debug
        roster_qbs = [p for p in players if p.get("position") == "QB"]
        print(f"  No match. QBs found: {[p.get('name') for p in roster_qbs]}")

print(f"\nPlayer IDs found so far: {len(player_ids)} / {len(qbs)}")

# ---------------------------------------------------------------------------
# Step 2: Pull player profiles (career season stats)
# ---------------------------------------------------------------------------
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
        seasons = profile.get("seasons", [])
        print(f"  Saved — {len(seasons)} seasons in profile")
    else:
        print(f"  Failed")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
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

# Quick stat preview for whoever has a profile
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
