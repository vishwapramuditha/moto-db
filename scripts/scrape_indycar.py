import os
import json
import time
import urllib.request
import urllib.error
import argparse
from datetime import datetime, timezone

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/racing/irl/scoreboard"
USER_AGENT = "MotoDBScraper/1.0 (https://github.com/vishwapramuditha/moto-db)"


def make_request(url):
    """Make HTTP GET request with custom User-Agent and retries."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    retries = 3
    for attempt in range(retries):
        try:
            print(f"Fetching: {url}")
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait_time = (attempt + 1) * 5
                print(f"Rate limited (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code == 404:
                print(f"Not Found (404): {url}")
                return None
            elif e.code == 403:
                print(f"Forbidden (403): {url}")
                return None
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
                if attempt == retries - 1:
                    raise
                time.sleep(2)
        except Exception as e:
            print(f"Error fetching data: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return None


def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_json(path, data):
    """Write dictionary to JSON file."""
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")


def parse_event_schedule(event):
    """Extract schedule-relevant fields from an ESPN event."""
    comp = event.get("competitions", [{}])[0]
    status_info = comp.get("status", {}).get("type", {})

    return {
        "event_id": event.get("id"),
        "name": event.get("name"),
        "short_name": event.get("shortName"),
        "date": event.get("date"),
        "status": status_info.get("name"),
        "status_detail": status_info.get("detail"),
        "completed": status_info.get("completed", False),
        "broadcast": comp.get("broadcast"),
    }


def parse_event_results(event):
    """Extract results from a completed ESPN event."""
    comp = event.get("competitions", [{}])[0]
    status_info = comp.get("status", {}).get("type", {})

    competitors = comp.get("competitors", [])
    results = []
    for c in competitors:
        athlete = c.get("athlete", {})
        flag = athlete.get("flag", {})
        results.append({
            "position": c.get("order"),
            "winner": c.get("winner", False),
            "driver_id": c.get("id"),
            "driver_name": athlete.get("fullName", ""),
            "driver_short_name": athlete.get("shortName", ""),
            "nationality": flag.get("alt", ""),
        })

    # Sort by finishing position (coerce None to 999 to push unknowns to end)
    results.sort(key=lambda x: x.get("position") or 999)

    return {
        "season": str(event.get("season", {}).get("year", "")),
        "event_id": event.get("id"),
        "name": event.get("name"),
        "date": event.get("date"),
        "status": status_info.get("name"),
        "status_detail": status_info.get("detail"),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
    }


def scrape_season(dest_dir, year):
    """Scrape IndyCar schedule and results for a given season year."""
    print(f"\n--- Scraping IndyCar season {year} ---")

    url = f"{ESPN_BASE}?dates={year}"
    data = make_request(url)
    if not data:
        print(f"No data returned for {year}")
        return

    events = data.get("events", [])
    if not events:
        print(f"No events found for {year}")
        return

    print(f"Found {len(events)} events for {year}")

    # Build schedule
    schedule_races = []
    for event in events:
        schedule_races.append(parse_event_schedule(event))

    schedule_output = {
        "season": str(year),
        "total_races": len(schedule_races),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "races": schedule_races,
    }
    write_json(os.path.join(dest_dir, str(year), "schedule.json"), schedule_output)

    # Scrape results for completed races
    today = datetime.now(timezone.utc).date()
    for event in events:
        event_id = event.get("id")
        event_name = event.get("name")
        comp = event.get("competitions", [{}])[0]
        status_name = comp.get("status", {}).get("type", {}).get("name", "")

        # Parse event date to check if it has occurred
        event_date_str = event.get("date", "")
        if not event_date_str:
            continue

        try:
            event_date = datetime.fromisoformat(
                event_date_str.replace("Z", "+00:00")
            ).date()
        except ValueError:
            print(f"Invalid date format '{event_date_str}' for event {event_id}")
            continue

        if status_name == "STATUS_FINAL" or (
            event_date <= today and status_name != "STATUS_SCHEDULED"
        ):
            print(f"Extracting results for {event_name} (ID: {event_id})...")
            results_output = parse_event_results(event)
            write_json(
                os.path.join(dest_dir, str(year), f"results_{event_id}.json"),
                results_output,
            )


def main():
    parser = argparse.ArgumentParser(
        description="Scrape IndyCar database from ESPN scoreboard API"
    )
    parser.add_argument(
        "--years",
        type=str,
        help="Comma-separated list of years to scrape (e.g. 2024,2025)",
    )
    parser.add_argument(
        "--all-time",
        action="store_true",
        help="Scrape all historical years (2008 to current)",
    )
    args = parser.parse_args()

    dest_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "indycar"
    )

    current_year = datetime.now().year

    # Determine years to scrape
    if args.all_time:
        years = list(range(2008, current_year + 1))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        # Default to current year
        years = [current_year]

    print(f"Target years for schedule & results: {years}")
    for year in years:
        scrape_season(dest_dir, year)
        time.sleep(1.0)

    print("\nIndyCar scraping completed!")


if __name__ == "__main__":
    main()
