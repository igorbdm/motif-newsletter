from bootstrap import get_newsletter_sender
from channels import CHANNELS
from collector import get_feed
from history import mark_as_sent
from newsletter import generate_html, generate_subject


def main(newsletter_sender=None):

    all_videos = []

    for name, config in CHANNELS.items():
        all_videos.extend(get_feed(name, config))

    if not all_videos:
        print("Nenhum vídeo novo encontrado. Nenhum e-mail foi enviado.")
        return

    html = generate_html(all_videos)

    with open("newsletter.html", "w", encoding="utf-8") as file:
        file.write(html)

    newsletter_sender = newsletter_sender or get_newsletter_sender()
    newsletter_sender.send(generate_subject(), html)
    mark_as_sent(all_videos)

    print(f"{len(all_videos)} vídeos encontrados e enviados para o provedor configurado.")


if __name__ == "__main__":
    main()
