import urllib.request
import urllib.error
import json
import os
import re
import time
import argparse
from html.parser import HTMLParser
from datetime import datetime, timezone


class WikiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.current_table = []
        self.tables = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and "wikitable" in attrs_dict.get("class", ""):
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self.in_table:
            self.in_table = False
            self.tables.append(self.current_table)
        elif tag == "tr" and self.in_row:
            self.in_row = False
            self.current_table.append(self.current_row)
        elif tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            text = "".join(self.current_cell).strip()
            text = re.sub(r"\[.*?\]", "", text).strip()
            self.current_row.append(text)

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.replace("\n", " "))


def fetch_with_retry(url, retries=3):
    """Fetch a URL with retry logic and exponential back-off."""
    req = urllib.request.Request(url, headers={"User-Agent": "MotoDBScraper/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} fetching {url} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"Error fetching {url}: {e} (attempt {attempt + 1}/{retries})")
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def fetch_wiki_data(year):
    url = f"https://en.wikipedia.org/wiki/{year}_FIA_Formula_3_Championship"
    print(f"Fetching F3 data from: {url}")
    html = fetch_with_retry(url)
    if not html:
        print(f"Error fetching F3 data for {year}")
        return [], []

    parser = WikiParser()
    parser.feed(html)

    schedule_table = None
    results_table = None

    for table in parser.tables:
        if not table or not table[0]:
            continue
        header = [h.lower() for h in table[0]]
        if len(table) > 1:
            header += [h.lower() for h in table[1]]

        # Schedule table: has 'round' and 'circuit'
        # F3 uses 'sprint race' / 'feature race(s)' columns for dates — no 'date' column
        if 'round' in header and 'circuit' in header:
            if schedule_table is None:
                schedule_table = table

        # Results table: has 'round' and 'winning driver' or 'winner'
        if 'round' in header and ('winning driver' in header or 'winner' in header):
            results_table = table

    if not schedule_table:
        print(f"Could not find the Schedule table for {year}!")
    if not results_table:
        print(f"Could not find the Results table for {year} (might not be available yet).")

    schedule = parse_schedule(schedule_table) if schedule_table else []
    results = parse_results(results_table) if results_table else []
    return schedule, results


def parse_schedule(table):
    schedule = []
    headers = [h.lower() for h in table[0]]

    idx_round   = next((i for i, h in enumerate(headers) if h == "round"), 0)
    idx_circuit = next((i for i, h in enumerate(headers) if "circuit" in h), None)
    idx_country = next((i for i, h in enumerate(headers) if "country" in h or "location" in h), None)
    # F3 doesn't have a 'date' column — it has 'sprint race' and 'feature race(s)' with dates
    idx_sprint  = next((i for i, h in enumerate(headers) if "sprint" in h), None)
    idx_feature = next((i for i, h in enumerate(headers) if "feature" in h), None)
    idx_date    = next((i for i, h in enumerate(headers) if h == "date"), None)

    for row in table[1:]:
        if not row:
            continue
        if len(row) < 2 or "source" in row[0].lower():
            continue
        round_num = row[idx_round].strip()
        if not round_num.isdigit():
            continue

        circuit  = row[idx_circuit].strip() if idx_circuit is not None and len(row) > idx_circuit else ""
        country  = row[idx_country].strip() if idx_country is not None and len(row) > idx_country else ""
        # Use sprint race date if no dedicated date column
        if idx_date is not None and len(row) > idx_date:
            date_str = row[idx_date].strip()
        elif idx_sprint is not None and len(row) > idx_sprint:
            date_str = row[idx_sprint].strip()
        elif idx_feature is not None and len(row) > idx_feature:
            date_str = row[idx_feature].strip()
        else:
            date_str = ""

        schedule.append({
            "round":   int(round_num),
            "circuit": circuit,
            "country": country,
            "date":    date_str,
        })

    return schedule


def parse_results(table):
    """Parse the F3 results table.

    Two rows per round on Wikipedia:
      SR row (8 cells): [round, 'SR', circuit, pole_position, fastest_lap, winning_driver, winning_team, 'Report']
      FR row (5 cells): ['FR', fastest_lap, pole_position, winning_driver, winning_team]
                        (circuit is inherited from the preceding SR row)
    """
    results = []
    current_round = None
    current_circuit = ""

    for row in table[1:]:
        if not row:
            continue

        first = row[0].strip()
        if "source" in first.lower() or first.lower() in ("key", "colour", "round"):
            continue

        if first.isdigit():
            # SR primary row
            current_round = int(first)
            session_type    = row[1].strip() if len(row) > 1 else "SR"
            current_circuit = row[2].strip() if len(row) > 2 else ""
            pole            = row[3].strip() if len(row) > 3 else ""
            fastest_lap     = row[4].strip() if len(row) > 4 else ""
            winner          = row[5].strip() if len(row) > 5 else ""
            team            = row[6].strip() if len(row) > 6 else ""
        else:
            # FR sub-row — circuit inherited
            if current_round is None:
                continue
            session_type = first  # 'FR'
            fastest_lap  = row[1].strip() if len(row) > 1 else ""
            pole         = row[2].strip() if len(row) > 2 else ""
            winner       = row[3].strip() if len(row) > 3 else ""
            team         = row[4].strip() if len(row) > 4 else ""

        if winner and winner.lower() not in ("tbd", "", "cancelled"):
            results.append({
                "round":          current_round,
                "race_type":      "Sprint Race" if session_type.upper() == "SR" else "Feature Race",
                "circuit":        current_circuit,
                "pole_position":  pole,
                "fastest_lap":    fastest_lap,
                "winning_driver": winner,
                "winning_team":   team,
            })

    return results





def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_json(path, data):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape FIA Formula 3 Schedule and Results from Wikipedia")
    parser.add_argument("--year",     type=int, help="Single year to scrape (e.g. 2026)")
    parser.add_argument("--years",    type=str, help="Comma-separated years (e.g. 2024,2025,2026)")
    parser.add_argument("--all-time", action="store_true", help="Scrape all historical years (2019 to current)")
    args = parser.parse_args()

    current_year = datetime.now().year

    if args.all_time:
        years = list(range(2019, current_year + 1))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    elif args.year:
        years = [args.year]
    else:
        years = [current_year - 1, current_year]

    for year in years:
        print(f"\n--- Processing F3 {year} ---")
        schedule, results = fetch_wiki_data(year)

        if not schedule and not results:
            print(f"No data found for {year}, skipping.")
            continue

        out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "f3", str(year))
        ensure_dir(out_dir)

        if schedule:
            write_json(os.path.join(out_dir, "schedule.json"), {
                "season":       str(year),
                "total_rounds": len(schedule),
                "updated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "races":        schedule,
            })

        if results:
            write_json(os.path.join(out_dir, "results.json"), {
                "season":     str(year),
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "results":    results,
            })


if __name__ == "__main__":
    main()
