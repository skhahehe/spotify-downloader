import os
import json
from pathlib import Path
import threading

class LogService:
    def __init__(self, data_dir="logs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _get_log_path(self, playlist_id):
        return self.data_dir / f"{playlist_id}.json"

    def init_or_load_playlist(self, playlist_id, total_tracks, new_tracks, playlist_name=None):
        """
        Merge newly fetched tracks with existing JSON.
        Existing tracks keep their state. Missing new tracks are appended.
        """
        log_path = self._get_log_path(playlist_id)
        
        with self.lock:
            state = {
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
                "total_tracks": total_tracks,
                "tracks": []
            }
            
            existing_tracks_map = {}
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        old_state = json.load(f)
                        if not playlist_name:
                            state["playlist_name"] = old_state.get("playlist_name")
                        for t in old_state.get("tracks", []):
                            existing_tracks_map[t['id']] = t
                except Exception as e:
                    print(f"⚠️ Failed to parse existing log for {playlist_id}: {e}")

            # Merge
            for t in new_tracks:
                if t['id'] in existing_tracks_map:
                    # preserve status and urls from previous runs
                    t['status'] = existing_tracks_map[t['id']].get('status', 'pending')
                    t['youtube_url'] = existing_tracks_map[t['id']].get('youtube_url')
                    # preserve other fields too if needed
                    if not t.get('playlist_name'):
                        t['playlist_name'] = state.get('playlist_name')
                    # if it was 'downloading' but interrupted, reset to pending
                    if t['status'] == 'downloading':
                        t['status'] = 'pending'
                state['tracks'].append(t)

            self._save_raw(log_path, state)
            return state

    def get_playlist_state(self, playlist_id):
        log_path = self._get_log_path(playlist_id)
        if log_path.exists():
            with self.lock:
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return None
        return None

    def update_track_status(self, playlist_id, track_id, status, youtube_url=None):
        log_path = self._get_log_path(playlist_id)
        if not log_path.exists():
            return
            
        with self.lock:
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                for t in state['tracks']:
                    if t['id'] == track_id:
                        if status:
                            t['status'] = status
                        if youtube_url:
                            t['youtube_url'] = youtube_url
                        break
                        
                self._save_raw(log_path, state)
            except Exception as e:
                print(f"⚠️ Failed to update track status for {track_id}: {e}")

    def _save_raw(self, path, data):
        tmp_path = str(path) + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
