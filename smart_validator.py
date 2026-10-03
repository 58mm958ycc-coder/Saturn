#!/usr/bin/env python3
import os
import sys
import re
import urllib.request
import json
import time

# Using one of the provided keys for the fallback AI dynamic patcher
AI_API_KEY = "sk-abcdef1234567890abcdef1234567890abcdef12"

def ai_fallback_fix(file_path, content, error_reason):
    """Fallback method: Uses the provided API key to ask an AI to fix unknown errors."""
    print(f"[AI-FIX] Attempting dynamic AI fix for {file_path} using API key...")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    prompt = f"Fix the following C/C++ file. It has this error: {error_reason}. Return ONLY the raw fixed C/C++ code, nothing else, no markdown formatting.\n\n{content}"
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            fixed_code = result["choices"][0]["message"]["content"].strip()
            
            # Clean up potential markdown formatting from the AI response
            if fixed_code.startswith("```"):
                fixed_code = "\n".join(fixed_code.split("\n")[1:-1])
                
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)
            print(f"[AI-FIX] Successfully patched {file_path}")
            return True
    except Exception as e:
        print(f"[AI-FIX] AI fix failed or timed out: {e}")
        return False

def check_for_missing_local_files(full_text, current_dir, repo_root):
    """Scans for #include "file.h". If 'file.h' doesn't exist anywhere, trigger a hard stop."""
    local_includes = re.findall(r'#include\s+"([^"]+)"', full_text)
    for inc in local_includes:
        # Ignore system-like includes wrapped in quotes by mistake
        if inc.startswith("SDL") or inc.startswith("PR/"):
            continue
            
        # Check if the file exists relative to the current file or anywhere in the repo
        local_path = os.path.join(current_dir, inc)
        if not os.path.exists(local_path):
            found_anywhere = False
            for root, _, files in os.walk(repo_root):
                if inc in files:
                    found_anywhere = True
                    break
            if not found_anywhere:
                return inc
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

                # 1. FATAL CHECK: Missing local files
                missing_file = check_for_missing_local_files(content, root, repo_root)
                if missing_file:
                    print(f"\n[FATAL ERROR] File {rel_path} requires '{missing_file}', but it does not exist in the repository.")
                    print("Stopping execution. Missing core files cannot be auto-generated.")
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
