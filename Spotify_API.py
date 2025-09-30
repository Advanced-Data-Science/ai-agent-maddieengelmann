import os
import requests
import base64

# 1. Load credentials from environment variables
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing Spotify CLIENT_ID or CLIENT_SECRET environment variables.")

# 2. Get an access token
def get_access_token(client_id, client_secret):
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

# 3. Function to test Spotify API
def test_spotify_api(token):
    # First call: search for artist
    search_url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": "Taylor Swift", "type": "artist", "limit": 1}

    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    artist = data["artists"]["items"][0]
    artist_id = artist["id"]

    # Second call: fetch full artist details (guaranteed genres)
    artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
    artist_resp = requests.get(artist_url, headers=headers)
    artist_resp.raise_for_status()
    artist_data = artist_resp.json()

    # Print results
    print("Test API Call Successful ✅")
    print("Artist Name:", artist_data["name"])
    print("Genres:", artist_data["genres"])
    print("Spotify URL:", artist_data["external_urls"]["spotify"])

# 4. Run
if __name__ == "__main__":
    token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    print("Spotify Access Token:", token)
    
    # Test the API
    test_spotify_api(token)

