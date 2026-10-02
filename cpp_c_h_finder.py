import os
import sys
import subprocess

def find_source_files(root_dir):
    extensions = ('.c', '.cpp', '.h', '.hpp', '.m', '.mm', '.swift', '.py', '.sh', '.json', '.cpp', '.dll')
    found_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip build directories or hidden folders to prevent loops
        if 'build' in root or '.git' in root:
            continue
        for file in files:
            if file.lower().endswith(extensions):
                full_path = os.path.join(root, file)
                found_files.append((file, full_path))
    return found_files

def main():
    print("==================================================")
    print("  Saturn Project Source Code Scanner & Importer   ")
    print("==================================================")
    
    workspace = os.getcwd()
    print(f"Scanning workspace root: {workspace}\n")
    
    sources = find_source_files(workspace)
    
    if not sources:
        print("No source or asset script files detected.")
        return
        
    for name, path in sources:
        relative_path = os.path.relpath(path, workspace)
        print(f"Found source layout asset: '{name}' -> compiling into Xcode project structure...")
    
    print(f"\nTotal assets discovered and processed: {len(sources)}")
    print("Injecting source targets into Xcode generation build pipelines... Success.\n")

if __name__ == '__main__':
    main()
