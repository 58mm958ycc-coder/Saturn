#!/usr/bin/env python3
import os
import sys
import re

def scan_file_for_errors(file_path):
    errors = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    full_text = "".join(lines)
    
    # Check 1: size_t usage without stddef header
    if re.search(r'\bsize_t\b', full_text):
        if not re.search(r'#include\s+[<"](stddef\.h|cstddef)[>"]', full_text):
            errors.append("Uses 'size_t' but is missing '#include '")

    # Check 2: SDL events/keys without SDL.h
    sdl_identifiers = ['SDL_Event', 'SDL_KEYDOWN', 'SDLK_m', 'SDLK_n', 'SDL_MOUSEMOTION', 'SDL_Delay']
    for ident in sdl_identifiers:
        if re.search(rf'\b{ident}\b', full_text):
            if not re.search(r'#include\s+[<"](SDL2/SDL\.h|SDL\.h)[>"]', full_text):
                errors.append(f"Uses SDL identifier '{ident}' but is missing '#include '")
                break

    # Check 3: G_TRI2 without gbi.h header
    if re.search(r'\bG_TRI2\b', full_text):
        if not re.search(r'#include\s+[<"](PR/gbi\.h|gbi\.h)[>"]', full_text):
            errors.append("Uses 'G_TRI2' macro but is missing '#include '")

    return errors

def run_pre_build_scan():
    print("==================================================")
    print("      PRE-BUILD DIAGNOSTIC FILE SCANNER           ")
    print("==================================================")
    
    found_errors = False
    scanned_count = 0

    for root, _, files in os.walk(os.getcwd()):
        if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload', 'external_deps']):
            continue
            
        for file in files:
            if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                scanned_count += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, os.getcwd())
                
                issues = scan_file_for_errors(file_path)
                if issues:
                    found_errors = True
                    print(f"\n[ERROR DETECTED] File causing compilation failure:")
                    print(f"  --> Path: {rel_path}")
                    for issue in issues:
                        print(f"      - {issue}")

    print("\n--------------------------------------------------")
    print(f"Scanned {scanned_count} source files.")

    if found_errors:
        print("[PRE-BUILD FAILED] Identified syntax/header defects in the files listed above.")
        print("Stopping execution before running xcodebuild.")
        sys.exit(1)
    else:
        print("[PRE-BUILD PASSED] All source files passed initial header checks.")
        print("==================================================\n")

if __name__ == "__main__":
    run_pre_build_scan()
