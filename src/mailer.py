import os
import smtplib
from collections.abc import Sequence
from email.message import EmailMessage


def get_settings():
    required_settings = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD"]
    missing_settings = [setting for setting in required_settings if not os.getenv(setting)]

    if missing_settings:
        names = ", ".join(missing_settings)
        raise RuntimeError(f"Configurações de e-mail ausentes: {names}")

    return {
        "host": os.environ["SMTP_HOST"],
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "sender": os.getenv("EMAIL_FROM", os.environ["SMTP_USERNAME"]),
    }


class SmtpEmailProvider:
    """Adaptador SMTP compatível com a configuração atual do projeto."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def send(self, subject: str, html: str, recipients: Sequence[str]) -> None:
        """Envia uma cópia individual para cada destinatário.

        A interface é a mesma que futuros provedores de API usarão. Para o
        atual destinatário único, o comportamento permanece idêntico.
        """
        if not recipients:
            raise RuntimeError("Nenhum destinatário disponível para envio")

        with smtplib.SMTP(self.settings["host"], self.settings["port"]) as server:
            server.starttls()
            server.login(self.settings["username"], self.settings["password"])

            for recipient in recipients:
                message = EmailMessage()
                message["Subject"] = subject
                message["From"] = self.settings["sender"]
                message["To"] = recipient
                message.set_content("Abra este e-mail em um leitor que suporte HTML.")
                message.add_alternative(html, subtype="html")
                server.send_message(message)
