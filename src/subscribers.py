import os
from collections.abc import Sequence
from typing import Protocol


class SubscriberProvider(Protocol):
    """Fornece os assinantes aptos a receber a newsletter."""

    def get_recipients(self) -> Sequence[str]:
        """Retorna endereços de e-mail únicos e ativos."""


class EnvironmentSubscriberProvider:
    """Implementação temporária compatível com o atual EMAIL_TO.

    Aceita um único endereço ou uma lista separada por vírgulas. Quando uma
    plataforma de assinantes for escolhida, basta substituir esta classe no
    bootstrap sem alterar o fluxo da newsletter.
    """

    def get_recipients(self) -> Sequence[str]:
        value = os.getenv("EMAIL_TO", "")
        recipients = [email.strip() for email in value.split(",") if email.strip()]

        if not recipients:
            raise RuntimeError("Configuração de e-mail ausente: EMAIL_TO")

        return list(dict.fromkeys(recipients))
