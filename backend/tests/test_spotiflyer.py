import requests
import base64

client_id = "5f573c9620494bae87890c0f08a60293"
client_secret = "212476d9b0f3472eaa762d90b19b0ba8"

print("Authenticating via SpotiFlyer Client Credentials...")
# Encode credentials
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()

try:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"}
    )
    if response.status_code != 200:
        print(f"Auth Failed: {response.text}")
        exit(1)

    token = response.json()["access_token"]
    print("Token acquired successfully.\n")
    
    url = "https://api.spotify.com/v1/playlists/1e4CG0e4LCf61mwnVKCqjv/tracks?offset=0&limit=100"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Playlist Fetch Status: {response.status_code}")
    if response.status_code != 200:
        print(f"FAILED: {response.text}")
    else:
        print("WORKED!")
        
except Exception as e:
    print(e)
