from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def scrape_spotify_playlist(playlist_id):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"Loading {url}")
    driver.get(url)
    time.sleep(4)
    
    found_tracks = set()
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    
    while True:
        # Extract tracks currently visible in DOM
        rows = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="tracklist-row"]')
        for row in rows:
            try:
                title_el = row.find_element(By.CSS_SELECTOR, 'a[data-testid="internal-track-link-name"]')
                artist_els = row.find_elements(By.CSS_SELECTOR, 'a[href^="/artist/"]')
                artist_name = artist_els[0].text if artist_els else "Unknown"
                
                track_id = title_el.get_attribute('href').split('/')[-1]
                title = title_el.text
                
                found_tracks.add((track_id, title, artist_name))
            except Exception as e:
                continue
                
        print(f"Unique tracks so far: {len(found_tracks)}")
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)
        
        new_height = driver.execute_script("return document.documentElement.scrollTop") + driver.execute_script("return window.innerHeight")
        
        # Check if we reached bottom
        if new_height >= driver.execute_script("return document.documentElement.scrollHeight"):
            time.sleep(2) # Wait a bit to see if more loads
            new_height_check = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height >= new_height_check:
                break
                
    driver.quit()
    print(f"Scrape Complete. Total: {len(found_tracks)}")
    return found_tracks

scrape_spotify_playlist("1e4CG0e4LCf61mwnVKCqjv")
