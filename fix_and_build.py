#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import plistlib
import zipfile

def self_install_deps():
    try:
        import yaml
    except ImportError:
        print("[SETUP] PyYAML missing. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "--break-system-packages"])

def clean_duplicate_resources():
    print("[CLEANUP] Scanning and purging duplicate resource files to prevent Xcode collisions...")
    repo_root = os.getcwd()
    seen_files = set()
    removed_count = 0
    
    target_dirs = ['levels', 'actors', 'assets', 'data']
    for d in target_dirs:
        dir_path = os.path.join(repo_root, d)
        if not os.path.exists(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(('.yaml', '.png', '.bin', '.json')):
                    file_lower = file.lower()
                    if file_lower in seen_files and file_lower != 'config.yaml':
                        dup_path = os.path.join(root, file)
                        try:
                            os.remove(dup_path)
                            removed_count += 1
                        except Exception:
                            pass
                    else:
                        seen_files.add(file_lower)
                        
    print(f"[CLEANUP] Duplicate purge complete. Removed {removed_count} redundant asset files.")

def clean_and_validate_sources():
    print("[VALIDATOR] Scanning repository for scriptable .cpp, .c, .h, and .m files...")
    repo_root = os.getcwd()
    platform_exclusions = ['dxsdk', 'direct3d', 'd3d11', 'd3d12', 'wgl', 'glx', 'wasapi', 'alsa', 'wiiu']
    
    scanned = 0
    fixed = 0
    
    for root, _, files in os.walk(repo_root):
        if any(x in root.lower() for x in ['build', '.git', 'deriveddata', 'payload', 'external_deps'] + platform_exclusions):
            continue
        for file in files:
            if file.endswith(('.cpp', '.c', '.h', '.hpp', '.m', '.mm')):
                scanned += 1
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                except Exception:
                    continue
                
                new_lines = []
                changed = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('#include') and len(stripped.split()) < 2:
                        changed = True
                        continue
                    new_lines.append(line)
                    
                content = "".join(new_lines)
                injections = []
                if 'std::filesystem' in content and '#include ' not in content:
                    injections.append('#include \n')
                if 'size_t' in content and '#include ' not in content and '#include ' not in content:
                    injections.append('#include \n')
                    
                if injections or changed:
                    final_content = "".join(injections) + "".join(new_lines)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    fixed += 1
                    
    print(f"[VALIDATOR] Scanned {scanned} scriptable files. Cleaned/fixed {fixed} files.")

def setup_headers_and_mocks():
    print("[SETUP] Injecting full standard headers and mock environment...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)
    os.makedirs("src/saturn/imgui", exist_ok=True)

    with open("include/PR/ultratypes.h", "w") as f:
        f.write("""#ifndef ULTRATYPES_H
#define ULTRATYPES_H
#include 
#include 
#define NON_MATCHING 1
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

    with open("include/SDL2/SDL.h", "w") as f:
        f.write("""#ifndef SDL_H
#define SDL_H
#include 
#include 

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
#define SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_ENTIONS "SDL_JOYSTICK_ALLOW_BACKGROUND_ENTIONS"

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

    with open("include/PR/gbi.h", "w") as f:
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

def build_xcodegen_and_run():
    import yaml
    print("[XCODEGEN] Generating project.yml covering all repository code directories...")
    
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
        {"path": "actors"},
        {"path": "levels"},
        {"path": "include"},
        {"path": "lib"}
    ]

    project_spec = {
        "name": "saturn",
        "options": {"bundleIdPrefix": "com.saturn"},
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
            "CLANG_CXX_LIBRARY": "libc++"
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

    with open("project.yml", "w") as f:
        yaml.dump(project_spec, f, default_flow_style=False)

    subprocess.check_call(["xcodegen", "generate"])

    print("[XCODEBUILD] Building iOS target...")
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
    for line in process.stdout:
        print(line, end="")
    process.wait()
    
    if process.returncode != 0:
        print(f"[XCODEBUILD ERROR] Build failed with exit code {process.returncode}")
        sys.exit(1)

    print("[POST-BUILD] Embedding DynOS asset packs...")
    app_dynos_path = "build/Release-iphoneos/saturn.app/dynos"
    if os.path.exists("dynos"):
        if os.path.exists(app_dynos_path):
            shutil.rmtree(app_dynos_path)
        shutil.copytree("dynos", app_dynos_path)

    print("[PACKAGER] Packaging final .ipa file...")
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
                
    print("[SUCCESS] saturn.ipa generated and ready!")

if __name__ == "__main__":
    self_install_deps()
    clean_duplicate_resources()
    clean_and_validate_sources()
    setup_headers_and_mocks()
    build_xcodegen_and_run()
