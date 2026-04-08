import sys
from pathlib import Path
import asyncio
import json

# Add project root to sys path to simulate backend runtime context
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "vendor"))

from backend.services.spotify_service import SpotifyService

async def run_test():
    try:
        service = SpotifyService()
        playlist_url = "https://open.spotify.com/playlist/1e4CG0e4LCf61mwnVKCqjv"
        print(f"Testing Selenium Extraction on {playlist_url}...")
        
        pid, pname, tracks = service.get_playlist_tracks(playlist_url)
        
        print("\n=== FINAL RESULTS ===")
        print(f"Playlist Name: {pname}")
        print(f"Playlist ID: {pid}")
        print(f"Final Count of Extracted Tracks: {len(tracks)}")
        
        if tracks:
            print("\nPreview of first 3 tracks:")
            for t in tracks[:3]:
                print(f"- {t['title']} by {t['artist']} (Album: {t['album']})")
                
            print("\nPreview of last 3 tracks:")
            for t in tracks[-3:]:
                print(f"- {t['title']} by {t['artist']} (Album: {t['album']})")
                
        # Write to JSON for inspection if needed
        with open("selenium_dump.json", "w") as f:
            json.dump(tracks, f, indent=4)
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
