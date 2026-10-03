#!/usr/bin/env python3
import os
import sys
import re
import urllib.request

def download_remote_resources():
    print("[CHANGE_SCRIPTS] Checking and downloading required remote patches/headers...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)

    # Remote missing header fallbacks if local files are missing
    remote_files = {
        "include/PR/os_cache.h": "https://raw.githubusercontent.com/n64decomp/sm64/main/include/PR/os_cache.h",
        "include/PR/os_pi.h": "https://raw.githubusercontent.com/n64decomp/sm64/main/include/PR/os_pi.h"
    }

    for path, url in remote_files.items():
        if not os.path.exists(path):
            try:
                print(f"[FETCH] Downloading missing header: {path}...")
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"[WARNING] Could not fetch {url}: {e}")

def patch_all_source_files():
    print("[CHANGE_SCRIPTS] Scanning repository and injecting missing standard header includes...")
    
    modified_files_count = 0
    scanned_count = 0

    sdl_identifiers = ['SDL_Event', 'SDL_KEYDOWN', 'SDLK_m', 'SDLK_n', 'SDL_MOUSEMOTION', 'SDL_Delay']

    for root, _, files in os.walk(os.getcwd()):
        if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload', 'external_deps']):
            continue

        for file in files:
            if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                scanned_count += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, os.getcwd())

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    injections = []

                    # 1. Check size_t requirement
                    if re.search(r'\bsize_t\b', content):
                        if not re.search(r'#include\s+[<"](stddef\.h|cstddef)[>"]', content):
                            injections.append('#include ')

                    # 2. Check SDL identifier requirements
                    if any(re.search(rf'\b{ident}\b', content) for ident in sdl_identifiers):
                        if not re.search(r'#include\s+[<"](SDL2/SDL\.h|SDL\.h)[>"]', content):
                            injections.append('#include ')

                    # 3. Check G_TRI2 requirement
                    if re.search(r'\bG_TRI2\b', content) and rel_path != 'include/PR/gbi.h':
                        if not re.search(r'#include\s+[<"](PR/gbi\.h|gbi\.h)[>"]', content):
                            injections.append('#include ')

                    if injections:
                        # Prevent duplicate injection headers
                        unique_injections = []
                        for inj in injections:
                            if inj not in unique_injections and inj not in content:
                                unique_injections.append(inj)

                        if unique_injections:
                            header_block = "\n".join(unique_injections) + "\n"
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(header_block + content)
                            
                            modified_files_count += 1
                            print(f"[PATCHED] {rel_path} -> Injected: {', '.join(unique_injections)}")

                except Exception as e:
                    print(f"[ERROR] Could not patch file {rel_path}: {e}")

    print(f"[CHANGE_SCRIPTS] Patching complete. Modified {modified_files_count} out of {scanned_count} scanned files.")

if __name__ == "__main__":
    download_remote_resources()
    patch_all_source_files()
