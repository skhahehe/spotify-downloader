import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")  # dep_manager prints emoji; Windows CI console is cp1252

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RELEASES_DIR = os.path.join(PROJECT_ROOT, "releases")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

def build_windows():
    print("--- Starting Offline Windows Build Packager ---")
    os.makedirs(RELEASES_DIR, exist_ok=True)
    
    print(f"Location: {os.getcwd()}")
    print(f"Frontend: {os.listdir(FRONTEND_DIR)}")
    
    print("Building Desktop App for Windows...")
    # Get dependencies first
    subprocess.run(["flutter", "pub", "get"], cwd=FRONTEND_DIR, check=True, shell=True)
    subprocess.run(["flutter", "build", "windows"], cwd=FRONTEND_DIR, check=True, shell=True)
    
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

    # runtimes/, bin/ and vendor/ are gitignored, so a fresh checkout (CI) has none of them: fetch them
    runtime_python = os.path.join(PROJECT_ROOT, "runtimes", "windows", "python", "python.exe")
    if not os.path.exists(runtime_python) or not os.path.exists(os.path.join(PROJECT_ROOT, "bin", "windows", "yt-dlp.exe")):
        print("  Fetching bundled Python runtime and yt-dlp...")
        subprocess.run([sys.executable, "-X", "utf8", os.path.join(SCRIPT_DIR, "bundle_all_runtimes.py"), "windows"], check=True)
    sys.path.insert(0, PROJECT_ROOT)
    from backend.services.dep_manager import ensure_dependencies
    ensure_dependencies()  # ffmpeg/ffprobe into bin/windows if missing

    # Install with the bundled Python so compiled wheels match its version (host CI python is 3.9)
    print("  Refreshing vendor dependencies from requirements.txt...")
    try:
        subprocess.run([runtime_python, "-m", "pip", "install", "-r", os.path.join(PROJECT_ROOT, "backend", "requirements.txt"), "--target", os.path.join(PROJECT_ROOT, "vendor")], check=True)
    except Exception as e:
        print(f" Warning: Dependency refresh failed: {e}. Continuing with existing vendor folder.")

    for path, name in [(runtime_python, "Python runtime"), (os.path.join(PROJECT_ROOT, "vendor"), "vendor"),
                       *[(os.path.join(PROJECT_ROOT, "bin", "windows", b), b) for b in ("ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe")]]:
        if not os.path.exists(path):
            print(f" ERROR: Mandatory component missing: {name} at {path}")
            sys.exit(1)

    shutil.copytree(os.path.join(PROJECT_ROOT, "backend"), os.path.join(backend_env_dir, "backend"))
    shutil.copytree(os.path.join(PROJECT_ROOT, "vendor"), os.path.join(backend_env_dir, "vendor"))
    
    os.makedirs(os.path.join(backend_env_dir, "runtimes", "windows"), exist_ok=True)
    os.makedirs(os.path.join(backend_env_dir, "bin", "windows"), exist_ok=True)

    shutil.copytree(os.path.dirname(runtime_python), os.path.join(backend_env_dir, "runtimes", "windows", "python"))

    bin_src = os.path.join(PROJECT_ROOT, "bin", "windows")
    for f in os.listdir(bin_src):
        shutil.copy(os.path.join(bin_src, f), os.path.join(backend_env_dir, "bin", "windows"))

    print(f"Done: Desktop payload completely embedded into {bundle_name}")

if __name__ == "__main__":
    build_windows()
