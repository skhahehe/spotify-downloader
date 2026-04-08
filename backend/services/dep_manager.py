import os
import sys
import platform
import zipfile
import requests
import io
from pathlib import Path

# Base directories
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
BIN_DIR = PROJECT_ROOT / "bin"

def is_android():
    return os.environ.get('ANDROID_STORAGE') is not None or "android" in sys.platform

def get_binary_path(name: str) -> str:
    """Returns the path to the bundled binary with auto-resolve per system."""
    system = platform.system().lower()
    if system == "darwin":
        system = "macos"
    
    if is_android():
        binary_path = os.path.join(os.getcwd(), "bin", name)
        if os.path.exists(binary_path):
            return binary_path
        return name
        
    ext = ".exe" if system == "windows" else ""
    binary_name = f"{name}{ext}"
    
    # Check bundled 'bin' directory first
    bundled_path = BIN_DIR / system / binary_name
    if bundled_path.exists():
        return str(bundled_path.absolute())
    
    return str(bundled_path.absolute())

def ensure_dependencies():
    """Auto-detect and download yt-dlp and ffmpeg/ffprobe if missing."""
    if is_android():
        return True
        
    system = platform.system().lower()
    os_name = "macos" if system == "darwin" else system
    
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    (BIN_DIR / os_name).mkdir(parents=True, exist_ok=True)

    # 1. Ensure yt-dlp
    ytdlp_path = Path(get_binary_path("yt-dlp"))
    if not ytdlp_path.exists():
        print(f"📥 Downloading yt-dlp for {os_name}...")
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        if system == "windows":
            url += ".exe"
        
        try:
            response = requests.get(url, timeout=30)
            ytdlp_path.write_bytes(response.content)
            if system != "windows":
                ytdlp_path.chmod(0o755)
            print("✅ yt-dlp downloaded.")
        except Exception as e:
            print(f"❌ Failed to download yt-dlp: {e}")

    # 2. Ensure ffmpeg & ffprobe
    # Using specific stable links if the ffbinaries API is acting up
    base_urls = {
        "macos": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1",
        "windows": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1",
        "linux": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1"
    }
    
    plat_suffixes = {
        "macos": "osx-64",
        "windows": "windows-64",
        "linux": "linux-64"
    }

    for component in ["ffmpeg", "ffprobe"]:
        binary_path = Path(get_binary_path(component))
        if not binary_path.exists():
            print(f"📥 Downloading {component} for {os_name}...")
            
            suffix = plat_suffixes.get(os_name, "linux-64")
            # Construct direct GitHub download URL (ffbinaries mirror)
            # Pattern: {base_url}/{component}-{version}-{suffix}.zip
            dl_url = f"{base_urls[os_name]}/{component}-4.4.1-{suffix}.zip"
            
            try:
                r = requests.get(dl_url, timeout=60)
                if r.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                        z.extractall(BIN_DIR / os_name)
                    
                    if system != "windows":
                        binary_path.chmod(0o755)
                    print(f"✅ {component} downloaded.")
                else:
                    print(f"❌ Failed to download {component}: Status {r.status_code}")
            except Exception as e:
                print(f"❌ Error downloading {component}: {e}")

    return True

def get_ffmpeg_path():
    return get_binary_path("ffmpeg")

def get_ytdlp_path():
    return get_binary_path("yt-dlp")

def ensure_dependencies():
    """Download deps and keep yt-dlp updated."""
    p = Path(get_ytdlp_path())
    if p.exists():
        try:
            import subprocess
            subprocess.run([str(p), "-U"], capture_output=True, timeout=10)
        except: pass
    return True

if __name__ == "__main__":
    ensure_dependencies()
