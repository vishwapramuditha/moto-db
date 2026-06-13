import os
import json
import time
import urllib.request
import urllib.error
import argparse
from datetime import datetime, timezone

BASE_URL = "https://cf.nascar.com/cacher"
USER_AGENT = "MotoDBScraper/1.0 (https://github.com/vishwapramuditha/moto-db)"

SERIES_MAP = {
    1: "cup",
    2: "xfinity",
    3: "truck"
}

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

def load_json_or_default(path, default):
    """Load JSON from path, return default if file doesn't exist."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return default

def update_global_db(file_path, items_key, new_items, id_key="id"):
    """Merge new items into an existing JSON database by ID to avoid duplicates."""
    db = load_json_or_default(file_path, {items_key: [], "total": 0})
    
    # Index existing items by ID
    existing_map = {item[id_key]: item for item in db.get(items_key, []) if id_key in item}
    
    # Merge new items
    for item in new_items:
        if id_key in item:
            existing_map[item[id_key]] = item
            
    updated_items = list(existing_map.values())
    
    # Sort items for consistency
    if items_key == "tracks":
        updated_items.sort(key=lambda x: x.get("name", ""))
    elif items_key == "drivers":
        updated_items.sort(key=lambda x: x.get("full_name", ""))
        
    db[items_key] = updated_items
    db["total"] = len(updated_items)
    db["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    write_json(file_path, db)

def scrape_drivers(dest_dir):
    """Scrape all NASCAR drivers and save them."""
    print("Scraping drivers...")
    url = f"{BASE_URL}/drivers.json"
    data = make_request(url)
    if not data or "response" not in data:
        print("Failed to fetch drivers data.")
        return
    
    raw_drivers = data.get("response", [])
    cleaned_drivers = []
    for item in raw_drivers:
        driver_id = item.get("Nascar_Driver_ID")
        if not driver_id:
            continue
        cleaned_drivers.append({
            "id": driver_id,
            "first_name": (item.get("First_Name") or "").strip(),
            "last_name": (item.get("Last_Name") or "").strip(),
            "full_name": (item.get("Full_Name") or "").strip(),
            "manufacturer": (item.get("Manufacturer") or "").strip(),
            "team": (item.get("Team") or "").strip(),
            "image": (item.get("Image") or "").strip(),
            "twitter": (item.get("Twitter_Handle") or "").strip()
        })
        
    update_global_db(os.path.join(dest_dir, "drivers.json"), "drivers", cleaned_drivers, id_key="id")

def scrape_tracks(dest_dir):
    """Scrape all NASCAR tracks and save them."""
    print("Scraping tracks...")
    url = f"{BASE_URL}/tracks.json"
    data = make_request(url)
    if not data or "items" not in data:
        print("Failed to fetch tracks data.")
        return
    
    raw_tracks = data.get("items", [])
    cleaned_tracks = []
    for item in raw_tracks:
        track_id = item.get("track_id")
        if not track_id:
            continue
        cleaned_tracks.append({
            "id": track_id,
            "name": (item.get("track_name") or "").strip(),
            "type": (item.get("track_type") or "").strip(),
            "length": item.get("length"),
            "city": (item.get("city") or "").strip(),
            "state": (item.get("state") or "").strip(),
            "image": (item.get("track_image") or "").strip()
        })
        
    update_global_db(os.path.join(dest_dir, "tracks.json"), "tracks", cleaned_tracks, id_key="id")

def scrape_season(dest_dir, year):
    """Scrape schedule and results for a given year."""
    print(f"\n--- Scraping season {year} ---")
    url = f"{BASE_URL}/{year}/race_list_basic.json"
    data = make_request(url)
    if not data:
        print(f"No schedule data found for {year}")
        return
    
    # Save schedule
    schedule_output = {
        "season": str(year),
        "total_races": sum(len(data.get(k, [])) for k in data),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "series": {
            "cup": data.get("series_1", []),
            "xfinity": data.get("series_2", []),
            "truck": data.get("series_3", [])
        }
    }
    write_json(os.path.join(dest_dir, str(year), "schedule.json"), schedule_output)
    
    today = datetime.now(timezone.utc).date()
    
    # Scrape results for races in the past or today
    for s_id, s_name in SERIES_MAP.items():
        races = data.get(f"series_{s_id}", [])
        for race in races:
            race_id = race.get("race_id")
            race_name = race.get("race_name")
            race_date_str = race.get("race_date") or race.get("date_scheduled")
            
            if not race_id or not race_date_str:
                continue
                
            # Parse race date to see if we should fetch results
            # E.g. "2024-02-19T16:00:00"
            try:
                # Take only the date part YYYY-MM-DD
                race_date = datetime.strptime(race_date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                print(f"Invalid date format '{race_date_str}' for race {race_id}")
                continue
                
            # If the race is in the past (or today), fetch results
            if race_date <= today:
                print(f"Scraping results for {year} {s_name} race {race_id} ({race_name})...")
                results_url = f"{BASE_URL}/{year}/{s_id}/{race_id}/lap-times.json"
                time.sleep(0.5)  # Rate limit safety pause
                results_data = make_request(results_url)
                
                if not results_data or "laps" not in results_data:
                    print(f"No results available yet for {year} race {race_id}")
                    continue
                    
                raw_laps = results_data.get("laps", [])
                results_list = []
                for driver_lap in raw_laps:
                    running_pos = driver_lap.get("RunningPos")
                    driver_id = driver_lap.get("NASCARDriverID")
                    if driver_id is None or running_pos is None:
                        continue
                    results_list.append({
                        "position": running_pos,
                        "driver_id": driver_id,
                        "driver_name": (driver_lap.get("FullName") or "").strip(),
                        "car_number": str(driver_lap.get("Number", "")),
                        "manufacturer": (driver_lap.get("Manufacturer") or "").strip()
                    })
                
                # Sort by position
                results_list.sort(key=lambda x: x["position"])
                
                results_output = {
                    "season": str(year),
                    "series_id": s_id,
                    "series_name": s_name,
                    "race_id": race_id,
                    "race_name": race_name,
                    "track_name": race.get("track_name"),
                    "date": race_date_str,
                    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "results": results_list
                }
                
                write_json(
                    os.path.join(dest_dir, str(year), s_name, f"results_{race_id}.json"),
                    results_output
                )

def main():
    parser = argparse.ArgumentParser(description="Scrape NASCAR database from nascar.com cacher API")
    parser.add_argument("--years", type=str, help="Comma-separated list of years to scrape (e.g. 2024,2025)")
    args = parser.parse_args()
    
    dest_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nascar")
    
    # Always scrape global metadata
    scrape_drivers(dest_dir)
    time.sleep(1.0)
    scrape_tracks(dest_dir)
    time.sleep(1.0)
    
    current_year = datetime.now().year
    
    # Determine years to scrape
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        # Default to current year
        years = [current_year]
        
    print(f"Target years for schedule & results: {years}")
    for year in years:
        scrape_season(dest_dir, year)
        time.sleep(1.0)
        
    print("\nScraping completed!")

if __name__ == "__main__":
    main()
