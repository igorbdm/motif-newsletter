import os
import re

import requests

from history import already_sent
from utils import is_last_7_days, parse_date

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
VIDEO_API_URL = "https://www.googleapis.com/youtube/v3/videos"


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


def parse_duration(duration):
    """Converte uma duração ISO 8601 do YouTube em segundos."""
    match = re.fullmatch(
        r"P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration,
    )

    if not match:
        raise ValueError(f"Duração inválida: {duration}")

    hours, minutes, seconds = (int(value or 0) for value in match.groups())

    return hours * 3600 + minutes * 60 + seconds


def fetch_video_durations(video_ids):
    """Busca as durações de até 50 vídeos em uma única chamada à API."""
    if not video_ids:
        return {}

    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "A variável YOUTUBE_API_KEY não foi configurada. "
            "Veja o README para saber como criar e configurar a chave."
        )

    params = {
        "part": "contentDetails",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(VIDEO_API_URL, params=params, timeout=30)
    response.raise_for_status()

    return {
        item["id"]: parse_duration(item["contentDetails"]["duration"])
        for item in response.json().get("items", [])
    }


def get_feed(channel_name, config):
    playlist_id = get_uploads_playlist_id(config["id"])
    min_duration = config.get("min_duration")

    results = []
    page_token = None

    while True:
        data = fetch_playlist_page(playlist_id, page_token)

        stop_paging = False
        candidates = []

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

            if config.get("keep") and not contains_any(title, config["keep"]):
                continue

            if contains_any(title, config.get("ignore", [])):
                continue

            if already_sent(video_id):
                continue

            candidates.append({
                "channel": channel_name,
                "title": title,
                "published": published,
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
            })

        if min_duration is not None and candidates:
            durations = fetch_video_durations(
                [video["video_id"] for video in candidates]
            )

            candidates = [
                video
                for video in candidates
                if durations.get(video["video_id"], 0) >= min_duration
            ]

        results.extend(candidates)

        page_token = data.get("nextPageToken")

        if stop_paging or not page_token:
            break

    return sorted(
        results,
        key=lambda video: parse_date(video["published"]),
        reverse=True,
    )
