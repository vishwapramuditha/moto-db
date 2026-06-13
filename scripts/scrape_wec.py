import os
import json
import time
import re
import urllib.request
import urllib.error
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser

BASE_URL = "https://www.fiawec.com"
USER_AGENT = "MotoDBScraper/1.0 (https://github.com/vishwapramuditha/moto-db)"


class WecHomepageParser(HTMLParser):
    """Parses fiawec.com homepage to extract seasons and race URLs."""
    def __init__(self):
        super().__init__()
        self.season_mapping = {}  # data-season -> year (int)
        self.races = []  # list of (season_id, href)
        self.current_season_id = None
        self.depth_in_season = 0
        self.in_button = False
        self.current_button_season = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "button" and "season-selector" in attrs_dict.get("class", ""):
            self.in_button = True
            self.current_button_season = attrs_dict.get("data-season")
        elif tag == "div":
            if "class" in attrs_dict and "season-content" in attrs_dict["class"]:
                self.current_season_id = attrs_dict.get("data-season")
                self.depth_in_season = 1
            elif self.current_season_id is not None:
                self.depth_in_season += 1
        elif tag == "a" and self.current_season_id is not None:
            href = attrs_dict.get("href", "")
            if "/en/race/" in href:
                self.races.append((self.current_season_id, href))

    def handle_data(self, data):
        if self.in_button and self.current_button_season:
            # Extract 4-digit year from button text (e.g. "Season 2025")
            m = re.search(r'\b(20\d{2})\b', data)
            if m:
                self.season_mapping[self.current_button_season] = int(m.group(1))

    def handle_endtag(self, tag):
        if tag == "button":
            self.in_button = False
            self.current_button_season = None
        elif tag == "div" and self.current_season_id is not None:
            self.depth_in_season -= 1
            if self.depth_in_season == 0:
                self.current_season_id = None


def make_request(url):
    """Make HTTP GET request and return raw HTML content string."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    retries = 3
    for attempt in range(retries):
        try:
            print(f"Fetching: {url}")
            with urllib.request.urlopen(req) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait_time = (attempt + 1) * 5
                print(f"Rate limited (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code in (403, 404):
                print(f"HTTP Error {e.code} for: {url}")
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


def parse_race_page(slug, html):
    """Parse JSON-LD from race detail page html."""
    json_ld_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL
    )
    if not json_ld_blocks:
        print(f"Warning: No JSON-LD schema found for race {slug}")
        return None

    try:
        data = json.loads(json_ld_blocks[0].strip())
    except Exception as e:
        print(f"Error parsing JSON-LD for race {slug}: {e}")
        return None

    # Verify context and type
    if isinstance(data, list):
        event_data = next((item for item in data if item.get("@type") == "SportsEvent"), None)
    elif isinstance(data, dict) and data.get("@type") == "SportsEvent":
        event_data = data
    else:
        event_data = None

    if not event_data:
        print(f"Warning: No SportsEvent JSON-LD found for race {slug}")
        return None

    # Extract location details
    loc = event_data.get("location", {})
    venue = loc.get("name", "")
    address = loc.get("address", "")

    # Extract status details
    raw_status = event_data.get("eventStatus", "")
    status = raw_status.replace("https://schema.org/", "")
    completed = status == "EventCompleted"

    # Extract sessions (subEvents)
    sessions = []
    sub_events = event_data.get("subEvent", [])
    for sub in sub_events:
        sub_raw_status = sub.get("eventStatus", "")
        sub_status = sub_raw_status.replace("https://schema.org/", "")
        sub_completed = sub_status == "EventCompleted"
        
        sessions.append({
            "name": sub.get("name", ""),
            "date": sub.get("startDate", ""),
            "status": sub_status,
            "completed": sub_completed,
        })

    # Determine main race date/time (start time of the actual "Race" session)
    race_date = None
    for s in sessions:
        s_name = s["name"].lower()
        if "race" in s_name and not any(x in s_name for x in ["practice", "qualifying", "hyperpole", "warm-up", "warmup"]):
            race_date = s["date"]
            break
    if not race_date:
        # Fallback to main event's startDate
        race_date = event_data.get("startDate", "")

    return {
        "race_id": slug,
        "name": event_data.get("name", ""),
        "slug": slug,
        "url": f"{BASE_URL}/en/race/{slug}",
        "status": status,
        "completed": completed,
        "startDate": event_data.get("startDate", ""),
        "endDate": event_data.get("endDate", ""),
        "date": race_date,
        "location": {
            "venue": venue,
            "address": address
        },
        "sessions": sessions
    }


def scrape_season(dest_dir, year, homepage_parser):
    """Scrape WEC schedule for a given year."""
    print(f"\n--- Scraping WEC season {year} ---")

    # Find season ID for target year
    season_id = None
    for sid, yr in homepage_parser.season_mapping.items():
        if yr == year:
            season_id = sid
            break

    if not season_id:
        print(f"No season ID mapping found for year {year} on homepage")
        return

    # Extract slugs for this season
    races_slugs = []
    for sid, href in homepage_parser.races:
        if sid == season_id:
            # Extract slug from href, e.g. /en/race/qatar-1812km-2025 -> qatar-1812km-2025
            m = re.search(r'/en/race/([a-zA-Z0-9\-_]+)', href)
            if m:
                races_slugs.append(m.group(1))

    # De-duplicate while preserving order
    races_slugs = list(dict.fromkeys(races_slugs))
    if not races_slugs:
        print(f"No race slugs found for season {year} (ID: {season_id})")
        return

    print(f"Found {len(races_slugs)} races for WEC {year}")

    # Fetch and parse details for each race
    parsed_races = []
    for slug in races_slugs:
        url = f"{BASE_URL}/en/race/{slug}"
        # Safety sleep between page requests
        time.sleep(1.0)
        
        html = make_request(url)
        if not html:
            print(f"Error: Could not retrieve page for {slug}")
            continue

        race_details = parse_race_page(slug, html)
        if race_details:
            parsed_races.append(race_details)

    if not parsed_races:
        print(f"No valid race details extracted for WEC {year}")
        return

    # Sort races by date/startDate
    parsed_races.sort(key=lambda x: x.get("startDate") or "")

    # Save to schedule.json
    schedule_output = {
        "season": str(year),
        "total_races": len(parsed_races),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "races": parsed_races,
    }
    
    write_json(os.path.join(dest_dir, str(year), "schedule.json"), schedule_output)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape WEC (World Endurance Championship) schedule from fiawec.com"
    )
    parser.add_argument(
        "--years",
        type=str,
        help="Comma-separated list of years to scrape (e.g. 2025,2026)",
    )
    parser.add_argument(
        "--all-time",
        action="store_true",
        help="Scrape all historical years available on the WEC website",
    )
    args = parser.parse_args()

    dest_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wec"
    )

    # Fetch and parse fiawec.com homepage once
    print("Fetching homepage to detect seasons and races...")
    homepage_html = make_request(BASE_URL + "/")
    if not homepage_html:
        print("Error: Could not fetch fiawec.com homepage. Aborting.")
        return

    homepage_parser = WecHomepageParser()
    homepage_parser.feed(homepage_html)

    if not homepage_parser.season_mapping:
        print("Error: Could not parse season mapping from homepage. Aborting.")
        return

    print(f"Detected seasons: {homepage_parser.season_mapping}")

    current_year = datetime.now().year

    # Determine years to scrape
    if args.all_time:
        years = [int(y) for y in homepage_parser.season_mapping.keys() if str(y).isdigit()]
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        # Default to current year and previous year to align with standard practices
        years = [current_year - 1, current_year]

    print(f"Target years: {years}")
    for year in years:
        scrape_season(dest_dir, year, homepage_parser)

    print("\nWEC scraping completed!")


if __name__ == "__main__":
    main()
