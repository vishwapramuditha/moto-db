import os
import json
import sys

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def write_json(path, data):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Saved: {path}")

# Point calculation functions for series without explicit points
def get_nascar_points(position):
    if position == 1:
        return 40
    elif position >= 36:
        return 1
    else:
        return 37 - position

def get_indycar_points(position):
    table = {
        1: 50, 2: 40, 3: 35, 4: 32, 5: 30, 6: 28, 7: 26, 8: 24, 9: 22, 10: 20,
        11: 19, 12: 18, 13: 17, 14: 16, 15: 15, 16: 14, 17: 13, 18: 12, 19: 11,
        20: 10, 21: 9, 22: 8, 23: 7, 24: 6
    }
    return table.get(position, 5)

def parse_position(pos_raw):
    if pos_raw is None:
        return 999
    try:
        return int(pos_raw)
    except (ValueError, TypeError):
        return 999

def compile_f1_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'f1', year)
    if not os.path.exists(series_dir):
        return
        
    drivers = {}
    constructors = {}
    
    # Process results files in chronological order
    results_files = []
    for file in os.listdir(series_dir):
        if file.startswith('results_') and file.endswith('.json'):
            try:
                rnd = int(file.replace('results_', '').replace('.json', ''))
                results_files.append((rnd, file))
            except ValueError:
                continue
    results_files.sort()
    
    round_count = 0
    for rnd, file in results_files:
        round_count += 1
        file_path = os.path.join(series_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            for item in results:
                driver_data = item.get('Driver', {})
                driver_id = driver_data.get('driverId')
                constructor_data = item.get('Constructor', {})
                constructor_id = constructor_data.get('constructorId')
                
                pos = parse_position(item.get('position'))
                pts = float(item.get('points', 0))
                
                if driver_id:
                    if driver_id not in drivers:
                        drivers[driver_id] = {
                            'points': 0.0,
                            'wins': 0,
                            'finishes': [],
                            'Driver': driver_data,
                            'Constructor': constructor_data,
                            'pointsProgression': [0.0] * (round_count - 1)
                        }
                    drivers[driver_id]['points'] += pts
                    drivers[driver_id]['finishes'].append(pos)
                    if pos == 1:
                        drivers[driver_id]['wins'] += 1
                        
                if constructor_id:
                    if constructor_id not in constructors:
                        constructors[constructor_id] = {
                            'points': 0.0,
                            'wins': 0,
                            'finishes': [],
                            'Constructor': constructor_data,
                            'pointsProgression': [0.0] * (round_count - 1)
                        }
                    constructors[constructor_id]['points'] += pts
                    constructors[constructor_id]['finishes'].append(pos)
                    if pos == 1:
                        constructors[constructor_id]['wins'] += 1
                        
            # Record progression for this round
            for d_id in drivers:
                drivers[d_id]['pointsProgression'].append(drivers[d_id]['points'])
            for c_id in constructors:
                constructors[c_id]['pointsProgression'].append(constructors[c_id]['points'])
        except Exception as e:
            print(f"[WARNING] F1: Error reading {file}: {e}")

    # Helper function to sort standings with tie breakers
    def sort_key(item_tuple):
        val = item_tuple[1]
        finishes_sorted = sorted(val['finishes'])
        while len(finishes_sorted) < 50:
            finishes_sorted.append(999)
        return (val['points'], val['wins'], [-x for x in finishes_sorted])

    sorted_drivers = sorted(drivers.items(), key=sort_key, reverse=True)
    sorted_constructors = sorted(constructors.items(), key=sort_key, reverse=True)
    
    driver_standings = []
    for idx, (d_id, val) in enumerate(sorted_drivers):
        driver_standings.append({
            'position': idx + 1,
            'points': val['points'],
            'wins': val['wins'],
            'Driver': val['Driver'],
            'Constructor': val['Constructor'],
            'pointsProgression': val['pointsProgression']
        })
        
    constructor_standings = []
    for idx, (c_id, val) in enumerate(sorted_constructors):
        constructor_standings.append({
            'position': idx + 1,
            'points': val['points'],
            'wins': val['wins'],
            'Constructor': val['Constructor'],
            'pointsProgression': val['pointsProgression']
        })
        
    output_path = os.path.join(series_dir, 'standings.json')
    write_json(output_path, {
        'season': year,
        'driverStandings': driver_standings,
        'constructorStandings': constructor_standings,
        'updated_at': datetime_now_iso()
    })

def compile_motogp_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'motogp', year)
    if not os.path.exists(series_dir):
        return
        
    riders = {}
    
    # Process MotoGP results chronologically by date
    results_sessions = []
    for root, dirs, files in os.walk(series_dir):
        for file in files:
            if file.endswith('_RAC.json') or file.endswith('_SPR.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session_date = data.get('session', {}).get('date', '')
                    results_sessions.append((session_date, file_path, file.endswith('_SPR.json')))
                except Exception as e:
                    print(f"[WARNING] MotoGP: Error reading session date for {file}: {e}")
    results_sessions.sort(key=lambda x: x[0])
    
    round_count = 0
    for session_date, file_path, is_sprint in results_sessions:
        round_count += 1
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            for item in results:
                rider_data = item.get('rider', {})
                rider_id = rider_data.get('id')
                team_data = item.get('team', {})
                
                pos = parse_position(item.get('position'))
                pts = float(item.get('points', 0))
                
                if rider_id:
                    if rider_id not in riders:
                        riders[rider_id] = {
                            'points': 0.0,
                            'wins': 0,
                            'finishes': [],
                            'rider': rider_data,
                            'team': team_data,
                            'pointsProgression': [0.0] * (round_count - 1)
                        }
                    riders[rider_id]['points'] += pts
                    if not is_sprint:
                        riders[rider_id]['finishes'].append(pos)
                        if pos == 1:
                            riders[rider_id]['wins'] += 1
                            
            for r_id in riders:
                riders[r_id]['pointsProgression'].append(riders[r_id]['points'])
        except Exception as e:
            print(f"[WARNING] MotoGP: Error reading {file_path}: {e}")

    def sort_key(item_tuple):
        val = item_tuple[1]
        finishes_sorted = sorted(val['finishes'])
        while len(finishes_sorted) < 50:
            finishes_sorted.append(999)
        return (val['points'], val['wins'], [-x for x in finishes_sorted])

    sorted_riders = sorted(riders.items(), key=sort_key, reverse=True)
    
    rider_standings = []
    for idx, (r_id, val) in enumerate(sorted_riders):
        rider_standings.append({
            'position': idx + 1,
            'points': val['points'],
            'wins': val['wins'],
            'rider': val['rider'],
            'team': val['team'],
            'pointsProgression': val['pointsProgression']
        })
        
    output_path = os.path.join(series_dir, 'standings.json')
    write_json(output_path, {
        'season': year,
        'riderStandings': rider_standings,
        'updated_at': datetime_now_iso()
    })

def compile_nascar_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'nascar', year)
    if not os.path.exists(series_dir):
        return
        
    schedule_path = os.path.join(series_dir, 'schedule.json')
    series_dict = {}
    if os.path.exists(schedule_path):
        try:
            with open(schedule_path, 'r', encoding='utf-8') as f:
                schedule_data = json.load(f)
            series_dict = schedule_data.get('series', {})
        except Exception as e:
            print(f"[WARNING] NASCAR: Error reading schedule: {e}")

    for subseries in ['cup', 'xfinity', 'truck']:
        subseries_dir = os.path.join(series_dir, subseries)
        if not os.path.exists(subseries_dir):
            continue
            
        ordered_race_ids = []
        races_list = series_dict.get(subseries, [])
        for race in races_list:
            if race.get('race_type_id') == 1:
                ordered_race_ids.append(race.get('race_id'))
                
        drivers = {}
        round_count = 0
        for race_id in ordered_race_ids:
            file = f"results_{race_id}.json"
            file_path = os.path.join(subseries_dir, file)
            if not os.path.exists(file_path):
                continue
                
            round_count += 1
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results = data.get('results', [])
                for item in results:
                    driver_id = item.get('driver_id')
                    driver_name = item.get('driver_name')
                    mfr = item.get('manufacturer')
                    
                    pos = parse_position(item.get('position'))
                    pts = get_nascar_points(pos)
                    
                    if driver_id:
                        if driver_id not in drivers:
                            drivers[driver_id] = {
                                'points': 0,
                                'wins': 0,
                                'finishes': [],
                                'driver_id': driver_id,
                                'driver_name': driver_name,
                                'manufacturer': mfr,
                                'pointsProgression': [0] * (round_count - 1)
                            }
                        drivers[driver_id]['points'] += pts
                        drivers[driver_id]['finishes'].append(pos)
                        if pos == 1:
                            drivers[driver_id]['wins'] += 1
                            
                for d_id in drivers:
                    drivers[d_id]['pointsProgression'].append(drivers[d_id]['points'])
            except Exception as e:
                print(f"[WARNING] NASCAR {subseries}: Error reading {file}: {e}")

        def sort_key(item_tuple):
            val = item_tuple[1]
            finishes_sorted = sorted(val['finishes'])
            while len(finishes_sorted) < 50:
                finishes_sorted.append(999)
            return (val['points'], val['wins'], [-x for x in finishes_sorted])

        sorted_drivers = sorted(drivers.items(), key=sort_key, reverse=True)
        
        driver_standings = []
        for idx, (d_id, val) in enumerate(sorted_drivers):
            driver_standings.append({
                'position': idx + 1,
                'points': val['points'],
                'wins': val['wins'],
                'driver_id': val['driver_id'],
                'driver_name': val['driver_name'],
                'manufacturer': val['manufacturer'],
                'pointsProgression': val['pointsProgression']
            })
            
        output_path = os.path.join(subseries_dir, 'standings.json')
        write_json(output_path, {
            'season': year,
            'series': subseries,
            'driverStandings': driver_standings,
            'updated_at': datetime_now_iso()
        })

def compile_indycar_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'indycar', year)
    if not os.path.exists(series_dir):
        return
        
    drivers = {}
    
    results_files = []
    for file in os.listdir(series_dir):
        if file.startswith('results_') and file.endswith('.json'):
            file_path = os.path.join(series_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                date_str = data.get('date') or data.get('startDate') or ''
                results_files.append((date_str, file_path))
            except Exception as e:
                print(f"[WARNING] IndyCar: Error reading date for {file}: {e}")
    results_files.sort()
    
    round_count = 0
    for date_str, file_path in results_files:
        round_count += 1
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            for item in results:
                driver_id = item.get('driver_id')
                driver_name = item.get('driver_name')
                nationality = item.get('nationality')
                
                pos = parse_position(item.get('position'))
                pts = get_indycar_points(pos)
                
                if driver_id:
                    if driver_id not in drivers:
                        drivers[driver_id] = {
                            'points': 0,
                            'wins': 0,
                            'finishes': [],
                            'driver_id': driver_id,
                            'driver_name': driver_name,
                            'nationality': nationality,
                            'pointsProgression': [0] * (round_count - 1)
                        }
                    drivers[driver_id]['points'] += pts
                    drivers[driver_id]['finishes'].append(pos)
                    if pos == 1:
                        drivers[driver_id]['wins'] += 1
                        
            for d_id in drivers:
                drivers[d_id]['pointsProgression'].append(drivers[d_id]['points'])
        except Exception as e:
            print(f"[WARNING] IndyCar: Error reading {file_path}: {e}")

    def sort_key(item_tuple):
        val = item_tuple[1]
        finishes_sorted = sorted(val['finishes'])
        while len(finishes_sorted) < 50:
            finishes_sorted.append(999)
        return (val['points'], val['wins'], [-x for x in finishes_sorted])

    sorted_drivers = sorted(drivers.items(), key=sort_key, reverse=True)
    
    driver_standings = []
    for idx, (d_id, val) in enumerate(sorted_drivers):
        driver_standings.append({
            'position': idx + 1,
            'points': val['points'],
            'wins': val['wins'],
            'driver_id': val['driver_id'],
            'driver_name': val['driver_name'],
            'nationality': val['nationality'],
            'pointsProgression': val['pointsProgression']
        })
        
    output_path = os.path.join(series_dir, 'standings.json')
    write_json(output_path, {
        'season': year,
        'driverStandings': driver_standings,
        'updated_at': datetime_now_iso()
    })

def compile_formula_e_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'formula_e', year)
    if not os.path.exists(series_dir):
        return
        
    results_path = os.path.join(series_dir, 'results.json')
    if not os.path.exists(results_path):
        return
        
    drivers = {}
    teams = {}
    
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
            
        for item in results:
            winner = item.get('winning_driver')
            team = item.get('winning_team')
            
            if winner:
                if winner not in drivers:
                    drivers[winner] = { 'wins': 0, 'driver_name': winner, 'team_name': team }
                drivers[winner]['wins'] += 1
                
            if team:
                if team not in teams:
                    teams[team] = { 'wins': 0, 'team_name': team }
                teams[team]['wins'] += 1
    except Exception as e:
        print(f"[WARNING] Formula E: Error compiling standings: {e}")
        return

    sorted_drivers = sorted(drivers.values(), key=lambda x: x['wins'], reverse=True)
    sorted_teams = sorted(teams.values(), key=lambda x: x['wins'], reverse=True)
    
    driver_standings = []
    for idx, val in enumerate(sorted_drivers):
        driver_standings.append({
            'position': idx + 1,
            'wins': val['wins'],
            'driver_name': val['driver_name'],
            'team_name': val['team_name']
        })
        
    team_standings = []
    for idx, val in enumerate(sorted_teams):
        team_standings.append({
            'position': idx + 1,
            'wins': val['wins'],
            'team_name': val['team_name']
        })
        
    output_path = os.path.join(series_dir, 'standings.json')
    write_json(output_path, {
        'season': year,
        'driverStandings': driver_standings,
        'teamStandings': team_standings,
        'updated_at': datetime_now_iso()
    })

def compile_wrc_standings(year, data_dir):
    series_dir = os.path.join(data_dir, 'wrc', year)
    if not os.path.exists(series_dir):
        return
        
    results_path = os.path.join(series_dir, 'results.json')
    if not os.path.exists(results_path):
        return
        
    drivers = {}
    entrants = {}
    
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
            
        for item in results:
            winner = item.get('winning_driver')
            co_driver = item.get('winning_co_driver')
            entrant = item.get('winning_entrant')
            
            if winner:
                if winner not in drivers:
                    drivers[winner] = {
                        'wins': 0,
                        'driver_name': winner,
                        'co_driver_name': co_driver,
                        'entrant_name': entrant
                    }
                drivers[winner]['wins'] += 1
                
            if entrant:
                if entrant not in entrants:
                    entrants[entrant] = { 'wins': 0, 'entrant_name': entrant }
                entrants[entrant]['wins'] += 1
    except Exception as e:
        print(f"[WARNING] WRC: Error compiling standings: {e}")
        return

    sorted_drivers = sorted(drivers.values(), key=lambda x: x['wins'], reverse=True)
    sorted_entrants = sorted(entrants.values(), key=lambda x: x['wins'], reverse=True)
    
    driver_standings = []
    for idx, val in enumerate(sorted_drivers):
        driver_standings.append({
            'position': idx + 1,
            'wins': val['wins'],
            'driver_name': val['driver_name'],
            'co_driver_name': val['co_driver_name'],
            'entrant_name': val['entrant_name']
        })
        
    entrant_standings = []
    for idx, val in enumerate(sorted_entrants):
        entrant_standings.append({
            'position': idx + 1,
            'wins': val['wins'],
            'entrant_name': val['entrant_name']
        })
        
    output_path = os.path.join(series_dir, 'standings.json')
    write_json(output_path, {
        'season': year,
        'driverStandings': driver_standings,
        'entrantStandings': entrant_standings,
        'updated_at': datetime_now_iso()
    })

def datetime_now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compile standings.json files by aggregating results.")
    parser.add_argument('--series', choices=['f1', 'motogp', 'nascar', 'indycar', 'formula_e', 'wrc', 'all'], default='all', help='Series to compile')
    parser.add_argument('--year', default='2026', help='Year to compile standings for')
    args = parser.parse_args()
    
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    
    series_list = [args.series] if args.series != 'all' else ['f1', 'motogp', 'nascar', 'indycar', 'formula_e', 'wrc']
    
    print(f"[INFO] Compiling standings for year: {args.year}, series: {args.series}")
    
    for s in series_list:
        print(f"[INFO] Compiling {s}...")
        # Since WRC standings are only in 2025/2024, if year is 2026 and series is wrc, we compile for 2025
        target_year = args.year
        if s == 'wrc' and args.year == '2026':
            target_year = '2025'
            
        if s == 'f1':
            compile_f1_standings(target_year, data_dir)
        elif s == 'motogp':
            compile_motogp_standings(target_year, data_dir)
        elif s == 'nascar':
            compile_nascar_standings(target_year, data_dir)
        elif s == 'indycar':
            compile_indycar_standings(target_year, data_dir)
        elif s == 'formula_e':
            compile_formula_e_standings(target_year, data_dir)
        elif s == 'wrc':
            compile_wrc_standings(target_year, data_dir)
            
    print("[SUCCESS] Standings compilation complete!")

if __name__ == '__main__':
    main()
