import os
import re
import time
from typing import List, Dict, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class SpotifyService:
    def __init__(self):
        self.driver = None

    def _init_driver(self):
        print("🔧 Initializing Selenium Driver...")
        options = Options()
        # Headless by default for the .app bundle experience
        if os.environ.get("HEADLESS", "1") == "1":
            options.add_argument("--headless=new")
        
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.page_load_strategy = 'eager'
        
        # Suppress the "Open Spotify?" external protocol handler popup
        prefs = {
            "protocol_handler.excluded_schemes": {"spotify": False},
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Additional bot-evasion and stability
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--blink-settings=imagesEnabled=false") # Save bandwidth/CPU
        
        # Move window out of view if not headless
        options.add_argument("--window-position=-32000,-32000")
        
        try:
            # Selenium 4.6+ handles driver management automatically
            # We don't need webdriver_manager anymore.
            self.driver = webdriver.Chrome(options=options)
            print(f"✅ ChromeDriver started successfully. Browser version: {self.driver.capabilities.get('browserVersion', 'unknown')}")
        except Exception as e:
            print(f"❌ Failed to start Chrome: {str(e)}")
            # Fallback/Diagnostic: Try to find chrome binary if it's missing from path
            if "executable needs to be in PATH" in str(e):
                print("💡 Hint: Chrome or ChromeDriver might not be in the system PATH.")
            raise RuntimeError(f"Could not start Chrome. Please ensure Google Chrome is installed. Error: {e}")
        
    def _close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def get_playlist_tracks(self, playlist_url: str, on_progress: callable = None) -> Tuple[str, str, List[Dict]]:
        playlist_id_match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
        if not playlist_id_match:
            raise ValueError("Invalid Spotify playlist URL")
            
        playlist_id = playlist_id_match.group(1)
        
        try:
            self._init_driver()
            url = f"https://open.spotify.com/playlist/{playlist_id}"
            print(f"Loading {url} via Selenium...")
            self.driver.get(url)
            
            # Wait for Spotify single-page app to finish hydrating the metadata
            for i in range(15):
                raw_title = self.driver.execute_script("return document.title;")
                rows_exist = self.driver.execute_script("return document.querySelectorAll('div[data-testid=\"tracklist-row\"]').length > 0;")
                if "Spotify - Web Player" not in raw_title and "Spotify – Web Player" not in raw_title and rows_exist:
                    break
                time.sleep(1)
            
            # Extract Playlist Name reliably via document.title
            try:
                raw_title = self.driver.execute_script("return document.title;")
                playlist_name = raw_title.replace(" - playlist by Spotify | Spotify", "").split("|")[0].strip()
            except:
                playlist_name = "Spotify Playlist"
                
            print(f"Playlist Name: {playlist_name}")

            # Extract target track count to aggressively avoid Recommended tracks
            target_track_count = 9999
            try:
                # Try og:description first
                desc = self.driver.execute_script('return document.querySelector(\'meta[property=\"og:description\"]\') ? document.querySelector(\'meta[property=\"og:description\"]\').content : \"\"')
                if not desc:
                    # Robust fallback: Grab the raw innerText of the body and hunt for the "230 songs" pattern
                    desc = self.driver.execute_script('return document.body.innerText;')
                
                # Match "230 songs", "230 items", "230 tracks" etc
                match = re.search(r'(\d+)\s*(?:songs|items|tracks)', desc)
                if match:
                    target_track_count = int(match.group(1))
                    print(f"🎯 Target track count resolved: {target_track_count}")
                    if on_progress: on_progress(0, target_track_count)
            except Exception as e:
                print(f"⚠️ Metadata extraction error: {e}")
                pass
                
            all_tracks_dict = {}
            consecutive_no_new_tracks = 0
            
            while True:
                # Break exactly when target tracks reached, preventing Recommended poisoning
                if len(all_tracks_dict) >= target_track_count:
                    print(f"🎯 Target track count ({target_track_count}) reached exactly! Stopping.")
                    break
                    
                # Proactively crush the Recommended section so we only scrape valid list tokens
                self.driver.execute_script("let rec = document.querySelector('[data-testid=\"recommended-tracks\"]'); if(rec) rec.remove();")
                
                # Extract tracks currently visible in DOM
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="tracklist-row"]')
                start_count = len(all_tracks_dict)
                
                for row in rows:
                    try:
                        # Extract the anchor tag wrapping the track, which contains the track ID
                        title_anchor = row.find_element(By.CSS_SELECTOR, 'a[href^="/track/"]')
                        # Extract the actual text div inside the anchor or use the anchor text itself
                        title_el = title_anchor.find_element(By.CSS_SELECTOR, "div")
                        
                        artist_els = row.find_elements(By.CSS_SELECTOR, 'a[href^="/artist/"]')
                        album_els = row.find_elements(By.CSS_SELECTOR, 'a[href^="/album/"]')
                        
                        track_id = title_anchor.get_attribute('href').split('?')[0].split('/')[-1]
                        title = title_el.text.strip() if title_el.text.strip() else title_anchor.text.strip()
                        artist = artist_els[0].text if artist_els else "Unknown"
                        album = album_els[0].text if album_els else "Unknown"
                        
                        if not title:
                            continue # Skip empty ghost rows
                            
                        # Extract Image
                        try:
                            img_el = row.find_element(By.CSS_SELECTOR, "img")
                            image_url = img_el.get_attribute("src")
                        except:
                            image_url = None
                            
                        # Extract Duration Safely
                        duration_ms = 0
                        for div in row.find_elements(By.CSS_SELECTOR, 'div[role="gridcell"] div'):
                            text = div.text.strip()
                            if re.match(r'^(?:\d{1,2}:)?\d{1,2}:\d{2}$', text):
                                parts = text.split(':')
                                if len(parts) == 2:
                                    duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
                                elif len(parts) == 3:
                                    duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
                                break
                            
                        if track_id not in all_tracks_dict:
                            if len(all_tracks_dict) >= target_track_count:
                                break
                                
                            all_tracks_dict[track_id] = {
                                'id': track_id,
                                'title': self.clean_title(title),
                                'raw_title': title,
                                'artist': artist,
                                'album': album,
                                'year': '',
                                'duration_ms': duration_ms,
                                'image_url': image_url,
                                'playlist_name': playlist_name,
                                'status': 'pending',
                                'youtube_url': None
                            }
                    except Exception as e:
                        continue
                        
                end_count = len(all_tracks_dict)
                print(f"📄 SCRAPED Unique tracks so far: {end_count}")
                if on_progress: on_progress(end_count, target_track_count)
                
                if end_count == start_count:
                    consecutive_no_new_tracks += 1
                else:
                    consecutive_no_new_tracks = 0
                    
                if consecutive_no_new_tracks >= 4:
                    print("Reached bottom of playlist (no new tracks after multiple scrolls)")
                    break
                
                scroll_js = """
                let scrollNode = document.querySelector('.main-view-container__scroll-node');
                if(scrollNode) {
                    let scrollableElement = (scrollNode.scrollHeight > scrollNode.clientHeight) ? scrollNode : scrollNode.firstElementChild;
                    scrollableElement.scrollTop += 800;
                    return true;
                }
                return false;
                """
                self.driver.execute_script(scroll_js)
                time.sleep(2)
                        
            all_tracks = list(all_tracks_dict.values())[:target_track_count]
            print(f"✅ ALL SCRAPED: {len(all_tracks)}")
            
            if len(all_tracks) == 0:
                 raise RuntimeError("Validation Error: 0 tracks were found. The playlist might be private or UI has changed.")

            # Ensure we maintain original order approx
            return playlist_id, playlist_name, all_tracks
            
        except Exception as e:
            raise RuntimeError(f"Selenium Scraping Error: {e}")
        finally:
            self._close_driver()

    @staticmethod
    def clean_title(title):
        clean = re.sub(r'\(.*?\)', '', title)
        clean = re.sub(r'\[.*?\]', '', clean)
        return clean.strip()
