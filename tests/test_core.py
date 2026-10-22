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


    def test_pitchfork_keeps_only_full_over_under_episodes(self):
        from channels import CHANNELS

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        uploads = {
            "full": ("Audrey Hobert Rates Podcasts, Don Toliver, and Disney Adults | Pitchfork", 599),
            "clip": ("Audrey Hobert Rates Don Toliver", 31),
            "teaser": ("Audrey Hobert Does Pitchfork's Over/Under", 10),
            "other": ("Judeline's Perfect 10", 162),
        }
        playlist_response = {"items": [
            {"snippet": {"title": title, "publishedAt": recent, "resourceId": {"videoId": video_id}}}
            for video_id, (title, _) in uploads.items()
        ]}

        with patch.object(collector, "fetch_playlist_page", return_value=playlist_response), \
            patch.object(collector, "fetch_video_durations", side_effect=lambda ids: {
                video_id: uploads[video_id][1] for video_id in ids
            }):
            feed = collector.get_feed("Pitchfork", CHANNELS["Pitchfork"])

        self.assertEqual([video["video_id"] for video in feed], ["full"])
        self.assertEqual(feed[0]["section"], "extras")


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

    def test_extras_are_rendered_in_separate_section_after_live_videos(self):
        from newsletter import generate_html

        def video(channel, title, section=None):
            item = {"channel": channel, "title": title, "link": "https://www.youtube.com/watch?v=x"}
            if section:
                item["section"] = section
            return item

        html = generate_html([
            video("Amoeba Music", "Bag Video", "extras"),
            video("KEXP", "Live Video"),
        ], date(2026, 8, 28))

        self.assertLess(html.index("Live Video"), html.index("Know someone who might enjoy this?"))
        self.assertLess(html.index("Know someone who might enjoy this?"), html.index("Beyond the Stage"))
        self.assertLess(html.index("Beyond the Stage"), html.index("Bag Video"))
        self.assertEqual(html.count("Beyond the Stage"), 1)
        self.assertEqual(html.count("Know someone who might enjoy this?"), 1)

    def test_pick_is_rendered_before_live_videos(self):
        from newsletter import generate_html

        html = generate_html([{
            "channel": "KEXP",
            "title": "Live Video",
            "link": "https://www.youtube.com/watch?v=x",
        }], date(2026, 8, 28), pick={
            "artist": "Fontaines D.C.",
            "title": "Starburster",
            "album": "Romance",
            "image": "https://example.com/cover.jpg",
        })

        pick_start = html.index("Song of the Week")
        pick_end = html.index("Live Video")
        pick_html = html[pick_start:pick_end]

        self.assertLess(pick_start, pick_end)
        self.assertIn("Starburster", pick_html)
        self.assertIn("Fontaines D.C.", pick_html)
        self.assertIn("Romance", pick_html)
        self.assertIn('src="https://example.com/cover.jpg"', pick_html)
        self.assertNotIn("<a ", pick_html)

    def test_pick_shows_streaming_links_in_order(self):
        from newsletter import generate_pick_html

        html = generate_pick_html({
            "artist": "Artist",
            "title": "Song",
            "links": {
                "youtube_music": "https://music.youtube.com/watch?v=abc",
                "spotify": "https://open.spotify.com/search/Artist%20Song",
                "apple_music": "https://music.apple.com/us/album/x?i=1&a=2",
            },
        })

        self.assertLess(html.index(">Spotify</a>"), html.index(">Apple Music</a>"))
        self.assertLess(html.index(">Apple Music</a>"), html.index(">YouTube Music</a>"))
        self.assertIn('href="https://music.apple.com/us/album/x?i=1&amp;a=2"', html)

    def test_pick_section_is_omitted_without_pick(self):
        from newsletter import generate_html

        html = generate_html([], date(2026, 8, 28))

        self.assertNotIn("Song of the Week", html)

    def test_sign_off_closes_the_edition_before_the_footer(self):
        from newsletter import generate_html

        html = generate_html([], date(2026, 8, 28))

        self.assertLess(html.index("See you next Friday."), html.index("You're receiving this"))

    def test_extras_section_is_omitted_without_extra_videos(self):
        from newsletter import generate_html

        html = generate_html([{
            "channel": "KEXP",
            "title": "Live Video",
            "link": "https://www.youtube.com/watch?v=x",
        }], date(2026, 8, 28))

        self.assertNotIn("Beyond the Stage", html)
        self.assertEqual(html.count("Know someone who might enjoy this?"), 1)

    def test_week_without_extras_videos_sends_edition_without_beyond_the_stage(self):
        import main

        sender = unittest.mock.Mock()
        sender.send.return_value = "created"

        # Canais de música ao vivo publicaram; os canais do bloco de extras não.
        def get_feed(name, config, since=None):
            if config.get("section") == "extras":
                return []
            return [{
                "channel": name,
                "section": config.get("section", "live"),
                "title": f"{name} Session",
                "link": "https://www.youtube.com/watch?v=x",
            }]

        with patch.object(main, "get_edition_date", return_value=date(2026, 8, 28)), \
            patch.dict("os.environ", {"GITHUB_REF_NAME": "main"}, clear=True), \
            patch.object(main, "get_newsletter_sender", return_value=sender), \
            patch.object(main, "get_feed", side_effect=get_feed), \
            patch.object(main, "get_song_of_the_week", return_value=None):
            main.main()

        html = sender.send.call_args.args[1]
        self.assertIn("KEXP Session", html)
        self.assertNotIn("Beyond the Stage", html)
        self.assertNotIn("Watch video", html)


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


class SongOfTheWeekTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tempdir = tempfile.TemporaryDirectory()
        self.history_path = Path(self.tempdir.name) / "song_history.json"

    def tearDown(self):
        self.tempdir.cleanup()

    def track(self, title, plays=1, artist="Artist"):
        return {"artist": artist, "title": title, "plays": plays}

    def test_never_picks_a_song_already_in_history(self):
        import random
        from song_of_the_week import choose_track

        tracks = [self.track("Old"), self.track("New")]
        history = [{"artist": "ARTIST", "title": " old "}]

        for seed in range(50):
            self.assertEqual(
                choose_track(tracks, history, random.Random(seed))["title"],
                "New",
            )

    def test_only_top_ten_new_songs_are_candidates(self):
        import random
        from song_of_the_week import choose_track

        tracks = [self.track(f"Song {index}") for index in range(15)]
        history = [{"artist": "Artist", "title": "Song 0"}]

        picked = {
            choose_track(tracks, history, random.Random(seed))["title"]
            for seed in range(300)
        }

        self.assertEqual(picked, {f"Song {index}" for index in range(1, 11)})

    def test_songs_with_more_plays_are_picked_more_often(self):
        import random
        from song_of_the_week import choose_track

        tracks = [self.track("Many", plays=16), self.track("Few", plays=1)]
        rng = random.Random(0)

        picks = [choose_track(tracks, [], rng)["title"] for _ in range(2000)]

        # Peso = raiz dos plays: 4 contra 1, ou seja, ~80% para "Many".
        self.assertAlmostEqual(picks.count("Many") / len(picks), 0.8, delta=0.04)

    def test_prefers_artists_not_recommended_recently(self):
        import random
        from song_of_the_week import choose_track

        tracks = [
            self.track("Hit", plays=50, artist="Recent"),
            self.track("Deep Cut", plays=1, artist="Fresh"),
        ]
        history = [{"artist": "recent", "title": "Older Song"}]

        for seed in range(50):
            self.assertEqual(
                choose_track(tracks, history, random.Random(seed))["artist"],
                "Fresh",
            )

    def test_recent_artist_is_still_picked_when_there_is_no_alternative(self):
        from song_of_the_week import choose_track

        tracks = [self.track("Another Song", artist="Recent")]
        history = [{"artist": "Recent", "title": "Older Song"}]

        self.assertEqual(choose_track(tracks, history)["title"], "Another Song")

    def test_artists_from_older_editions_are_no_longer_avoided(self):
        import random
        from song_of_the_week import RECENT_ARTIST_EDITIONS, choose_track

        history = [{"artist": "Old Favorite", "title": "First"}] + [
            {"artist": f"Artist {index}", "title": "Song"}
            for index in range(RECENT_ARTIST_EDITIONS)
        ]
        tracks = [
            self.track("Second", plays=1, artist="Old Favorite"),
            self.track("Other", plays=1, artist="Someone"),
        ]

        picked = {
            choose_track(tracks, history, random.Random(seed))["artist"]
            for seed in range(100)
        }

        self.assertEqual(picked, {"Old Favorite", "Someone"})

    def test_returns_none_when_every_song_was_recommended(self):
        from song_of_the_week import choose_track

        self.assertIsNone(choose_track(
            [self.track("Old")],
            [{"artist": "Artist", "title": "Old"}],
        ))

    def test_falls_back_to_last_month_when_week_has_no_new_song(self):
        import song_of_the_week

        def top_tracks(username, period):
            return [self.track("Old")] if period == "7day" else [self.track("Monthly")]

        song_of_the_week.save_to_history(
            {"artist": "Artist", "title": "Old"}, "2026-08-21", self.history_path,
        )

        with patch.dict("os.environ", {"LASTFM_API_KEY": "key"}), \
            patch.object(song_of_the_week.lastfm, "get_top_tracks", side_effect=top_tracks), \
            patch.object(song_of_the_week.lastfm, "get_track_info", return_value={"album": "Record", "image": "https://example.com/c.jpg"}), \
            patch.object(song_of_the_week, "get_streaming_links", return_value={"spotify": "https://s"}):
            pick = song_of_the_week.get_song_of_the_week("user", self.history_path)

        self.assertEqual(pick, {
            "artist": "Artist",
            "title": "Monthly",
            "album": "Record",
            "image": "https://example.com/c.jpg",
            "links": {"spotify": "https://s"},
        })

    def test_lastfm_failure_does_not_block_the_newsletter(self):
        import song_of_the_week

        with patch.dict("os.environ", {"LASTFM_API_KEY": "key"}), \
            patch.object(song_of_the_week.lastfm, "get_top_tracks", side_effect=RuntimeError("offline")):
            self.assertIsNone(song_of_the_week.get_song_of_the_week("user", self.history_path))

    def test_missing_cover_keeps_the_song(self):
        import song_of_the_week

        with patch.dict("os.environ", {"LASTFM_API_KEY": "key"}), \
            patch.object(song_of_the_week.lastfm, "get_top_tracks", return_value=[self.track("New")]), \
            patch.object(song_of_the_week.lastfm, "get_track_info", side_effect=RuntimeError("404")), \
            patch.object(song_of_the_week, "get_streaming_links", return_value={}):
            pick = song_of_the_week.get_song_of_the_week("user", self.history_path)

        self.assertEqual(pick["title"], "New")
        self.assertIsNone(pick["album"])
        self.assertIsNone(pick["image"])

    def test_track_info_ignores_lastfm_placeholder_cover(self):
        import lastfm

        placeholder = "https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png"
        response = {"track": {"album": {"title": "Record", "image": [{"#text": placeholder}]}}}

        with patch.object(lastfm, "call_api", return_value=response):
            self.assertEqual(
                lastfm.get_track_info("Artist", "Song"),
                {"album": "Record", "image": None},
            )

    def test_track_info_without_album(self):
        import lastfm

        with patch.object(lastfm, "call_api", return_value={"track": {"name": "Song"}}):
            self.assertEqual(
                lastfm.get_track_info("Artist", "Song"),
                {"album": None, "image": None},
            )

    def run_main(self, branch, result):
        import main
        from song_of_the_week import load_history, save_to_history

        sender = unittest.mock.Mock()
        sender.send.return_value = result
        pick = {"artist": "Artist", "title": "Song", "image": None}
        video = {"channel": "KEXP", "title": "Video", "link": "https://www.youtube.com/watch?v=x"}

        with patch.object(main, "get_edition_date", return_value=date(2026, 8, 28)), \
            patch.dict("os.environ", {"GITHUB_REF_NAME": branch, "GITHUB_RUN_ID": "1"}, clear=True), \
            patch.object(main, "get_newsletter_sender", return_value=sender), \
            patch.object(main, "get_feed", return_value=[video]), \
            patch.object(main, "get_song_of_the_week", return_value=pick), \
            patch.object(main, "save_to_history", side_effect=lambda pick, edition_id: save_to_history(pick, edition_id, self.history_path)):
            main.main()

        return load_history(self.history_path)

    def test_production_send_records_the_song(self):
        history = self.run_main("main", "created")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["edition"], "2026-08-28")
        self.assertEqual(history[0]["title"], "Song")

    def test_test_branch_does_not_record_the_song(self):
        self.assertEqual(self.run_main("test", "created"), [])

    def test_existing_broadcast_does_not_record_the_song(self):
        self.assertEqual(self.run_main("main", "completed"), [])


class GenreTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tempdir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.tempdir.name) / "artist_genres.json"
        self.overrides_path = Path(self.tempdir.name) / "genre_overrides.json"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_each_channel_title_becomes_artist_and_program(self):
        from channels import CHANNELS
        from titles import display_title

        examples = [
            ("KEXP", "Death Cab For Cutie - Full Performance (Live on KEXP)", "Death Cab For Cutie — Live on KEXP"),
            ("Tiny Desk", "Tim Bernardes: Tiny Desk Concert", "Tim Bernardes — Tiny Desk Concert"),
            ("Audiotree", "Cold Steel on Audiotree Live (Full Session)", "Cold Steel — Audiotree Live"),
            ("La Blogothèque", "Naomi Greene | A Take Away Show", "Naomi Greene — A Take Away Show"),
            ("La Blogothèque", "Piers Faccini & Ballaké Sissoko | A Take Away Show at @sudsarles", "Piers Faccini & Ballaké Sissoko — A Take Away Show"),
            ("La Blogothèque", "Adèle Castillon | Live Session for The Collective by Stradivarius", "Adèle Castillon — Live Session"),
            ("KCRW", "Sébastien Tellier: Live on KCRW", "Sébastien Tellier — Live on KCRW"),
            ("Cultura Livre", "CULTURA LIVRE | Fera Neném | 10/10/26", "Fera Neném — Cultura Livre"),
            # A grafia do artista é a do título do vídeo.
            ("Cultura Livre", "NIGÉRIA FUTEBOL CLUBE NO CULTURA LIVRE", "NIGÉRIA FUTEBOL CLUBE — Cultura Livre"),
            ("Amoeba Music", 'Elvis Costello\'s "What\'s In My Bag?" | Amoeba Music', "Elvis Costello — What's In My Bag?"),
            ("Amoeba Music", "Daniel Lanois | What's in My Bag? (Teaser)", "Daniel Lanois — What's In My Bag?"),
            ("Pitchfork", "Audrey Hobert Rates Podcasts, Don Toliver, and Disney Adults | Pitchfork", "Audrey Hobert — Over/Under"),
        ]

        for channel, title, expected in examples:
            with self.subTest(title=title):
                self.assertEqual(display_title(title, CHANNELS[channel]), expected)

    def test_title_outside_the_pattern_is_kept_as_is(self):
        from channels import CHANNELS
        from titles import display_title

        title = "KEXP Holiday Special 2026"
        self.assertEqual(display_title(title, CHANNELS["KEXP"]), title)
        self.assertEqual(display_title(title, {}), title)

    def test_la_blogotheque_keeps_only_complete_sessions(self):
        from channels import CHANNELS

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        uploads = {
            "full_take_away": "Naomi Greene | A Take Away Show",
            "full_live_session": "Adèle Castillon | Live Session for The Collective by Stradivarius",
            "fragment_live_session": "Rostam - The Road to Death | Live Session",
            "fragment_take_away": "Voxtrot - Trouble | A Take Away Show",
            "festival": "Thylacine | Live at @arteconcert Festival 2022 (Paris)",
            "series": "Peter Broderick | The Sounds of Ireland",
        }
        playlist_response = {"items": [
            {"snippet": {"title": title, "publishedAt": recent, "resourceId": {"videoId": video_id}}}
            for video_id, title in uploads.items()
        ]}

        with patch.object(collector, "fetch_playlist_page", return_value=playlist_response), \
            patch.object(collector, "fetch_video_durations", side_effect=lambda ids: {video_id: 900 for video_id in ids}):
            feed = collector.get_feed("La Blogothèque", CHANNELS["La Blogothèque"])

        self.assertEqual(
            sorted(video["video_id"] for video in feed),
            ["full_live_session", "full_take_away"],
        )

    def test_email_shows_the_standardized_title(self):
        from newsletter import generate_html

        html = generate_html([{
            "channel": "KEXP",
            "title": "Death Cab For Cutie - Full Performance (Live on KEXP)",
            "display_title": "Death Cab For Cutie — Live on KEXP",
            "link": "https://www.youtube.com/watch?v=x",
        }], date(2026, 8, 28))

        self.assertIn("Death Cab For Cutie — Live on KEXP", html)
        self.assertNotIn("Full Performance", html)

    def test_compound_names_are_split_and_accents_removed(self):
        from genres import artist_candidates

        self.assertEqual(
            artist_candidates("Hélio Ziskind e Fera Neném"),
            [
                "Hélio Ziskind e Fera Neném", "Helio Ziskind e Fera Nenem",
                "Hélio Ziskind", "Helio Ziskind", "Fera Neném", "Fera Nenem",
            ],
        )
        self.assertEqual(
            artist_candidates("Scott Ian of Anthrax"),
            ["Scott Ian of Anthrax", "Scott Ian", "Anthrax"],
        )

    def test_only_tags_that_are_genres_are_used(self):
        from genres import pick_genre

        self.assertEqual(pick_genre([
            ("motherfuckin rabbits ejaculating sunshine", 100),
            ("brazilian", 90),
            ("saxophone", 80),
            ("seen live", 70),
            ("Indie Rock", 60),
        ]), "indie rock")
        self.assertEqual(pick_genre([("Alt-country", 100)]), "alt-country")
        self.assertIsNone(pick_genre([("french", 100), ("jazz", 2)]))

    def add_genres(self, videos, overrides=None, cache=None, **patches):
        import genres

        if overrides is not None:
            genres.save_json(overrides, self.overrides_path)
        if cache is not None:
            genres.save_json(cache, self.cache_path)

        channels = {"KEXP": {"artist_patterns": [r"^(?P<artist>.+?)\s+-\s+Full Performance"]}}

        with patch.dict("os.environ", {"LASTFM_API_KEY": "key"}), \
            patch.object(genres.lastfm, "get_artist_tags", **patches.get("lastfm", {"return_value": []})) as lastfm_tags, \
            patch.object(genres.collector, "fetch_video_topics", **patches.get("youtube", {"return_value": {}})):
            genres.add_genres(videos, channels, self.cache_path, self.overrides_path)

        return lastfm_tags

    def video(self, artist="Wednesday"):
        return {
            "channel": "KEXP",
            "title": f"{artist} - Full Performance (Live on KEXP)",
            "video_id": "abc",
        }

    def test_lastfm_genre_is_used_and_cached(self):
        import genres

        video = self.video()
        self.add_genres([video], lastfm={"return_value": [("shoegaze", 100)]})

        self.assertEqual(video["genre"], "shoegaze")
        self.assertEqual(genres.load_json(self.cache_path), {"wednesday": "shoegaze"})

    def test_cached_genre_skips_lastfm(self):
        video = self.video()
        lastfm_tags = self.add_genres([video], cache={"wednesday": "indie rock"})

        self.assertEqual(video["genre"], "indie rock")
        lastfm_tags.assert_not_called()

    def test_manual_override_wins_and_empty_override_hides_the_badge(self):
        corrected, hidden = self.video("Wednesday"), self.video("Rostam")
        self.add_genres(
            [corrected, hidden],
            overrides={"WEDNESDAY": "indie rock", "Rostam": ""},
            cache={"wednesday": "shoegaze"},
            youtube={"return_value": {"abc": ["https://en.wikipedia.org/wiki/Pop_music"]}},
        )

        self.assertEqual(corrected["genre"], "indie rock")
        self.assertIsNone(hidden["genre"])

    def test_youtube_topic_is_the_fallback(self):
        video = self.video()
        self.add_genres([video], youtube={"return_value": {"abc": [
            "https://en.wikipedia.org/wiki/Music",
            "https://en.wikipedia.org/wiki/Rock_music",
        ]}})

        self.assertEqual(video["genre"], "rock")

    def test_failures_leave_videos_without_badge(self):
        video = self.video()
        self.add_genres(
            [video],
            lastfm={"side_effect": RuntimeError("offline")},
            youtube={"side_effect": RuntimeError("quota")},
        )

        self.assertIsNone(video["genre"])

    def test_beyond_the_stage_videos_are_not_looked_up(self):
        video = {
            "channel": "KEXP",
            "section": "extras",
            "title": "Wednesday - Full Performance (Live on KEXP)",
            "video_id": "abc",
        }
        lastfm_tags = self.add_genres([video], youtube={"return_value": {"abc": [
            "https://en.wikipedia.org/wiki/Rock_music",
        ]}})

        self.assertIsNone(video["genre"])
        lastfm_tags.assert_not_called()

    def test_beyond_the_stage_videos_never_show_a_badge(self):
        from newsletter import generate_html

        html = generate_html([
            {"channel": "KEXP", "title": "Live Video", "link": "https://www.youtube.com/watch?v=x", "genre": "folk"},
            {"channel": "Amoeba Music", "section": "extras", "title": "Bag Video",
             "link": "https://www.youtube.com/watch?v=y", "genre": "new wave"},
        ], date(2026, 8, 28))

        self.assertIn("&nbsp;Folk&nbsp;</span>", html)
        self.assertNotIn("New wave", html)

    def test_genre_badge_is_rendered_before_the_link(self):
        from newsletter import generate_html

        video = {"channel": "KEXP", "title": "Live Video", "link": "https://www.youtube.com/watch?v=x"}
        with_genre = generate_html([dict(video, genre="mpb")], date(2026, 8, 28))
        without_genre = generate_html([dict(video, genre=None)], date(2026, 8, 28))

        self.assertIn("&nbsp;MPB&nbsp;</span>", with_genre)
        self.assertLess(with_genre.index("MPB"), with_genre.index("Watch performance"))
        self.assertNotIn("<span", without_genre)

    def test_genre_formatting(self):
        from newsletter import format_genre

        self.assertEqual(format_genre("indie rock"), "Indie rock")
        self.assertEqual(format_genre("r&b"), "R&B")
        self.assertEqual(format_genre("alt-country"), "Alt-country")



class StreamingLinksTests(unittest.TestCase):
    def response(self, data):
        from unittest.mock import Mock

        return Mock(json=Mock(return_value=data), raise_for_status=Mock())

    def test_apple_music_ignores_other_versions_and_artists(self):
        import streaming_links

        results = {"results": [
            {"artistName": "A$AP Rocky", "trackName": "Life Is", "trackViewUrl": "https://wrong"},
            {"artistName": "Jessica Pratt", "trackName": "Life Is (Live)", "trackViewUrl": "https://live"},
            {"artistName": "Jessica Pratt", "trackName": "Life Is (feat. Someone)", "trackViewUrl": "https://studio"},
        ]}

        with patch.object(streaming_links.requests, "get", return_value=self.response(results)):
            self.assertEqual(streaming_links.find_apple_music("Jessica Pratt", "Life Is"), "https://studio")

        with patch.object(streaming_links.requests, "get", return_value=self.response({"results": results["results"][:2]})):
            self.assertIsNone(streaming_links.find_apple_music("Jessica Pratt", "Life Is"))

    def test_apple_music_removes_tracking_parameter(self):
        import streaming_links

        results = {"results": [{
            "artistName": "Jessica Pratt",
            "trackName": "Life Is",
            "trackViewUrl": "https://music.apple.com/us/album/life-is/1?i=2&uo=4",
        }]}

        with patch.object(streaming_links.requests, "get", return_value=self.response(results)):
            self.assertEqual(
                streaming_links.find_apple_music("Jessica Pratt", "Life Is"),
                "https://music.apple.com/us/album/life-is/1?i=2",
            )

    def test_youtube_music_only_accepts_topic_channel(self):
        import streaming_links

        items = {"items": [
            {"id": {"videoId": "fan"}, "snippet": {"channelTitle": "Some Fan", "title": "Life Is"}},
            {"id": {"videoId": "official"}, "snippet": {"channelTitle": "Jessica Pratt - Topic", "title": "Life Is"}},
        ]}

        with patch.dict("os.environ", {"YOUTUBE_API_KEY": "key"}), \
            patch.object(streaming_links.requests, "get", return_value=self.response(items)):
            self.assertEqual(
                streaming_links.find_youtube_music("Jessica Pratt", "Life Is"),
                "https://music.youtube.com/watch?v=official",
            )

    def test_failures_fall_back_to_search_links(self):
        import streaming_links

        with patch.object(streaming_links, "find_apple_music", side_effect=RuntimeError("offline")), \
            patch.object(streaming_links, "find_youtube_music", return_value=None):
            links = streaming_links.get_streaming_links("Jessica Pratt", "Life Is")

        self.assertEqual(links, {
            "spotify": "https://open.spotify.com/search/Jessica%20Pratt%20Life%20Is",
            "apple_music": "https://music.apple.com/search?term=Jessica+Pratt+Life+Is",
            "youtube_music": "https://music.youtube.com/search?q=Jessica+Pratt+Life+Is",
        })

    def test_direct_links_replace_search_links(self):
        import streaming_links

        with patch.object(streaming_links, "find_apple_music", return_value="https://apple"), \
            patch.object(streaming_links, "find_youtube_music", return_value="https://ytm"):
            links = streaming_links.get_streaming_links("Artist", "Song")

        self.assertEqual(links["apple_music"], "https://apple")
        self.assertEqual(links["youtube_music"], "https://ytm")
        self.assertTrue(links["spotify"].startswith("https://open.spotify.com/search/"))


if __name__ == "__main__":
    unittest.main()
