from collections.abc import Sequence
from typing import Protocol


class EmailProvider(Protocol):
    """Entrega uma newsletter para os destinatários informados."""

    def send(self, subject: str, html: str, recipients: Sequence[str]) -> None:
        """Entrega a mensagem ou lança uma exceção se o envio não for aceito."""
