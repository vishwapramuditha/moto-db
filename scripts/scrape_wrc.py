import urllib.request
import json
import os
import argparse
from html.parser import HTMLParser
from datetime import datetime

class WikiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.tables = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table' and 'wikitable' in attrs_dict.get('class', ''):
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.current_cell = []
            
    def handle_endtag(self, tag):
        if tag == 'table' and self.in_table:
            self.in_table = False
            self.tables.append(self.current_table)
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_cell:
            self.in_cell = False
            # Clean up footnote references like [a], [1]
            text = ''.join(self.current_cell).strip()
            import re
            text = re.sub(r'\[.*?\]', '', text).strip()
            self.current_row.append(text)
            
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.replace('\n', ' '))


def fetch_wiki_data(year):
    url = f"https://en.wikipedia.org/wiki/{year}_World_Rally_Championship"
        
    print(f"Fetching WRC data from: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'MotoDBScraper/1.0'})
    
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching data for {year}: {e}")
        return [], []
        
    parser = WikiParser()
    parser.feed(html)
    
    schedule_table = None
    results_table = None
    
    for table in parser.tables:
        if not table or not table[0]: continue
        header = [h.lower() for h in table[0]]
        
        # Identify schedule table
        if 'round' in header and any('date' in h for h in header) and 'rally' in header:
            schedule_table = table
        # Identify results table
        elif 'round' in header and 'winning driver' in header:
            results_table = table
            
    if not schedule_table:
        print(f"Could not find the Schedule table for {year}!")
    
    # Results table might not exist yet for future years
    if not results_table:
        print(f"Could not find the Results table for {year} (might not be available yet).")

    schedule = parse_schedule(schedule_table) if schedule_table else []
    results = parse_results(results_table) if results_table else []
    
    return schedule, results

def parse_schedule(table):
    schedule = []
    headers = [h.lower() for h in table[0]]
    
    idx_round = headers.index('round') if 'round' in headers else 0
    idx_rally = headers.index('rally') if 'rally' in headers else 3
    idx_start = headers.index('start date') if 'start date' in headers else 1
    idx_finish = headers.index('finish date') if 'finish date' in headers else 2
    idx_surface = headers.index('surface') if 'surface' in headers else 5
    
    for row in table[1:]:
        if not row: continue
        
        # Skip source/citation rows
        if len(row) < 5 or 'source' in row[0].lower():
            continue
            
        round_num = row[idx_round]
        rally_name = row[idx_rally]
        start_date = row[idx_start] if len(row) > idx_start else ''
        finish_date = row[idx_finish] if len(row) > idx_finish else ''
        surface = row[idx_surface] if len(row) > idx_surface else ''
            
        schedule.append({
            "round": round_num,
            "name": rally_name,
            "start_date": start_date,
            "finish_date": finish_date,
            "surface": surface
        })
        
    return schedule

def parse_results(table):
    results = []
    headers = [h.lower() for h in table[0]]
    
    idx_round = headers.index('round') if 'round' in headers else 0
    idx_event = headers.index('event') if 'event' in headers else 1
    idx_winner = headers.index('winning driver') if 'winning driver' in headers else 2
    idx_codriver = headers.index('winning co-driver') if 'winning co-driver' in headers else 3
    idx_entrant = headers.index('winning entrant') if 'winning entrant' in headers else 4
    idx_time = headers.index('winning time') if 'winning time' in headers else 5
    
    for row in table[1:]:
        if not row: continue
        
        if len(row) < 4 or 'source' in row[0].lower():
            continue
            
        round_num = row[idx_round]
        event = row[idx_event] if len(row) > idx_event else ''
        winner = row[idx_winner] if len(row) > idx_winner else ''
        codriver = row[idx_codriver] if len(row) > idx_codriver else ''
        entrant = row[idx_entrant] if len(row) > idx_entrant else ''
        time_str = row[idx_time] if len(row) > idx_time else ''
            
        # Only append if race has actually happened (we have a winner)
        if winner and winner.strip() and winner.lower() != 'tbd' and 'cancelled' not in winner.lower():
            results.append({
                "round": round_num,
                "event": event,
                "winning_driver": winner,
                "winning_co_driver": codriver,
                "winning_entrant": entrant,
                "winning_time": time_str
            })
            
    return results

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")

def main():
    parser = argparse.ArgumentParser(description="Scrape WRC Schedule and Results from Wikipedia")
    parser.add_argument('--years', type=str, help="Comma-separated list of years to scrape (e.g. 2024,2025)")
    parser.add_argument('--all-time', action='store_true', help="Scrape all historical years (2015 to current)")
    args = parser.parse_args()
    
    current_year = datetime.now().year
    
    if args.all_time:
        years = list(range(2015, current_year + 1))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(',')]
    else:
        # Default to previous and current year
        years = [current_year - 1, current_year]
        
    for year in years:
        schedule, results = fetch_wiki_data(year)
        
        if schedule or results:
            out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'wrc', str(year))
            ensure_dir(out_dir)
            
            if schedule:
                # Wrap schedule to match MotoDB standard formatting
                schedule_output = {
                    "season": str(year),
                    "total_races": len(schedule),
                    "updated_at": datetime.now().astimezone().isoformat().replace("+00:00", "Z"),
                    "races": schedule
                }
                write_json(os.path.join(out_dir, 'schedule.json'), schedule_output)
                
            if results:
                # Write a single results array, or split by round if we want to match others.
                # Since Formula E saves as a single results.json, we'll do the same.
                write_json(os.path.join(out_dir, 'results.json'), results)
            
if __name__ == "__main__":
    main()
