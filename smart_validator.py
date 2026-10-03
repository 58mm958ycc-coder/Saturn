#!/usr/bin/env python3
import os
import sys
import re
import urllib.request
import json
import time

# AI Fallback Key
AI_API_KEY = "sk-abcdef1234567890abcdef1234567890abcdef12"

def download_missing_file(missing_include):
    """Attempts to download missing standard SM64/Saturn headers from the web."""
    # Common SM64 file paths mapping
    base_url = "https://raw.githubusercontent.com/n64decomp/sm64/main/"
    
    # Try to construct the likely path
    if missing_include.startswith("game/"):
        target_path = f"src/{missing_include}"
    else:
        target_path = f"include/{missing_include}"
        
    url = base_url + target_path
    
    # Strip the directory structure to save it in the current directory or include/
    save_dir = "include/game" if missing_include.startswith("game/") else "include"
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, os.path.basename(missing_include))
    
    try:
        print(f"[DOWNLOADER] Attempting to fetch missing file '{missing_include}' from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
            with open(save_path, "wb") as f:
                f.write(content)
        print(f"[DOWNLOADER] Success! Saved to {save_path}")
        return True
    except Exception as e:
        print(f"[DOWNLOADER] Failed to fetch {missing_include}: {e}")
        return False

def check_for_missing_local_files(full_text, current_dir, repo_root):
    """Scans for #include "file.h" and verifies it exists in the repo."""
    local_includes = re.findall(r'#include\s+"([^"]+)"', full_text)
    for inc in local_includes:
        if inc.startswith("SDL") or inc.startswith("PR/"):
            continue
            
        # Extract just the filename (e.g., 'ingame_menu.h' from 'game/ingame_menu.h')
        base_name = os.path.basename(inc)
        
        # Check if it exists relative to the current file
        local_path = os.path.join(current_dir, inc)
        if not os.path.exists(local_path):
            found_anywhere = False
            # Search the entire repo for the base filename
            for root, _, files in os.walk(repo_root):
                if base_name in files:
                    found_anywhere = True
                    break
            
            # If it's truly not in the repo, try downloading it!
            if not found_anywhere:
                if download_missing_file(inc):
                    return None # Download succeeded, no longer missing
                return inc # Still missing, trigger error
    return None

def run_smart_scan():
    print("==================================================")
    print("      SMART VALIDATOR & AUTO-PATCHER RUNNING      ")
    print("==================================================")
    
    repo_root = os.getcwd()
    sdl_identifiers = ['SDL_Event', 'SDL_KEYDOWN', 'SDLK_m', 'SDLK_n', 'SDL_MOUSEMOTION', 'SDL_Delay']
    
    files_patched = 0
    scanned_count = 0

    for root, _, files in os.walk(repo_root):
        if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload', 'external_deps']):
            continue
            
        for file in files:
            if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                scanned_count += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_root)
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 1. FATAL CHECK: Missing local files with Auto-Download Fallback
                missing_file = check_for_missing_local_files(content, root, repo_root)
                if missing_file:
                    print(f"\n[FATAL ERROR] File {rel_path} requires '{missing_file}', and it could not be found or downloaded.")
                    print("Stopping execution.")
                    sys.exit(1)

                # 2. INSTANT FIX: Missing Standard Headers
                injections = []
                needs_save = False

                if re.search(r'\bsize_t\b', content) and not re.search(r'#include\s+[<"](stddef\.h|cstddef)[>"]', content):
                    injections.append("#include ")
                    needs_save = True

                if any(re.search(rf'\b{ident}\b', content) for ident in sdl_identifiers):
                    if not re.search(r'#include\s+[<"](SDL2/SDL\.h|SDL\.h)[>"]', content):
                        injections.append("#include ")
                        needs_save = True

                if re.search(r'\bG_TRI2\b', content) and rel_path != 'include/PR/gbi.h':
                    if not re.search(r'#include\s+[<"](PR/gbi\.h|gbi\.h)[>"]', content):
                        injections.append("#include ")
                        needs_save = True

                if needs_save:
                    header_block = "\n".join(injections) + "\n"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(header_block + content)
                    files_patched += 1
                    print(f"[AUTO-FIX] {rel_path} -> Injected missing headers: {', '.join(injections)}")

    print("--------------------------------------------------")
    print(f"Scanned {scanned_count} source files. Automatically patched {files_patched} files.")
    print("[SMART VALIDATOR PASSED] All checks complete. Proceeding to build.")
    print("==================================================\n")

if __name__ == "__main__":
    run_smart_scan()
