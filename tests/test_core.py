import sys
import tempfile
import unittest
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import collector
import history
from kit import KitNewsletterSender
from mailer import SmtpEmailProvider
from newsletter_sender import SmtpNewsletterSender
from subscribers import EnvironmentSubscriberProvider
from utils import is_last_7_days


class CollectorTests(unittest.TestCase):
    def test_contains_any_is_case_insensitive(self):
        self.assertTrue(collector.contains_any("A FULL performance", ["full performance"]))
        self.assertFalse(collector.contains_any("A concert", ["full performance"]))

    def test_get_uploads_playlist_id_swaps_prefix(self):
        self.assertEqual(
            collector.get_uploads_playlist_id("UC3I2GFN_F8WudD_2jUZbojA"),
            "UU3I2GFN_F8WudD_2jUZbojA",

                def test_parse_duration_converts_youtube_duration_to_seconds(self):
        self.assertEqual(collector.parse_duration("PT10M"), 600)
        self.assertEqual(collector.parse_duration("PT1H2M3S"), 3723)
        self.assertEqual(collector.parse_duration("PT45S"), 45)

    def test_parse_duration_rejects_invalid_duration(self):
        with self.assertRaises(ValueError):
            collector.parse_duration("10 minutes")

    def test_get_feed_applies_minimum_duration(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        playlist_response = {
            "items": [
                {
                    "snippet": {
                        "title": "Short performance",
                        "publishedAt": recent,
                        "resourceId": {"videoId": "short"},
                    }
                },
                {
                    "snippet": {
                        "title": "Long performance",
                        "publishedAt": recent,
                        "resourceId": {"videoId": "long"},
                    }
                },
            ]
        }

        config = {
            "id": "UC3I2GFN_F8WudD_2jUZbojA",
            "keep": [],
            "ignore": [],
            "min_duration": 600,
        }

        with patch.object(
            collector,
            "fetch_playlist_page",
            return_value=playlist_response,
        ), patch.object(
            collector,
            "fetch_video_durations",
            return_value={
                "short": 599,
                "long": 600,
            },
        ), patch.object(
            collector,
            "already_sent",
            return_value=False,
        ):
            feed = collector.get_feed("Test Channel", config)

        self.assertEqual(
            [video["video_id"] for video in feed],
            ["long"],
        )
        )


class HistoryTests(unittest.TestCase):
    def test_marks_multiple_videos_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary_file = Path(directory) / "sent_videos.json"

            with patch.object(history, "HISTORY_FILE", temporary_file):
                now = datetime.now(timezone.utc).isoformat()
                videos = [
                    {"video_id": "one", "published": now},
                    {"video_id": "two", "published": now},
                    {"video_id": "one", "published": now},
                ]
                history.mark_as_sent(videos)
                self.assertTrue(history.already_sent("one"))
                self.assertTrue(history.already_sent("two"))
                self.assertFalse(history.already_sent("three"))

    def test_prunes_entries_older_than_7_days(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary_file = Path(directory) / "sent_videos.json"

            with patch.object(history, "HISTORY_FILE", temporary_file):
                old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
                recent = datetime.now(timezone.utc).isoformat()

                history.save_history({"old_video": old})
                history.mark_as_sent([{"video_id": "new_video", "published": recent}])

                self.assertFalse(history.already_sent("old_video"))
                self.assertTrue(history.already_sent("new_video"))


class DateTests(unittest.TestCase):
    def test_accepts_recent_and_rejects_old_dates(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()

        self.assertTrue(is_last_7_days(recent))
        self.assertFalse(is_last_7_days(old))


class SubscriberTests(unittest.TestCase):
    def test_environment_provider_preserves_single_recipient(self):
        with patch.dict("os.environ", {"EMAIL_TO": "reader@example.com"}, clear=True):
            self.assertEqual(
                EnvironmentSubscriberProvider().get_recipients(),
                ["reader@example.com"],
            )

    def test_environment_provider_accepts_multiple_unique_recipients(self):
        with patch.dict(
            "os.environ",
            {"EMAIL_TO": "one@example.com, two@example.com, one@example.com"},
            clear=True,
        ):
            self.assertEqual(
                EnvironmentSubscriberProvider().get_recipients(),
                ["one@example.com", "two@example.com"],
            )


class SmtpProviderTests(unittest.TestCase):
    def test_sends_one_private_message_per_recipient(self):
        settings = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "password",
            "sender": "newsletter@example.com",
        }

        with patch("mailer.smtplib.SMTP") as smtp:
            server = smtp.return_value.__enter__.return_value
            SmtpEmailProvider(settings).send(
                "Music Weekly",
                "<p>Conteúdo</p>",
                ["one@example.com", "two@example.com"],
            )

        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user", "password")
        self.assertEqual(server.send_message.call_count, 2)
        self.assertEqual(server.send_message.call_args_list[0].args[0]["To"], "one@example.com")
        self.assertEqual(server.send_message.call_args_list[1].args[0]["To"], "two@example.com")


class NewsletterSenderTests(unittest.TestCase):
    def test_smtp_sender_uses_configured_subscribers(self):
        email_provider = unittest.mock.Mock()
        subscriber_provider = unittest.mock.Mock()
        subscriber_provider.get_recipients.return_value = ["reader@example.com"]

        SmtpNewsletterSender(email_provider, subscriber_provider).send("Assunto", "<p>Olá</p>")

        email_provider.send.assert_called_once_with("Assunto", "<p>Olá</p>", ["reader@example.com"])


class KitSenderTests(unittest.TestCase):
    class Response:
        def __init__(self, data):
            self.data = data

        def read(self):
            return json.dumps(self.data).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    def test_creates_non_public_broadcast_for_matching_tag(self):
        responses = [
            self.Response({"tags": [{"id": 42, "name": "music-weekly"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 7}}),
        ]

        with patch("kit.urlopen", side_effect=responses) as urlopen:
            KitNewsletterSender("key", "music-weekly", "oi@igorbdm.com").send(
                "Music Weekly", "<p>Conteúdo</p>"
            )

        request = urlopen.call_args_list[1].args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.kit.com/v4/broadcasts")
        self.assertFalse(payload["public"])
        self.assertEqual(payload["email_address"], "oi@igorbdm.com")
        self.assertEqual(payload["subscriber_filter"][0]["all"][0], {"type": "tag", "ids": [42]})


if __name__ == "__main__":
    unittest.main()
