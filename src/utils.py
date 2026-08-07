from datetime import datetime, timedelta, timezone


def is_last_7_days(date_string):
    return parse_date(date_string) >= datetime.now(timezone.utc) - timedelta(days=7)


def parse_date(date_string):
    """Converte a data ISO recebida pelo feed para uma data com fuso horário."""
    published = datetime.fromisoformat(date_string.replace("Z", "+00:00"))

    if published.tzinfo is None:
        return published.replace(tzinfo=timezone.utc)

    return published
