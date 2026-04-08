from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import asyncio
import os
import sys
import threading
import tempfile
from pathlib import Path

from contextlib import asynccontextmanager

print(f"📍 BACKEND SOURCE: {Path(__file__).resolve()}")
print(f"🚀 [VER: parallel-pipeline-2.5] Initializing Parallel Architecture...")

# Robust Absolute Pathing
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"
VENDOR_DIR = PROJECT_ROOT / "vendor"

# Ensure runtime directories exist
LOGS_DIR.mkdir(exist_ok=True)

# Add bundled dependencies and project root to sys.path
sys.path.insert(0, str(PROJECT_ROOT)) # Project root
sys.path.insert(0, str(VENDOR_DIR)) # Vendor folder

def suicide_if_parent_dies():
    try:
        sys.stdin.read()
    except:
        pass
    os._exit(0)

if "--desktop" in sys.argv:
    threading.Thread(target=suicide_if_parent_dies, daemon=True).start()

from backend.services.spotify_service import SpotifyService
from backend.services.youtube_service import YouTubeService
from backend.services.download_service import DownloadService
from backend.services.tagging_service import TaggingService
from backend.services.dep_manager import ensure_dependencies
from backend.services.log_service import LogService
from backend.services.queue_manager import QueueManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1: Automated Dependency Handling
    await asyncio.to_thread(ensure_dependencies)
    # Initialize Queue Manager with 5 parallel workers (Issue 7)
    print("🚀 [VER: parallel-pipeline-2.6] Initializing Parallel Architecture...")
    state.queue = QueueManager(download_worker_func, concurrency=5)
    await state.queue.start()
    yield
    # Cleanup logic if needed...

app = FastAPI(title="Spotify Smart Downloader Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AppState:
    spotify = SpotifyService()
    youtube = YouTubeService()
    downloader = DownloadService()
    tagger = TaggingService()
    logger = LogService(data_dir=str(LOGS_DIR))
    tracks: Dict[str, dict] = {} # track_id -> info
    downloads: Dict[str, dict] = {} # track_id -> {status, progress}
    search_cache: Dict[str, list] = {} # track_id -> [results]
    current_playlist_id: str = None
    current_playlist_name: str = None
    queue: Optional[QueueManager] = None
    min_confidence: int = 70
    scrape_count: int = 0
    scrape_target: int = 0

state = AppState()

async def prefetch_youtube_results(track_info):
    track_id = track_info['id']
    if track_id in state.search_cache: return
    try:
        results = await asyncio.to_thread(state.youtube.search_and_rank, track_info, limit=5)
        state.search_cache[track_id] = results
    except: pass

async def download_worker_func(track_info, manual_url=None):
    track_id = track_info['id']
    # 0. Initial Status Pulse
    download_progress_callback(track_id, "searching", 0.0)
    
    # 1. Gather Candidates (Manual > Cache > New Search)
    candidates = []
    if manual_url:
        candidates = [{'url': manual_url, 'confidence': 100, 'type': 'Manual Selection'}]
    elif track_id in state.search_cache:
        candidates = state.search_cache[track_id]
    else:
        candidates = await asyncio.to_thread(state.youtube.search_and_rank, track_info, limit=5)
        state.search_cache[track_id] = candidates

    if not candidates:
        download_progress_callback(track_id, "failed", 0.0)
        return False

    best_suspect = None
    
    # 2. Iterate Candidates (Issue 2 & 5)
    best_candidate = candidates[0] if candidates else None
    
    if best_candidate and best_candidate.get('confidence', 0) < state.min_confidence:
        print(f"⚠️  Match confidence ({best_candidate['confidence']}%) is below threshold ({state.min_confidence}%). Skipping auto-download for {track_info['title']}.")
        download_progress_callback(track_id, "failed", 0.0)
        return False

    for cand_idx, candidate in enumerate(candidates[:3]): # Try top 3
        youtube_url = candidate['url']
        
        state.logger.update_track_status(state.current_playlist_id, track_id, 'downloading', youtube_url)
        download_progress_callback(track_id, "downloading", 0.0)
        
        result = await state.downloader.download_track(
            track_info, 
            youtube_url, 
            callback=download_progress_callback,
            skip_verification=(manual_url is not None)
        )
        
        if result['status'] == 'ACCEPT':
            # Perfect match found. Cleanup any old suspect.
            if best_suspect and best_suspect['file_path'].exists():
                try: best_suspect['file_path'].unlink()
                except: pass
            
            file_path = result['file_path']
            download_progress_callback(track_id, "tagging", 99.0)
            state.tagger.tag_file(str(file_path), track_info)
            download_progress_callback(track_id, "done", 100.0)
            return True
        elif result['status'] == 'SUSPECT':
            # Keep this as a fallback. Move to a temporary path so it isn't overwritten.
            suspect_path = result['file_path'].with_suffix(result['file_path'].suffix + '.suspect')
            try:
                if suspect_path.exists(): suspect_path.unlink()
                result['file_path'].rename(suspect_path)
                result['file_path'] = suspect_path
                if not best_suspect: best_suspect = result
            except: pass
            
            # If it's manual, we don't try other candidates
            if manual_url: break 
            continue # Try next candidate for a better match
        else:
            # If download itself failed and it's manual, don't try other candidates
            if manual_url: break
            continue
                
    # 3. Last Resort: Use best suspect (Issue 1)
    if best_suspect and best_suspect['file_path'].exists():
        final_path = best_suspect['file_path'].with_suffix(best_suspect['file_path'].suffix.replace('.suspect', ''))
        try:
            best_suspect['file_path'].rename(final_path)
            download_progress_callback(track_id, "tagging", 99.0)
            state.tagger.tag_file(str(final_path), track_info)
            download_progress_callback(track_id, "done", 100.0)
            return True
        except: pass

    download_progress_callback(track_id, "failed", 0.0)
    return False

def download_progress_callback(track_id, status, details=None):
    if not details: details = {}
    if isinstance(details, float):
        details = {"progress": details}
        
    state.downloads[track_id] = {"status": status, **details}
    if status in ['done', 'failed', 'error']:
        log_status = 'done' if status == 'done' else 'failed'
        state.logger.update_track_status(state.current_playlist_id, track_id, log_status)

class SpotifyConfig(BaseModel):
    download_path: Optional[str] = None
    format: Optional[str] = "mp3"
    concurrency: Optional[int] = 3
    min_confidence: Optional[int] = 70

@app.post("/config")
async def update_config(config: SpotifyConfig):
    if config.download_path:
        state.downloader.output_dir = Path(config.download_path)
    if config.format:
        state.downloader.format = config.format
    if config.concurrency and state.queue:
        state.queue.concurrency = config.concurrency
    if config.min_confidence is not None:
        state.min_confidence = config.min_confidence
        
    return {"status": "ok"}

@app.get("/scrape_status")
async def get_scrape_status():
    return {"count": state.scrape_count, "target": state.scrape_target}

@app.get("/playlist")
async def get_playlist(url: str, custom_name: str = None):
    try:
        def on_progress(count, target):
            state.scrape_count = count
            state.scrape_target = target if target != 9999 else 0
            
        state.scrape_count = 0
        state.scrape_target = 0
        
        # Pass a callback to the threaded call
        playlist_id, playlist_name, new_tracks = await asyncio.to_thread(
            state.spotify.get_playlist_tracks, 
            url, 
            on_progress
        )
        
        if custom_name and custom_name.strip():
            playlist_name = custom_name.strip()
            for t in new_tracks:
                t['playlist_name'] = playlist_name
                
        state.current_playlist_id = playlist_id
        state.current_playlist_name = playlist_name
        
        # 2. Strict Log Integration & Filtering
        log_state = state.logger.init_or_load_playlist(playlist_id, len(new_tracks), new_tracks, playlist_name)
        
        state.tracks.clear()
        state.downloads.clear()
        
        return_list = []
        
        for t in log_state['tracks']:
            # Calculate the local file path to check if it already exists correctly
            artist_safe = state.downloader.safe_name(t['artist'])
            title_safe = state.downloader.safe_name(t['title'])
            playlist_safe = state.downloader.safe_name(playlist_name)
            filename = f"{title_safe} - {artist_safe}"
            
            # Use current configured output_dir
            ext = ".mp3" if state.downloader.format == "mp3" else ".m4a"
            if state.downloader.format == "original": ext = ".mp3" # Default check
            
            local_path = state.downloader.output_dir / playlist_safe / f"{filename}{ext}"
            
            # --- SMART VALIDATION ---
            if local_path.exists():
                is_perfect = state.tagger.verify_file_complete(str(local_path))
                if is_perfect:
                    t['status'] = 'done'
                else:
                    print(f"🗑 Local file {filename} is missing metadata or icon. Deleting and re-queueing.")
                    try: local_path.unlink()
                    except: pass
                    t['status'] = 'pending'

            # ALWAYS store in state for reference
            state.tracks[t['id']] = t
            state.downloads[t['id']] = {"status": t['status'], "progress": 100.0 if t['status'] == 'done' else 0.0}
            
            # Send all tracks to UI so previously downloaded ones aren't hidden
            return_list.append(t)
            
            # ONLY actively start/queue pending or failed tracks
            if t['status'] in ['pending', 'failed']:
                # Set initial queued status
                download_progress_callback(t['id'], "queued", 0.0)
                # Background tasks for active tracks
                asyncio.create_task(prefetch_youtube_results(t))
                await state.queue.add_task(t['id'], t)
            
        print(f"📊 Sending full list of {len(return_list)} tracks to UI")
        return return_list
    except Exception as e:
        print(f"❌ PLAYLIST ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def start_download(track_id: str, youtube_url: Optional[str] = None):
    if not state.queue:
        raise HTTPException(status_code=500, detail="Queue not initialized")
    if track_id not in state.tracks:
        raise HTTPException(status_code=404, detail="Track not found")
        
    t = state.tracks[track_id]
    
    # --- MANUAL OVERRIDE LOGIC ---
    if youtube_url:
        print(f"🔄 Manual Override detected for {t['title']}. Aborting old task...")
        # 1. Cancel running task if any
        state.queue.cancel_task(track_id)
        
        # 2. Aggressively wipe existing files
        artist_safe = state.downloader.safe_name(t['artist'])
        title_safe = state.downloader.safe_name(t['title'])
        playlist_safe = state.downloader.safe_name(state.current_playlist_name or "Downloads")
        filename = f"{title_safe} - {artist_safe}"
        target_base = state.downloader.output_dir / playlist_safe / filename
        state.downloader._cleanup_partial(target_base)
        
        # 3. Force Reset status to pending to allow re-entry
        t['status'] = 'pending'
        state.downloads[track_id] = {"status": "pending", "progress": 0.0}
        
    if t.get('status') == 'done' and not youtube_url:
        return {"status": "skipped_done"}
            
    t['status'] = 'queued'
    state.downloads[track_id] = {"status": "queued", "progress": 0.0}
    await state.queue.add_task(track_id, t, manual_url=youtube_url)
    return {"status": "queued"}

@app.post("/retry_failed")
async def retry_failed():
    if not state.current_playlist_id:
        return {"status": "no_playlist"}
        
    count = 0
    for track_id, info in state.downloads.items():
        if info['status'] == 'failed' or info['status'] == 'error':
            state.downloads[track_id] = {"status": "pending", "progress": 0.0}
            state.logger.update_track_status(state.current_playlist_id, track_id, 'pending')
            await start_download(track_id)
            count += 1
            
    return {"status": "started", "count": count}



@app.get("/search")
async def search_youtube(track_id: str, limit: int = 5):
    if track_id not in state.tracks:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Issue 4: Return cached results instantly
    if track_id in state.search_cache:
        return state.search_cache[track_id]
        
    t = state.tracks[track_id]
    results = await asyncio.to_thread(state.youtube.search_and_rank, t, limit=limit)
    state.search_cache[track_id] = results
    return results

@app.get("/status")
async def get_status():
    return state.downloads

if __name__ == "__main__":
    import socket
    import subprocess
    import os
    from pathlib import Path
    from uvicorn import Config, Server
    
    port = 17017
    
    # NEW: Automated Binary Discovery
    base_dir = Path(__file__).resolve().parent.parent
    system = "macos" if os.name != 'nt' else "windows"
    bin_path = base_dir / "bin" / system
    
    if bin_path.exists():
        print(f"🔧 Adding binaries to PATH: {bin_path}")
        os.environ["PATH"] = f"{bin_path}:{os.environ.get('PATH', '')}"
    
    # Aggressive Cleanup: Kill anything on port 17017
    print(f"🧹 Cleaning up port {port}...")
    if os.name != 'nt':
        try:
            pid = subprocess.check_output(["lsof", "-t", f"-i:{port}"]).decode().strip()
            if pid:
                subprocess.run(["kill", "-9", pid])
                print(f"✅ Killed ghost process {pid} on port {port}")
        except:
            pass
    
    print(f"📍 BACKEND SOURCE: {Path(__file__).resolve()}")
    print(f"🚀 [VER: architecture-v3.0] Starting on FIXED PORT {port}...")
    
    config = Config(app=app, host="127.0.0.1", port=port, log_level="info")
    server = Server(config=config)
    
    try:
        asyncio.run(server.serve())
    finally:
        print("🛑 Backend shutdown.")
