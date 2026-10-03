#!/usr/bin/env python3
import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
import plistlib

def self_install_deps():
    try:
        import yaml
    except ImportError:
        print("[SETUP] PyYAML missing. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "--break-system-packages"])

def fetch_external_assets_and_ipas():
    print("[DOWNLOADER] Checking for missing external bundles and IPA resources...")
    os.makedirs("external_deps", exist_ok=True)
    
    # Download extra asset archives or reference IPAs if required
    downloads = {
        "imgui_src.zip": "https://github.com/ocornut/imgui/archive/refs/heads/master.zip"
    }

    for target_file, url in downloads.items():
        destination = os.path.join("external_deps", target_file)
        if not os.path.exists(destination):
            try:
                print(f"[DOWNLOAD] Fetching {url}...")
                urllib.request.urlretrieve(url, destination)
            except Exception as e:
                print(f"[WARNING] Could not fetch {url}: {e}")

    # Extract missing ImGui headers if src/imgui is empty
    if os.path.exists("external_deps/imgui_src.zip") and not os.path.exists("src/imgui/imgui.h"):
        print("[EXTRACT] Extracting Dear ImGui source into src/imgui...")
        os.makedirs("src/imgui", exist_ok=True)
        with zipfile.ZipFile("external_deps/imgui_src.zip", "r") as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith((".cpp", ".h")) and "examples" not in member:
                    filename = os.path.basename(member)
                    if filename:
                        with zip_ref.open(member) as source, open(os.path.join("src/imgui", filename), "wb") as target:
                            shutil.copyfileobj(source, target)

def setup_headers_and_mocks():
    print("[SETUP] Injecting standard headers and creating mock environment...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)
    os.makedirs("src/saturn/imgui", exist_ok=True)

    ultratypes = """#ifndef ULTRATYPES_H
#define ULTRATYPES_H
#include 
#define NON_MATCHING 1
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed char s8;
typedef short s16;
typedef int s32;
typedef long long s64;
typedef float f32;
typedef double f64;
#endif
"""
    with open("include/PR/ultratypes.h", "w") as f:
        f.write(ultratypes)

    sdl_header = """#ifndef SDL_H
#define SDL_H
#include 
typedef unsigned int Uint32;
typedef unsigned char Uint8;
typedef unsigned short Uint16;
typedef int Sint32;
typedef int SDL_bool;
typedef int SDL_Keycode;

typedef struct SDL_Keysym {
    SDL_Keycode sym;
} SDL_Keysym;

typedef struct SDL_KeyboardEvent {
    SDL_Keysym keysym;
} SDL_KeyboardEvent;

typedef struct SDL_MouseMotionEvent {
    Sint32 xrel;
    Sint32 yrel;
} SDL_MouseMotionEvent;

typedef union SDL_Event {
    Uint32 type;
    SDL_KeyboardEvent key;
    SDL_MouseMotionEvent motion;
} SDL_Event;

typedef int SDL_Scancode;

#define SDL_KEYDOWN 0x300
#define SDL_MOUSEMOTION 0x400
#define SDLK_m 'm'
#define SDLK_n 'n'
#define SDL_WINDOWPOS_CENTERED 0x2FFF0000
#define SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS "SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"

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
"""
    with open("include/SDL2/SDL.h", "w") as f:
        f.write(sdl_header)

    gbi_header = """#ifndef GBI_H
#define GBI_H
#define G_TRI2 0xb1
#endif
"""
    with open("include/PR/gbi.h", "w") as f:
        f.write(gbi_header)

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

def patch_missing_includes():
    print("[PATCH] Injecting stddef.h, SDL.h, and gbi.h into source files...")
    
    headers_to_fix = ["include/PR/os_cache.h", "include/PR/os_pi.h"]
    for header in headers_to_fix:
        if os.path.exists(header):
            with open(header, "r") as f:
                content = f.read()
            if "" not in content:
                with open(header, "w") as f:
                    f.write("#include \n" + content)

    machinima_cpp = "src/saturn/imgui/saturn_imgui_machinima.cpp"
    if os.path.exists(machinima_cpp):
        with open(machinima_cpp, "r") as f:
            content = f.read()
        
        injections = ""
        if "" not in content:
            injections += "#include \n"
        if "SDL.h" not in content:
            injections += "#include \n"
        if "gbi.h" not in content:
            injections += "#include \n"

        if injections:
            with open(machinima_cpp, "w") as f:
                f.write(injections + content)

def build_xcodegen_and_run():
    import yaml
    print("[XCODEGEN] Generating project.yml...")
    sources = []
    for root, _, files in os.walk(os.getcwd()):
        if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload', 'external_deps']):
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ('.c', '.cpp', '.h', '.hpp', '.m', '.mm'):
                rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                sources.append({"path": rel_path, "optional": True})

    project_spec = {
        "name": "saturn",
        "options": {"bundleIdPrefix": "com.saturn"},
        "settings": {
            "GCC_PREPROCESSOR_DEFINITIONS": ["NON_MATCHING=1", "$(inherited)"],
            "HEADER_SEARCH_PATHS": ["$(inherited)", "include", "src", "."]
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
                    "PRODUCT_NAME": "saturn"
                }
            }
        }
    }

    with open("project.yml", "w") as f:
        yaml.dump(project_spec, f, default_flow_style=False)

    subprocess.check_call(["xcodegen", "generate"])

    cmd = (
        "xcodebuild -project saturn.xcodeproj -scheme saturn -configuration Release "
        "-sdk iphoneos ARCHS=arm64 ONLY_ACTIVE_ARCH=NO CODE_SIGNING_ALLOWED=NO "
        "CODE_SIGN_IDENTITY='' CODE_SIGNING_REQUIRED=NO "
        "CONFIGURATION_BUILD_DIR=build/Release-iphoneos clean build"
    )
    subprocess.check_call(cmd, shell=True)

if __name__ == "__main__":
    self_install_deps()
    fetch_external_assets_and_ipas()
    setup_headers_and_mocks()
    patch_missing_includes()
    build_xcodegen_and_run()
