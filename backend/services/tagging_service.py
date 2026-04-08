from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK
from mutagen.mp4 import MP4, MP4Cover
import requests
import os

class TaggingService:
    def __init__(self):
        pass

    def tag_file(self, file_path, track_info):
        ext = os.path.splitext(file_path)[1].lower()
        
        # Download album art
        image_data = None
        if track_info.get('image_url'):
            try:
                r = requests.get(track_info['image_url'], timeout=10)
                if r.status_code == 200:
                    image_data = r.content
            except Exception as e:
                print(f"⚠️ Failed to download image: {e}")

        # Note: We ONLY tag extensions we natively support right now.
        # Original webm/opus files fetched via yt-dlp won't get Spotify ID3 tags injected
        # unless specifically re-muxed.
        if ext == ".mp3":
            self.tag_mp3(file_path, track_info, image_data)
        elif ext == ".m4a":
            self.tag_m4a(file_path, track_info, image_data)
        else:
            print(f"Tagging not supported natively for {ext}, skipped.")

    def tag_mp3(self, file_path, track_info, image_data):
        try:
            audio = ID3(file_path)
        except Exception:
            # If no ID3 tags exist, initialize them
            audio = ID3()
            audio.add_tags()
            
        audio['TIT2'] = TIT2(encoding=3, text=track_info['title']) 
        audio['TPE1'] = TPE1(encoding=3, text=track_info['artist'])
        audio['TDRC'] = TDRC(encoding=3, text=track_info.get('year', ''))
        
        if image_data:
            audio['APIC'] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3, # Front cover
                desc='Front Cover',
                data=image_data
            )
            
        audio.save(file_path, v2_version=3) # Use ID3v2.3 for maximum compatibility

    def tag_m4a(self, file_path, track_info, image_data):
        audio = MP4(file_path)
        audio['\xa9nam'] = track_info['title']
        audio['\xa9ART'] = track_info['artist']
        # audio['\xa9alb'] = track_info['album'] # Removed as requested
        audio['\xa9day'] = track_info['year']
        
        if image_data:
            audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
            
        audio.save()

    def verify_file_complete(self, file_path):
        """Verifies if the file has at least Title, Artist, and Cover Art."""
        if not os.path.exists(file_path):
            return False
            
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".mp3":
                audio = ID3(file_path)
                # Check for Title (TIT2), Artist (TPE1), and Cover (APIC)
                has_title = 'TIT2' in audio
                has_artist = 'TPE1' in audio
                has_cover = 'APIC' in audio
                return has_title and has_artist and has_cover
            elif ext == ".m4a":
                audio = MP4(file_path)
                # Check for Title (©nam), Artist (©ART), and Cover (covr)
                has_title = '\xa9nam' in audio
                has_artist = '\xa9ART' in audio
                has_cover = 'covr' in audio
                return has_title and has_artist and has_cover
        except Exception as e:
            print(f"Verification error for {file_path}: {e}")
            return False
            
        return False
