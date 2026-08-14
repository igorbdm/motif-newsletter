import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.kit.com/v4"


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

    def send(self, subject: str, html: str) -> None:
        tag_id = self._find_tag_id()
        now = datetime.now(timezone.utc)
        send_at = (now + timedelta(minutes=self.send_delay_minutes)).replace(second=0, microsecond=0)

        if send_at <= now:
            send_at += timedelta(minutes=1)

        payload = {
            "email_address": self.sender_email,
            "content": html,
            "description": f"Music Weekly — {subject}",
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
