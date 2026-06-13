import os
import json
import time
import urllib.request
import urllib.error
import argparse
from datetime import datetime

BASE_URL = "https://api.motogp.pulselive.com/motogp/v1"
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

def clean_name(name):
    """Clean category names like MotoGP™ -> motogp."""
    return "".join(c for c in name if c.isalnum()).lower()

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
    
    # Sort items for consistency (e.g. by name or year)
    if items_key == "tracks":
        updated_items.sort(key=lambda x: x.get("name", ""))
    elif items_key == "drivers":
        updated_items.sort(key=lambda x: x.get("full_name", ""))
        
    db[items_key] = updated_items
    db["total"] = len(updated_items)
    db["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    write_json(file_path, db)

def main():
    parser = argparse.ArgumentParser(description="Scrape MotoGP database from Pulse Live API")
    parser.add_argument("--years", type=str, help="Comma-separated list of years to scrape (e.g. 2024,2025)")
    args = parser.parse_args()
    
    dest_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "motogp")
    drivers_path = os.path.join(dest_dir, "drivers.json")
    tracks_path = os.path.join(dest_dir, "tracks.json")
    
    # 1. Fetch seasons to map year to season UUID
    print("Fetching MotoGP seasons...")
    seasons_url = f"{BASE_URL}/results/seasons"
    seasons_data = make_request(seasons_url)
    if not seasons_data:
        print("Failed to fetch seasons.")
        return
        
    current_year = datetime.now().year
    target_years = [current_year]
    if args.years:
        target_years = [int(y.strip()) for y in args.years.split(",")]
        
    # Map target years to season UUIDs
    year_to_uuid = {}
    for season in seasons_data:
        yr = season.get("year")
        if yr in target_years:
            year_to_uuid[yr] = season.get("id")
            
    print(f"Targeting years: {list(year_to_uuid.keys())}")
    
    discovered_riders = []
    discovered_tracks = []
    
    for year, season_uuid in year_to_uuid.items():
        print(f"\n--- Scraping season {year} ({season_uuid}) ---")
        
        # 2. Fetch events (schedule) for this season
        events_url = f"{BASE_URL}/results/events?seasonUuid={season_uuid}"
        events_data = make_request(events_url)
        if not events_data:
            print(f"No events found for season {year}")
            continue
            
        # Save schedule
        schedule_output = {
            "season": str(year),
            "season_uuid": season_uuid,
            "total_events": len(events_data),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "events": events_data
        }
        write_json(os.path.join(dest_dir, str(year), "schedule.json"), schedule_output)
        
        # Collect track info from events
        for event in events_data:
            circuit = event.get("circuit")
            if circuit:
                discovered_tracks.append(circuit)
                
            # Only scrape classifications for events in the past (or running)
            # Skip test events
            if event.get("test"):
                continue
                
            event_uuid = event.get("id")
            event_short_name = event.get("short_name", "UNK")
            event_status = event.get("status")
            
            # Skip if the event hasn't started yet
            if event_status not in ["FINISHED", "RUNNING"]:
                print(f"Skipping event {event.get('name')} (Status: {event_status})")
                continue
                
            print(f"\nScraping event: {event.get('name')} ({event_short_name})")
            
            # 3. Fetch categories for this event
            categories_url = f"{BASE_URL}/results/categories?eventUuid={event_uuid}"
            time.sleep(0.5)
            categories_data = make_request(categories_url)
            if not categories_data:
                continue
                
            for category in categories_data:
                category_uuid = category.get("id")
                category_name = clean_name(category.get("name", "unknown"))
                
                # We only focus on core categories: motogp, moto2, moto3, motoe
                if category_name not in ["motogp", "moto2", "moto3", "motoe"]:
                    continue
                    
                # 4. Fetch sessions for this category at this event
                sessions_url = f"{BASE_URL}/results/sessions?eventUuid={event_uuid}&categoryUuid={category_uuid}"
                time.sleep(0.5)
                sessions_data = make_request(sessions_url)
                if not sessions_data:
                    continue
                    
                for session in sessions_data:
                    session_type = session.get("type")
                    session_status = session.get("status")
                    session_uuid = session.get("id")
                    
                    # We only care about Race (RAC) and Sprint (SPR) classifications
                    if session_type not in ["RAC", "SPR"]:
                        continue
                        
                    if session_status != "FINISHED":
                        print(f"  Skipping session {session_type} (Status: {session_status})")
                        continue
                        
                    # 5. Fetch classification results
                    classification_url = f"{BASE_URL}/results/session/{session_uuid}/classification"
                    print(f"  Fetching results for {category_name} {session_type} ({session_uuid})...")
                    time.sleep(1.0)
                    class_data = make_request(classification_url)
                    if not class_data:
                        continue
                        
                    classification_list = class_data.get("classification", [])
                    
                    # Extract rider profiles for the global rider database
                    for row in classification_list:
                        rider = row.get("rider")
                        if rider:
                            discovered_riders.append(rider)
                            
                    # Save the clean classification results
                    results_output = {
                        "season": str(year),
                        "event": {
                            "id": event.get("id"),
                            "name": event.get("name"),
                            "short_name": event_short_name,
                            "circuit": event.get("circuit"),
                            "date_start": event.get("date_start"),
                            "date_end": event.get("date_end")
                        },
                        "category": category,
                        "session": {
                            "id": session.get("id"),
                            "type": session_type,
                            "date": session.get("date"),
                            "condition": session.get("condition")
                        },
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                        "results": classification_list
                    }
                    
                    write_json(
                        os.path.join(dest_dir, str(year), event_short_name, f"{category_name}_{session_type}.json"),
                        results_output
                    )

    # 6. Save/update global tracks and riders databases
    if discovered_tracks:
        print("\nUpdating global tracks database...")
        update_global_db(tracks_path, "tracks", discovered_tracks)
        
    if discovered_riders:
        print("Updating global riders database...")
        update_global_db(drivers_path, "drivers", discovered_riders)
        
    print("\nScraping completed!")

if __name__ == "__main__":
    main()
