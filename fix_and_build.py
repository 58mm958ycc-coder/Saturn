import os

def patch_missing_includes():
    print("[PATCH] Fixing missing size_t, SDL, and GBI includes...")
    
    # 1. Fix size_t in PR headers
    pr_headers = ["include/PR/os_cache.h", "include/PR/os_pi.h"]
    for header in pr_headers:
        if os.path.exists(header):
            with open(header, "r+") as f:
                content = f.read()
                if "" not in content:
                    f.seek(0, 0)
                    f.write("#include \n" + content)

    # 2. Fix SDL and Fast3D in Machinima UI
    machinima_cpp = "src/saturn/imgui/saturn_imgui_machinima.cpp"
    if os.path.exists(machinima_cpp):
        with open(machinima_cpp, "r+") as f:
            content = f.read()
            includes_to_add = ""
            if "SDL.h" not in content:
                includes_to_add += "#include \n"
            if "gbi.h" not in content:
                includes_to_add += "#include \n"
            
            if includes_to_add:
                f.seek(0, 0)
                f.write(includes_to_add + content)

# Call this before your XcodeGen/Build steps
patch_missing_includes()
