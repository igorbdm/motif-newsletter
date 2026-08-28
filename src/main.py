from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bootstrap import get_newsletter_sender
from channels import CHANNELS
from collector import get_feed
from history import mark_as_sent
from newsletter import generate_html, generate_subject


LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def get_edition_key(now=None):
    """Identifica a edição pela sexta-feira da semana em curso.

    Se uma execução atrasar para sábado/domingo, ela continua pertencendo à edição
    da sexta-feira anterior, evitando criar uma nova edição apenas por causa do atraso.
    """
    local_date = (now or datetime.now(LOCAL_TIMEZONE)).date()
    days_since_friday = (local_date.weekday() - 4) % 7
    edition_date = local_date - timedelta(days=days_since_friday)
    return edition_date.isoformat()


def main(newsletter_sender=None):
    newsletter_sender = newsletter_sender or get_newsletter_sender()
    edition_key = get_edition_key()
    all_videos = []

    for name, config in CHANNELS.items():
        all_videos.extend(get_feed(name, config))

    if not all_videos:
        print("Nenhum vídeo novo encontrado. Nenhum e-mail foi enviado.")
        return

    html = generate_html(all_videos)

    with open("newsletter.html", "w", encoding="utf-8") as file:
        file.write(html)

    created = newsletter_sender.send(
        generate_subject(),
        html,
        edition_key=edition_key,
        video_ids=[video["video_id"] for video in all_videos],
    )

    if created is False:
        print("Broadcast já existente; histórico local será sincronizado.")

    mark_as_sent(all_videos)
    print(f"{len(all_videos)} vídeos encontrados e processados para o provedor configurado.")


if __name__ == "__main__":
    main()
