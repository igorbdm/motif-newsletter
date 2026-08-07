import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "sent_videos.json"


def load_history():
    if not HISTORY_FILE.exists():
        return {}

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_history(history):
    HISTORY_FILE.parent.mkdir(exist_ok=True)

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)


def already_sent(video_id):
    history = load_history()
    return video_id in history


def mark_as_sent(videos):
    """Registra os vídeos (com data de publicação) somente depois de o e-mail ter sido enviado.
    Também aproveita para limpar do histórico vídeos com mais de 7 dias, já que esses
    nunca mais seriam consultados de qualquer forma (o script só busca a última semana)."""
    history = load_history()

    for video in videos:
        history[video["video_id"]] = video["published"]

    save_history(prune_old_entries(history))


def prune_old_entries(history):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    pruned = {}

    for video_id, published in history.items():
        published_date = datetime.fromisoformat(published.replace("Z", "+00:00"))

        if published_date >= seven_days_ago:
            pruned[video_id] = published

    return pruned
