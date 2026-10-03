#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import plistlib
import zipfile
import re

def install_deps():
    try:
        import yaml
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "--break-system-packages"])

def restore_clean_repo():
    print("[CLEANUP] Resetting git workspace to clean state...")
    try:
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
        subprocess.run(["git", "clean", "-fd"], check=True)
    except Exception as e:
        print(f"[WARNING] Git reset error: {e}")

def fix_broken_includes_in_all_files():
    print("[SCANNER] Cleaning broken empty #include lines across codebase...")
    repo_root = os.getcwd()
    cleaned = 0
    for root, _, files in os.walk(repo_root):
        if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload']):
            continue
        for file in files:
            if file.endswith(('.c', '.cpp', '.h', '.hpp', '.m', '.mm')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Remove broken empty includes like "#include \n" or "#include \r\n"
                    new_content = re.sub(r'#include\s*(\r?\n|\Z)', '', content)
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        cleaned += 1
                except Exception:
                    pass
    print(f"[SCANNER] Purged empty includes in {cleaned} source files.")

def create_info_plist():
    print("[PLIST] Creating Info.plist...")
    plist_data = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": "saturn",
        "CFBundleIdentifier": "com.saturn.app",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "saturn",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1",
        "LSRequiresIPhoneOS": True,
        "UIDeviceFamily": [1, 2]
    }
    with open("Info.plist", "wb") as f:
        plistlib.dump(plist_data, f)

def generate_mock_headers():
    print("[MOCKS] Generating global mock headers with explicit standard includes...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)

    inc_stddef = "#include " + "\n"
    inc_stdint = "#include " + "\n"
    inc_stdbool = "#include " + "\n"

    with open("include/PR/ultratypes.h", "w", encoding="utf-8") as f:
        f.write("#ifndef ULTRATYPES_H\n#define ULTRATYPES_H\n")
        f.write(inc_stddef)
        f.write(inc_stdint)
        f.write(inc_stdbool)
        f.write("""
#ifndef NON_MATCHING
#define NON_MATCHING 1
#endif

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t   s8;
typedef int16_t  s16;
typedef int32_t  s32;
typedef int64_t  s64;
typedef float    f32;
typedef double   f64;
#endif
""")

    with open("include/SDL2/SDL.h", "w", encoding="utf-8") as f:
        f.write("#ifndef SDL_H\n#define SDL_H\n")
        f.write(inc_stddef)
        f.write(inc_stdint)
        f.write(inc_stdbool)
        f.write("""
typedef struct SDL_Window SDL_Window;
typedef void* SDL_GLContext;
typedef struct SDL_Renderer SDL_Renderer;
typedef struct SDL_Texture SDL_Texture;
typedef struct SDL_Surface SDL_Surface;

typedef uint32_t Uint32;
typedef uint8_t  Uint8;
typedef uint16_t Uint16;
typedef int32_t  Sint32;
typedef int      SDL_bool;
typedef int      SDL_Keycode;

typedef struct SDL_Keysym { SDL_Keycode sym; } SDL_Keysym;
typedef struct SDL_KeyboardEvent { SDL_Keysym keysym; } SDL_KeyboardEvent;
typedef struct SDL_MouseMotionEvent { Sint32 xrel; Sint32 yrel; } SDL_MouseMotionEvent;
typedef union SDL_Event { Uint32 type; SDL_KeyboardEvent key; SDL_MouseMotionEvent motion; } SDL_Event;
typedef int SDL_Scancode;

#define SDL_KEYDOWN 0x300
#define SDL_MOUSEMOTION 0x400
#define SDLK_m 'm'
#define SDLK_n 'n'
#define SDL_WINDOWPOS_CENTERED 0x2FFF0000
#define SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_ENTIONS ""

#ifdef __cplusplus
extern "C" {
#endif
const char* SDL_GetScancodeName(SDL_Scancode scancode);
void SDL_SetWindowSize(void* window, int w, int h);
void SDL_SetWindowPosition(void* window, int x, int y);
SDL_bool SDL_SetHint(const char* name, const char* value);
void SDL_Delay(Uint32 ms);
#ifdef __cplusplus
}
#endif
#endif
""")

    with open("include/PR/gbi.h", "w", encoding="utf-8") as f:
        f.write("""#ifndef GBI_H
#define GBI_H
#include "ultratypes.h"

#define G_TRI2 0xb1

#ifdef __cplusplus
extern "C" {
#endif

typedef struct Gfx Gfx;
typedef struct Mtx Mtx;
typedef struct Vp Vp;
typedef struct LookAt LookAt;
typedef struct Lights1 Lights1;
typedef struct Light Light;
typedef struct Hilite Hilite;

typedef struct {
    s16 ob[3];
    u16 tc[2];
    u8  cn[4];
} Vtx_t;

typedef union {
    Vtx_t v;
    long long force_structure_alignment;
} Vtx;

#ifdef __cplusplus
}
#endif
#endif
""")

def generate_project_spec(extra_excludes=None):
    import yaml
    if extra_excludes is None:
        extra_excludes = []

    base_asset_excludes = ["**/*.yaml", "**/*.png", "**/*.json", "**/*.bin", "**/*.a", "**/*.m64"] + list(set(extra_excludes))

    sources = [
        {
            "path": "src",
            "excludes": [
                "pc/win32",
                "pc/dxsdk",
                "pc/gfx/gfx_direct3d11.cpp",
                "pc/gfx/gfx_dxgi.cpp",
                "pc/gfx/gfx_glx.c",
                "pc/gfx/gfx_wgl.c",
                "pc/audio/audio_wasapi.c",
                "pc/audio/audio_alsa.c"
            ]
        },
        {"path": "actors", "excludes": base_asset_excludes},
        {"path": "levels", "excludes": base_asset_excludes},
        {"path": "include"},
        {"path": "lib"}
    ]

    force_include_flags = [
        "-w",
        "-DNON_MATCHING=1",
        "-DVERSION_US=1",
        "-DDYNOS=1",
        "-DRAPI_GL=1",
        "-DWAPI_SDL2=1",
        "-DHAVE_SDL2=1",
        "-include", "include/PR/ultratypes.h",
        "-include", "include/PR/gbi.h",
        "-include", "include/SDL2/SDL.h"
    ]

    project_spec = {
        "name": "saturn",
        "options": {
            "bundleIdPrefix": "com.saturn",
            "createIntermediateGroups": True
        },
        "settings": {
            "GCC_PREPROCESSOR_DEFINITIONS": [
                "NON_MATCHING=1",
                "DYNOS=1",
                "RAPI_GL=1",
                "WAPI_SDL2=1",
                "HAVE_SDL2=1",
                "VERSION_US=1",
                "$(inherited)"
            ],
            "HEADER_SEARCH_PATHS": [
                "$(inherited)",
                "include",
                "src",
                "actors",
                "levels",
                ".",
                "/opt/homebrew/include",
                "/opt/homebrew/include/SDL2"
            ],
            "LIBRARY_SEARCH_PATHS": [
                "$(inherited)",
                "/opt/homebrew/lib"
            ],
            "CLANG_CXX_LANGUAGE_STANDARD": "c++17",
            "CLANG_CXX_LIBRARY": "libc++",
            "OTHER_CFLAGS": force_include_flags,
            "OTHER_CPLUSPLUSFLAGS": force_include_flags
        },
        "targets": {
            "saturn": {
                "type": "application",
                "platform": "iOS",
                "deploymentTarget": "14.0",
                "sources": sources,
                "info": {"path": "Info.plist"},
                "settings": {
                    "ENABLE_BITCODE": "NO",
                    "CODE_SIGNING_ALLOWED": "NO",
                    "PRODUCT_NAME": "saturn",
                    "OTHER_LDFLAGS": ["$(inherited)", "-lSDL2"]
                }
            }
        }
    }

    with open("project.yml", "w", encoding="utf-8") as f:
        yaml.dump(project_spec, f, default_flow_style=False)

def continuous_smart_build_loop():
    extra_excludes = []
    iteration = 1

    while True:
        print(f"\n==================================================")
        print(f"       CONTINUOUS BUILD & PATCH LOOP: ITERATION {iteration}")
        print(f"==================================================")

        # 1. Ensure mock headers and cleaned files are in place
        fix_broken_includes_in_all_files()
        generate_mock_headers()
        generate_project_spec(extra_excludes)

        # 2. Run XcodeGen
        print("[XCODEGEN] Refreshing Xcode project...")
        subprocess.check_call(["xcodegen", "generate"])

        # 3. Execute Xcode build and capture output
        print("[XCODEBUILD] Executing build...")
        cmd = [
            "xcodebuild",
            "-project", "saturn.xcodeproj",
            "-scheme", "saturn",
            "-configuration", "Release",
            "-sdk", "iphoneos",
            "ARCHS=arm64",
            "ONLY_ACTIVE_ARCH=NO",
            "CODE_SIGNING_ALLOWED=NO",
            "CODE_SIGN_IDENTITY=",
            "CODE_SIGNING_REQUIRED=NO",
            "CONFIGURATION_BUILD_DIR=build/Release-iphoneos",
            "clean",
            "build"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        build_output = []

        for line in process.stdout:
            print(line, end="")
            build_output.append(line)

        process.wait()

        if process.returncode == 0:
            print("\n==================================================")
            print(" [SUCCESS] Xcode build completed with ZERO errors!")
            print("==================================================")
            return True

        # 4. Error Analysis & Auto-Patching
        full_log = "".join(build_output)
        print("\n[BUILD FAILED] Analyzing logs to auto-repair issues...")

        patched_something = False

        # Repair 1: Resource Collision ("Multiple commands produce" or "duplicate output file")
        collisions = re.findall(r"Multiple commands produce '.*?/saturn\.app/(.*?)'", full_log)
        collisions += re.findall(r"duplicate output file '.*?/saturn\.app/(.*?)'", full_log)
        if collisions:
            for item in set(collisions):
                pattern = f"**/{item}"
                if pattern not in extra_excludes:
                    extra_excludes.append(pattern)
                    print(f"[AUTO-FIX] Added build exclusion for colliding resource: {pattern}")
                    patched_something = True

        # Repair 2: Check for broken include syntax errors in specific files
        error_files = re.findall(r"(/[^:\n]+):\d+:\d+: error:", full_log)
        if error_files:
            for filepath in set(error_files):
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            c = f.read()
                        new_c = re.sub(r'#include\s*(\r?\n|\Z)', '', c)
                        if new_c != c:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_c)
                            print(f"[AUTO-FIX] Repaired broken #include syntax in: {filepath}")
                            patched_something = True
                    except Exception:
                        pass

        iteration += 1

        if not patched_something and iteration > 30:
            print("[FATAL] Maximum repair iterations reached without progress.")
            return False

def package_ipa():
    print("[POST-BUILD] Embedding DynOS asset packs...")
    app_dynos_path = "build/Release-iphoneos/saturn.app/dynos"
    if os.path.exists("dynos"):
        if os.path.exists(app_dynos_path):
            shutil.rmtree(app_dynos_path)
        shutil.copytree("dynos", app_dynos_path)

    print("[PACKAGING] Generating saturn.ipa package...")
    payload_dir = "Payload"
    if os.path.exists(payload_dir):
        shutil.rmtree(payload_dir)
    os.makedirs(payload_dir)

    shutil.copytree("build/Release-iphoneos/saturn.app", os.path.join(payload_dir, "saturn.app"))

    with zipfile.ZipFile("saturn.ipa", "w", zipfile.ZIP_DEFLATED) as ipa:
        for root, _, files in os.walk(payload_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, payload_dir)
                ipa.write(abs_path, os.path.join("Payload", rel_path))

    print("[COMPLETED] saturn.ipa generated successfully!")

if __name__ == "__main__":
    install_deps()
    restore_clean_repo()
    create_info_plist()
    
    if continuous_smart_build_loop():
        package_ipa()
    else:
        sys.exit(1)
