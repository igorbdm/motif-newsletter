from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from bootstrap import get_newsletter_sender
from channels import CHANNELS
from collector import get_feed
from newsletter import generate_html, generate_subject


def get_edition_date(today=None):
    today = today or datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    days_until_friday = (4 - today.weekday()) % 7
    return today + timedelta(days=days_until_friday)


def get_collection_start(edition_date):
    previous_edition = edition_date - timedelta(days=7)
    return datetime.combine(
        previous_edition,
        time.min,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def main(newsletter_sender=None):
    edition_date = get_edition_date()
    edition_id = edition_date.isoformat()
    collection_start = get_collection_start(edition_date)
    newsletter_sender = newsletter_sender or get_newsletter_sender()

    all_videos = []

    for name, config in CHANNELS.items():
        all_videos.extend(get_feed(name, config, since=collection_start))

    if not all_videos:
        print("Nenhum vídeo novo encontrado. Nenhum e-mail foi enviado.")
        return

    html = generate_html(all_videos, edition_date)

    with open("newsletter.html", "w", encoding="utf-8") as file:
        file.write(html)

    result = newsletter_sender.send(
        generate_subject(edition_date),
        html,
        edition_id=edition_id,
    )

    if result in {"scheduled", "sending", "draft"}:
        print(f"A edição {edition_id} já está em processamento no Kit; nenhum novo envio foi feito.")
        return

    if result == "created":
        print(f"A edição {edition_id} foi aceita pelo Kit.")
        return

    print(f"Nenhum novo envio foi criado para a edição {edition_id}.")


if __name__ == "__main__":
    main()
