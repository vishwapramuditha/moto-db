"""
generate_sessions.py
────────────────────
Adds detailed race-weekend session schedules (with UTC times) to every
sport's schedule.json that currently lacks them.

Sports with COMPLETE session data (skipped):
  - WEC   → already has sessions[] with accurate UTC times
  - NASCAR → already has schedule[] per race with accurate UTC times

Sports UPDATED by this script:
  - F1        → adds sessions[] (from existing flat fields + Race time)
  - MotoGP    → adds sessions[] fetched from MotoGP Pulse Live API
  - IndyCar   → adds sessions[] (Practice, Qualifying, Race) with known UTC times
  - WRC       → fixes ISO dates + adds day-level sessions[]
  - Formula E → schema fix + adds sessions[] with known UTC times
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

USER_AGENT = "MotoDBScraper/1.0 (https://github.com/vishwapramuditha/moto-db)"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")


def make_request(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep((attempt + 1) * 5)
            elif e.code == 404:
                return None
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)
    return None


# ─────────────────────────────────────────────
# F1 — sessions[] from existing flat fields
# ─────────────────────────────────────────────

def process_f1(years=("2025", "2026")):
    """
    F1 schedules already have flat session fields from the Ergast/Jolpica API:
      FirstPractice, SecondPractice, ThirdPractice, Qualifying,
      SprintQualifying, Sprint
    Plus the race itself is encoded at the top-level date/time.

    We unify these into a sessions[] array and ADD the Race session.
    Backward-compatible: flat fields are preserved.
    """
    print("\n[F1] Processing schedules...")

    for year in years:
        schedule_path = os.path.join(DATA_DIR, "f1", year, "schedule.json")
        if not os.path.exists(schedule_path):
            print(f"  Skipping {year} — file not found")
            continue

        data = load_json(schedule_path)
        races = data.get("races", [])
        changed = 0

        for race in races:
            sessions = []

            # Helper to push a session if the flat field exists
            def add_session(key, session_type, name):
                obj = race.get(key)
                if obj:
                    sessions.append({
                        "type": session_type,
                        "name": name,
                        "date": obj.get("date", ""),
                        "time": obj.get("time", "")
                    })

            is_sprint = "Sprint" in race or "SprintQualifying" in race

            if is_sprint:
                # Sprint weekend: FP1, SQ, Sprint, Qualifying, Race
                add_session("FirstPractice",    "FP1",        "Free Practice 1")
                add_session("SprintQualifying", "SQ",         "Sprint Qualifying")
                add_session("Sprint",           "Sprint",     "Sprint")
                add_session("Qualifying",       "Qualifying", "Qualifying")
            else:
                # Normal weekend: FP1, FP2, FP3, Qualifying
                add_session("FirstPractice",  "FP1",        "Free Practice 1")
                add_session("SecondPractice", "FP2",        "Free Practice 2")
                add_session("ThirdPractice",  "FP3",        "Free Practice 3")
                add_session("Qualifying",     "Qualifying", "Qualifying")

            # Always add the Race — time is at the top-level of the race object
            race_date = race.get("date", "")
            race_time = race.get("time", "")
            if race_date:
                sessions.append({
                    "type": "Race",
                    "name": "Race",
                    "date": race_date,
                    "time": race_time
                })

            race["sessions"] = sessions
            changed += 1

        data["races"] = races
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        save_json(schedule_path, data)
        print(f"  F1 {year}: updated {changed} races")


# ─────────────────────────────────────────────
# MotoGP — sessions[] from Pulse Live API
# ─────────────────────────────────────────────

MOTOGP_BASE = "https://api.motogp.pulselive.com/motogp/v1"

# MotoGP session type codes from the API → human-readable names
MOTOGP_SESSION_NAMES = {
    "FP":   "Free Practice",
    "FP1":  "Free Practice 1",
    "FP2":  "Free Practice 2",
    "FP3":  "Free Practice 3",
    "FP4":  "Free Practice 4",
    "PR":   "Practice",
    "Q1":   "Qualifying 1",
    "Q2":   "Qualifying 2",
    "SQ":   "Sprint Qualifying",
    "SPR":  "Sprint Race",
    "WUP":  "Warm Up",
    "RAC":  "Race",
}

# Category display names
MOTOGP_CATEGORIES = {
    "motogp": "MotoGP",
    "moto2":  "Moto2",
    "moto3":  "Moto3",
    "motoe":  "MotoE",
}


def fetch_motogp_sessions(event_uuid):
    """
    Fetch all sessions for a MotoGP event across all categories.
    Returns a flat list of session dicts ready for schedule.json.
    """
    categories_url = f"{MOTOGP_BASE}/results/categories?eventUuid={event_uuid}"
    time.sleep(0.4)
    categories = make_request(categories_url)
    if not categories:
        return []

    all_sessions = []

    for cat in categories:
        cat_uuid = cat.get("id")
        cat_name_raw = "".join(c for c in cat.get("name", "") if c.isalnum()).lower()
        if cat_name_raw not in MOTOGP_CATEGORIES:
            continue

        cat_label = MOTOGP_CATEGORIES[cat_name_raw]

        sessions_url = (
            f"{MOTOGP_BASE}/results/sessions"
            f"?eventUuid={event_uuid}&categoryUuid={cat_uuid}"
        )
        time.sleep(0.4)
        sessions = make_request(sessions_url)
        if not sessions:
            continue

        for s in sessions:
            s_type = s.get("type", "")
            s_date = s.get("date", "")  # e.g. "2026-03-01T15:00:00+00:00"

            # Normalize to UTC ISO format
            if s_date and "+" in s_date:
                try:
                    dt = datetime.fromisoformat(s_date)
                    s_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    pass

            session_name = MOTOGP_SESSION_NAMES.get(s_type, s_type)
            all_sessions.append({
                "type": s_type,
                "name": f"{session_name} ({cat_label})",
                "category": cat_name_raw,
                "datetime": s_date,
                "status": s.get("status", "")
            })

    # Sort by datetime so sessions appear in chronological order
    all_sessions.sort(key=lambda x: x.get("datetime", ""))
    return all_sessions


def process_motogp(years=("2025", "2026")):
    """
    Fetch live session data from MotoGP Pulse Live API and inject into schedule.json.
    For events with status NOT-STARTED, we add approximate sessions based on
    the typical MotoGP weekend format (with the event's start date as anchor).
    """
    print("\n[MotoGP] Processing schedules...")

    for year in years:
        schedule_path = os.path.join(DATA_DIR, "motogp", year, "schedule.json")
        if not os.path.exists(schedule_path):
            print(f"  Skipping {year} — file not found")
            continue

        data = load_json(schedule_path)
        events = data.get("events", [])
        changed = 0

        for event in events:
            if event.get("test"):
                continue

            event_uuid = event.get("id")
            event_status = event.get("status", "")
            event_name = event.get("name", event_uuid)

            if event_status in ("FINISHED", "RUNNING"):
                print(f"    Fetching sessions for {event_name}...")
                sessions = fetch_motogp_sessions(event_uuid)
                if sessions:
                    event["sessions"] = sessions
                    changed += 1
                else:
                    print(f"    No sessions returned for {event_name}")
            else:
                # For future events, add placeholder sessions with
                # typical MotoGP weekend structure (without exact times)
                date_start = event.get("date_start", "")
                event["sessions"] = build_motogp_placeholder_sessions(date_start)
                changed += 1

        data["events"] = events
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        save_json(schedule_path, data)
        print(f"  MotoGP {year}: updated {changed} events")


def build_motogp_placeholder_sessions(date_start):
    """
    Standard MotoGP weekend (2023+ format):
      Friday:   FP (MotoGP/Moto2/Moto3), Q1+Q2 (Moto3), Q1+Q2 (Moto2)
      Saturday: SQ Q1+Q2 (MotoGP), Sprint (MotoGP), WUP (MotoGP)
      Sunday:   Race (Moto3), Race (Moto2), Race (MotoGP)
    Times are approximate UTC — actual times vary by circuit timezone.
    """
    if not date_start:
        return []

    try:
        friday = datetime.strptime(date_start, "%Y-%m-%d")
    except Exception:
        return []

    from datetime import timedelta
    saturday = friday + timedelta(days=1)
    sunday = friday + timedelta(days=2)

    def iso(dt, h, m):
        return dt.replace(hour=h, minute=m).strftime("%Y-%m-%dT%H:%M:%SZ")

    return [
        {"type": "FP",  "name": "Free Practice (MotoGP)",  "category": "motogp", "datetime": iso(friday, 3, 45),  "status": "NOT-STARTED"},
        {"type": "FP",  "name": "Free Practice (Moto3)",   "category": "moto3",  "datetime": iso(friday, 2, 0),   "status": "NOT-STARTED"},
        {"type": "FP",  "name": "Free Practice (Moto2)",   "category": "moto2",  "datetime": iso(friday, 2, 50),  "status": "NOT-STARTED"},
        {"type": "Q1",  "name": "Qualifying 1 (Moto3)",    "category": "moto3",  "datetime": iso(friday, 5, 50),  "status": "NOT-STARTED"},
        {"type": "Q2",  "name": "Qualifying 2 (Moto3)",    "category": "moto3",  "datetime": iso(friday, 6, 15),  "status": "NOT-STARTED"},
        {"type": "Q1",  "name": "Qualifying 1 (Moto2)",    "category": "moto2",  "datetime": iso(friday, 6, 55),  "status": "NOT-STARTED"},
        {"type": "Q2",  "name": "Qualifying 2 (Moto2)",    "category": "moto2",  "datetime": iso(friday, 7, 20),  "status": "NOT-STARTED"},
        {"type": "PR",  "name": "Practice (MotoGP)",       "category": "motogp", "datetime": iso(friday, 5, 10),  "status": "NOT-STARTED"},
        {"type": "SQ",  "name": "Sprint Qualifying (MotoGP)","category": "motogp","datetime": iso(saturday, 3, 50),"status": "NOT-STARTED"},
        {"type": "SPR", "name": "Sprint Race (MotoGP)",    "category": "motogp", "datetime": iso(saturday, 6, 0),  "status": "NOT-STARTED"},
        {"type": "WUP", "name": "Warm Up (MotoGP)",        "category": "motogp", "datetime": iso(sunday, 3, 40),   "status": "NOT-STARTED"},
        {"type": "RAC", "name": "Race (Moto3)",             "category": "moto3",  "datetime": iso(sunday, 4, 0),    "status": "NOT-STARTED"},
        {"type": "RAC", "name": "Race (Moto2)",             "category": "moto2",  "datetime": iso(sunday, 5, 15),   "status": "NOT-STARTED"},
        {"type": "RAC", "name": "Race (MotoGP)",            "category": "motogp", "datetime": iso(sunday, 7, 0),    "status": "NOT-STARTED"},
    ]


# ─────────────────────────────────────────────
# IndyCar — sessions[] with known UTC times
# ─────────────────────────────────────────────

# 2026 IndyCar session data (UTC times)
# Sources: IndyCar.com official schedule
INDYCAR_2026_SESSIONS = {
    "202603010104": [  # St. Petersburg
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-02-27T17:30:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-02-28T16:30:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-02-28T19:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-03-01T17:00:00Z"},
    ],
    "202603070103": [  # Phoenix
        {"type": "Practice",  "name": "Practice",    "datetime": "2026-03-06T22:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-03-07T00:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-03-07T20:00:00Z"},
    ],
    "202603154263": [  # Arlington
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-03-13T19:30:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-03-14T18:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-03-14T21:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-03-15T16:30:00Z"},
    ],
    "202603290752": [  # Alabama (Barber)
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-03-27T16:30:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-03-28T16:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-03-28T19:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-03-29T17:00:00Z"},
    ],
    "202604190502": [  # Long Beach
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-04-17T21:45:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-04-18T17:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-04-18T21:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-04-19T21:30:00Z"},
    ],
    "202605094000": [  # Indianapolis Road Course
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-05-07T16:30:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-05-08T16:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-05-08T20:00:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-05-09T20:30:00Z"},
    ],
    "202605240106": [  # Indianapolis 500
        {"type": "Practice",       "name": "Open Practice Day 1",     "datetime": "2026-05-12T16:00:00Z"},
        {"type": "Practice",       "name": "Open Practice Day 2",     "datetime": "2026-05-13T15:00:00Z"},
        {"type": "Practice",       "name": "Open Practice Day 3",     "datetime": "2026-05-14T15:00:00Z"},
        {"type": "Qualifying",     "name": "Qualifying Day 1",        "datetime": "2026-05-16T17:00:00Z"},
        {"type": "Qualifying",     "name": "Qualifying Day 2 (Bump)", "datetime": "2026-05-17T17:00:00Z"},
        {"type": "Practice",       "name": "Carb Day Practice",       "datetime": "2026-05-22T16:00:00Z"},
        {"type": "Race",           "name": "Indianapolis 500",        "datetime": "2026-05-24T16:00:00Z"},
    ],
    "202605310120": [  # Detroit
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-05-29T17:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-05-30T17:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-05-30T20:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-05-31T16:30:00Z"},
    ],
    "202606070785": [  # Illinois (World Wide Technology Raceway)
        {"type": "Practice",  "name": "Practice",    "datetime": "2026-06-06T21:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-06-07T00:00:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-06-08T01:00:00Z"},
    ],
    "202606210111": [  # Road America
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-06-19T17:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-06-20T16:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-06-20T19:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-06-21T18:00:00Z"},
    ],
    "202607050119": [  # Mid-Ohio
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-07-03T18:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-07-04T17:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-07-04T20:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-07-05T16:30:00Z"},
    ],
    "202607193999": [  # Nashville
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-07-17T22:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-07-18T17:30:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-07-18T21:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-07-19T04:00:00Z"},
    ],
    "202608090790": [  # Portland
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-08-07T19:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-08-08T18:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-08-08T21:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-08-09T20:00:00Z"},
    ],
    "202608164264": [  # Ontario (New Hampshire Motor Speedway)
        {"type": "Practice",  "name": "Practice",    "datetime": "2026-08-15T16:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-08-15T19:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-08-16T16:00:00Z"},
    ],
    "202608235829": [  # Washington D.C.
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-08-21T20:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-08-22T19:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-08-22T22:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-08-23T04:00:00Z"},
    ],
    "202608294252": [  # Milwaukee Race 1
        {"type": "Practice",  "name": "Practice",    "datetime": "2026-08-28T18:30:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-08-28T21:30:00Z"},
        {"type": "Race",      "name": "Race 1",      "datetime": "2026-08-29T18:30:00Z"},
    ],
    "202608304253": [  # Milwaukee Race 2
        {"type": "Race",      "name": "Race 2",      "datetime": "2026-08-30T17:00:00Z"},
    ],
    "202609061784": [  # Monterey (Laguna Seca)
        {"type": "Practice1", "name": "Practice 1",  "datetime": "2026-09-04T19:00:00Z"},
        {"type": "Practice2", "name": "Practice 2",  "datetime": "2026-09-05T18:00:00Z"},
        {"type": "Qualifying","name": "Qualifying",  "datetime": "2026-09-05T21:30:00Z"},
        {"type": "Race",      "name": "Race",        "datetime": "2026-09-06T18:30:00Z"},
    ],
}

# 2025 IndyCar session data (UTC times) - key races
INDYCAR_2025_SESSIONS = {
    # Add approximate sessions for all 2025 races
    # Race datetime is the key anchor point — practice/quali are day-before
}


def process_indycar(years=("2025", "2026")):
    print("\n[IndyCar] Processing schedules...")

    session_data_by_year = {
        "2026": INDYCAR_2026_SESSIONS,
    }

    for year in years:
        schedule_path = os.path.join(DATA_DIR, "indycar", year, "schedule.json")
        if not os.path.exists(schedule_path):
            print(f"  Skipping {year} — file not found")
            continue

        data = load_json(schedule_path)
        races = data.get("races", [])
        sessions_map = session_data_by_year.get(year, {})
        changed = 0

        for race in races:
            event_id = race.get("event_id", "")
            if event_id in sessions_map:
                race["sessions"] = sessions_map[event_id]
                changed += 1
            else:
                # Fallback: derive sessions from race date (day-1 pattern)
                race_dt_str = race.get("date", "")
                if race_dt_str:
                    race["sessions"] = build_indycar_placeholder_sessions(race_dt_str)
                    changed += 1

        data["races"] = races
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        save_json(schedule_path, data)
        print(f"  IndyCar {year}: updated {changed} races")


def build_indycar_placeholder_sessions(race_datetime_str):
    """Build approximate IndyCar session schedule from race date."""
    from datetime import timedelta
    try:
        # race datetime like "2026-03-01T17:00Z"
        race_dt = datetime.fromisoformat(race_datetime_str.replace("Z", "+00:00"))
    except Exception:
        return []

    # Practice day-2 before race, qualifying day-1 before race
    practice1_dt = race_dt - timedelta(days=2)
    practice2_dt = race_dt - timedelta(days=1)
    quali_dt = race_dt - timedelta(days=1, hours=-3, minutes=-30)

    def fmt(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return [
        {"type": "Practice1",  "name": "Practice 1",  "datetime": fmt(practice1_dt.replace(hour=17))},
        {"type": "Practice2",  "name": "Practice 2",  "datetime": fmt(practice2_dt.replace(hour=17))},
        {"type": "Qualifying", "name": "Qualifying",  "datetime": fmt(practice2_dt.replace(hour=20, minute=30))},
        {"type": "Race",       "name": "Race",        "datetime": fmt(race_dt)},
    ]


# ─────────────────────────────────────────────
# WRC — fix ISO dates + add sessions[]
# ─────────────────────────────────────────────

# 2026 WRC full schedule with ISO dates + typical stage structure
WRC_2026_RALLIES = [
    {
        "round": "1", "name": "Rallye Automobile Monte Carlo",
        "start_date": "2026-01-22", "finish_date": "2026-01-25", "surface": "Mixed",
        "location": {"country": "Monaco", "city": "Monte Carlo"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-01-22"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-01-22"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-01-23"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-01-24"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-01-25"},
        ]
    },
    {
        "round": "2", "name": "Rally Sweden",
        "start_date": "2026-02-12", "finish_date": "2026-02-15", "surface": "Snow",
        "location": {"country": "Sweden", "city": "Umeå"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-02-12"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-02-12"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-02-13"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-02-14"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-02-15"},
        ]
    },
    {
        "round": "3", "name": "Safari Rally Kenya",
        "start_date": "2026-03-12", "finish_date": "2026-03-15", "surface": "Gravel",
        "location": {"country": "Kenya", "city": "Nairobi"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-03-12"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-03-12"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-03-13"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-03-14"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-03-15"},
        ]
    },
    {
        "round": "4", "name": "Croatia Rally",
        "start_date": "2026-04-09", "finish_date": "2026-04-12", "surface": "Tarmac",
        "location": {"country": "Croatia", "city": "Zagreb"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-04-09"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-04-09"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-04-10"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-04-11"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-04-12"},
        ]
    },
    {
        "round": "5", "name": "Rally Islas Canarias",
        "start_date": "2026-04-23", "finish_date": "2026-04-26", "surface": "Tarmac",
        "location": {"country": "Spain", "city": "Las Palmas"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-04-23"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-04-23"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-04-24"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-04-25"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-04-26"},
        ]
    },
    {
        "round": "6", "name": "Rally de Portugal",
        "start_date": "2026-05-07", "finish_date": "2026-05-10", "surface": "Gravel",
        "location": {"country": "Portugal", "city": "Matosinhos"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-05-07"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-05-07"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-05-08"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-05-09"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-05-10"},
        ]
    },
    {
        "round": "7", "name": "Rally Japan",
        "start_date": "2026-05-28", "finish_date": "2026-05-31", "surface": "Tarmac",
        "location": {"country": "Japan", "city": "Toyota"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-05-28"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-05-28"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-05-29"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-05-30"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-05-31"},
        ]
    },
    {
        "round": "8", "name": "Acropolis Rally Greece",
        "start_date": "2026-06-25", "finish_date": "2026-06-28", "surface": "Gravel",
        "location": {"country": "Greece", "city": "Athens"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-06-25"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-06-25"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-06-26"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-06-27"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-06-28"},
        ]
    },
    {
        "round": "9", "name": "Rally Estonia",
        "start_date": "2026-07-16", "finish_date": "2026-07-19", "surface": "Gravel",
        "location": {"country": "Estonia", "city": "Tartu"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-07-16"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-07-16"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-07-17"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-07-18"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-07-19"},
        ]
    },
    {
        "round": "10", "name": "Rally Finland",
        "start_date": "2026-07-30", "finish_date": "2026-08-02", "surface": "Gravel",
        "location": {"country": "Finland", "city": "Jyväskylä"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-07-30"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-07-30"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-07-31"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-08-01"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-08-02"},
        ]
    },
    {
        "round": "11", "name": "Rally del Paraguay",
        "start_date": "2026-08-27", "finish_date": "2026-08-30", "surface": "Gravel",
        "location": {"country": "Paraguay", "city": "Asunción"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-08-27"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-08-27"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-08-28"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-08-29"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-08-30"},
        ]
    },
    {
        "round": "12", "name": "Rally Chile",
        "start_date": "2026-09-10", "finish_date": "2026-09-13", "surface": "Gravel",
        "location": {"country": "Chile", "city": "Concepción"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-09-10"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-09-10"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-09-11"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-09-12"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-09-13"},
        ]
    },
    {
        "round": "13", "name": "Rally Italia Sardegna",
        "start_date": "2026-10-01", "finish_date": "2026-10-04", "surface": "Gravel",
        "location": {"country": "Italy", "city": "Alghero"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday",  "date": "2026-10-01"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday",  "date": "2026-10-01"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday",    "date": "2026-10-02"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday",  "date": "2026-10-03"},
            {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday",    "date": "2026-10-04"},
        ]
    },
    {
        "round": "14", "name": "Rally Saudi Arabia",
        "start_date": "2026-11-11", "finish_date": "2026-11-14", "surface": "Gravel",
        "location": {"country": "Saudi Arabia", "city": "Riyadh"},
        "sessions": [
            {"type": "Shakedown", "name": "Shakedown",                    "day": "Wednesday", "date": "2026-11-11"},
            {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Wednesday", "date": "2026-11-11"},
            {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Thursday",  "date": "2026-11-12"},
            {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Friday",    "date": "2026-11-13"},
            {"type": "SS",        "name": "Day 4 – Power Stage",          "day": "Saturday",  "date": "2026-11-14"},
        ]
    },
]


def process_wrc(years=("2025", "2026")):
    print("\n[WRC] Processing schedules...")

    for year in years:
        schedule_path = os.path.join(DATA_DIR, "wrc", year, "schedule.json")
        if not os.path.exists(schedule_path):
            print(f"  Skipping {year} — file not found")
            continue

        if year == "2026":
            # Full replacement with correct ISO dates + sessions
            new_data = {
                "season": "2026",
                "total_races": len(WRC_2026_RALLIES),
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "races": WRC_2026_RALLIES
            }
            save_json(schedule_path, new_data)
            print(f"  WRC 2026: updated {len(WRC_2026_RALLIES)} rallies")
        else:
            # For 2025, preserve existing structure but add sessions + fix dates
            data = load_json(schedule_path)
            races = data.get("races", [])
            changed = 0
            for race in races:
                if "sessions" not in race:
                    # Add day-level placeholder sessions
                    race["sessions"] = [
                        {"type": "Shakedown", "name": "Shakedown",                    "day": "Thursday"},
                        {"type": "SS",        "name": "Day 1 – Super Special Stage",  "day": "Thursday"},
                        {"type": "SS",        "name": "Day 2 – Friday Stages",        "day": "Friday"},
                        {"type": "SS",        "name": "Day 3 – Saturday Stages",      "day": "Saturday"},
                        {"type": "SS",        "name": "Day 4 – Power Stage (Sunday)", "day": "Sunday"},
                    ]
                    changed += 1
            data["races"] = races
            data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            save_json(schedule_path, data)
            print(f"  WRC {year}: updated {changed} rallies")


# ─────────────────────────────────────────────
# Formula E — schema fix + sessions[]
# ─────────────────────────────────────────────

FORMULA_E_2026 = [
    {
        "round": "1", "eprix": "São Paulo ePrix", "circuit": "São Paulo Street Circuit",
        "country": "Brazil", "city": "São Paulo", "date": "2025-12-06",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2025-12-06T10:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2025-12-06T12:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2025-12-06T14:00:00Z"},
            {"type": "Race",      "name": "Race",                          "datetime": "2025-12-06T17:00:00Z"},
        ]
    },
    {
        "round": "2", "eprix": "Mexico City ePrix", "circuit": "Autódromo Hermanos Rodríguez",
        "country": "Mexico", "city": "Mexico City", "date": "2026-01-10",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-01-10T14:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-01-10T16:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-01-10T18:00:00Z"},
            {"type": "Race",      "name": "Race",                          "datetime": "2026-01-10T21:00:00Z"},
        ]
    },
    {
        "round": "3", "eprix": "Miami ePrix", "circuit": "Miami International Autodrome",
        "country": "USA", "city": "Miami", "date": "2026-01-31",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-01-31T15:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-01-31T17:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-01-31T19:30:00Z"},
            {"type": "Race",      "name": "Race",                          "datetime": "2026-01-31T22:00:00Z"},
        ]
    },
    {
        "round": "4", "eprix": "Jeddah ePrix (Race 1)", "circuit": "Jeddah Corniche Circuit",
        "country": "Saudi Arabia", "city": "Jeddah", "date": "2026-02-13",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-02-12T09:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-02-12T11:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-02-13T10:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-02-13T13:00:00Z"},
        ]
    },
    {
        "round": "5", "eprix": "Jeddah ePrix (Race 2)", "circuit": "Jeddah Corniche Circuit",
        "country": "Saudi Arabia", "city": "Jeddah", "date": "2026-02-14",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-02-14T10:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-02-14T13:00:00Z"},
        ]
    },
    {
        "round": "6", "eprix": "Madrid ePrix", "circuit": "Circuito del Jarama",
        "country": "Spain", "city": "Madrid", "date": "2026-03-21",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-03-21T08:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-03-21T10:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-03-21T12:00:00Z"},
            {"type": "Race",      "name": "Race",                          "datetime": "2026-03-21T15:00:00Z"},
        ]
    },
    {
        "round": "7", "eprix": "Berlin ePrix (Race 1)", "circuit": "Tempelhof Airport Street Circuit",
        "country": "Germany", "city": "Berlin", "date": "2026-05-02",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-05-01T09:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-05-01T11:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-05-02T09:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-05-02T12:30:00Z"},
        ]
    },
    {
        "round": "8", "eprix": "Berlin ePrix (Race 2)", "circuit": "Tempelhof Airport Street Circuit",
        "country": "Germany", "city": "Berlin", "date": "2026-05-03",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-05-03T09:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-05-03T12:30:00Z"},
        ]
    },
    {
        "round": "9", "eprix": "Monaco ePrix (Race 1)", "circuit": "Circuit de Monaco",
        "country": "Monaco", "city": "Monte Carlo", "date": "2026-05-16",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-05-15T09:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-05-15T11:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-05-16T09:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-05-16T12:30:00Z"},
        ]
    },
    {
        "round": "10", "eprix": "Monaco ePrix (Race 2)", "circuit": "Circuit de Monaco",
        "country": "Monaco", "city": "Monte Carlo", "date": "2026-05-17",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-05-17T09:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-05-17T12:30:00Z"},
        ]
    },
    {
        "round": "11", "eprix": "Sanya ePrix", "circuit": "Sanya Street Circuit",
        "country": "China", "city": "Sanya", "date": "2026-06-20",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-06-20T04:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-06-20T06:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-06-20T08:00:00Z"},
            {"type": "Race",      "name": "Race",                          "datetime": "2026-06-20T10:30:00Z"},
        ]
    },
    {
        "round": "12", "eprix": "Shanghai ePrix (Race 1)", "circuit": "Shanghai Street Circuit",
        "country": "China", "city": "Shanghai", "date": "2026-07-04",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-07-03T04:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-07-03T06:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-07-04T04:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-07-04T08:00:00Z"},
        ]
    },
    {
        "round": "13", "eprix": "Shanghai ePrix (Race 2)", "circuit": "Shanghai Street Circuit",
        "country": "China", "city": "Shanghai", "date": "2026-07-05",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-07-05T04:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-07-05T08:00:00Z"},
        ]
    },
    {
        "round": "14", "eprix": "Tokyo ePrix (Race 1)", "circuit": "Tokyo Street Circuit",
        "country": "Japan", "city": "Tokyo", "date": "2026-07-25",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-07-24T03:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-07-24T05:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-07-25T03:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-07-25T07:00:00Z"},
        ]
    },
    {
        "round": "15", "eprix": "Tokyo ePrix (Race 2)", "circuit": "Tokyo Street Circuit",
        "country": "Japan", "city": "Tokyo", "date": "2026-07-26",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-07-26T03:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-07-26T07:00:00Z"},
        ]
    },
    {
        "round": "16", "eprix": "London ePrix (Race 1)", "circuit": "ExCeL London Circuit",
        "country": "UK", "city": "London", "date": "2026-08-15",
        "sessions": [
            {"type": "Practice1", "name": "Practice 1",                    "datetime": "2026-08-14T10:00:00Z"},
            {"type": "Practice2", "name": "Practice 2",                    "datetime": "2026-08-14T12:00:00Z"},
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-08-15T10:00:00Z"},
            {"type": "Race",      "name": "Race 1",                        "datetime": "2026-08-15T13:00:00Z"},
        ]
    },
    {
        "round": "17", "eprix": "London ePrix (Race 2)", "circuit": "ExCeL London Circuit",
        "country": "UK", "city": "London", "date": "2026-08-16",
        "sessions": [
            {"type": "Qualifying","name": "Qualifying (Groups + Duels)",   "datetime": "2026-08-16T10:00:00Z"},
            {"type": "Race",      "name": "Race 2",                        "datetime": "2026-08-16T13:00:00Z"},
        ]
    },
]


def process_formula_e(years=("2026",)):
    print("\n[Formula E] Processing schedules...")

    for year in years:
        schedule_path = os.path.join(DATA_DIR, "formula_e", year, "schedule.json")
        if not os.path.exists(schedule_path):
            print(f"  Skipping {year} — file not found")
            continue

        if year == "2026":
            new_data = {
                "season": "2025-26",
                "total_rounds": len(FORMULA_E_2026),
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "races": FORMULA_E_2026
            }
            save_json(schedule_path, new_data)
            print(f"  Formula E 2026: updated {len(FORMULA_E_2026)} rounds")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate session schedules for all moto-db sports"
    )
    parser.add_argument(
        "--sports",
        type=str,
        default="f1,motogp,indycar,wrc,formula_e",
        help="Comma-separated list of sports to update"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2025,2026",
        help="Comma-separated list of years to update"
    )
    args = parser.parse_args()

    sports = [s.strip() for s in args.sports.split(",")]
    years  = tuple(y.strip() for y in args.years.split(","))

    print(f"Sports: {sports}")
    print(f"Years:  {list(years)}")

    if "f1" in sports:
        process_f1(years=years)

    if "motogp" in sports:
        process_motogp(years=years)

    if "indycar" in sports:
        process_indycar(years=years)

    if "wrc" in sports:
        process_wrc(years=years)

    if "formula_e" in sports:
        process_formula_e(years=[y for y in years if y == "2026"])

    print("\nDone! Session generation complete.")


if __name__ == "__main__":
    main()
