from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def test_unauth_scroll(playlist_id):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    url = f"https://open.spotify.com/playlist/{playlist_id}"
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(3)
    
    # Scroll multiple times
    print("Scrolling...")
    for i in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
    # Get tracks
    track_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tracklist-row']")
    print(f"Tracks found: {len(track_elements)}")
    driver.quit()

test_unauth_scroll("1e4CG0e4LCf61mwnVKCqjv")
