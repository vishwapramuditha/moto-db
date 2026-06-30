import os, glob
import json

def resolve_conflicts_in_file(filepath):
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    in_conflict = False
    keep_section = False
    
    for line in lines:
        if line.startswith("<<<<<<< HEAD"):
            in_conflict = True
            keep_section = True
            continue
        elif line.startswith("======="):
            if in_conflict:
                keep_section = False
                continue
        elif line.startswith(">>>>>>>"):
            if in_conflict:
                in_conflict = False
                keep_section = True
                continue
        
        if not in_conflict:
            new_lines.append(line)
        elif in_conflict and keep_section:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Resolved conflicts in {filepath}")

files = [
    r"data\indycar\2026\schedule.json",
    r"data\f1\2025\schedule.json",
    r"data\f1\2026\schedule.json",
    r"data\wrc\2025\schedule.json",
    r"data\wrc\2026\schedule.json",
    r"data\motogp\2026\schedule.json"
]

for f in files:
    full_path = os.path.join(r"f:\Dev\Projects\moto-db", f)
    resolve_conflicts_in_file(full_path)
    
    # Try parsing to make sure it is valid JSON
    try:
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"Successfully validated JSON for {f}")
    except Exception as e:
        print(f"ERROR parsing JSON for {f}: {e}")
