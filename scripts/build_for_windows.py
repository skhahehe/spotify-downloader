import os
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RELEASES_DIR = os.path.join(PROJECT_ROOT, "releases")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

def build_windows():
    print("🚀 Starting Offline Windows Build Packager...")
    os.makedirs(RELEASES_DIR, exist_ok=True)
    
    print("💻 Building Desktop App for Windows...")
    subprocess.run(["flutter", "build", "windows"], cwd=FRONTEND_DIR, check=True)
    
    ui_build_dir = os.path.join(FRONTEND_DIR, "build", "windows", "x64", "runner", "Release")
    bundle_name = "SpotifySmartDownloader-Windows"
    desktop_bundle_dir = os.path.join(RELEASES_DIR, bundle_name)
    
    if os.path.exists(desktop_bundle_dir):
        shutil.rmtree(desktop_bundle_dir)
        
    print("  Copying compiled Flutter UI into releases...")
    shutil.copytree(ui_build_dir, desktop_bundle_dir)
    
    # Rename frontend.exe to SpotifySmartDownloader.exe
    if os.path.exists(os.path.join(desktop_bundle_dir, "frontend.exe")):
        os.rename(os.path.join(desktop_bundle_dir, "frontend.exe"), os.path.join(desktop_bundle_dir, "SpotifySmartDownloader.exe"))

    backend_env_dir = os.path.join(desktop_bundle_dir, "BackendEnv")
    os.makedirs(backend_env_dir, exist_ok=True)
    
    print("  Injecting Python backend, runtimes, binaries, and vendor dependencies into BackendEnv...")
    shutil.copytree(os.path.join(PROJECT_ROOT, "backend"), os.path.join(backend_env_dir, "backend"))
    if os.path.exists(os.path.join(PROJECT_ROOT, "vendor")):
        shutil.copytree(os.path.join(PROJECT_ROOT, "vendor"), os.path.join(backend_env_dir, "vendor"))
    else:
        print("⚠️ Warning: 'vendor' directory not found. Backend may crash if dependencies are missing.")
    
    os.makedirs(os.path.join(backend_env_dir, "runtimes", "windows"), exist_ok=True)
    os.makedirs(os.path.join(backend_env_dir, "bin", "windows"), exist_ok=True)

    runtime_src = os.path.join(PROJECT_ROOT, "runtimes", "windows", "python")
    if os.path.exists(runtime_src):
        shutil.copytree(runtime_src, os.path.join(backend_env_dir, "runtimes", "windows", "python"))
    
    bin_src = os.path.join(PROJECT_ROOT, "bin", "windows")
    if os.path.exists(bin_src):
        for f in os.listdir(bin_src):
            shutil.copy(os.path.join(bin_src, f), os.path.join(backend_env_dir, "bin", "windows"))

    print(f"✅ Desktop payload completely embedded into {bundle_name}")

if __name__ == "__main__":
    build_windows()
