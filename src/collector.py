import os

import requests

from history import already_sent
from utils import is_last_7_days, parse_date

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


def contains_any(text, terms):
    normalized_text = text.casefold()
    return any(term.casefold() in normalized_text for term in terms)


def get_uploads_playlist_id(channel_id):
    """Todo canal do YouTube tem uma playlist automática com todos os uploads.
    O ID dela é sempre igual ao ID do canal, trocando o prefixo 'UC' por 'UU'."""
    return "UU" + channel_id[2:]


def fetch_playlist_page(playlist_id, page_token=None):
    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "A variável YOUTUBE_API_KEY não foi configurada. "
            "Veja o README para saber como criar e configurar a chave."
        )

    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    if page_token:
        params["pageToken"] = page_token

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    return response.json()


def get_feed(channel_name, config):
    playlist_id = get_uploads_playlist_id(config["id"])

    results = []
    page_token = None

    while True:
        data = fetch_playlist_page(playlist_id, page_token)

        stop_paging = False

        for item in data.get("items", []):
            snippet = item["snippet"]
            title = snippet["title"]
            published = snippet["publishedAt"]
            video_id = snippet["resourceId"]["videoId"]

            # A playlist de uploads vem sempre do vídeo mais recente para o
            # mais antigo. Assim que encontramos um vídeo fora dos últimos 7
            # dias, todos os próximos também estarão fora, então paramos.
            if not is_last_7_days(published):
                stop_paging = True
                break

            if not contains_any(title, config["keep"]):
                continue

            if contains_any(title, config.get("ignore", [])):
                continue

            if already_sent(video_id):
                continue

            results.append({
                "channel": channel_name,
                "title": title,
                "published": published,
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
            })

        page_token = data.get("nextPageToken")

        if stop_paging or not page_token:
            break

    return sorted(results, key=lambda video: parse_date(video["published"]), reverse=True)
