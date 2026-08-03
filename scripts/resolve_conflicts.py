import os
import glob
import json
import argparse

# Resolve the repo root relative to this script's location
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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


def main():
    parser = argparse.ArgumentParser(
        description="Resolve git merge conflicts in JSON data files, keeping the HEAD (local) version."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Relative paths (from repo root) of JSON files to resolve. "
             "Defaults to common schedule files if none specified.",
    )
    args = parser.parse_args()

    if args.files:
        relative_paths = args.files
    else:
        # Default set of files most likely to hit conflicts during concurrent CI runs
        relative_paths = [
            "data/indycar/2026/schedule.json",
            "data/f1/2025/schedule.json",
            "data/f1/2026/schedule.json",
            "data/wrc/2025/schedule.json",
            "data/wrc/2026/schedule.json",
            "data/motogp/2026/schedule.json",
        ]

    for rel_path in relative_paths:
        full_path = os.path.join(REPO_ROOT, rel_path.replace("\\", os.sep))
        if not os.path.exists(full_path):
            print(f"SKIP: {full_path} does not exist.")
            continue
        resolve_conflicts_in_file(full_path)
        # Validate the result is parseable JSON
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"  ✓ JSON valid: {rel_path}")
        except Exception as e:
            print(f"  ✗ JSON parse error for {rel_path}: {e}")


if __name__ == "__main__":
    main()

