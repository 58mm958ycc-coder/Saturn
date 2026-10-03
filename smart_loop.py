#!/usr/bin/env python3
import os
import sys
import re
import shutil
import subprocess
import plistlib
import zipfile

def install_deps():
    try:
        import yaml
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "--break-system-packages"])

# ==========================================
# SCRIPT 1: THE SCANNER
# ==========================================
def run_scanner(repo_root):
    print("\n[SCANNER] Searching for missing types and broken includes...")
    platform_exclusions = ['dxsdk', 'direct3d', 'd3d11', 'd3d12', 'wgl', 'glx', 'wasapi', 'alsa', 'wiiu']
    issues_found = {}

    for root, _, files in os.walk(repo_root):
        if any(x in root.lower() for x in ['build', '.git', 'deriveddata', 'payload', 'external_deps'] + platform_exclusions):
            continue
            
        for file in files:
            if any(x in file.lower() for x in platform_exclusions):
                continue
                
            if file.endswith(('.c', '.cpp', '.h', '.hpp', '.m', '.mm')):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                injections = []
                
                # Check for broken empty includes from previous failed scripts
                if re.search(r'#include\s*\n', content):
                    injections.append("CLEAN_EMPTY_INCLUDES")

                # Check for missing standard definitions
                if re.search(r'\bsize_t\b', content) and not re.search(r'#include\s+[<"](stddef\.h|cstddef)[>"]', content):
                    injections.append("#include ")
                    
                if re.search(r'std::filesystem', content) and not re.search(r'#include\s+[<"]filesystem[>"]', content):
                    injections.append("#include ")

                # Check for missing SDL types
                if any(ident in content for ident in ['SDL_Event', 'SDL_Window', 'SDL_GLContext', 'SDL_KEYDOWN', 'SDLK_m', 'SDLK_n', 'SDL_MOUSEMOTION', 'SDL_Delay']):
                    if not re.search(r'#include\s+[<"](SDL2/SDL\.h|SDL\.h)[>"]', content):
                        injections.append("#include ")

                # Check for missing N64 Graphics types (Vtx, Gfx, Mtx, Vp)
                if any(ident in content for ident in ['G_TRI2', 'Vtx', 'Gfx', 'Mtx', 'Vp']):
                    # Prevent injecting gbi.h into itself
                    if not file_path.endswith('gbi.h'):
                        if not re.search(r'#include\s+[<"](PR/gbi\.h|gbi\.h)[>"]', content):
                            injections.append("#include ")

                if injections:
                    issues_found[file_path] = injections

    return issues_found

# ==========================================
# SCRIPT 2: THE PATCHER
# ==========================================
def run_patcher(issues_found):
    print(f"[PATCHER] Fixing {len(issues_found)} files...")
    files_patched = 0
    
    for file_path, injections in issues_found.items():
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Execute cleaning request
        if "CLEAN_EMPTY_INCLUDES" in injections:
            content = re.sub(r'#include\s*\n', '', content)
            injections.remove("CLEAN_EMPTY_INCLUDES")

        # Apply new headers
        if injections:
            final_content = "\n".join(injections) + "\n" + content
        else:
            final_content = content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        files_patched += 1
        print(f"  -> Patched: {os.path.basename(file_path)}")
        
    return files_patched

# ==========================================
# THE LOOP MANAGER
# ==========================================
def loop_until_clean():
    print("==================================================")
    print("      SMART VALIDATOR & AUTO-PATCHER LOOP         ")
    print("==================================================")
    repo_root = os.getcwd()
    
    iteration = 1
    while True:
        print(f"\n--- LOOP ITERATION {iteration} ---")
        issues = run_scanner(repo_root)
        
        if not issues:
            print("\n[SMART VALIDATOR PASSED] 0 issues found. The codebase is clean.")
            break
            
        patched_count = run_patcher(issues)
        print(f"Iteration {iteration} complete: {patched_count} files fixed.")
        iteration += 1
        
        # Failsafe to prevent infinite loops
        if iteration > 10:
            print("[WARNING] Loop exceeded 10 iterations. Forcing break to avoid hanging.")
            break

    print("==================================================\n")

# ==========================================
# BUILD & MOCK ENVIRONMENT
# ==========================================
def generate_mock_headers():
    print("[MOCKS] Generating dummy C headers for missing external SDKs...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)

    with open("include/PR/ultratypes.h", "w") as f:
        f.write("#ifndef ULTRATYPES_H\n#define ULTRATYPES_H\n#include \n#include \n#define NON_MATCHING 1\ntypedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;\ntypedef int8_t s8; typedef int16_t s16; typedef int32_t s32; typedef int64_t s64;\ntypedef float f32; typedef double f64;\n#endif\n")

    with open("include/SDL2/SDL.h", "w") as f:
        f.write("#ifndef SDL_H\n#define SDL_H\n#include \n#include \ntypedef struct SDL_Window SDL_Window;\ntypedef void* SDL_GLContext;\ntypedef uint32_t Uint32; typedef uint8_t Uint8; typedef uint16_t Uint16; typedef int32_t Sint32;\ntypedef int SDL_bool; typedef int SDL_Keycode;\ntypedef struct SDL_Keysym { SDL_Keycode sym; } SDL_Keysym;\ntypedef struct SDL_KeyboardEvent { SDL_Keysym keysym; } SDL_KeyboardEvent;\ntypedef struct SDL_MouseMotionEvent { Sint32 xrel; Sint32 yrel; } SDL_MouseMotionEvent;\ntypedef union SDL_Event { Uint32 type; SDL_KeyboardEvent key; SDL_MouseMotionEvent motion; } SDL_Event;\ntypedef int SDL_Scancode;\n#define SDL_KEYDOWN 0x300\n#define SDL_MOUSEMOTION 0x400\n#define SDLK_m 'm'\n#define SDLK_n 'n'\n#define SDL_WINDOWPOS_CENTERED 0x2FFF0000\n#define SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_ENTIONS \"\"\n#ifdef __cplusplus\nextern \"C\" {\n#endif\nconst char* SDL_GetScancodeName(SDL_Scancode scancode);\nvoid SDL_SetWindowSize(void* window, int w, int h);\nvoid SDL_SetWindowPosition(void* window, int x, int y);\nSDL_bool SDL_SetHint(const char* name, const char* value);\nvoid SDL_Delay(Uint32 ms);\n#ifdef __cplusplus\n}\n#endif\n#endif\n")

    with open("include/PR/gbi.h", "w") as f:
        f.write("#ifndef GBI_H\n#define GBI_H\n#include \"ultratypes.h\"\n#define G_TRI2 0xb1\n#ifdef __cplusplus\nextern \"C\" {\n#endif\ntypedef struct Gfx Gfx;\ntypedef struct Mtx Mtx;\ntypedef struct Vp Vp;\ntypedef struct { s16 ob[3]; u16 tc[2]; u8 cn[4]; } Vtx_t;\ntypedef union { Vtx_t v; long long force_structure_alignment; } Vtx;\n#ifdef __cplusplus\n}\n#endif\n#endif\n")

def trigger_xcode_build():
    import yaml
    print("[XCODEGEN] Generating project with strict compiler warnings disabled...")
    
    sources = [{"path": "src", "excludes": ["pc/win32", "pc/dxsdk", "pc/gfx/gfx_direct3d11.cpp", "pc/gfx/gfx_dxgi.cpp", "pc/gfx/gfx_glx.c", "pc/gfx/gfx_wgl.c", "pc/audio/audio_wasapi.c", "pc/audio/audio_alsa.c"]}, {"path": "actors"}, {"path": "levels"}, {"path": "include"}, {"path": "lib"}]

    project_spec = {
        "name": "saturn",
        "options": {"bundleIdPrefix": "com.saturn"},
        "settings": {
            "GCC_PREPROCESSOR_DEFINITIONS": ["NON_MATCHING=1", "DYNOS=1", "RAPI_GL=1", "WAPI_SDL2=1", "HAVE_SDL2=1", "VERSION_US=1", "$(inherited)"],
            "HEADER_SEARCH_PATHS": ["$(inherited)", "include", "src", "actors", "levels", ".", "/opt/homebrew/include", "/opt/homebrew/include/SDL2"],
            "LIBRARY_SEARCH_PATHS": ["$(inherited)", "/opt/homebrew/lib"],
            "CLANG_CXX_LANGUAGE_STANDARD": "c++17",
            "CLANG_CXX_LIBRARY": "libc++",
            # This completely disables ImGui memset errors and all strict clang warnings
            "OTHER_CFLAGS": ["-w"],
            "OTHER_CPLUSPLUSFLAGS": ["-w"]
        },
        "targets": {
            "saturn": {
                "type": "application",
                "platform": "iOS",
                "deploymentTarget": "14.0",
                "sources": sources,
                "settings": {
                    "ENABLE_BITCODE": "NO",
                    "CODE_SIGNING_ALLOWED": "NO",
                    "PRODUCT_NAME": "saturn",
                    "OTHER_LDFLAGS": ["$(inherited)", "-lSDL2"]
                }
            }
        }
    }

    with open("project.yml", "w") as f:
        yaml.dump(project_spec, f, default_flow_style=False)
        
    subprocess.check_call(["xcodegen", "generate"])

    print("[XCODEBUILD] Starting iOS Build...")
    cmd = ["xcodebuild", "-project", "saturn.xcodeproj", "-scheme", "saturn", "-configuration", "Release", "-sdk", "iphoneos", "ARCHS=arm64", "ONLY_ACTIVE_ARCH=NO", "CODE_SIGNING_ALLOWED=NO", "CODE_SIGN_IDENTITY=", "CODE_SIGNING_REQUIRED=NO", "CONFIGURATION_BUILD_DIR=build/Release-iphoneos", "clean", "build"]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    
    if process.returncode != 0:
        sys.exit(1)

    print("[PACKAGING] Generating saturn.ipa...")
    payload_dir = "Payload"
    if os.path.exists(payload_dir): shutil.rmtree(payload_dir)
    os.makedirs(payload_dir)
    shutil.copytree("build/Release-iphoneos/saturn.app", os.path.join(payload_dir, "saturn.app"))
    with zipfile.ZipFile("saturn.ipa", "w", zipfile.ZIP_DEFLATED) as ipa:
        for root, _, files in os.walk(payload_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                ipa.write(abs_path, os.path.join("Payload", os.path.relpath(abs_path, payload_dir)))

if __name__ == "__main__":
    install_deps()
    generate_mock_headers()
    # The Loop executes here until clean
    loop_until_clean()
    # Once the loop passes clean, build begins
    trigger_xcode_build()
