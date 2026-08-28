import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.kit.com/v4"
BROADCAST_DESCRIPTION_PREFIX = "Motif Weekly | edition="


class KitNewsletterSender:
    """Entrega uma edição como Broadcast do Kit para uma tag da audiência."""

    def __init__(self, api_key, tag_name, sender_email=None, publish_to_web=False, send_delay_minutes=1):
        self.api_key = api_key
        self.tag_name = tag_name
        self.sender_email = sender_email
        self.publish_to_web = publish_to_web
        self.send_delay_minutes = send_delay_minutes

    @classmethod
    def from_environment(cls):
        required = ["KIT_API_KEY", "KIT_TAG_NAME"]
        missing = [name for name in required if not os.getenv(name)]

        if missing:
            raise RuntimeError(f"Configurações do Kit ausentes: {', '.join(missing)}")

        return cls(
            api_key=os.environ["KIT_API_KEY"],
            tag_name=os.environ["KIT_TAG_NAME"],
            sender_email=os.getenv("KIT_SENDER_EMAIL"),
            publish_to_web=os.getenv("KIT_PUBLISH_TO_WEB", "false").casefold() == "true",
            send_delay_minutes=int(os.getenv("KIT_SEND_DELAY_MINUTES", "1")),
        )

    def send(self, subject: str, html: str, edition_key: str, video_ids) -> bool:
        """Cria o broadcast uma única vez para a edição/conjunto de vídeos.

        Retorna True quando criou um novo broadcast e False quando a mesma edição
        já existe no Kit e pode ser considerada concluída com segurança.
        """
        tag_id = self._find_tag_id()
        description = self._build_description(edition_key, video_ids)

        existing = self._find_edition_broadcast(edition_key)
        matching = [broadcast for broadcast in existing if broadcast.get("description") == description]
        if matching:
            print(
                f"A edição {edition_key} já existe no Kit (broadcast {matching[0].get('id')}). "
                "Nenhum novo broadcast será criado."
            )
            return False

        if existing:
            raise RuntimeError(
                f"Já existe um broadcast da edição {edition_key} no Kit, mas com outro conteúdo. "
                "O envio foi interrompido para evitar duplicidade ou perda de conteúdo."
            )

        now = datetime.now(timezone.utc)
        send_at = (now + timedelta(minutes=self.send_delay_minutes)).replace(second=0, microsecond=0)

        if send_at <= now:
            send_at += timedelta(minutes=1)

        payload = {
            "email_address": self.sender_email,
            "content": html,
            "description": description,
            "public": self.publish_to_web,
            "published_at": send_at.isoformat() if self.publish_to_web else None,
            "send_at": send_at.isoformat(),
            "thumbnail_alt": None,
            "thumbnail_url": None,
            "preview_text": "What showed up this week in the world of live music",
            "subject": subject,
            "subscriber_filter": [
                {"all": [{"type": "tag", "ids": [tag_id]}], "any": None, "none": None}
            ],
        }

        self._request("POST", "/broadcasts", payload)
        return True

    @staticmethod
    def _build_description(edition_key: str, video_ids) -> str:
        normalized_ids = sorted(set(video_ids))
        fingerprint = hashlib.sha256("\n".join(normalized_ids).encode("utf-8")).hexdigest()[:16]
        return f"{BROADCAST_DESCRIPTION_PREFIX}{edition_key} | videos={fingerprint}"

    def _find_edition_broadcast(self, edition_key):
        path = "/broadcasts?per_page=1000"
        matches = []
        prefix = f"{BROADCAST_DESCRIPTION_PREFIX}{edition_key} |"

        while path:
            response = self._request("GET", path)

            for broadcast in response.get("broadcasts", []):
                description = broadcast.get("description") or ""
                if description.startswith(prefix):
                    matches.append(broadcast)

            pagination = response.get("pagination", {})
            cursor = pagination.get("end_cursor")
            path = f"/broadcasts?per_page=1000&after={cursor}" if pagination.get("has_next_page") and cursor else None

        return matches

    def _find_tag_id(self):
        path = "/tags?per_page=1000"

        while path:
            response = self._request("GET", path)

            for tag in response["tags"]:
                if tag["name"] == self.tag_name:
                    return tag["id"]

            pagination = response.get("pagination", {})
            cursor = pagination.get("end_cursor")
            path = f"/tags?per_page=1000&after={cursor}" if pagination.get("has_next_page") and cursor else None

        raise RuntimeError(f"A tag do Kit não foi encontrada: {self.tag_name}")

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{API_BASE_URL}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Kit-Api-Key": self.api_key,
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"O Kit recusou a solicitação ({error.code}): {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Não foi possível conectar ao Kit: {error.reason}") from error
