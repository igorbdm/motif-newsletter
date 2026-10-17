"""Escolhe a Song of the Week a partir do que foi ouvido no Last.fm.

Como funciona:
1. Busca as músicas mais ouvidas dos últimos 7 dias.
2. Remove as que já foram recomendadas em edições anteriores (histórico).
3. Dá preferência a artistas que não foram recomendados nas últimas 4
   edições. Se só houver artistas recentes, eles continuam valendo: a
   preferência nunca deixa a seção vazia.
4. Fica com as 10 mais ouvidas que sobraram e sorteia uma delas. Músicas
   com mais plays têm um pouco mais de chance: o peso é a raiz quadrada dos
   plays (4 plays pesam 2x mais que 1 play, e não 4x).
5. Se a semana não tiver nenhuma música nova, tenta o último mês. Se ainda
   assim não houver, a seção não aparece nessa edição.

O histórico fica em data/song_history.json e é salvo no repositório pelo
GitHub Actions depois de cada envio de produção.
"""

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import lastfm

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "song_history.json"

CANDIDATES = 10
RECENT_ARTIST_EDITIONS = 4
PERIODS = ["7day", "1month"]


def song_key(artist, title):
    """Identifica uma música sem diferenciar maiúsculas, minúsculas e espaços."""
    return f"{artist.strip().casefold()}|{title.strip().casefold()}"


def load_history(path=HISTORY_PATH):
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_to_history(pick, edition_id, path=HISTORY_PATH):
    history = load_history(path)
    history.append({
        "edition": edition_id,
        "artist": pick["artist"],
        "title": pick["title"],
        "recommended_at": datetime.now(timezone.utc).date().isoformat(),
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")


def choose_track(tracks, history, rng=random):
    """Sorteia uma música entre as mais ouvidas que ainda não foram recomendadas.

    As músicas já recomendadas são retiradas antes do sorteio, em vez de
    sortear de novo quando cai uma repetida: o resultado é o mesmo, mas
    assim o sorteio nunca fica preso tentando várias vezes.
    """
    recommended = {song_key(item["artist"], item["title"]) for item in history}
    recent_artists = {
        item["artist"].strip().casefold()
        for item in history[-RECENT_ARTIST_EDITIONS:]
    }

    new_songs = [
        track
        for track in tracks
        if song_key(track["artist"], track["title"]) not in recommended
    ]

    # Artistas recomendados recentemente só entram se não houver outra opção.
    fresh_artists = [
        track
        for track in new_songs
        if track["artist"].strip().casefold() not in recent_artists
    ]

    candidates = (fresh_artists or new_songs)[:CANDIDATES]

    if not candidates:
        return None

    weights = [track["plays"] ** 0.5 for track in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def get_song_of_the_week(username=None, history_path=HISTORY_PATH, rng=random):
    """Retorna {"artist", "title", "album", "image"} ou None.

    Qualquer problema com o Last.fm é avisado no log, mas não impede o envio
    da newsletter: a edição sai sem a seção.
    """
    username = username or os.environ.get("LASTFM_USERNAME")

    if not username or not os.environ.get("LASTFM_API_KEY"):
        print("Last.fm não configurado (LASTFM_USERNAME/LASTFM_API_KEY). Edição sem Song of the Week.")
        return None

    try:
        history = load_history(history_path)

        for period in PERIODS:
            track = choose_track(lastfm.get_top_tracks(username, period=period), history, rng)
            if track:
                break
        else:
            print("Nenhuma música nova para recomendar. Edição sem Song of the Week.")
            return None

        try:
            info = lastfm.get_track_info(track["artist"], track["title"])
        except Exception as error:
            print(f"Álbum e capa não encontrados no Last.fm ({error}). A música vai sem eles.")
            info = {"album": None, "image": None}

        return {
            "artist": track["artist"],
            "title": track["title"],
            "album": info["album"],
            "image": info["image"],
        }
    except Exception as error:
        print(f"Não foi possível escolher a Song of the Week: {error}. Edição sem a seção.")
        return None
