import os

from kit import KitNewsletterSender
from mailer import SmtpEmailProvider
from newsletter_sender import NewsletterSender, SmtpNewsletterSender
from subscribers import EnvironmentSubscriberProvider, SubscriberProvider


def get_subscriber_provider() -> SubscriberProvider:
    """Define a origem da lista de assinantes da aplicação."""
    return EnvironmentSubscriberProvider()


def get_newsletter_sender() -> NewsletterSender:
    """Monta a entrega escolhida sem acoplar o restante da aplicação."""
    provider = os.getenv("EMAIL_DELIVERY_PROVIDER", "smtp").casefold()

    if provider == "kit":
        return KitNewsletterSender.from_environment()

    if provider == "smtp":
        return SmtpNewsletterSender(SmtpEmailProvider(), get_subscriber_provider())

    raise RuntimeError(f"Provedor de e-mail desconhecido: {provider}")
