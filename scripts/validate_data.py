import os
import json
import re
import sys

# Ensure UTF-8 output if supported, else fallback gracefully
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_RE = re.compile(r'^\d{2}:\d{2}:\d{2}Z$')


def validate_sessions(sessions, file_path, race_idx):
    """Validate the sessions[] array for a single race entry.

    Different series use different session schemas:
    - Standard (F1, F3, WRC, Formula E): { type, name, date (YYYY-MM-DD), time (HH:MM:SSZ) }
    - MotoGP: { type, name, category, datetime (ISO-8601), status }
    - WEC: { name, date (ISO-8601 with TZ offset), status, completed }

    We enforce: each session is an object and has at least a 'name'.
    For sessions that have 'date' / 'time' as separate fields, we validate the format.
    """
    ok = True
    if not isinstance(sessions, list):
        print(f"[ERROR] DATA ERROR: {file_path} race[{race_idx}].sessions is not a list.")
        return False
    if len(sessions) == 0:
        print(f"[WARN]  DATA WARN:  {file_path} race[{race_idx}].sessions is empty.")
        return True
    for s_idx, session in enumerate(sessions):
        if not isinstance(session, dict):
            print(f"[ERROR] DATA ERROR: {file_path} race[{race_idx}].sessions[{s_idx}] is not an object.")
            ok = False
            continue
        # All sessions must at minimum have a name
        if 'name' not in session:
            print(f"[ERROR] DATA ERROR: {file_path} race[{race_idx}].sessions[{s_idx}] missing 'name'.")
            ok = False
        # Only enforce YYYY-MM-DD on 'date' if it looks like a date-only field (no T in value)
        if 'date' in session and isinstance(session['date'], str):
            val = session['date']
            if 'T' not in val and not DATE_RE.match(val):
                print(f"[ERROR] FORMAT ERROR: {file_path} race[{race_idx}].sessions[{s_idx}].date "
                      f"'{val}' is not YYYY-MM-DD.")
                ok = False
        # Only enforce HH:MM:SSZ on 'time' if it is present as a separate field
        if 'time' in session and isinstance(session['time'], str):
            val = session['time']
            if not TIME_RE.match(val):
                print(f"[ERROR] FORMAT ERROR: {file_path} race[{race_idx}].sessions[{s_idx}].time "
                      f"'{val}' is not HH:MM:SSZ.")
                ok = False
    return ok

def validate_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] SYNTAX ERROR: {file_path} is not valid JSON. Error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] READ ERROR: Failed to read {file_path}. Error: {e}")
        return False
        
    filename = os.path.basename(file_path)
    
    # 1. Drivers metadata validation
    if filename == 'drivers.json':
        drivers_list = None
        if isinstance(data, list):
            drivers_list = data
        elif isinstance(data, dict) and 'drivers' in data and isinstance(data['drivers'], list):
            drivers_list = data['drivers']
            
        if drivers_list is None:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} must be a list of drivers or a dictionary with a 'drivers' list key.")
            return False
            
        for idx, driver in enumerate(drivers_list):
            if not isinstance(driver, dict):
                print(f"[ERROR] DATA ERROR: {file_path} driver at index {idx} is not an object.")
                return False
            has_id = any(k in driver for k in ['driverId', 'id', 'riders_id', 'riderId', 'uuid'])
            if not has_id:
                print(f"[ERROR] DATA ERROR: {file_path} driver at index {idx} is missing a driver identification key.")
                return False
                
    # 2. Tracks metadata validation
    elif filename == 'tracks.json':
        tracks_list = None
        if isinstance(data, list):
            tracks_list = data
        elif isinstance(data, dict):
            for k in ['tracks', 'circuits', 'locations']:
                if k in data and isinstance(data[k], list):
                    tracks_list = data[k]
                    break
        
        if tracks_list is None:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} must be a list of tracks or a dictionary with a tracks list key.")
            return False
            
        for idx, track in enumerate(tracks_list):
            if not isinstance(track, dict):
                print(f"[ERROR] DATA ERROR: {file_path} track at index {idx} is not an object.")
                return False
            has_id = any(k in track for k in ['circuitId', 'id', 'trackId', 'circuitName'])
            if not has_id:
                print(f"[ERROR] DATA ERROR: {file_path} track at index {idx} is missing an identification key.")
                return False
                
    # 3. Schedule files validation
    elif filename == 'schedule.json':
        races_lists = []
        
        if isinstance(data, list):
            races_lists.append(data)
        elif isinstance(data, dict):
            has_season = any(k in data for k in ['season', 'year', 'season_year', 'series'])
            if not has_season:
                print(f"[ERROR] DATA ERROR: {file_path} is missing a 'season' or 'year' field.")
                return False
                
            if 'series' in data and isinstance(data['series'], dict):
                for series_name, series_list in data['series'].items():
                    if isinstance(series_list, list):
                        races_lists.append(series_list)
            else:
                found_list = False
                for k in ['races', 'schedule', 'events', 'rounds']:
                    if k in data and isinstance(data[k], list):
                        races_lists.append(data[k])
                        found_list = True
                        break
                if not found_list:
                    print(f"[ERROR] STRUCTURE ERROR: {file_path} schedule must contain an events/races list.")
                    return False
        else:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} schedule must be a list or a dictionary.")
            return False

        if not races_lists:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} schedule does not contain any races to validate.")
            return False
            
        for races_list in races_lists:
            for idx, race in enumerate(races_list):
                if not isinstance(race, dict):
                    print(f"[ERROR] DATA ERROR: {file_path} race event at index {idx} is not an object.")
                    return False
                has_name = any(k in race for k in ['raceName', 'name', 'event_name', 'title', 'race_name', 'eprix', 'circuit'])
                if not has_name:
                    print(f"[ERROR] DATA ERROR: {file_path} race event at index {idx} is missing a name/title/eprix/race_name.")
                    return False
                # Validate sessions[] if present
                if 'sessions' in race:
                    if not validate_sessions(race['sessions'], file_path, idx):
                        return False

        # Assert total_rounds / total_races matches actual race count if the field is present
        if isinstance(data, dict):
            for count_key in ('total_rounds', 'total_races'):
                if count_key in data:
                    total_actual = sum(len(rl) for rl in races_lists)
                    if data[count_key] != total_actual:
                        print(f"[ERROR] DATA ERROR: {file_path} '{count_key}' is {data[count_key]} "
                              f"but actual race count is {total_actual}.")
                        return False
    # 4. Results files validation
    elif filename == 'results.json':
        # Accept either a plain list OR a wrapped dict { "season": ..., "results": [...] }
        if isinstance(data, dict):
            has_season = any(k in data for k in ['season', 'year', 'season_year'])
            if not has_season:
                print(f"[ERROR] DATA ERROR: {file_path} wrapped results.json is missing a 'season' field.")
                return False
            results_list = data.get('results')
            if not isinstance(results_list, list):
                print(f"[ERROR] STRUCTURE ERROR: {file_path} wrapped results.json must have a 'results' list.")
                return False
        elif isinstance(data, list):
            results_list = data
        else:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} results.json must be a list or a wrapped dict.")
            return False
        for idx, item in enumerate(results_list):
            if not isinstance(item, dict):
                print(f"[ERROR] DATA ERROR: {file_path} item at index {idx} is not an object.")
                return False
            if 'round' not in item:
                print(f"[ERROR] DATA ERROR: {file_path} item at index {idx} is missing a 'round' field.")
                return False

    elif filename.startswith('results_') or filename.endswith('_RAC.json') or filename.endswith('_SPR.json'):
        if not isinstance(data, dict):
            print(f"[ERROR] STRUCTURE ERROR: {file_path} results file must be an object (dict).")
            return False
            
        has_season = any(k in data for k in ['season', 'year', 'season_year'])
        if not has_season:
            print(f"[ERROR] DATA ERROR: {file_path} is missing a season/year field.")
            return False
            
        results_list = None
        for k in ['results', 'standings', 'classification', 'entries']:
            if k in data and isinstance(data[k], list):
                results_list = data[k]
                break
                
        if results_list is None:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} results must contain a results list.")
            return False
            
        for idx, result in enumerate(results_list):
            if not isinstance(result, dict):
                print(f"[ERROR] DATA ERROR: {file_path} result item at index {idx} is not an object.")
                return False
            has_pos = any(k in result for k in ['position', 'pos', 'finish_position', 'classification'])
            if not has_pos:
                print(f"[ERROR] DATA ERROR: {file_path} result item at index {idx} is missing a position field.")
                return False
                
    # 5. Standings files validation
    elif filename == 'standings.json':
        if not isinstance(data, dict):
            print(f"[ERROR] STRUCTURE ERROR: {file_path} standings file must be an object (dict).")
            return False
            
        has_season = any(k in data for k in ['season', 'year', 'season_year'])
        if not has_season:
            print(f"[ERROR] DATA ERROR: {file_path} is missing a season/year field.")
            return False
            
        standings_list = None
        for k in ['driverStandings', 'riderStandings', 'teamStandings', 'constructorStandings', 'entrantStandings', 
                  'hypercarDriverStandings', 'hypercarTeamStandings', 'lmgt3DriverStandings', 'lmgt3TeamStandings']:
            if k in data and isinstance(data[k], list):
                standings_list = data[k]
                break
                
        if standings_list is None:
            print(f"[ERROR] STRUCTURE ERROR: {file_path} standings must contain a standings list (e.g. driverStandings, riderStandings, hypercarDriverStandings).")
            return False
            
        for idx, standing in enumerate(standings_list):
            if not isinstance(standing, dict):
                print(f"[ERROR] DATA ERROR: {file_path} standing item at index {idx} is not an object.")
                return False
            has_pos = any(k in standing for k in ['position', 'pos'])
            if not has_pos:
                print(f"[ERROR] DATA ERROR: {file_path} standing item at index {idx} is missing a position field.")
                return False
                
    return True

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    if not os.path.exists(data_dir):
        print(f"[ERROR] Data directory '{data_dir}' not found.")
        sys.exit(1)
        
    print(f"[INFO] Starting validation of JSON files in data directory: {data_dir}")
    total_files = 0
    failed_files = 0
    
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.json'):
                total_files += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, data_dir)
                is_valid = validate_json_file(file_path)
                if not is_valid:
                    print(f"  └─ File failing: data/{rel_path}")
                    failed_files += 1
                    
    print("\n--- Validation Summary ---")
    print(f"Total JSON Files Scanned: {total_files}")
    if failed_files > 0:
        print(f"[ERROR] Validation FAILED: {failed_files} file(s) failed validation checks.")
        sys.exit(1)
    else:
        print("[SUCCESS] Validation PASSED: All files are syntactically and structurally correct!")
        sys.exit(0)

if __name__ == '__main__':
    main()
