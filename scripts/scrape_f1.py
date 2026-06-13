import os
import json
import time
import urllib.request
import urllib.error
import argparse
from datetime import datetime

BASE_URL = "https://api.jolpi.ca/ergast/f1"
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

def scrape_drivers(dest_dir):
    """Scrape all F1 drivers and save them."""
    print("Scraping drivers...")
    url = f"{BASE_URL}/drivers.json?limit=1500"
    data = make_request(url)
    if not data:
        return
    
    drivers = data.get("MRData", {}).get("DriverTable", {}).get("Drivers", [])
    output = {
        "total": len(drivers),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "drivers": drivers
    }
    write_json(os.path.join(dest_dir, "drivers.json"), output)

def scrape_tracks(dest_dir):
    """Scrape all F1 circuits/tracks and save them."""
    print("Scraping tracks...")
    url = f"{BASE_URL}/circuits.json?limit=500"
    data = make_request(url)
    if not data:
        return
    
    circuits = data.get("MRData", {}).get("CircuitTable", {}).get("Circuits", [])
    output = {
        "total": len(circuits),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "tracks": circuits
    }
    write_json(os.path.join(dest_dir, "tracks.json"), output)

def scrape_season(dest_dir, year):
    """Scrape schedule and results for a given year."""
    print(f"Scraping schedule for {year}...")
    url = f"{BASE_URL}/{year}.json"
    data = make_request(url)
    if not data:
        print(f"No schedule data found for {year}")
        return
    
    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        print(f"No races listed in schedule for {year}")
        return
    
    # Save schedule
    schedule_output = {
        "season": str(year),
        "total_rounds": len(races),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "races": races
    }
    write_json(os.path.join(dest_dir, str(year), "schedule.json"), schedule_output)
    
    # Scrape results for races that have already happened
    today = datetime.utcnow().date()
    for race in races:
        round_num = race.get("round")
        race_date_str = race.get("date")
        
        if not race_date_str:
            continue
            
        try:
            race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format '{race_date_str}' for round {round_num}")
            continue
            
        # If the race is in the past (or today), fetch results
        if race_date <= today:
            print(f"Scraping results for {year} round {round_num} ({race.get('raceName')})...")
            results_url = f"{BASE_URL}/{year}/{round_num}/results.json"
            time.sleep(1.0)  # Rate limit safety pause
            results_data = make_request(results_url)
            
            if not results_data:
                continue
                
            race_details_list = results_data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
            if race_details_list:
                race_details = race_details_list[0]
                results_output = {
                    "season": str(year),
                    "round": str(round_num),
                    "raceName": race_details.get("raceName"),
                    "circuit": race_details.get("Circuit"),
                    "date": race_details.get("date"),
                    "time": race_details.get("time"),
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                    "results": race_details.get("Results", [])
                }
                write_json(os.path.join(dest_dir, str(year), f"results_{round_num}.json"), results_output)
            else:
                print(f"No results available yet for {year} round {round_num}")

def main():
    parser = argparse.ArgumentParser(description="Scrape F1 database from Jolpica/Ergast API")
    parser.add_argument("--years", type=str, help="Comma-separated list of years to scrape (e.g. 2024,2025)")
    parser.add_argument("--all-time", action="store_true", help="Scrape all historical years (1950 to current)")
    args = parser.parse_args()
    
    dest_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "f1")
    
    # Always scrape global metadata
    scrape_drivers(dest_dir)
    time.sleep(1.0)
    scrape_tracks(dest_dir)
    time.sleep(1.0)
    
    current_year = datetime.now().year
    
    # Determine years to scrape
    if args.all_time:
        years = list(range(1950, current_year + 1))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        # Default to current year and previous year
        years = [current_year - 1, current_year]
        
    print(f"Target years for schedule & results: {years}")
    for year in years:
        scrape_season(dest_dir, year)
        time.sleep(1.0)

if __name__ == "__main__":
    main()
