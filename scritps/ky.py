#!/usr/bin/env python3
import os
import re
import shutil
import time
import zlib
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich import box

console = Console()

# ───── CONFIG ────────────────────────────────────────────────────────────────
import os

BASE_MOD_DIR = os.path.expanduser("~")  # Termux home directory
GAME_DIRS = {"PAK/kill": os.path.join(BASE_MOD_DIR, "PAK", "kill")}
OUTPUT_DIR_NAME = "org"
EDITED_DIR_NAME = "edited"
KILLMSG_FILE = os.path.join(BASE_MOD_DIR, "PAK", "kill", "killmsg.txt")  # File inside Termux home PAK/kill/
MAX_COMPRESSED_SIZE = 6689  # Maximum allowed compressed size
# ───── CORE LOGIC FUNCTIONS ──────────────────────────────────────────────────
def load_killmsg_patterns():
    """Load long hex patterns from killmsg.txt file"""
    patterns = {}
    
    if not os.path.exists(KILLMSG_FILE):
        console.print(f"[red]✖ {KILLMSG_FILE} not found[/]")
        return patterns
    
    try:
        with open(KILLMSG_FILE, 'r') as f:
            content = f.read().strip()
        
        # Parse the file content - expected format: ID - HEXPATTERN
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if '-' in line:
                parts = line.split('-', 1)
                id_part = parts[0].strip()
                hex_part = parts[1].strip()
                
                # Convert hex string to bytes
                try:
                    hex_bytes = bytes.fromhex(hex_part)
                    patterns[id_part] = hex_bytes
                except ValueError:
                    console.print(f"[yellow]⚠ Invalid hex pattern for {id_part}: {hex_part}[/]")
    
    except Exception as e:
        console.print(f"[red]✖ Error reading {KILLMSG_FILE}: {e}[/]")
    
    return patterns

def get_compressed_size(data):
    """Get the compressed size of data using zlib"""
    compressed = zlib.compress(data)
    return len(compressed)

def apply_nulls_to_meet_size(file_path, modified_patterns):
    """Apply nulls to meet the size requirement - keep applying until size is under limit"""
    # Extract all destination patterns that we've modified
    modified_bytes = []
    for swaps in modified_patterns:
        for _, dst_pattern in swaps:
            modified_bytes.append(dst_pattern)
    
    # Extended null IDs list - more patterns to null
    null_ids = [
        # Original patterns
        b"601001001", b"601001002", b"601001003", b"601001004", b"601001005",
        b"601002001", b"601002002", b"601002003", b"601002004", b"601002005",
        b"601003001", b"601003002", b"601003003", b"601003004", b"601003005",
        b"601004001", b"601004002", b"601004003", b"601004004", b"601004005",
        b"601005001", b"601005002", b"601005003", b"601005004", b"601005005",
        b"601006001", b"601006002", b"601006003", b"601006004", b"601006005",
        b"601007001", b"601007002", b"601007003", b"601007004", b"601007005",
        b"601008001", b"601008002", b"601008003", b"601008004", b"601008005",
        b"601009001", b"601009002", b"601009003", b"601009004", b"601009005",
        b"601010001", b"601010002", b"601010003", b"601010004", b"601010005",
        
        # Additional patterns - more specific to find more null opportunities
        b"602001001", b"602001002", b"602001003", b"602001004", b"602001005",
        b"602002001", b"602002002", b"602002003", b"602002004", b"602002005",
        b"603001001", b"603001002", b"603001003", b"603001004", b"603001005",
        b"604001001", b"604001002", b"604001003", b"604001004", b"604001005",
        
        # Even more patterns - try to find any 9-digit number pattern
        b"605001001", b"605001002", b"605001003", b"605001004", b"605001005",
        b"606001001", b"606001002", b"606001003", b"606001004", b"606001005",
        b"607001001", b"607001002", b"607001003", b"607001004", b"607001005",
        b"608001001", b"608001002", b"608001003", b"608001004", b"608001005",
        b"609001001", b"609001002", b"609001003", b"609001004", b"609001005",
        b"610001001", b"610001002", b"610001003", b"610001004", b"610001005",
        
        # Try some common patterns that might exist
        b"611001001", b"611001002", b"611001003", b"611001004", b"611001005",
        b"612001001", b"612001002", b"612001003", b"612001004", b"612001005",
        b"613001001", b"613001002", b"613001003", b"613001004", b"613001005",
        b"614001001", b"614001002", b"614001003", b"614001004", b"614001005",
        b"615001001", b"615001002", b"615001003", b"615001004", b"615001005",
    ]
    
    # Read the file
    with open(file_path, 'rb') as f:
        data = bytearray(f.read())
    
    # Calculate initial compressed size
    compressed_size = get_compressed_size(data)
    if compressed_size <= MAX_COMPRESSED_SIZE:
        return 0  # No nulls needed
    
    console.print(f"[yellow]File exceeds size limit by {compressed_size - MAX_COMPRESSED_SIZE} bytes[/]")
    
    # Keep applying nulls until we meet the size requirement
    nulls_applied = 0
    max_attempts = 200  # Increased safety limit
    
    for attempt in range(max_attempts):
        # Find and collect all matches
        matches = []
        for id_bytes in null_ids:
            start_search = 0
            while (pos := data.find(id_bytes, start_search)) >= 0:
                # Check if this position overlaps with any modified pattern
                overlap = False
                for modified in modified_bytes:
                    # Check if this null ID is within the modified pattern
                    for check_pos in range(max(0, pos - len(modified) + 1), min(len(data), pos + len(id_bytes))):
                        check_end = check_pos + len(modified)
                        if check_end <= len(data) and data[check_pos:check_end] == modified:
                            overlap = True
                            break
                    if overlap:
                        break
                
                if not overlap:
                    matches.append((pos, id_bytes))
                start_search = pos + 1
        
        if not matches:
            console.print("[red]No more null patterns found to apply[/]")
            
            # As a last resort, try to find any 9-digit number pattern
            console.print("[yellow]Trying to find any 9-digit number pattern as last resort[/]")
            digit_pattern = re.compile(rb'\d{9}')
            digit_matches = list(digit_pattern.finditer(data))
            
            for match in digit_matches:
                pos = match.start()
                id_bytes = data[pos:pos+9]
                
                # Check if this overlaps with any modified pattern
                overlap = False
                for modified in modified_bytes:
                    for check_pos in range(max(0, pos - len(modified) + 1), min(len(data), pos + 9)):
                        check_end = check_pos + len(modified)
                        if check_end <= len(data) and data[check_pos:check_end] == modified:
                            overlap = True
                            break
                    if overlap:
                        break
                
                if not overlap:
                    matches.append((pos, id_bytes))
            
            if not matches:
                console.print("[red]No patterns found even with regex search[/]")
                break
        
        # Sort by position (reverse to avoid offset issues)
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Apply nulling to multiple patterns in each attempt
        applied_in_this_attempt = 0
        for pos, id_bytes in matches:
            if pos + len(id_bytes) + 5 > len(data):
                continue
                
            # Check boundaries
            before = data[pos - 1:pos] if pos > 0 else None
            after = data[pos + len(id_bytes) + 5:pos + len(id_bytes) + 6] if pos + len(id_bytes) + 5 < len(data) else None
            
            if (before and before in b"0123456789") or (after and after in b"0123456789"):
                continue
            
            # Null the pattern
            data[pos:pos + len(id_bytes) + 5] = b'\x00' * (len(id_bytes) + 5)
            nulls_applied += 1
            applied_in_this_attempt += 1
            
            # Apply multiple nulls per attempt to be more aggressive
            if applied_in_this_attempt >= 3:  # Apply up to 3 nulls per attempt
                break
        
        # Check if we've met the size requirement
        new_compressed_size = get_compressed_size(data)
        if new_compressed_size <= MAX_COMPRESSED_SIZE:
            console.print(f"[green]Size requirement met after {nulls_applied} nulls[/]")
            break
        
        if applied_in_this_attempt == 0:
            console.print("[red]Could not apply any more nulls[/]")
            break
    
    # Write back the modified data
    with open(file_path, 'wb') as f:
        f.write(data)
    
    # Final size check
    final_compressed_size = get_compressed_size(data)
    console.print(f"[cyan]Final compressed size: {final_compressed_size} bytes (limit: {MAX_COMPRESSED_SIZE})[/]")
    
    if final_compressed_size > MAX_COMPRESSED_SIZE:
        console.print(f"[red]❌ WARNING: File still exceeds size limit by {final_compressed_size - MAX_COMPRESSED_SIZE} bytes[/]")
        console.print(f"[yellow]Trying one more approach: aggressive nulling of any patterns[/]")
        
        # Last resort: try to find any pattern that looks like an ID and null it
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())
        
        # Look for any 9-digit number that's not part of modified patterns
        digit_pattern = re.compile(rb'\d{9}')
        matches = list(digit_pattern.finditer(data))
        
        for match in matches:
            pos = match.start()
            id_bytes = data[pos:pos+9]
            
            # Check if this overlaps with any modified pattern
            overlap = False
            for modified in modified_bytes:
                for check_pos in range(max(0, pos - len(modified) + 1), min(len(data), pos + 9)):
                    check_end = check_pos + len(modified)
                    if check_end <= len(data) and data[check_pos:check_end] == modified:
                        overlap = True
                        break
                if overlap:
                    break
            
            if not overlap and pos + 14 <= len(data):
                # Null the pattern
                data[pos:pos + 14] = b'\x00' * 14
                nulls_applied += 1
                
                # Check if we've met the size requirement
                new_compressed_size = get_compressed_size(data)
                if new_compressed_size <= MAX_COMPRESSED_SIZE:
                    console.print(f"[green]Size requirement met after aggressive nulling[/]")
                    break
        
        # Write back the modified data
        with open(file_path, 'wb') as f:
            f.write(data)
        
        # Final final size check
        final_compressed_size = get_compressed_size(data)
        console.print(f"[cyan]Final compressed size after aggressive nulling: {final_compressed_size} bytes[/]")
    
    return nulls_applied

def mod_skin_flow(id_pairs):
    console.clear()
    console.print(Panel("[bold bright_cyan]🚀 Processing Started[/]", expand=False, border_style="cyan"))
    
    # Load long hex patterns from killmsg.txt
    killmsg_patterns = load_killmsg_patterns()
    if not killmsg_patterns:
        console.print("[red]✖ No valid patterns found in killmsg.txt[/]")
        return
    
    game_base_dir = GAME_DIRS["PAK/kill"]
    output_dir = os.path.join(game_base_dir, OUTPUT_DIR_NAME)
    edited_dir = os.path.join(game_base_dir, EDITED_DIR_NAME)

    if not os.path.isdir(output_dir):
        console.print(f"[red]✖ Source directory not found: {output_dir}[/]")
        return

    # Get all files (including 000258.uasset)
    all_files = []
    for fn in os.listdir(output_dir):
        path = os.path.join(output_dir, fn)
        if os.path.isfile(path):
            all_files.append(path)
    
    console.print(f"[green]✔ Found {len(all_files)} files to process.[/]")
    if not all_files:
        return

    # Cache all file contents
    cache = {p: open(p, 'rb').read() for p in all_files}

    if not id_pairs:
        console.print("[yellow]⚠ No valid ID pairs provided.[/]")
        return

    # Build replacement map using patterns from killmsg.txt
    replacement_map = {}
    for id1, id2 in id_pairs:
        if id1 in killmsg_patterns and id2 in killmsg_patterns:
            src_pattern = killmsg_patterns[id1]
            dst_pattern = killmsg_patterns[id2]
            replacement_map[(id1, id2)] = [(src_pattern, dst_pattern)]
            console.print(f"[OK] {id1}<{id2}")
        else:
            missing_ids = []
            if id1 not in killmsg_patterns:
                missing_ids.append(id1)
            if id2 not in killmsg_patterns:
                missing_ids.append(id2)
           # console.print(f"[yellow]⚠ Patterns not found for IDs: {', '.join(missing_ids)}[/]")

    if not replacement_map:
        #console.print("[red]✖ No valid replacement patterns found for the provided IDs[/]")
        return

    # Find valid files
    valid_files = []
    patterns_to_find = [pattern for swaps in replacement_map.values() for pattern, _ in swaps]
    
    for file_path, data in cache.items():
        for pattern in patterns_to_find:
            if pattern in data:
                valid_files.append(file_path)
                break

    if not valid_files:
        console.print("[yellow]⚠ No files contain specified patterns.[/]")
        return

    # Create/clear edited directory
    if os.path.isdir(edited_dir):
        shutil.rmtree(edited_dir)
    os.makedirs(edited_dir, exist_ok=True)

    # Copy and process files
    console.print(f"[cyan]📋 Processing {len(valid_files)} files[/]")
    
    progress = Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))
    
    total_nulls_applied = 0
    with Live(progress, refresh_per_second=10) as live:
        task = progress.add_task("[cyan]Modifying files...", total=len(valid_files))
        
        for src_path in sorted(valid_files):
            filename = os.path.basename(src_path)
            progress.update(task, advance=1, description=f"[cyan]Processing {filename}[/]")
            
            # Copy to edited directory
            edited_path = os.path.join(edited_dir, filename)
            shutil.copy2(src_path, edited_path)
            
            # Load and modify
            orig = open(edited_path, 'rb').read()
            new = bytearray(orig)
            
            # Apply pattern replacements
            modified = False
            for swaps in replacement_map.values():
                for src_pattern, dst_pattern in swaps:
                    # Simple replacement (no regex needed as we have exact patterns)
                    offset = 0
                    while True:
                        pos = new.find(src_pattern, offset)
                        if pos == -1:
                            break
                        # Replace the pattern
                        new[pos:pos + len(src_pattern)] = dst_pattern
                        offset = pos + len(dst_pattern)
                        modified = True
            
            # Write modified file
            if modified:
                with open(edited_path, 'wb') as f:
                    f.write(new)
                
                # Apply nulls to meet size requirements
                nulls_applied = apply_nulls_to_meet_size(edited_path, replacement_map.values())
                total_nulls_applied += nulls_applied
            
            time.sleep(0.02)

    console.print(Panel("[bold green]✔ Modding Complete[/]", expand=False, border_style="green"))
    
    # Summary
    summary_table = Table(title="[bold]Processing Summary[/]", box=box.MINIMAL_HEAVY_HEAD)
    summary_table.add_column("Metric", style="bold magenta")
    summary_table.add_column("Value", style="white")
    summary_table.add_row("Files Processed", str(len(valid_files)))
    summary_table.add_row("Total Nulls Applied", str(total_nulls_applied))
    summary_table.add_row("Max Compressed Size", str(MAX_COMPRESSED_SIZE))
    console.print(summary_table)

import os
import re
from rich.console import Console

console = Console()

def main():
    console.clear()
    console.print("[bold bright_cyan]ZSDIC SKIN MODDING TOOL[/]\n")

    file_path = os.path.expanduser("~/SKIN/hit1.txt")

    if not os.path.exists(file_path):
        console.print(f"[red]✖ Input file not found:[/] {file_path}")
        return

    # Read file
    with open(file_path, "r", encoding="utf-8") as f:
        raw_input = f.read().strip()

    if not raw_input:
        console.print("[red]✖ File is empty. Exiting.[/]")
        return

    # Normalize input: treat commas and spaces as separators
    raw_input = re.sub(r'[,\s]+', ' ', raw_input)
    parts = raw_input.split()

    if len(parts) % 2 != 0:
        console.print("[red]✖ Error: Uneven number of IDs in file. Provide pairs of IDs.[/]")
        return

    pairs = [(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    console.print(f"[green]✔ Found {len(pairs)} ID pairs from file[/]")

    mod_skin_flow(pairs)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]✖ Program interrupted. Exiting.[/]")
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {e}[/]")
        import traceback
        traceback.print_exc()
