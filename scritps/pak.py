#!/usr/bin/env python3
# coding: utf-8
"""
pak.py - simple CLI to unpack/repack .pak files (no UI, no colors).
Place this script where you want the workspace to be; it will create:
  GAMEPATCH_FILES, UNPACK_FILES, REPACK_FILES, RESULT
"""

import argparse
import json
import os
import sys
import time
import zlib
import gzip
import io
import shutil
from pathlib import Path
from typing import Optional

# ---------------------- Base paths (script location) ------------------------
from pathlib import Path

# Base directory in Termux home/PAK
BASEDIR = Path.home() / "PAK"

GAMEPATCH_DIR = BASEDIR / "GAMEPATCH_FILES"
UNPACK_DIR = BASEDIR / "UNPACK_FILES"
REPACK_DIR = BASEDIR / "REPACK_FILES"
RESULT_DIR = BASEDIR / "RESULT"

# Create directories if they don't exist
for d in (GAMEPATCH_DIR, UNPACK_DIR, REPACK_DIR, RESULT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------- Config / constants ---------------------------------
SIG2KEY = {
    bytes.fromhex("9DC7"): bytes.fromhex("E55B4ED1"),
    # add more if needed
}

MAGIC_EXT = {
    0x9e2a83c1: ".uasset",
    0x61754c1b: ".lua",
    0x090a0d7b: ".dat",
    0x007bfeff: ".dat",
    0x200a0d7b: ".dat",
    0x27da0020: ".res",
    0x00000001: ".res",
    0x7bbfbbef: ".res",
    0x44484b42: ".bnk",
}

ZLIB_HEADERS = [b"\x78\x01", b"\x78\x5E", b"\x78\x9C", b"\x78\xDA"]
GZIP_HEADER = b"\x1F\x8B"

MIN_RESULT_SIZE = 32
MAX_OFFSET_TRY = 8

# ---------------------- Core helpers --------------------------------------
def is_sig_at(data: bytes, i: int) -> Optional[bytes]:
    if i + 2 > len(data):
        return None
    return SIG2KEY.get(data[i:i+2], None)

def xor_decode_with_feedback(data: bytes) -> bytes:
    """
    Decode encoded data using the feedback XOR algorithm (as in original).
    Fixed index increments to avoid infinite loops.
    """
    out = bytearray()
    key = None
    seg_pos = 0
    seg_start_out = 0
    i = 0
    L = len(data)
    while i < L:
        k = is_sig_at(data, i)
        if k is not None:
            key = k
            seg_pos = 0
            seg_start_out = len(out)
        if key is not None:
            # decode current byte
            if seg_pos < 4:
                o = data[i] ^ key[seg_pos]
            else:
                fb_index = seg_start_out + (seg_pos - 4)
                o = data[i] ^ out[fb_index]
            out.append(o)
            seg_pos += 1
            i += 1
        else:
            out.append(data[i])
            i += 1
    return bytes(out)

def xor_reencode_from_original(encoded_original: bytes, decoded_modified: bytes) -> bytes:
    """
    Re-encode the modified decoded bytes into XOR-encoded form using original encoded
    to locate key-change positions. Lengths must match.
    """
    assert len(encoded_original) == len(decoded_modified)
    out_enc = bytearray()
    key = None
    seg_pos = 0
    seg_start_out = 0
    L = len(decoded_modified)
    for i in range(L):
        k = is_sig_at(encoded_original, i)
        if k is not None:
            key = k
            seg_pos = 0
            seg_start_out = i
        if key is not None:
            if seg_pos < 4:
                b = decoded_modified[i] ^ key[seg_pos]
            else:
                fb_index = seg_start_out + (seg_pos - 4)
                b = decoded_modified[i] ^ decoded_modified[fb_index]
            out_enc.append(b)
            seg_pos += 1
        else:
            out_enc.append(decoded_modified[i])
    return bytes(out_enc)

def is_valid_zlib_header(b1: int, b2: int) -> bool:
    if (b1 & 0x0F) != 8:
        return False
    cmf_flg = (b1 << 8) | b2
    return (cmf_flg % 31) == 0

def guess_extension(blob: bytes) -> str:
    if len(blob) < 4:
        return ".uexp"
    magic = int.from_bytes(blob[:4], "little")
    return MAGIC_EXT.get(magic, ".uexp")

# ---------------------- decompression helpers ------------------------------
def try_decompress_at(buf: bytes, start: int, max_offset: int = MAX_OFFSET_TRY):
    """
    Try to decompress zlib/gzip at position start (with small offset tries).
    Returns dict with result, consumed, mode, ofs or None.
    """
    length = len(buf)
    modes = [("zlib", 15), ("gzip", 31)]
    for ofs in range(0, max_offset + 1):
        s = start + ofs
        if s >= length - 2:
            break
        for mode_name, wbits in modes:
            if mode_name == "zlib":
                b1 = buf[s]
                if b1 != 0x78:
                    continue
                b2 = buf[s + 1]
                if not is_valid_zlib_header(b1, b2):
                    continue
            if mode_name == "gzip":
                if s + 1 >= length:
                    continue
                if not (buf[s] == 0x1F and buf[s + 1] == 0x8B):
                    continue
            try:
                d = zlib.decompressobj(wbits)
                res = d.decompress(buf[s:])
                res += d.flush()
                consumed = len(buf[s:]) - len(d.unused_data)
                if not d.eof:
                    continue
                if consumed <= 0 or res is None or len(res) < MIN_RESULT_SIZE:
                    continue
                return {"result": res, "consumed": consumed, "mode": mode_name, "ofs": ofs}
            except Exception:
                continue
    return None

def compress_by_mode(raw_bytes: bytes, mode: str) -> bytes:
    if mode == "zlib":
        return zlib.compress(raw_bytes, level=9)
    elif mode == "gzip":
        bio = io.BytesIO()
        with gzip.GzipFile(fileobj=bio, mode="wb") as gzf:
            gzf.write(raw_bytes)
        return bio.getvalue()
    else:
        return zlib.compress(raw_bytes, level=9)

# ---------------------- scanning & extraction -----------------------------
def scan_and_extract_smart(data: bytes, out_dir: Path, manifest_path: Path):
    """
    Scans for zlib/gzip streams, decompresses them and writes extracted files into out_dir.
    Produces manifest.json with offsets and sizes.
    """
    count = 0
    pos = 0
    length = len(data)
    entries = []

    def find_next_candidate(p):
        idxs = []
        i = data.find(b"\x78", p)
        if i != -1:
            idxs.append(i)
        j = data.find(GZIP_HEADER, p)
        if j != -1:
            idxs.append(j)
        return min(idxs) if idxs else -1

    print(f"{'Offset':>10} | {'Size':>6} | {'Mode':<5} | {'Name':<20}")
    print("-" * 60)

    while True:
        cand = find_next_candidate(pos)
        if cand == -1 or cand >= length - 2:
            break
        trial = try_decompress_at(data, cand, MAX_OFFSET_TRY)
        if trial:
            res = trial["result"]
            consumed = trial["consumed"]
            ofs = trial["ofs"]
            mode = trial["mode"]

            count += 1
            ext = guess_extension(res)

            range_start = (count - 1) // 1000 * 1000
            range_end = range_start + 1000
            subdir = out_dir / f"{range_start}_{range_end}"
            subdir.mkdir(parents=True, exist_ok=True)

            fname = f"{count:06d}{ext}"
            outpath = subdir / fname
            outpath.write_bytes(res)

            relpath = str(outpath.relative_to(out_dir))
            start_pos = cand + ofs
            entries.append({
                "index": count,
                "start": start_pos,
                "consumed": consumed,
                "relpath": relpath,
                "ext": ext,
                "mode": mode,
            })

            print(f"0x{start_pos:08X} | {len(res):6d} | {mode:<5} | {fname:<20}")
            pos = start_pos + consumed
        else:
            pos = cand + 1

    manifest = {"total": count, "entries": entries}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 60)
    print(f"Total {count} files unpacked -> {out_dir}")
    print(f"Manifest saved -> {manifest_path}")
    return count

# ---------------------- CLI actions ---------------------------------------
def list_pak_files():
    files = sorted(GAMEPATCH_DIR.glob("*.pak"))
    if not files:
        print("No .pak files in GAMEPATCH_FILES.")
        return []
    for i, f in enumerate(files, 1):
        print(f"{i}. {f.name}")
    return files

def choose_pak_file(files, default_name=None):
    if not files:
        return None
    if default_name:
        for f in files:
            if f.name == default_name:
                return f
    # show list and prompt
    for i, f in enumerate(files, 1):
        print(f"{i}. {f.name}")
    try:
        choice = input("Select file by number: ").strip()
        idx = int(choice) - 1
        return files[idx]
    except Exception:
        print("Invalid selection.")
        return None

def do_unpack(selected: Path):
    if not selected:
        print("No file selected for unpack.")
        return
    outdir = UNPACK_DIR / selected.stem
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"Decoding XOR for: {selected.name}")
    data_enc = selected.read_bytes()
    decoded = xor_decode_with_feedback(data_enc)
    print("Scanning and extracting compressed streams...")
    manifest_path = outdir / "manifest.json"
    count = scan_and_extract_smart(decoded, outdir, manifest_path)
    print(f"Unpack finished: {count} files -> {outdir}")
    # create repack subdir hint (for user's convenience)
    repack_sub = REPACK_DIR / selected.stem
    repack_sub.mkdir(parents=True, exist_ok=True)
    print(f"Place edited files for repack in: {REPACK_DIR} (or {repack_sub})")

def find_repack_candidates(repack_dir: Path):
    # find files recursively; map filename -> path (if multiple same names, first wins)
    mapping = {}
    for p in repack_dir.rglob("*"):
        if p.is_file():
            mapping.setdefault(p.name, p)
    return mapping

def do_repack(selected: Path):
    if not selected:
        print("No file selected for repack.")
        return
    unpack_sub = UNPACK_DIR / selected.stem
    if not unpack_sub.exists():
        print("UNPACK not run for this file (no directory):", unpack_sub)
        return
    manifest_path = unpack_sub / "manifest.json"
    if not manifest_path.exists():
        print("manifest.json not found at:", manifest_path)
        return

    print("Decoding original encoded file...")
    data_enc_orig = selected.read_bytes()
    decoded = bytearray(xor_decode_with_feedback(data_enc_orig))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])

    repack_files_map = find_repack_candidates(REPACK_DIR)
    if not repack_files_map:
        print("No files found in REPACK_FILES. Place edited files there (flat or in subfolders).")
        return

    Repacked_cnt = skipped_cnt = not_found_cnt = 0

    print("Processing manifest entries and trying to patch from REPACK_FILES...")
    for e in entries:
        relpath = e["relpath"]
        start = int(e["start"])
        consumed = int(e["consumed"])
        mode = e.get("mode", "zlib")

        filename = Path(relpath).name
        src_edit = repack_files_map.get(filename)
        if not src_edit:
            not_found_cnt += 1
            continue
        try:
            raw = src_edit.read_bytes()
            comp = compress_by_mode(raw, mode)
            if len(comp) <= consumed:
                decoded[start:start+len(comp)] = comp
                if len(comp) < consumed:
                    decoded[start+len(comp):start+consumed] = b"\x00" * (consumed - len(comp))
                Repacked_cnt += 1
                print(f"Repacked {filename} | {len(comp)} <= slot {consumed} (mode:{mode})")
            else:
                skipped_cnt += 1
                print(f"Skipped {filename} | {len(comp)} > slot {consumed} (mode:{mode})")
        except Exception as ex:
            skipped_cnt += 1
            print(f"Error with {filename}: {ex}")

    print(f"Summary: {Repacked_cnt} Repacked, {skipped_cnt} skipped, {not_found_cnt} not found")
    if Repacked_cnt == 0:
        print("No files Repacked. Aborting write.")
        return

    print("Re-encoding XOR and writing result...")
    encoded_final = xor_reencode_from_original(data_enc_orig, bytes(decoded))
    result_file = RESULT_DIR / selected.name
    result_file.write_bytes(encoded_final)
    print(f"Repack complete -> {result_file} (size: {len(encoded_final)} bytes)")

# ---------------------- CLI entrypoint ------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Simple pak unpack/repack tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_list = sub.add_parser("list", help="List .pak files in GAMEPATCH_FILES")

    p_unpack = sub.add_parser("unpack", help="Unpack/Decode selected .pak")
    p_unpack.add_argument("file", nargs="?", help="Optional .pak filename to use (in GAMEPATCH_FILES)")
    p_unpack.add_argument("--loot", action="store_true", help="Auto-select loot file core_patch_4.0.0.20328.pak if present")
    p_unpack.add_argument("--kill", action="store_true", help="Auto-select kill file game_patch_4.0.0.20329.pak if present")

    p_repack = sub.add_parser("repack", help="Repack/Encode selected .pak (apply edited files from REPACK_FILES)")
    p_repack.add_argument("file", nargs="?", help="Optional .pak filename to use (in GAMEPATCH_FILES)")
    p_repack.add_argument("--loot", action="store_true", help="Auto-select loot file core_patch_4.0.0.20328.pak if present")
    p_repack.add_argument("--kill", action="store_true", help="Auto-select kill file game_patch_4.0.0.20329.pak if present")

    sub_clear = sub.add_parser("clear-unpack", help="Clear UNPACK_FILES folder")

    args = parser.parse_args()

    if args.cmd == "list":
        list_pak_files()
        return

    files = sorted(GAMEPATCH_DIR.glob("*.pak"))
    if args.cmd in ("unpack", "repack"):
        chosen_file = None
        # priority: explicit filename arg -> loot/kill flags -> interactive choice
        target_name = None
        if getattr(args, "file", None):
            target_name = args.file
        elif getattr(args, "loot", False):
            target_name = "core_patch_4.0.0.20328.pak"
        elif getattr(args, "kill", False):
            target_name = "game_patch_4.0.0.20329.pak"

        if target_name:
            # try to find exact match
            for f in files:
                if f.name == target_name:
                    chosen_file = f
                    break
            if not chosen_file:
                print(f"Requested file '{target_name}' not found in {GAMEPATCH_DIR}")
                return
        else:
            if not files:
                print("No .pak files found. Place your .pak files in:", GAMEPATCH_DIR)
                return
            # interactive choose
            chosen_file = choose_pak_file(files)

        if not chosen_file:
            return

        if args.cmd == "unpack":
            do_unpack(chosen_file)
        else:
            do_repack(chosen_file)
        return

    if args.cmd == "clear-unpack":
        if UNPACK_DIR.exists():
            shutil.rmtree(UNPACK_DIR)
            UNPACK_DIR.mkdir(parents=True, exist_ok=True)
            print("UNPACK_FILES cleared.")
        else:
            print("UNPACK_FILES already empty.")
        return

if __name__ == "__main__":
    main()
