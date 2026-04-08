import yt_dlp
import os
import asyncio
import subprocess
import json
from pathlib import Path
from rapidfuzz import fuzz
from backend.services.dep_manager import get_ffmpeg_path, get_ytdlp_path, get_binary_path

class DownloadService:
    def __init__(self, output_dir="Music", format="mp3"):
        self.output_dir = Path(output_dir)
        self.format = format # "mp3", "m4a", "original"

    def get_ydl_opts(self, target_path):
        ffmpeg_location = get_ffmpeg_path()
        
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(target_path.with_suffix('')), 
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'ffmpeg_location': ffmpeg_location,
            'prefer_ffmpeg': True,
            'postprocessors': []
        }
        
        if self.format == "mp3":
            opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            })
        elif self.format == "m4a":
            opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            })
            
        return opts

    async def download_track(self, track_info, youtube_url, callback=None, skip_verification: bool = False) -> dict:
        loop = asyncio.get_running_loop()
        
        # 0. Strict Validation & Pathing
        artist_raw = track_info.get('artist', 'Unknown')
        title_raw = track_info.get('title', 'Unknown')
        playlist_raw = track_info.get('playlist_name', 'Downloads') # Use playlist as main folder
        
        if title_raw == "Unknown":
            print(f"⚠️ Skipping track {track_info['id']} due to missing Title.")
            if callback:
                loop.call_soon_threadsafe(callback, track_info['id'], 'failed', 0.0)
            return {'status': 'REJECT', 'file_path': None}

        artist = self.safe_name(artist_raw)
        title_safe = self.safe_name(title_raw)
        playlist_safe = self.safe_name(playlist_raw)
        filename = f"{title_safe} - {artist}"
        
        # Download into the user's chosen output_dir nested inside the playlist name
        dir_path = self.output_dir / playlist_safe
        dir_path.mkdir(parents=True, exist_ok=True)
        target_file = dir_path / filename
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%', '')
                try: p = float(p)
                except: p = 0.0
                
                speed = d.get('_speed_str', '0KiB/s').strip()
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes', d.get('total_bytes_estimate', 0))
                
                dl_mb = f"{downloaded_bytes / 1024 / 1024:.1f}MB" if float(downloaded_bytes) > 0 else ""
                tot_mb = f"{total_bytes / 1024 / 1024:.1f}MB" if float(total_bytes) > 0 else ""

                details = {
                    "progress": p,
                    "speed": speed,
                    "downloadedMb": dl_mb,
                    "totalMb": tot_mb
                }
                
                if callback:
                    loop.call_soon_threadsafe(callback, track_info['id'], 'downloading', details)
            elif d['status'] == 'finished':
                if callback:
                    loop.call_soon_threadsafe(callback, track_info['id'], 'processing', {"progress": 100.0})

        # 1. Prepare YDL options with explicit FFmpeg location
        opts = self.get_ydl_opts(target_file)
        opts['progress_hooks'] = [progress_hook]
        
        # Ensure we use our bundled binaries for EVERYTHING
        opts['ffmpeg_location'] = get_ffmpeg_path()
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                if self.format == "original":
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(youtube_url, download=True))
                    final_ext = info.get('ext', 'webm')
                else:
                    await loop.run_in_executor(None, lambda: ydl.download([youtube_url]))
                    final_ext = "mp3" if self.format == "mp3" else "m4a"
            
            final_path = target_file.with_suffix(f".{final_ext}")
            
            # 2. Duration Verification (Issue 1)
            if skip_verification:
                print(f"✅ Manual Trust: Skipping duration check for {filename}")
                return {'status': 'ACCEPT', 'file_path': final_path}
                
            status = await self.verify_duration(final_path, track_info.get('duration_ms', 0), track_info)
            if status == 'REJECT':
                print(f"❌ Duration mismatch (REJECT) for {filename}. Removing file.")
                self._cleanup_partial(target_file)
                return {'status': 'REJECT', 'file_path': None}
                
            return {'status': status, 'file_path': final_path}
            
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            self._cleanup_partial(target_file)
            if callback:
                loop.call_soon_threadsafe(callback, track_info['id'], 'error', 0.0)
            return {'status': 'REJECT', 'file_path': None}

    def _cleanup_partial(self, target_file):
        """Removes all partial, temp, and final files related to a target."""
        try:
            # 1. The final file
            for ext in ['.mp3', '.m4a', '.webm', '.opus', '.m4v']:
                p = target_file.with_suffix(ext)
                if p.exists(): p.unlink()
            
            # 2. Partials and Temp
            parent = target_file.parent
            if parent.exists():
                name = target_file.name
                for f in parent.iterdir():
                    if f.name.startswith(name) and (f.suffix in ['.part', '.temp', '.ytdlp'] or f.name.endswith('.part')):
                        try: f.unlink()
                        except: pass
        except:
            pass

    async def verify_duration(self, file_path, expected_ms, track_info) -> str:
        if expected_ms <= 0: return 'ACCEPT'
        
        if not file_path.exists():
            return 'REJECT'

        ffprobe = get_binary_path("ffprobe")
        cmd = [
            ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(file_path)
        ]
        
        try:
            result = await asyncio.create_task(asyncio.to_thread(subprocess.check_output, cmd))
            data = json.loads(result)
            actual_s = float(data['format']['duration'])
            expected_s = expected_ms / 1000.0
            
            diff = abs(actual_s - expected_s)
            
            # Issue 1 logic
            if diff <= 5.0:
                return 'ACCEPT'
            if diff <= 30.0:
                print(f"⚠️ SUSPECT Duration for {file_path}: Diff {round(diff, 2)}s")
                return 'SUSPECT'
            
            # High similarity check for 30-90s
            if diff <= 90.0:
                title_similarity = fuzz.token_set_ratio(track_info['title'].lower(), file_path.stem.split(' - ')[0].lower())
                if title_similarity > 80:
                    print(f"⚠️ ACCEPT (Similarity Match) for {file_path}: Diff {round(diff, 2)}s, Similarity {round(title_similarity, 2)}%")
                    return 'ACCEPT'
                return 'SUSPECT'
                
            return 'REJECT'
        except Exception as e:
            print(f"Failed to verify duration for {file_path}: {e}")
            return 'SUSPECT'

    def safe_name(self, name):
        return "".join([c for c in name if c.isalnum() or c in (' ', '.', '-', '_')]).strip()
