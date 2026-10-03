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
    print("[DOWNLOADER] Checking for missing external bundles...")
    os.makedirs("external_deps", exist_ok=True)
    downloads = {"imgui_src.zip": "https://github.com/ocornut/imgui/archive/refs/heads/master.zip"}
    for target_file, url in downloads.items():
        destination = os.path.join("external_deps", target_file)
        if not os.path.exists(destination):
            try:
                urllib.request.urlretrieve(url, destination)
            except Exception as e:
                pass

def setup_headers_and_mocks():
    print("[SETUP] Injecting standard headers and creating mock environment...")
    os.makedirs("include/PR", exist_ok=True)
    os.makedirs("include/SDL2", exist_ok=True)
    os.makedirs("src/saturn/imgui", exist_ok=True)

    with open("include/PR/ultratypes.h", "w") as f:
        f.write("#ifndef ULTRATYPES_H\n#define ULTRATYPES_H\n#include \n#define NON_MATCHING 1\ntypedef unsigned char u8;\ntypedef unsigned short u16;\ntypedef unsigned int u32;\ntypedef unsigned long long u64;\ntypedef signed char s8;\ntypedef short s16;\ntypedef int s32;\ntypedef long long s64;\ntypedef float f32;\ntypedef double f64;\n#endif\n")

    with open("include/SDL2/SDL.h", "w") as f:
        f.write("#ifndef SDL_H\n#define SDL_H\n#include \ntypedef unsigned int Uint32;\ntypedef unsigned char Uint8;\ntypedef unsigned short Uint16;\ntypedef int Sint32;\ntypedef int SDL_bool;\ntypedef int SDL_Keycode;\ntypedef struct SDL_Keysym { SDL_Keycode sym; } SDL_Keysym;\ntypedef struct SDL_KeyboardEvent { SDL_Keysym keysym; } SDL_KeyboardEvent;\ntypedef struct SDL_MouseMotionEvent { Sint32 xrel; Sint32 yrel; } SDL_MouseMotionEvent;\ntypedef union SDL_Event { Uint32 type; SDL_KeyboardEvent key; SDL_MouseMotionEvent motion; } SDL_Event;\ntypedef int SDL_Scancode;\n#define SDL_KEYDOWN 0x300\n#define SDL_MOUSEMOTION 0x400\n#define SDLK_m 'm'\n#define SDLK_n 'n'\n#define SDL_WINDOWPOS_CENTERED 0x2FFF0000\n#define SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS \"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS\"\n#ifdef __cplusplus\nextern \"C\" {\n#endif\nconst char* SDL_GetScancodeName(SDL_Scancode scancode);\nvoid SDL_SetWindowSize(void* window, int w, int h);\nvoid SDL_SetWindowPosition(void* window, int x, int y);\nSDL_bool SDL_SetHint(const char* name, const char* value);\nvoid SDL_Delay(Uint32 ms);\n#ifdef __cplusplus\n}\n#endif\n#endif\n")

    with open("include/PR/gbi.h", "w") as f:
        f.write("#ifndef GBI_H\n#define GBI_H\n#define G_TRI2 0xb1\n#endif\n")

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
    print("[XCODEGEN] Generating iOS project.yml (Excluding Windows/DirectX)...")
    sources = []
    
    # Exclusions to prevent DirectX and Windows Audio from breaking the iOS build
    platform_exclusions = ['dxsdk', 'direct3d', 'd3d11', 'd3d12', 'wgl', 'glx', 'wasapi', 'alsa', 'wiiu']
    
    for root, _, files in os.walk(os.getcwd()):
        if any(x in root.lower() for x in ['build', '.git', 'deriveddata', 'payload', 'external_deps'] + platform_exclusions):
            continue
        for file in files:
            if any(x in file.lower() for x in platform_exclusions):
                continue
                
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
    build_xcodegen_and_run()
