import os
import urllib.request
import tarfile
import zipfile
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

RUNTIMES = {
    "windows": {
        "python": "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.10.13+20240224-x86_64-pc-windows-msvc-shared-install_only.tar.gz",
        "yt_dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
        "ffmpeg": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "ffmpeg_extract": "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"
    },
    "macos": {
        "python": "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.10.13+20240224-x86_64-apple-darwin-install_only.tar.gz",
        "yt_dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
        "ffmpeg": "https://evermeet.cx/ffmpeg/getrelease/zip",
        "ffmpeg_extract": "ffmpeg"
    },
    "linux": {
        "python": "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.10.13+20240224-x86_64-unknown-linux-gnu-install_only.tar.gz",
        "yt_dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
        "ffmpeg": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "ffmpeg_extract": "ffmpeg-6.0.1-amd64-static/ffmpeg"
    }
}

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def extract_archive(archive_path, extract_dir):
    print(f"Extracting {archive_path} to {extract_dir}...")
    if archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_dir)
    elif archive_path.endswith('.tar.xz'):
        with tarfile.open(archive_path, 'r:xz') as tar_ref:
            tar_ref.extractall(extract_dir)

def install_pip_deps(python_target_dir, os_name):
    # 3. Pip Install
    python_platform_args = []
    target_dir = ""
    if os_name == "windows":
        target_dir = os.path.join(python_target_dir, "Lib", "site-packages")
        python_platform_args = ["--platform", "win_amd64"]
    elif os_name == "linux":
        target_dir = os.path.join(python_target_dir, "lib", "python3.10", "site-packages")
        python_platform_args = ["--platform", "manylinux2014_x86_64"]
    elif os_name == "macos":
        target_dir = os.path.join(python_target_dir, "lib", "python3.10", "site-packages")
        python_platform_args = ["--platform", "macosx_10_9_x86_64"]

    req_file = os.path.join(PROJECT_ROOT, "backend", "requirements.txt")
    
    # Use the host python to download wheels for the target platform
    pip_cmd = [
        sys.executable, "-m", "pip", "install", 
        "-r", req_file,
        "--target", target_dir,
        "--python-version", "3.10",
        "--only-binary=:all:"
    ] + python_platform_args
    
    print(f"Installing pip dependencies for {os_name} using host pip...")
    try:
        subprocess.run(pip_cmd, check=True)
    except Exception as e:
        print(f"⚠️ Warning: Failed to install pip deps for {os_name}: {e}")

def main():
    print("🚀 Starting Zero-Dependency Runtime Bundler...")
    
    for os_name, urls in RUNTIMES.items():
        print(f"\n--- Platform: {os_name} ---")
        
        runtime_dir = os.path.join(PROJECT_ROOT, "runtimes", os_name)
        bin_dir = os.path.join(PROJECT_ROOT, "bin", os_name)
        
        os.makedirs(runtime_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        
        # 1. Python
        python_target_dir = os.path.join(runtime_dir, "python")
        
        # Check if python is already there and complete (by checking for the binary)
        python_bin_name = "python.exe" if os_name == "windows" else "bin/python3"
        python_bin_path = os.path.join(python_target_dir, python_bin_name)
        
        if not os.path.exists(python_target_dir) or not os.path.exists(python_bin_path):
            if os.path.exists(python_target_dir):
                print(f"Python folder exists but is incomplete (missing {python_bin_name}), re-extracting...")
                shutil.rmtree(python_target_dir)
                
            archive_path = os.path.join(runtime_dir, f"python_archive.tar.gz") if os_name != "windows" else os.path.join(runtime_dir, f"python_archive.tar.gz")
            # Windows archive is also tar.gz in the urls map
            
            download_file(urls["python"], archive_path)
            extract_archive(archive_path, runtime_dir)
            
            # python-build-standalone usually extracts to a 'python' folder.
            # If it extracts directly, we should handle that, but typically it doesn't.
            if os.path.exists(archive_path):
                os.remove(archive_path)
        else:
            print("Python already exists and appears complete, skipping.")
            
        # 2. YT-DLP
        yt_dlp_name = "yt-dlp.exe" if os_name == "windows" else "yt-dlp"
        yt_dlp_path = os.path.join(bin_dir, yt_dlp_name)
        if not os.path.exists(yt_dlp_path):
            download_file(urls["yt_dlp"], yt_dlp_path)
            if os_name != "windows":
                os.chmod(yt_dlp_path, 0o755)
        else:
            print("YT-DLP already exists, skipping.")
            
        install_pip_deps(python_target_dir, os_name)
        
    print("\n✅ Bundling complete for Windows, Linux, and macOS!")

if __name__ == "__main__":
    main()
