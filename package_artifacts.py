#!/usr/bin/env python3
import os
import shutil
import zipfile

def create_ipa():
    print("[PACKAGING] Locating compiled saturn.app...")
    app_path = "build/Release-iphoneos/saturn.app"
    if not os.path.exists(app_path):
        for root, dirs, files in os.walk("."):
            if "saturn.app" in dirs:
                app_path = os.path.join(root, "saturn.app")
                break

    payload_dir = "Payload"
    if os.path.exists(payload_dir):
        shutil.rmtree(payload_dir)
    os.makedirs(payload_dir)
    
    dest_app = os.path.join(payload_dir, "saturn.app")
    if os.path.exists(app_path):
        shutil.copytree(app_path, dest_app)
    else:
        print(f"[WARNING] saturn.app not found at {app_path}. Creating fallback bundle structure.")
        os.makedirs(dest_app, exist_ok=True)

    # Copy resources into the app bundle payload
    for resource in ["imgui.ini", "baserom.us.z64", "discord_game_sdk.dll"]:
        if os.path.exists(resource) and not os.path.exists(os.path.join(dest_app, resource)):
            shutil.copy(resource, os.path.join(dest_app, resource))

    ipa_name = "saturn.ipa"
    with zipfile.ZipFile(ipa_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(payload_dir):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, start="."))

    print(f"[ARTIFACT 1 READY] {ipa_name} (~{os.path.getsize(ipa_name) / (1024 * 1024):.2f} MB)")

def create_xcode_source_zip():
    print("[PACKAGING] Creating Xcode source project archive...")
    zip_name = "saturn-xcode-source.zip"
    allowed_exts = ('.c', '.cpp', '.h', '.hpp', '.m', '.mm', '.py', '.sh', '.json', '.dll', '.z64', '.ini', '.yml', '.plist', '.xcodeproj', '.xcworkspace')
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("."):
            if any(x in root for x in ['build', '.git', 'DerivedData', 'Payload']):
                continue
            for file in files:
                if os.path.splitext(file)[1].lower() in allowed_exts or file in ["project.yml", "Info.plist", "imgui.ini"]:
                    full_path = os.path.join(root, file)
                    zipf.write(full_path, os.path.relpath(full_path, start="."))

    print(f"[ARTIFACT 2 READY] {zip_name} (~{os.path.getsize(zip_name) / (1024 * 1024):.2f} MB)")

if __name__ == "__main__":
    create_ipa()
    create_xcode_source_zip()
