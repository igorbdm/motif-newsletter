import os

import requests

api_key = os.environ["YOUTUBE_API_KEY"]
playlist_id = "UU3I2GFN_F8WudD_2jUZbojA"  # uploads da KEXP

response = requests.get(
    "https://www.googleapis.com/youtube/v3/playlistItems",
    params={"part": "snippet", "playlistId": playlist_id, "maxResults": 5, "key": api_key},
    timeout=30,
)

print(response.status_code)
print(response.json())
