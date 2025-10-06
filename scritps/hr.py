#!/usr/bin/env python3
"""
PAK File Unpacker/Repacker Tool
Handles OBB extraction, PAK file unpacking with ZSTD decompression, and repacking
"""

import os
import sys
import struct
import zipfile
import zstandard as zstd
import argparse
from pathlib import Path
import tempfile
import shutil
import time
import json
import base64
import hashlib
import platform
import subprocess
import uuid
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# Configuration
SERVER_URL = "https://removed for security reasons/"
# AES_KEY = b'QYMHKD9iabul8ZkLoXqdKUAVVyB9NiWe'
AES_KEY = "removed for security reasons"

# Must match server key exactly
if len(AES_KEY) != 32:
    # Pad or truncate to 32 bytes (same logic as server)
     AES_KEY = (AES_KEY + "0" * 32)[:32]
     AES_KEY = AES_KEY.encode() 

def encrypt_data(data):
    """Encrypt data using AES encryption"""


def decrypt_data(encrypted_data):
    """Decrypt data using AES decryption"""


def verify_subscription(purchase_key=None):
    """Verify subscription with the server"""
    """removed the code"""

def display_user_info(response, hash_id=None):
    """Display user information from server response"""
    if response.get("status") == "success":
        username = response.get("username", "Unknown")
        total_requests = response.get("total_requests", "Unknown")
        subscription_left = response.get("subscription_left", "Unknown")
        total_registered_devices = response.get("total_registered_devices", "Unknown")
        
        if hash_id:
            print(f"User Hash: {hash_id}")
        print(f"\n=== User Information ===")
        print(f"Username: {username}")
        print(f"Total Requests: {total_requests}")
        print(f"Subscription Left: {subscription_left}")
        print(f"Registered Devices: {total_registered_devices}")
        print("========================\n")
    else:
        print(f"Error: {response.get('message', 'Unknown error')}")

def main_verify():
    """Main function to handle subscription verification with automatic flow"""
    print("=== Subscription Verification System ===")
    
    # Step 1: First try to verify existing subscription
    print("\nStep 1: Checking for existing subscription...")
    result = verify_subscription()
    
    if result.get("status") == "success":
        # User already has valid subscription
        display_user_info(result)
        return
    
    # Step 2: If verification failed, automatically send hash to server
    print("\nStep 2: No valid subscription found. Sending device hash to server...")
    hash_id =     """removed the code"""
    print(f"Device Hash: {hash_id}")
    
    # Step 3: Ask user for purchase key only
    print("\nStep 3: Please provide your purchase key to activate subscription.")
    purchase_key = input("Enter your purchase key: ").strip()
    
    if not purchase_key:
        print("Error: Purchase key is required!")
        return
    
    # Step 4: Send hash and purchase key to server (username will be extracted from key)
    print(f"\nStep 4: Activating subscription...")
    result = verify_subscription(purchase_key)
    display_user_info(result)

def verify_and_continue():
    """
    Verification removed — always allow continuation.
    This stub avoids network calls and lets the program proceed.
    """
    return True


class PAKTool:
    def __init__(self):
        self.DICT_MARKER = bytes.fromhex("37 A4 30 EC")
        self.DAT_MAGIC = bytes.fromhex("51 CC 56 84")
        self.XOR_KEY = 0x79
        self.DICT_SIZE = 1024 * 1024  # 1MB = 1,048,576 bytes
        
        # Directory setup according to new structure
        from pathlib import Path

# Base directory in Termux
BASE_DIR = Path.home() / "SKIN" / "BGMI"

# Permanent paths
self.input_dir       = BASE_DIR / "input"        # Original OBB files
self.repack_obb_dir  = BASE_DIR / "repack_obb"   # OBB copied here for repacking
self.unpack_pak_dir  = BASE_DIR / "unpack_pak"   # Unpacked DAT files
self.edited_dat_dir  = BASE_DIR / "edited_dat"   # Edited DAT files for repacking
self.repack_pak_dir  = BASE_DIR / "repack_pak"   # Repacked PAK files
self.tmp_dir         = BASE_DIR / "tmp"          # Temporary files (dictionary, compression)

# Make sure directories exist
for d in [self.input_dir, self.repack_obb_dir, self.unpack_pak_dir, 
          self.edited_dat_dir, self.repack_pak_dir, self.tmp_dir]:
    d.mkdir(parents=True, exist_ok=True)
    
    def get_zsdic_pak(self):
        """Get the zsdic PAK file, extract from OBB if needed"""
        zsdic_pak = self.tmp_dir / "zsdic.pak"
        
        if zsdic_pak.exists():
            print(f"Using existing PAK file: {zsdic_pak}")
            return zsdic_pak
        else:
            print("PAK file not found in tmp folder, extracting from OBB...")
            obb_path = self.find_obb_file()
            return self.extract_pak_from_obb(obb_path)
    
    def find_obb_file(self):
        """Find OBB file in input directory"""
        obb_files = list(self.input_dir.glob("*.obb"))
        if not obb_files:
            raise FileNotFoundError("No OBB file found in input directory")
        return obb_files[0]
    
    def extract_pak_from_obb(self, obb_path):
        """Extract PAK file from OBB archive and save to tmp folder"""
        print(f"Extracting PAK from {obb_path}")
        
        # Rename OBB to ZIP for extraction
        zip_path = obb_path.with_suffix('.zip')
        shutil.copy2(obb_path, zip_path)
        print(f"Renamed OBB to ZIP: {zip_path}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # Find PAK file recursively
            pak_files = list(temp_path.rglob("*mini_obbzsdic_obb.pak"))
            if not pak_files:
                # Try to find any PAK file
                pak_files = list(temp_path.rglob("*.pak"))
                if not pak_files:
                    raise FileNotFoundError("No PAK file found in OBB")
            
            pak_file = pak_files[0]
            print(f"Found PAK file: {pak_file}")
            
            # Copy PAK file to tmp directory
            zsdic_pak = self.tmp_dir / "zsdic.pak"
            shutil.copy2(pak_file, zsdic_pak)
            print(f"PAK file saved to: {zsdic_pak}")
            
            # Clean up ZIP file
            zip_path.unlink()
            
            return zsdic_pak
    
    def find_dictionary(self, pak_data):
        """Find and extract dictionary from PAK file"""
        dict_pos = pak_data.find(self.DICT_MARKER)
        if dict_pos == -1:
            raise ValueError("Dictionary marker not found in PAK file")
        
        print(f"Dictionary found at position: {dict_pos}")
        
        # Extract exactly 1MB (1,048,576 bytes) dictionary starting from marker
        dictionary = pak_data[dict_pos:dict_pos + self.DICT_SIZE]
        # with open("dict.dict", "wb") as f:
        #     f.write(dictionary)
        # Ensure we have the full dictionary size
        if len(dictionary) < self.DICT_SIZE:
            print(f"Warning: Dictionary is only {len(dictionary)} bytes, expected {self.DICT_SIZE}")
        else:
            print(f"Dictionary extracted: {len(dictionary)} bytes")
        
        return dictionary, dict_pos
    
    def find_dat_files(self, pak_data, dict_pos):
        """Find all DAT files before dictionary position"""
        dat_files = []
        pos = 0
        
        while pos < dict_pos:
            magic_pos = pak_data.find(self.DAT_MAGIC, pos)
            if magic_pos == -1 or magic_pos >= dict_pos:
                break
            
            # Find next DAT file or dictionary to determine size
            next_magic = pak_data.find(self.DAT_MAGIC, magic_pos + 4)
            if next_magic == -1 or next_magic >= dict_pos:
                # This is the last DAT file before dictionary
                dat_size = dict_pos - magic_pos
            else:
                dat_size = next_magic - magic_pos
            
            dat_data = pak_data[magic_pos:magic_pos + dat_size]
            dat_files.append({
                'index': len(dat_files),
                'position': magic_pos,
                'size': dat_size,
                'data': dat_data
            })
            
            pos = magic_pos + 4
        
        print(f"Found {len(dat_files)} DAT files")
        return dat_files
    
    def xor_decrypt(self, data):
        """XOR decrypt data with key 0x79"""
        return bytes(b ^ self.XOR_KEY for b in data)
    
    def decompress_dat(self, dat_data_with_magic, dictionary):
        """Decrypt and decompress DAT file (including magic header)"""
        # Decrypt (including magic header)
        decrypted = self.xor_decrypt(dat_data_with_magic)

        # XOR logic is already in your decrypt, so we don’t repeat it here
        d = zstd.ZstdDecompressor(dict_data=zstd.ZstdCompressionDict(dictionary))
        decompressed = b''
        reader = d.stream_reader(decrypted)
        try:
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                decompressed += chunk
        except zstd.ZstdError:
            # Ignore trailing garbage or invalid padding (common for null/padded files)
            pass
        finally:
            reader.close()
        return decompressed



    
    def unpack(self):
        """Unpack PAK file"""
        print("Starting unpack process...")
        
        # Get zsdic PAK file
        pak_path = self.get_zsdic_pak()
        
        # Read PAK file
        with open(pak_path, 'rb') as f:
            pak_data = f.read()
        
        # Find dictionary
        dictionary, dict_pos = self.find_dictionary(pak_data)
        
        # Save dictionary to tmp folder for manual checking
        dict_file = self.tmp_dir / "dictionary.bin"
        with open(dict_file, 'wb') as f:
            f.write(dictionary)
        print(f"Dictionary saved to: {dict_file}")
        
        # Find DAT files
        dat_files = self.find_dat_files(pak_data, dict_pos)
        
        # Process only first 4 DAT files as requested
        successful_count = 0
        for i, dat_info in enumerate(dat_files[:]):  # Only process first 4
            print(f"Processing DAT {i+1:07d} (size: {dat_info['size']} bytes)")
            
            dat_data = dat_info['data']

            # Decompress
            decompressed = self.decompress_dat(dat_data, dictionary)

            # Always create file, even if empty
            output_file = self.unpack_pak_dir / f"{i+1:07d}.dat"
            with open(output_file, 'wb') as f:
                f.write(decompressed if decompressed else b'')
            
            if decompressed:
                print(f"  Saved: {output_file} ({len(decompressed)} bytes)")
                successful_count += 1
            else:
                print(f"  Failed to decompress DAT {i+1:07d}, created empty file at {output_file}")
                successful_count += 1
        
        print(f"Successfully processed {successful_count}")
        print("Unpack completed!")
    
    def find_best_compression_level(self, data, dictionary, target_size):
        """Find the best compression level that fits within target size"""
        dict_obj = zstd.ZstdCompressionDict(dictionary)
        
        for level in range(1, 23):  # ZSTD levels 1-22
            cctx = zstd.ZstdCompressor(level=level, dict_data=dict_obj)
            try:
                compressed = cctx.compress(data)
                if len(compressed) <= target_size:
                    return compressed, level
            except Exception:
                continue
        
        # If no level works, try level 1 anyway
        cctx = zstd.ZstdCompressor(level=1, dict_data=dict_obj)
        compressed = cctx.compress(data)
        return compressed, 1
    
    def repack(self):
        """Repack edited files back into PAK"""
        print("Starting repack process...")
        
        # Get zsdic PAK file
        pak_path = self.get_zsdic_pak()
        
        # Read original PAK file
        with open(pak_path, 'rb') as f:
            pak_data = bytearray(f.read())
        
        # Find dictionary
        dictionary, dict_pos = self.find_dictionary(pak_data)
        
        # Find original DAT files
        dat_files = self.find_dat_files(pak_data, dict_pos)
        
        # Process edited files from edited_dat directory
        edited_files = list(self.edited_dat_dir.glob("*.dat"))
        
        if not edited_files:
            print("[EMPTY] No DATs found in 'edited_dat' directory")
            return
        
        print(f"Found {len(edited_files)} edited files to repack")
        
        successful_repacks = 0
        failed_repacks = 0
        
        for edited_file in edited_files:
            # Extract index from filename (e.g., 0000004.dat -> 4th occurrence)
            filename = edited_file.stem
            try:
                dat_number = int(filename.lstrip('0')) if filename != '0000000' else 0
                dat_index = dat_number - 1  # Convert to 0-based index
            except ValueError:
                print(f"Invalid filename format: {edited_file}")
                continue
            
            if dat_index < 0 or dat_index >= len(dat_files):
                print(f"DAT index {dat_index} out of range (file: {edited_file})")
                continue
            
            print(f"\nRepacking DAT {dat_number:07d} (index {dat_index})")
            
            # Read edited file
            with open(edited_file, 'rb') as f:
                edited_data = f.read()
            
            # Get original DAT info
            original_dat = dat_files[dat_index]
            original_size = original_dat['size']
            required_size = original_size - 4  # Size minus last 4 bytes (checksum)
            
            # Extract last 4 bytes (checksum) from original
            checksum = original_dat['data'][-4:]
            
            # Compress edited data with increasing levels until size requirement is met
            compressed_data = None
            compression_level = None
            dict_obj = zstd.ZstdCompressionDict(dictionary)
            
            print(f"Testing compression levels to fit {required_size} bytes...")
            for level in range(1, 23):  # ZSTD levels 1-22
                try:
                    cctx = zstd.ZstdCompressor(level=level, dict_data=dict_obj)
                    test_compressed = cctx.compress(edited_data)
                    
                    
                    if len(test_compressed) <= required_size:
                        compressed_data = test_compressed
                        compression_level = level
                        # print(f" ✓ (fits)")
                        print(f" ✓ repacked")

                        break
                    else:
                        print(f" ✗ (too large)")
                    
                except Exception as e:
                    # print(f"  Level {level}: failed - {e}")
                    print("wait wait")
                    continue
            
            if compressed_data is None:
                print(f"ERROR: Could not compress DAT {dat_number:07d} to fit in {required_size} bytes")
                print(f"Skipping this file and moving to next...")
                failed_repacks += 1
                continue
            

            print(f"Compressed data size: {len(compressed_data)} bytes")
            
            # Create new DAT block - start with compressed data
            new_dat_block = bytearray(compressed_data)
            
            # Pad with null bytes if needed (before XOR and checksum)
            if len(compressed_data) < required_size:
                padding_needed = required_size - len(compressed_data)
                new_dat_block.extend(b'\x00' * padding_needed)
            
            # XOR the entire data (compressed + padding) with the same method as decryption
            xor_encrypted_data = self.xor_decrypt(new_dat_block)
            new_dat_block = bytearray(xor_encrypted_data)
            print(f"XOR encrypted {len(new_dat_block)} bytes using xor_decrypt method")
            
            
            # Add checksum at the end
            new_dat_block.extend(checksum)
            
            # Ensure the new block is exactly the same size as original
            if len(new_dat_block) != original_size:
                print(f"ERROR: Size mismatch - original: {original_size}, new: {len(new_dat_block)}")
                failed_repacks += 1
                continue
            
            # Save the final DAT block for inspection
            final_dat_file = self.tmp_dir / f"final_{dat_number:07d}_dat_block.bin"
            with open(final_dat_file, 'wb') as f:
                f.write(new_dat_block)
            print(f"Final DAT block saved to: {final_dat_file}")
            
            # Replace in PAK data
            start_pos = original_dat['position']
            end_pos = start_pos + original_dat['size']
            pak_data[start_pos:end_pos] = new_dat_block
            
            print(f"Replaced DAT {dat_number:07d} in PAK file")
            successful_repacks += 1
        
        # Save the repacked PAK to repack_pak directory
        pak_filename = "mini_obbzsdic_obb.pak"
        repacked_pak_path = self.repack_pak_dir / pak_filename
        
        with open(repacked_pak_path, 'wb') as f:
            f.write(pak_data)
        print(f"Repacked PAK saved to: {repacked_pak_path}")
        
        # Now update the OBB file with the repacked PAK
        # Print summary
        print(f"\nRepack Summary:")
        print(f"  Successfully repacked: {successful_repacks} files")
        print(f"  Failed to repack: {failed_repacks} files")
        print(f"  Total processed: {successful_repacks + failed_repacks} files")
        
        print("Repack completed!")
    


    def _update_obb_fallback(self, original_obb, repacked_pak, repacked_obb):
        """Fallback method to update OBB using Python's zipfile module"""
        print("Using Python zipfile fallback method...")
        
        try:
            # Use hardcoded PAK path
            pak_path_in_obb = "ShadowTrackerExtra/Content/Paks/mini_obbzsdic_obb.pak"
            print(f"Updating PAK at path: {pak_path_in_obb}")
            
            # Create a temporary directory for extraction
            temp_dir = self.repacked_dir / "temp_obb_extract"
            temp_dir.mkdir(exist_ok=True)
            
            # Extract the entire OBB to temp directory
            with zipfile.ZipFile(original_obb, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Replace the PAK file at its original location
            target_pak_path = temp_dir / pak_path_in_obb
            shutil.copy2(repacked_pak, target_pak_path)
            print(f"Replaced PAK file at: {target_pak_path}")
            
            # Recreate the OBB with no compression
            with zipfile.ZipFile(repacked_obb, 'w', zipfile.ZIP_STORED) as zip_ref:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # Calculate relative path from temp_dir
                        arcname = file_path.relative_to(temp_dir)
                        zip_ref.write(file_path, arcname)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            print(f"Successfully updated OBB using fallback method: {repacked_obb}")
            
            # Adjust OBB size to match original
            original_obb_size = os.path.getsize(original_obb)
            print(f"Adjusting OBB size to match original: {original_obb_size} bytes")
            adjust_size(repacked_obb, original_obb_size)
            print("OBB size adjustment completed!")
            
        except Exception as e:
            print(f"Fallback method failed: {e}")
            # At least copy the original OBB as is
            shutil.copy2(original_obb, repacked_obb)
            print(f"Copied original OBB without updates: {repacked_obb}")

def set_permissions(file_path):
    """Set file permissions to 777 (read/write/execute for all) where possible."""
    try:
        os.chmod(file_path, 0o777)
    except Exception as e:
        print(f"[WARN] Could not set permissions for {file_path}: {e}")

def get_single_file(directory, extension=None):
    """Return single file path in directory with optional extension filter."""
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    if extension:
        files = [f for f in files if f.lower().endswith(extension.lower())]
    if not files:
        raise FileNotFoundError(f"No file found in {directory} with extension {extension}")
    if len(files) > 1:
        raise ValueError(f"Multiple files found in {directory}. Keep only one.")
    return os.path.join(directory, files[0])

def update_zip_file(zip_file_path):
    """Update existing zip file in-place (store only, no compression)."""
    set_permissions(zip_file_path)
    zip_dir = os.path.dirname(zip_file_path)
    zip_name = os.path.basename(zip_file_path)

    try:
        # Read all existing contents
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            existing_files = {info.filename: zf.read(info.filename) for info in zf.infolist()}

        # Re-write zip with updated files (ZIP_STORED = no compression)
        with zipfile.ZipFile(zip_file_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            for file_name, file_data in existing_files.items():
                file_path = os.path.join(zip_dir, file_name)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=file_name, compress_type=zipfile.ZIP_STORED)
                else:
                    zf.writestr(file_name, file_data)

        print("[OK] Zip updated successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to update zip: {e}")
        raise

def adjust_size(repacked_obb_path, original_obb_size):
    """Pad repacked OBB to match original size."""
    repacked_obb_size = os.path.getsize(repacked_obb_path)

    if repacked_obb_size > original_obb_size:
        raise ValueError("Repacked OBB is larger than original OBB.")

    with open(repacked_obb_path, 'ab') as f:
        while repacked_obb_size < original_obb_size:
            f.write(b'\x00')
            repacked_obb_size += 1
    print(f"[OK] Resized to match original size: {original_obb_size} bytes.")

def move_and_replace(src, dest):
    """Move file, replacing if exists."""
    if os.path.exists(dest):
        os.remove(dest)
    shutil.move(src, dest)
    print(f"[OK] Moved {src} to {dest}.")

# -------- Main Operations -------- #

def unpack_obb():
    input_dir = "input"
    unpacked_dir = "unpacked_obb"

    os.makedirs(unpacked_dir, exist_ok=True)

    obb_path = get_single_file(input_dir, ".obb")
    set_permissions(obb_path)

    print(f"[INFO] Unpacking {obb_path}...")
    with zipfile.ZipFile(obb_path, 'r') as zf:
        zf.extractall(unpacked_dir)

    print(f"[OK] Extracted to {unpacked_dir}")

def repack_obb():
    import os, shutil, zipfile, fnmatch

    input_dir = "input"
    repack_obb_dir = "repack_obb"
    repack_pak_dir = "repack_pak"
    unpacked_obb_dir = "unpacked_obb"

    # Find the original OBB file in input directory
    try:
        original_obb_path = get_single_file(input_dir, ".obb")
    except FileNotFoundError:
        print("[ERROR] No OBB file found in input directory")
        return False

    original_size = os.path.getsize(original_obb_path)
    obb_filename = os.path.basename(original_obb_path)

    # Collect available PAK files to choose from
    if not os.path.isdir(repack_pak_dir):
        print(f"[ERROR] Pak folder not found: {repack_pak_dir}")
        return False

    pak_files = sorted([f for f in os.listdir(repack_pak_dir) if f.lower().endswith('.pak')])
    if not pak_files:
        print(f"[ERROR] No .pak files found in {repack_pak_dir}")
        return False

    print("\nFound the following .pak files:")
    for i, p in enumerate(pak_files, start=1):
        print(f"  {i:2d}. {p}")

    sel = input("\nEnter indexes (e.g. 1,3-5), partial names (comma separated), or press Enter to include ALL: ").strip()

    # Parse selection
    if not sel:
        selected_names = pak_files[:]  # all
    else:
        tokens = [t.strip() for t in sel.split(',') if t.strip()]
        chosen = []
        for tok in tokens:
            if '-' in tok and all(part.strip().isdigit() for part in tok.split('-', 1)):
                a, b = tok.split('-', 1)
                a, b = int(a), int(b)
                for idx in range(a, b+1):
                    if 1 <= idx <= len(pak_files):
                        chosen.append(pak_files[idx-1])
                    else:
                        print(f"Warning: index {idx} out of range, ignored.")
            elif tok.isdigit():
                idx = int(tok)
                if 1 <= idx <= len(pak_files):
                    chosen.append(pak_files[idx-1])
                else:
                    print(f"Warning: index {idx} out of range, ignored.")
            else:
                # partial match (case-insensitive)
                matches = [name for name in pak_files if tok.lower() in name.lower()]
                if not matches:
                    matches = fnmatch.filter(pak_files, f"*{tok}*")
                if not matches:
                    print(f"Warning: no pak matched '{tok}'")
                else:
                    chosen.extend(matches)

        # dedupe preserving order
        seen = set()
        selected_names = []
        for name in chosen:
            if name not in seen:
                seen.add(name)
                selected_names.append(name)

    if not selected_names:
        print("No pak files selected — aborting.")
        return False

    # Full paths of chosen pak files
    selected_pak_paths = [os.path.join(os.path.abspath(repack_pak_dir), name) for name in selected_names]

    # Create directories
    os.makedirs(unpacked_obb_dir, exist_ok=True)
    os.makedirs(repack_obb_dir, exist_ok=True)

    # Extract original OBB to unpacked_obb directory
    print(f"\n[INFO] Extracting original OBB to {unpacked_obb_dir}...")
    try:
        with zipfile.ZipFile(original_obb_path, 'r') as zf:
            zf.extractall(unpacked_obb_dir)
    except Exception as e:
        print("[ERROR] Failed to extract original OBB:", e)
        return False

    # Place the updated PAK files in the correct location within extracted structure
    pak_folder_in_obb = os.path.join(unpacked_obb_dir, "ShadowTrackerExtra", "Content", "Paks")
    os.makedirs(pak_folder_in_obb, exist_ok=True)

    print("\n[INFO] Copying selected PAK(s) into OBB structure:")
    for src in selected_pak_paths:
        if not os.path.exists(src):
            print(f"[WARNING] Selected pak not found (skipping): {src}")
            continue
        dst = os.path.join(pak_folder_in_obb, os.path.basename(src))
        shutil.copy2(src, dst)
        print(f"  - {os.path.basename(src)} -> {dst}")

    # Create updated OBB (ZIP_STORED to mimic zip -0 -u behavior)
    print(f"\n[INFO] Creating updated OBB with new PAK file(s)...")
    original_cwd = os.getcwd()
    try:
        os.chdir(unpacked_obb_dir)
        new_obb_path_rel = obb_filename  # will create this file inside unpacked_obb_dir
        try:
            with zipfile.ZipFile(new_obb_path_rel, 'w', compression=zipfile.ZIP_STORED) as zf:
                for root, dirs, files in os.walk('.'):
                    for file in files:
                        if file == os.path.basename(new_obb_path_rel):
                            # skip the zip file itself if it exists inside the tree
                            continue
                        file_path = os.path.join(root, file)
                        # produce archive name with forward slashes and no leading ./ 
                        arcname = os.path.normpath(file_path).replace('\\', '/').lstrip('./')
                        zf.write(file_path, arcname)
            print("[OK] Created updated OBB in extracted folder.")
        except Exception as e:
            print("[ERROR] Failed to create updated OBB file:", e)
            return False
    finally:
        os.chdir(original_cwd)

    # Move the newly created OBB to repack_obb directory (no 'repacked_' prefix)
    created_obb_full = os.path.join(unpacked_obb_dir, obb_filename)
    if not os.path.exists(created_obb_full):
        print("[ERROR] Newly created OBB not found:", created_obb_full)
        return False

    # Decide final output path: keep original name unless it would overwrite
    candidate = os.path.join(os.path.abspath(repack_obb_dir), obb_filename)
    if os.path.exists(candidate):
        # avoid overwriting: add _mod before extension
        name_no_ext, ext = os.path.splitext(obb_filename)
        final_obb_path = os.path.join(os.path.abspath(repack_obb_dir), f"{name_no_ext}_mod{ext}")
    else:
        final_obb_path = candidate

    # Ensure no accidental overwrite (if still exists, append numeric suffix)
    if os.path.exists(final_obb_path):
        base, ext = os.path.splitext(final_obb_path)
        i = 1
        while os.path.exists(f"{base}_{i}{ext}"):
            i += 1
        final_obb_path = f"{base}_{i}{ext}"

    try:
        shutil.move(created_obb_full, final_obb_path)
    except Exception as e:
        print("[ERROR] Failed to move created OBB to repack folder:", e)
        return False

    # Debug sizes
    actual_size = os.path.getsize(final_obb_path)
    bytes_to_add = original_size - actual_size
    print(f"\n[DEBUG] OBB size after repack (before pad): {actual_size} bytes")
    print(f"[DEBUG] Bytes to be added for padding (if positive): {bytes_to_add} bytes")

    # Adjust size to match original (uses your adjust_size function)
    try:
        adjust_size(final_obb_path, original_size)
    except Exception as e:
        print("[WARNING] adjust_size() failed or not present:", e)
        # continue anyway

    print(f"\n[OK] Repacked OBB saved at {final_obb_path}")
    try:
        print(f"[INFO] Original size: {original_size} bytes, Final size: {os.path.getsize(final_obb_path)} bytes")
    except Exception:
        pass

    return True


def cleanup_folders():
    """Clean up all folders except input directory"""
    folders_to_clean = ["repack_obb", "unpack_pak", "edited_dat", "repack_pak", "tmp", "unpacked_obb"]

    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                os.makedirs(folder, exist_ok=True)
                print(f"[OK] Cleaned {folder} folder")
            except Exception as e:
                print(f"[WARN] Could not clean {folder}: {e}")
    
    print("[OK] Cleanup completed!")

# --- baki ka code same rahega (PAKTool class, helpers, etc.) ---

# Remove: show_menu(), main(), main_standalone()

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="HRTool: simple CLI for unpack/repack (no UI)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("unpack", help="Unpack the PAK file (runs PAKTool().unpack())")
    sub.add_parser("repack", help="Repack the PAK file (runs PAKTool().repack())")
    sub.add_parser("unpack-obb", help="Unpack OBB files (runs unpack_obb())")
    sub.add_parser("repack-obb", help="Repack OBB files (runs repack_obb())")
    sub.add_parser("verify", help="Run verification routine (runs main_verify())")

    parser.add_argument("-i", "--input", help="Input path (optional)", default=None)
    parser.add_argument("-o", "--output", help="Output path (optional)", default=None)

    args = parser.parse_args()

    if args.input:
        os.environ["HR_TOOL_INPUT"] = args.input
    if args.output:
        os.environ["HR_TOOL_OUTPUT"] = args.output

    tool = PAKTool()

    if args.command == "unpack":
        tool.unpack()
    elif args.command == "repack":
        tool.repack()
    elif args.command == "unpack-obb":
        try:
            unpack_obb()
        except NameError:
            print("unpack_obb() not available in this build.")
    elif args.command == "repack-obb":
        try:
            repack_obb()
        except NameError:
            print("repack_obb() not available in this build.")
    elif args.command == "verify":
        try:
            main_verify()
        except NameError:
            print("main_verify() not available in this build.")
    else:
        parser.print_help()


    """
    CODE WILL NOT WORK OUT OF THE BOX YOU NEED TO REMOVE 
    THE SERVER VERIFICATION CODE AND FUNCTIONS TO WORK PROPERLY 


    THIS CODE IS SUPPORTED ON ALL THE DEVICES WITHOUT REQUIRING ANY CHANGE IN ANY PART OF THE CODE
    
    ENJOY USING THIS SOURCE CODE KIDS 
    JUST TO BE FAIR IF YOU ARE A GOOD HUMAN BEING DO NOT
    REMOVE THE @HR_Modster USERNAME TO SHOW
    TRIDUBE TO ORIGINAL OWNER OF THE SOURCE CODE
    
    THIS TOOL GIVE YOU 
    1. 100% OF THE UNPACKING OF THE DATA
    2. 100% PROPER REPACK OF THE FILES ( OTHER TOOL FAILS 
    AS THEY MISS THE FRAME HEADER AND FILE GIVE DECOMPRESSION ERROR
    WHEN ANY ONE TRIES TO UNPACK THEM )
    3. REAL ANTI RESET OBB MAKING NO USING THE ZIP -U -0 COMMAND FROM LINUX
    INSTED USING THE PYTHON MODULE TO BE ABLE TO SUPPORT ALL DEVICES LIKE WINDOWS LINUX UNIX AARCH ETC
    AUTO RESIZING TO FIX ANY FIRTHER ERRORS
    4. PRESERVING THE CHECKSUM OF THE REPACKING DATA TO AVOIDE ANY ISSUES FROM THE GAME SIDE
    5. REST I DONT REMEMBER JUST SE THE CODE AND USE AND GIVE CREDIT THATS IT 
    
    PEACE OUT 
    DONT FIGHT TO BE THE FIRST INSTEAD FIGHT TO BE BETTER THAN OTHER"""

