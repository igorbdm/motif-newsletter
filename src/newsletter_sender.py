from typing import Protocol

from email_provider import EmailProvider
from subscribers import SubscriberProvider


class NewsletterSender(Protocol):
    """Entrega uma edição sem expor o fluxo principal ao provedor escolhido."""

    def send(self, subject: str, html: str) -> None:
        """Aceita a edição para envio ou lança uma exceção."""


class SmtpNewsletterSender:
    """Combina o SMTP atual com a origem temporária de destinatários."""

    def __init__(self, email_provider: EmailProvider, subscriber_provider: SubscriberProvider):
        self.email_provider = email_provider
        self.subscriber_provider = subscriber_provider

    def send(self, subject: str, html: str) -> None:
        recipients = self.subscriber_provider.get_recipients()
        self.email_provider.send(subject, html, recipients)
