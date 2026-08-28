import sys
import unittest
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from environment import get_audience_tag, get_edition_id, get_runtime_branch

import collector
from kit import KitNewsletterSender
from mailer import SmtpEmailProvider
from newsletter_sender import SmtpNewsletterSender
from subscribers import EnvironmentSubscriberProvider
from utils import parse_date


class CollectorTests(unittest.TestCase):
    def test_contains_any_is_case_insensitive(self):
        self.assertTrue(collector.contains_any("A FULL performance", ["full performance"]))
        self.assertFalse(collector.contains_any("A concert", ["full performance"]))

    def test_get_uploads_playlist_id_swaps_prefix(self):
        self.assertEqual(
            collector.get_uploads_playlist_id("UC3I2GFN_F8WudD_2jUZbojA"),
            "UU3I2GFN_F8WudD_2jUZbojA",
        )

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
        ):
            feed = collector.get_feed("Test Channel", config)

        self.assertEqual(
            [video["video_id"] for video in feed],
            ["long"],
        )


class EnvironmentTests(unittest.TestCase):
    def test_main_branch_uses_production_audience(self):
        self.assertEqual(get_audience_tag("main"), "music-weekly")

    def test_test_branch_uses_test_audience(self):
        self.assertEqual(get_audience_tag("test"), "test")

    def test_unknown_branch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Branch não autorizada"):
            get_audience_tag("feature/newsletter")

    def test_github_branch_is_used_when_running_in_actions(self):
        with patch.dict("os.environ", {"GITHUB_REF_NAME": "test"}, clear=True):
            self.assertEqual(get_runtime_branch(), "test")

    def test_production_edition_id_uses_edition_date(self):
        with patch.dict("os.environ", {"GITHUB_REF_NAME": "main"}, clear=True):
            self.assertEqual(get_edition_id(date(2026, 8, 28)), "2026-08-28")

    def test_test_edition_id_uses_unique_github_run_identity(self):
        with patch.dict(
            "os.environ",
            {
                "GITHUB_REF_NAME": "test",
                "GITHUB_RUN_ID": "123456",
                "GITHUB_RUN_ATTEMPT": "2",
            },
            clear=True,
        ):
            self.assertEqual(
                get_edition_id(date(2026, 8, 28)),
                "test-2026-08-28-run-123456-attempt-2",
            )

    def test_test_edition_id_requires_github_run_id(self):
        with patch.dict("os.environ", {"GITHUB_REF_NAME": "test"}, clear=True):
            with self.assertRaises(RuntimeError):
                get_edition_id(date(2026, 8, 28))


class DateTests(unittest.TestCase):
    def test_collection_start_is_previous_friday_at_midnight(self):
        from main import get_collection_start

        start = get_collection_start(date(2026, 8, 28))

        self.assertEqual(start.isoformat(), "2026-08-21T00:00:00-03:00")

    def test_get_feed_stops_at_previous_edition_boundary(self):
        boundary = "2026-08-21T00:00:00+00:00"
        newer = "2026-08-22T10:00:00+00:00"

        playlist_response = {
            "items": [
                {
                    "snippet": {
                        "title": "New video",
                        "publishedAt": newer,
                        "resourceId": {"videoId": "new"},
                    }
                },
                {
                    "snippet": {
                        "title": "Boundary video",
                        "publishedAt": boundary,
                        "resourceId": {"videoId": "boundary"},
                    }
                },
                {
                    "snippet": {
                        "title": "Older video",
                        "publishedAt": "2026-08-20T23:00:00+00:00",
                        "resourceId": {"videoId": "old"},
                    }
                },
            ]
        }

        config = {
            "id": "UC3I2GFN_F8WudD_2jUZbojA",
            "keep": [],
            "ignore": [],
        }

        with patch.object(collector, "fetch_playlist_page", return_value=playlist_response):
            feed = collector.get_feed("Test Channel", config, since=parse_date(boundary))

        self.assertEqual([video["video_id"] for video in feed], ["new"])

    def test_edition_date_is_friday(self):
        from main import get_edition_date

        self.assertEqual(get_edition_date(date(2026, 8, 28)), date(2026, 8, 28))
        self.assertEqual(get_edition_date(date(2026, 8, 27)), date(2026, 8, 28))
        self.assertEqual(get_edition_date(date(2026, 8, 29)), date(2026, 9, 4))

    def test_main_collects_from_previous_edition_start(self):
        import main

        calls = []
        sender = unittest.mock.Mock()
        sender.send.return_value = "created"

        with patch.object(main, "get_edition_date", return_value=date(2026, 8, 28)), \
            patch.dict("os.environ", {"GITHUB_REF_NAME": "main"}, clear=True), \
            patch.object(main, "get_newsletter_sender", return_value=sender), \
            patch.object(main, "get_feed", side_effect=lambda name, config, since=None: calls.append(since) or [{
                "channel": name,
                "title": "Video",
                "published": "2026-08-22T10:00:00Z",
                "link": "https://www.youtube.com/watch?v=video",
                "video_id": "video",
            }]), \
            patch.object(main, "generate_html", return_value="<p>Conteúdo</p>"):
            main.main()

        self.assertEqual(len(calls), len(main.CHANNELS))
        self.assertTrue(all(value.isoformat() == "2026-08-21T00:00:00-03:00" for value in calls))
        sender.send.assert_called_once()

    def test_subject_uses_edition_date(self):
        from newsletter import generate_subject

        self.assertEqual(
            generate_subject(date(2026, 8, 28)),
            "A Week in Music · August 28, 2026",
        )


class BootstrapTests(unittest.TestCase):
    def test_kit_sender_receives_production_tag_on_main(self):
        import bootstrap

        with patch.dict(
            "os.environ",
            {
                "EMAIL_DELIVERY_PROVIDER": "kit",
                "KIT_API_KEY": "key",
                "GITHUB_REF_NAME": "main",
            },
            clear=True,
        ), patch.object(
            bootstrap.KitNewsletterSender,
            "from_environment",
            return_value=unittest.mock.Mock(),
        ) as from_environment:
            bootstrap.get_newsletter_sender()

        from_environment.assert_called_once_with(tag_name="music-weekly")

    def test_kit_sender_receives_test_tag_on_test_branch(self):
        import bootstrap

        with patch.dict(
            "os.environ",
            {
                "EMAIL_DELIVERY_PROVIDER": "kit",
                "KIT_API_KEY": "key",
                "GITHUB_REF_NAME": "test",
            },
            clear=True,
        ), patch.object(
            bootstrap.KitNewsletterSender,
            "from_environment",
            return_value=unittest.mock.Mock(),
        ) as from_environment:
            bootstrap.get_newsletter_sender()

        from_environment.assert_called_once_with(tag_name="test")

    def test_kit_sender_rejects_unknown_branch_before_initializing_kit(self):
        import bootstrap

        with patch.dict(
            "os.environ",
            {
                "EMAIL_DELIVERY_PROVIDER": "kit",
                "KIT_API_KEY": "key",
                "GITHUB_REF_NAME": "feature/newsletter",
            },
            clear=True,
        ), patch.object(
            bootstrap.KitNewsletterSender,
            "from_environment",
        ) as from_environment:
            with self.assertRaisesRegex(RuntimeError, "Branch não autorizada"):
                bootstrap.get_newsletter_sender()

        from_environment.assert_not_called()


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
            self.Response({"broadcasts": [], "pagination": {"has_next_page": False}}),
            self.Response({"tags": [{"id": 42, "name": "music-weekly"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 7, "status": "scheduled"}}),
        ]

        with patch("kit.urlopen", side_effect=responses) as urlopen:
            result = KitNewsletterSender("key", "music-weekly", "oi@igorbdm.com").send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="2026-08-28"
            )

        request = urlopen.call_args_list[2].args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result, "created")
        self.assertEqual(request.full_url, "https://api.kit.com/v4/broadcasts")
        self.assertFalse(payload["public"])
        self.assertEqual(payload["email_address"], "oi@igorbdm.com")
        self.assertEqual(payload["subscriber_filter"][0]["all"][0], {"type": "tag", "ids": [42]})
        self.assertIn("edition=2026-08-28", payload["description"])

    def test_does_not_confuse_test_and_production_edition_ids(self):
        responses = [
            self.Response({"broadcasts": [], "pagination": {"has_next_page": False}}),
            self.Response({"tags": [{"id": 42, "name": "test"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 8, "status": "scheduled"}}),
        ]

        with patch("kit.urlopen", side_effect=responses) as urlopen:
            result = KitNewsletterSender("key", "test").send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="test-2026-08-28-run-123-attempt-1"
            )

        request = urlopen.call_args_list[2].args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result, "created")
        self.assertIn("edition=test-2026-08-28-run-123-attempt-1", payload["description"])

    def test_test_runs_with_different_ids_can_each_create_broadcasts(self):
        responses = [
            self.Response({"broadcasts": [], "pagination": {"has_next_page": False}}),
            self.Response({"tags": [{"id": 42, "name": "test"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 9, "status": "scheduled"}}),
            self.Response({"broadcasts": [], "pagination": {"has_next_page": False}}),
            self.Response({"tags": [{"id": 42, "name": "test"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 10, "status": "scheduled"}}),
        ]

        with patch("kit.urlopen", side_effect=responses):
            sender = KitNewsletterSender("key", "test")
            first = sender.send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="test-2026-08-28-run-123-attempt-1"
            )
            second = sender.send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="test-2026-08-28-run-124-attempt-1"
            )

        self.assertEqual(first, "created")
        self.assertEqual(second, "created")

    def test_does_not_create_duplicate_for_existing_completed_broadcast(self):
        response = self.Response({
            "broadcasts": [{
                "id": 98,
                "description": "Music Weekly — edition=2026-08-28 — A Week in Music",
                "status": "completed",
            }],
            "pagination": {"has_next_page": False},
        })

        with patch("kit.urlopen", return_value=response) as urlopen:
            result = KitNewsletterSender("key", "music-weekly").send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="2026-08-28"
            )

        self.assertEqual(result, "completed")
        urlopen.assert_called_once()

    def test_does_not_create_duplicate_for_existing_scheduled_broadcast(self):
        response = self.Response({
            "broadcasts": [{
                "id": 99,
                "description": "Music Weekly — edition=2026-08-28 — A Week in Music",
                "status": "scheduled",
            }],
            "pagination": {"has_next_page": False},
        })

        with patch("kit.urlopen", return_value=response) as urlopen:
            result = KitNewsletterSender("key", "music-weekly").send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="2026-08-28"
            )

        self.assertEqual(result, "scheduled")
        urlopen.assert_called_once()

    def test_aborted_broadcast_allows_retry(self):
        responses = [
            self.Response({
                "broadcasts": [{
                    "id": 99,
                    "description": "Music Weekly — edition=2026-08-28 — A Week in Music",
                    "status": "aborted",
                }],
                "pagination": {"has_next_page": False},
            }),
            self.Response({"tags": [{"id": 42, "name": "music-weekly"}], "pagination": {}}),
            self.Response({"broadcast": {"id": 100, "status": "scheduled"}}),
        ]

        with patch("kit.urlopen", side_effect=responses) as urlopen:
            result = KitNewsletterSender("key", "music-weekly").send(
                "Music Weekly", "<p>Conteúdo</p>", edition_id="2026-08-28"
            )

        self.assertEqual(result, "created")
        self.assertEqual(urlopen.call_count, 3)

    def test_multiple_active_broadcasts_fail_closed(self):
        response = self.Response({
            "broadcasts": [
                {"id": 1, "description": "edition=2026-08-28", "status": "scheduled"},
                {"id": 2, "description": "edition=2026-08-28", "status": "sending"},
            ],
            "pagination": {"has_next_page": False},
        })

        with patch("kit.urlopen", return_value=response) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "Mais de um Broadcast ativo"):
                KitNewsletterSender("key", "music-weekly").send(
                    "Music Weekly", "<p>Conteúdo</p>", edition_id="2026-08-28"
                )

        urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
