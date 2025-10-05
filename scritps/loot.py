#!/usr/bin/env python3
"""
Simple Hit modder (no colors).

Usage:
- Put decimal pairs in ~/hit1.txt (one per line, DEC1,DEC2)
- Put mapping in ~/hit.txt (lines like: id | hexcode | name)
- Run: python hit

Modifies copies only; originals remain in org/.
"""
import sys
from pathlib import Path

# Paths (Termux home)
HOME = str(Path.home())
ORG_DIR = Path(f"{HOME}/PAK/loot/input/")
MODIFIED_DIR = Path(f"{HOME}/PAK/REPACK_FILES/")
INPUT_FILE = Path(f"{HOME}/SKIN/hit1.txt")
MAPPING_FILE = Path(f"{HOME}/SKIN/hit.txt")

def dec_to_le4_hex(n_str: str) -> str:
    n_str = n_str.strip()
    if not n_str:
        raise ValueError("empty decimal")
    n = int(n_str, 10)
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError("decimal out of 32-bit range")
    return n.to_bytes(4, 'little').hex()

def parse_mapping_file(path: Path) -> set:
    out = set()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if '|' in ln:
            parts = [p.strip() for p in ln.split('|')]
            if len(parts) >= 2 and parts[1]:
                h = parts[1].lower().replace("0x","").strip()
                h = ''.join(ch for ch in h if ch.isalnum())
                if h and len(h) % 2 == 0:
                    out.add(h)
        else:
            parts = ln.split()
            if len(parts) >= 2:
                h = parts[1].lower().replace("0x","").strip()
                h = ''.join(ch for ch in h if ch.isalnum())
                if h and len(h) % 2 == 0:
                    out.add(h)
    return out

def clear_modified():
    try:
        if not MODIFIED_DIR.exists():
            MODIFIED_DIR.mkdir(parents=True, exist_ok=True)
            return
        for f in MODIFIED_DIR.iterdir():
            if f.is_file():
                f.unlink()
    except Exception as e:
        print("Error clearing modified folder:", e)

def main():
    # sanity checks
    if not ORG_DIR.exists() or not ORG_DIR.is_dir():
        print("ORG directory not found:", ORG_DIR)
        sys.exit(1)
    if not INPUT_FILE.exists() or not INPUT_FILE.is_file():
        print("Input file not found:", INPUT_FILE)
        sys.exit(1)

    # Read decimal pairs from hit1.txt
    raw_pairs = []
    with INPUT_FILE.open("r", encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            if ',' not in ln:
                print("Skipping invalid line (expect DEC1,DEC2):", ln)
                continue
            a,b = ln.split(",",1)
            try:
                ha = dec_to_le4_hex(a)
                hb = dec_to_le4_hex(b)
            except Exception as e:
                print("Skipping invalid decimal line:", ln, "->", e)
                continue
            raw_pairs.append([ha, hb, "NO"])

    if not raw_pairs:
        print("No valid pairs found in", INPUT_FILE)
        return

    # Check phase
    print("Checking converted hex1 presence in ORG files...")
    for pair in raw_pairs:
        hex1 = pair[0]
        b1 = bytes.fromhex(hex1)
        found = False
        for file_path in ORG_DIR.iterdir():
            if not file_path.is_file():
                continue
            try:
                if b1 in file_path.read_bytes():
                    found = True
                    break
            except Exception:
                continue
        if found:
            pair[2] = "OK"
            print("[OK]",hex1)
        else:
            print("[NO]",hex1)

    # hex2 to keep (converted)
    hex2_keep = { pair[1] for pair in raw_pairs if pair[2] == "OK" }

    # parse mapping file from HOME/hit.txt (if exists)
    mapping_hexes = set()
    if MAPPING_FILE.exists() and MAPPING_FILE.is_file():
        mapping_hexes = parse_mapping_file(MAPPING_FILE)
        print("Mapping file used:", MAPPING_FILE.name, "entries:", len(mapping_hexes))
    else:
        print("Mapping file not found at", MAPPING_FILE, "- skipping zeroing step.")

    # Determine which mapping hexes to zero (exclude kept hex2)
    to_zero_hexes = set()
    if mapping_hexes:
        keep_norm = { h.lower().replace("0x","") for h in hex2_keep }
        for h in mapping_hexes:
            if h not in keep_norm:
                to_zero_hexes.add(h)
        print("Will zero", len(to_zero_hexes), "mapping hex(es).")

    # Replacement phase
    print("Starting replacement phase...")
    clear_modified()
    files_processed = 0
    files_modified = 0

    for file_path in ORG_DIR.iterdir():
        if not file_path.is_file():
            continue
        files_processed += 1
        try:
            data = file_path.read_bytes()
        except Exception as e:
            print("Error reading", file_path.name, "->", e)
            continue
        original = data

        # Replace OK hex1 -> hex2
        for hex1, hex2, status in raw_pairs:
            if status == "OK":
                b1 = bytes.fromhex(hex1)
                b2 = bytes.fromhex(hex2)
                if b1 in data:
                    data = data.replace(b1, b2)

        # Zero out mapping hexes not in keep
        for hz in to_zero_hexes:
            b = bytes.fromhex(hz)
            if b in data:
                zero_bytes = b'\x00' * len(b)
                data = data.replace(b, zero_bytes)

        if data != original:
            out_path = MODIFIED_DIR / file_path.name
            try:
                out_path.write_bytes(data)
                files_modified += 1
                print("Modified:", file_path.name)
            except Exception as e:
                print("Failed to write modified", file_path.name, "->", e)
        else:
            print("No changes in:", file_path.name)

    
    print("Processed files:", files_processed)
    print("Modified files:", files_modified)
    print("Modified:", MODIFIED_DIR)

if __name__ == "__main__":
    main()
