import urllib.request
import json
import os
import argparse
from html.parser import HTMLParser

class WikiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.tables = []
        self.is_header = False
        
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
            # Note if it's a header row
            self.is_header = tag == 'th'
            
    def handle_endtag(self, tag):
        if tag == 'table' and self.in_table:
            self.in_table = False
            self.tables.append(self.current_table)
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_cell:
            self.in_cell = False
            # Clean up footnote references like [a], [1], and extra spaces
            text = ''.join(self.current_cell).strip()
            import re
            text = re.sub(r'\[.*?\]', '', text).strip()
            self.current_row.append(text)
            
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.replace('\n', ' '))


def fetch_wiki_data(year):
    # Map the year to the Wikipedia season string
    # E.g. 2025 -> 2024-25, 2026 -> 2025-26
    prev_year = int(year) - 1
    # %E2%80%93 is the en dash URL encoded
    season_str = f"{prev_year}%E2%80%93{str(year)[-2:]}"
    
    if int(year) <= 2020:
        url = f"https://en.wikipedia.org/wiki/{season_str}_Formula_E_Championship"
    else:
        url = f"https://en.wikipedia.org/wiki/{season_str}_Formula_E_World_Championship"
        
    print(f"Fetching Formula E data from: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'MotoDBScraper/1.0'})
    
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    parser = WikiParser()
    parser.feed(html)
    
    schedule_table = None
    results_table = None
    
    for table in parser.tables:
        if not table or not table[0]: continue
        header = [h.lower() for h in table[0]]
        
        # Identify schedule table
        if 'round' in header and 'circuit' in header and 'date' in header:
            schedule_table = table
        # Identify results table
        elif 'round' in header and 'pole position' in header and 'winning driver' in header:
            results_table = table
            
    if not schedule_table:
        print("Could not find the Schedule table!")
        return [], []
        
    if not results_table:
        print("Could not find the Results table!")
        return [], []

    schedule = parse_schedule(schedule_table)
    results = parse_results(results_table)
    
    return schedule, results

def parse_schedule(table):
    schedule = []
    # Headers typically: Round, E-Prix, Official Title, Country, Circuit, Date
    # Double headers might omit E-Prix, Title, Country, Circuit, leaving only Round and Date
    last_eprix = ""
    last_country = ""
    last_circuit = ""
    
    headers = [h.lower() for h in table[0]]
    # Map headers to indices dynamically just in case
    idx_round = headers.index('round') if 'round' in headers else 0
    idx_date = headers.index('date') if 'date' in headers else -1
    
    for row in table[1:]:
        if not row: continue
        
        # Skip source/citation rows at the bottom
        if 'source' in row[0].lower():
            continue
            
        # If the row is short, it's a double header
        if len(row) <= 3:
            # Usually [Round, Date] or [Round, Name, Date]
            round_num = row[0]
            date_str = row[-1]
            eprix = last_eprix
            circuit = last_circuit
            country = last_country
        else:
            round_num = row[0]
            eprix = row[1]
            country = row[3] if len(row) > 3 else ''
            circuit = row[4] if len(row) > 4 else ''
            date_str = row[5] if len(row) > 5 else row[-1]
            
            last_eprix = eprix
            last_country = country
            last_circuit = circuit
            
        schedule.append({
            "round": round_num,
            "eprix": eprix,
            "country": country,
            "circuit": circuit,
            "date": date_str
        })
        
    return schedule

def parse_results(table):
    results = []
    last_eprix = ""
    
    headers = [h.lower() for h in table[0]]
    
    for row in table[1:]:
        if not row: continue
        
        # Short row for double header
        if len(row) <= 5:
            # Usually [Round, Pole, Fastest Lap, Winning Driver, Winning Team]
            # or [Round, Pole, Winning Driver, Winning Team]
            round_num = row[0]
            eprix = last_eprix
            pole = row[1] if len(row) > 1 else ''
            winner = row[3] if len(row) > 3 else (row[2] if len(row) > 2 else '')
            team = row[4] if len(row) > 4 else (row[3] if len(row) > 3 else '')
        else:
            round_num = row[0]
            eprix = row[1]
            pole = row[2] if len(row) > 2 else ''
            # fastest lap is 3
            winner = row[4] if len(row) > 4 else ''
            team = row[5] if len(row) > 5 else ''
            last_eprix = eprix
            
        # Only append if race has actually happened (we have a winner)
        if winner and winner.strip() and winner.lower() != 'tbd':
            results.append({
                "round": round_num,
                "eprix": eprix,
                "pole_position": pole,
                "winning_driver": winner,
                "winning_team": team
            })
            
    return results

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")

def main():
    parser = argparse.ArgumentParser(description="Scrape Formula E Schedule and Results from Wikipedia")
    parser.add_argument('--year', type=int, help="Season end year (e.g., 2025 for 2024-25 season)")
    parser.add_argument('--years', type=str, help="Comma-separated list of years to scrape (e.g. 2024,2025)")
    parser.add_argument('--all-time', action='store_true', help="Scrape all historical years (2015 to current)")
    args = parser.parse_args()
    
    from datetime import datetime
    current_year = datetime.now().year
    
    if args.all_time:
        years = list(range(2015, current_year + 1))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(',')]
    elif args.year:
        years = [args.year]
    else:
        years = [current_year]
        
    for year in years:
        schedule, results = fetch_wiki_data(year)
        
        if schedule or results:
            out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'formula_e', str(year))
            ensure_dir(out_dir)
            
            if schedule:
                write_json(os.path.join(out_dir, 'schedule.json'), schedule)
            if results:
                write_json(os.path.join(out_dir, 'results.json'), results)
            
if __name__ == "__main__":
    main()
