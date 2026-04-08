import os
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RELEASES_DIR = os.path.join(PROJECT_ROOT, "releases")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

def build_macos():
    print("🚀 Starting Offline Mac Build Packager...")
    os.makedirs(RELEASES_DIR, exist_ok=True)
    
    # 1. Aggressive Lock Cleanup
    bundle_name = "SpotifySmartDownloader.app"
    desktop_bundle_dir = os.path.join(RELEASES_DIR, bundle_name)
    
    print(f"Location: {os.getcwd()}")
    print(f"Frontend: {os.listdir(FRONTEND_DIR)}")
    
    print("Building Desktop App for macOS...")
    try:
        # 0. Clean and Get Dependencies
        print("  Cleaning and fetching dependencies...")
        subprocess.run(["flutter", "clean"], cwd=FRONTEND_DIR, check=True)
        subprocess.run(["flutter", "pub", "get"], cwd=FRONTEND_DIR, check=True)
        # 1. New build
        subprocess.run(["flutter", "build", "macos"], cwd=FRONTEND_DIR, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ FATAL ERROR: Flutter build failed: {e}")
        return # STOP the build here
    
    ui_build_dir = os.path.join(FRONTEND_DIR, "build", "macos", "Build", "Products", "Release", "Spotify Smart Downloader.app")
    
    if os.path.exists(desktop_bundle_dir):
        print(f"♻️  Removing old bundle: {desktop_bundle_dir}")
        shutil.rmtree(desktop_bundle_dir, ignore_errors=True)
        if os.path.exists(desktop_bundle_dir):
            subprocess.run(["rm", "-rf", desktop_bundle_dir], check=False)
            
    print("  Copying compiled Flutter UI into releases...")
    shutil.copytree(ui_build_dir, desktop_bundle_dir)
    
    backend_env_dir = os.path.join(desktop_bundle_dir, "Contents", "Resources", "BackendEnv")
    os.makedirs(backend_env_dir, exist_ok=True)
    
    print("  Injecting Python backend, runtimes, binaries, and vendor dependencies into .app...")
    
    # helper for component check
    def check_exists(path, name):
        if not os.path.exists(path):
            print(f"❌ ERROR: Mandatory component missing: {name} at {path}")
            return False
        return True

    # 1. Dependency Refresh
    print("  Refreshing vendor dependencies from requirements.txt...")
    try:
        subprocess.run(["pip3", "install", "-r", os.path.join(PROJECT_ROOT, "backend", "requirements.txt"), "--target", os.path.join(PROJECT_ROOT, "vendor")], check=True)
    except Exception as e:
        print(f"⚠️ Warning: Dependency refresh failed: {e}. Continuing with existing vendor folder.")

    # 2. Backend Code
    shutil.copytree(os.path.join(PROJECT_ROOT, "backend"), os.path.join(backend_env_dir, "backend"))
    
    # 2. Vendor
    if os.path.exists(os.path.join(PROJECT_ROOT, "vendor")):
        shutil.copytree(os.path.join(PROJECT_ROOT, "vendor"), os.path.join(backend_env_dir, "vendor"))
    else:
        print("⚠️ Warning: 'vendor' directory not found. Backend may crash if dependencies are missing.")
    
    # 3. Python Runtime
    runtime_src = os.path.join(PROJECT_ROOT, "runtimes", "macos", "python")
    runtime_dest = os.path.join(backend_env_dir, "runtimes", "macos", "python")
    os.makedirs(os.path.dirname(runtime_dest), exist_ok=True)
    
    if check_exists(runtime_src, "Python Source Runtime"):
        shutil.copytree(runtime_src, runtime_dest)
        # Verify python bin exists in destination
        python_bin_dest = os.path.join(runtime_dest, "bin", "python3")
        if not check_exists(python_bin_dest, "Python Binary (in bundle)"):
            return # Exit build
    else:
        return # Exit build
    
    # 4. Binaries (FFmpeg, ffprobe, yt-dlp)
    os.makedirs(os.path.join(backend_env_dir, "bin", "macos"), exist_ok=True)
    bin_src = os.path.join(PROJECT_ROOT, "bin", "macos")
    if check_exists(bin_src, "macOS Binaries Folder"):
        for f in os.listdir(bin_src):
            shutil.copy(os.path.join(bin_src, f), os.path.join(backend_env_dir, "bin", "macos"))
        
        # Verify specific binaries
        check_exists(os.path.join(backend_env_dir, "bin", "macos", "ffmpeg"), "FFmpeg")
        check_exists(os.path.join(backend_env_dir, "bin", "macos", "ffprobe"), "ffprobe")
        check_exists(os.path.join(backend_env_dir, "bin", "macos", "yt-dlp"), "yt-dlp")
    else:
        return # Exit build

    # 1. Dependency Refresh (Handled earlier, this is just a placeholder to keep the code structure clean)
    
    # NEW: Create a bundled launcher script that mimics run.sh
    launcher_path = os.path.join(backend_env_dir, "launch_backend.app.sh")
    with open(launcher_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("cd \"$(dirname \"$0\")\"\n") # Ensure we are in the bundle resources directory
        f.write("export PYTHONPATH=\".:./vendor\"\n")
        # Add bin paths for ffmpeg/yt-dlp
        f.write("export PATH=\"./bin/macos:$PATH\"\n")
        # Run with the bundled python
        f.write("./runtimes/macos/python/bin/python3 ./backend/main.py --desktop\n")
    os.chmod(launcher_path, 0o755)

    print(f"✅ Desktop payload completely embedded into {bundle_name}")
    
    print("🔒 Fix permissions...")
    # Ensure the main executable is executable
    os.chmod(os.path.join(desktop_bundle_dir, "Contents", "MacOS", "Spotify Smart Downloader"), 0o755)
    
    # Applying recursive permissions to ensure nested Python libs and binaries are usable
    print("  Applying recursive permissions to runtime and binaries...")
    subprocess.run(["chmod", "-R", "755", os.path.join(backend_env_dir, "runtimes", "macos", "python")], check=True)
    subprocess.run(["chmod", "-R", "755", os.path.join(backend_env_dir, "bin", "macos")], check=True)

    print("🖋  Re-signing the .app bundle ad-hoc...")
    try:
        # First sign internal frameworks and dylibs in the Python runtime
        python_lib_dir = os.path.join(backend_env_dir, "runtimes", "macos", "python", "lib")
        if os.path.exists(python_lib_dir):
            print("  Signing Python internal libraries...")
            subprocess.run(["find", python_lib_dir, "-name", "*.dylib", "-exec", "codesign", "--force", "--sign", "-", "{}", "+"], check=True)
            subprocess.run(["find", python_lib_dir, "-name", "*.so", "-exec", "codesign", "--force", "--sign", "-", "{}", "+"], check=True)

        # Sign the standalone binaries
        print("  Signing helper binaries (ffmpeg/yt-dlp)...")
        for b in ["ffmpeg", "ffprobe", "yt-dlp"]:
            b_path = os.path.join(backend_env_dir, "bin", "macos", b)
            subprocess.run(["codesign", "--force", "--sign", "-", b_path], check=True)

        # Finally sign the whole app bundle
        print("  Signing main application bundle...")
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", desktop_bundle_dir], check=True)
        print("✅ App successfully re-signed and ready for offline use.")
    except Exception as e:
        print(f"⚠️ Warning: Code signing encountered issues: {e}")
        print("App may still fail to open due to security policies.")

if __name__ == "__main__":
    build_macos()
