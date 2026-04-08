import yt_dlp
from rapidfuzz import fuzz
import re

class YouTubeService:
    def __init__(self, bin_path='yt-dlp'):
        self.bin_path = bin_path
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'noprogress': True,
            'format': 'bestaudio/best',
            'ignoreerrors': True,
            'source_address': '0.0.0.0'
        }

    def search_and_rank(self, track_info, limit=5):
        title = track_info.get('raw_title') or track_info.get('name') or "Unknown Track"
        query = f"{track_info.get('artist', 'Unknown Artist')} - {title}"
        
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            search_query = f"ytsearch{limit}:{query}"
            result = ydl.extract_info(search_query, download=False)
            
            if 'entries' not in result:
                return []
                
            ranked_results = []
            for entry in result['entries']:
                if not entry: continue
                
                score = self.calculate_score(track_info, entry)
                ranked_results.append({
                    'id': entry['id'],
                    'title': entry['title'],
                    'url': entry['url'],
                    'duration_s': int(entry.get('duration', 0)),
                    'channel': entry.get('uploader', ''),
                    'confidence': score,
                    'type': self.detect_type(entry)
                })
                
            # Sort by confidence
            ranked_results.sort(key=lambda x: x['confidence'], reverse=True)
            return ranked_results

    def calculate_score(self, target, candidate):
        # 1. Title Score
        title_score = fuzz.token_set_ratio(target['title'].lower(), candidate['title'].lower())
        
        # 2. Artist Score
        artist_score = max(
            fuzz.partial_ratio(target['artist'].lower(), candidate['title'].lower()),
            fuzz.partial_ratio(target['artist'].lower(), candidate.get('uploader', '').lower())
        )
        
        # 3. Duration Score (VERY HIGH WEIGHT)
        target_s = target['duration_ms'] / 1000
        candidate_s = candidate.get('duration', 0)
        if candidate_s == 0:
            diff = 999
        else:
            diff = abs(target_s - candidate_s)
        
        if diff <= 2:
            duration_score = 100
        elif diff <= 5:
            duration_score = 85
        elif diff <= 15:
            duration_score = 50
        else:
            duration_score = -50  # heavily penalize wrong durations
            
        # 4. Type Boosts (Official Audio / Topic priority)
        boost = 0
        cand_title = candidate['title'].lower()
        cand_channel = candidate.get('uploader', '').lower()
        
        if "topic" in cand_channel or "provided to youtube" in cand_title:
            boost += 30
        elif "music" in cand_channel:
            boost += 20
        elif "lyrics" in cand_title:
            boost += 15
        elif "official audio" in cand_title or "official music" in cand_title:
            boost += 10
            
        if "live" in cand_title and "live" not in target['title'].lower():
            boost -= 30
        if "cover" in cand_title and "cover" not in target['title'].lower():
            boost -= 50
            
        # VERY HIGH duration weight ratio: 40% Duration, 30% Title, 20% Artist, + Boosts
        final_score = (duration_score * 0.40) + (title_score * 0.30) + (artist_score * 0.20) + boost
        return min(max(round(final_score), 0), 100)

    def detect_type(self, entry):
        title = entry['title'].lower()
        channel = entry.get('uploader', '').lower()
        
        if "topic" in channel: return "Official Audio (Topic)"
        if "official audio" in title: return "Official Audio"
        if "official video" in title or "official music video" in title: return "Official Video"
        if "lyrics" in title: return "Lyrics Video"
        return "Video"
