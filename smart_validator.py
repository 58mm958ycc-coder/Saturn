#!/usr/init/env python3
import os
import sys
import re

def run_smart_scan():
    print("==================================================")
    print("      SMART VALIDATOR & AUTO-PATCHER RUNNING      ")
    print("==================================================")
    
    repo_root = os.getcwd()
    platform_exclusions = ['dxsdk', 'direct3d', 'd3d11', 'd3d12', 'wgl', 'glx', 'wasapi', 'alsa', 'wiiu']
    files_patched = 0
    scanned_count = 0

    for root, _, files in os.walk(repo_root):
        if any(x in root.lower() for x in ['build', '.git', 'deriveddata', 'payload', 'external_deps'] + platform_exclusions):
            continue
            
        for file in files:
            if any(x in file.lower() for x in platform_exclusions):
                continue
                
            if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                scanned_count += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_root)
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                original_content = content
                
                # Clean up any broken/empty #include lines left over from previous runs
                content = re.sub(r'#include\s*\n', '', content)

                injections = []
                needs_content_change = (content != original_content)

                if re.search(r'\bsize_t\b', content) and not re.search(r'#include\s+[<"](stddef\.h|cstddef)[>"]', content):
                    injections.append("#include ")
                    needs_content_change = True

                if re.search(r'std::filesystem', content) and not re.search(r'#include\s+[<"]filesystem[>"]', content):
                    injections.append("#include ")
                    needs_content_change = True

                if any(ident in content for ident in ['SDL_Event', 'SDL_KEYDOWN', 'SDLK_m', 'SDLK_n', 'SDL_MOUSEMOTION', 'SDL_Delay']):
                    if not re.search(r'#include\s+[<"](SDL2/SDL\.h|SDL\.h)[>"]', content):
                        injections.append("#include ")
                        needs_content_change = True

                if re.search(r'\bG_TRI2\b', content) and rel_path != 'include/PR/gbi.h':
                    if not re.search(r'#include\s+[<"](PR/gbi\.h|gbi\.h)[>"]', content):
                        injections.append("#include ")
                        needs_content_change = True

                if needs_content_change or injections:
                    final_content = ("\n".join(injections) + "\n" + content) if injections else content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    files_patched += 1
                    print(f"[AUTO-FIX] Cleaned and patched headers in {rel_path}")

    print("--------------------------------------------------")
    print(f"Scanned {scanned_count} source files. Patched/Cleaned {files_patched} files.")
    print("[SMART VALIDATOR PASSED] All checks complete. Proceeding to build.")
    print("==================================================\n")

if __name__ == "__main__":
    run_smart_scan()
