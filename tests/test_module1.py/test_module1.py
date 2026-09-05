import os
import re
import secrets
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash


# Keep the test database isolated from every developer or Render database.
_test_directory = tempfile.TemporaryDirectory(prefix="nexus-module1-")
_test_password = secrets.token_urlsafe(16)
os.environ["DATABASE_URL"] = (
    f"sqlite:///{Path(_test_directory.name) / 'module1.sqlite'}"
)
os.environ["NEXUS_AUTO_CREATE_DB"] = "1"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["TURNSTILE_SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["TURNSTILE_SITE_KEY"] = secrets.token_urlsafe(16)
os.environ["RENDER"] = ""

from app import PlaySession, User, UserActivity, app, db, hash_play_token, utc_now  # noqa: E402


class FakeTurnstileResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("fake Siteverify failure")

    def json(self):
        return self.payload


class ModuleOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)

    def setUp(self):
        with app.app_context():
            db.drop_all()
            db.create_all()
        self.client = app.test_client()
        self.csrf_token = self._csrf_token()

    def tearDown(self):
        with app.app_context():
            db.session.remove()

    def _csrf_token(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        match = re.search(
            rb'<meta name="csrf-token" content="([^"]+)"',
            response.data,
        )
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def _json_headers(self):
        return {
            "Content-Type": "application/json",
            "X-CSRFToken": self.csrf_token,
        }

    def _create_user(self, email="player@example.com", password=None):
        password = password or _test_password
        with app.app_context():
            user = User(
                name="Test Player",
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user_id
        return user_id

    def _signup_payload(self, email="new-player@example.com", token="valid-token"):
        return {
            "name": "New Player",
            "email": email,
            "password": _test_password,
            "confirm_password": _test_password,
            "turnstile_token": token,
        }

    @patch("app.requests.post")
    def test_signup_success_and_database_duplicate_protection(self, siteverify):
        siteverify.return_value = FakeTurnstileResponse({"success": True})
        payload = self._signup_payload()

        first = self.client.post(
            "/api/register",
            json=payload,
            headers=self._json_headers(),
        )
        second = self.client.post(
            "/api/register",
            json=payload,
            headers=self._json_headers(),
        )

        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json["ok"])
        self.assertTrue(first.json["turnstile_reset"])
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json["message"], "Account already exists.")
        with app.app_context():
            self.assertEqual(User.query.count(), 1)

    @patch("app.requests.post")
    def test_missing_turnstile_fails_without_siteverify_call(self, siteverify):
        response = self.client.post(
            "/api/register",
            json=self._signup_payload(token=""),
            headers=self._json_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json["message"],
            "Security check failed or expired. Please complete it again.",
        )
        siteverify.assert_not_called()

    @patch("app.requests.post")
    def test_expired_turnstile_can_be_retried(self, siteverify):
        siteverify.side_effect = [
            FakeTurnstileResponse(
                {"success": False, "error-codes": ["timeout-or-duplicate"]}
            ),
            FakeTurnstileResponse({"success": True}),
        ]

        expired = self.client.post(
            "/api/register",
            json=self._signup_payload(
                email="retry@example.com",
                token="expired-token",
            ),
            headers=self._json_headers(),
        )
        retry = self.client.post(
            "/api/register",
            json=self._signup_payload(
                email="retry@example.com",
                token="fresh-token",
            ),
            headers=self._json_headers(),
        )

        self.assertEqual(expired.status_code, 400)
        self.assertTrue(expired.json["turnstile_reset"])
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(siteverify.call_count, 2)

    @patch("app.requests.post")
    def test_turnstile_timeout_returns_safe_retry_message(self, siteverify):
        import requests

        siteverify.side_effect = requests.Timeout()
        response = self.client.post(
            "/api/register",
            json=self._signup_payload(email="timeout@example.com"),
            headers=self._json_headers(),
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json["message"],
            "Security check is temporarily unavailable. Please try again.",
        )

    @patch("app.requests.post")
    def test_turnstile_unexpected_payload_returns_safe_retry_message(self, siteverify):
        siteverify.return_value = FakeTurnstileResponse(["unexpected"])
        response = self.client.post(
            "/api/register",
            json=self._signup_payload(email="unexpected@example.com"),
            headers=self._json_headers(),
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json["message"],
            "Security check is temporarily unavailable. Please try again.",
        )

    @patch("app.requests.post")
    def test_missing_turnstile_secret_fails_without_siteverify_call(self, siteverify):
        with patch.dict(os.environ, {"TURNSTILE_SECRET_KEY": ""}):
            response = self.client.post(
                "/api/register",
                json=self._signup_payload(email="no-secret@example.com"),
                headers=self._json_headers(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json["message"],
            "Security check is temporarily unavailable. Please try again.",
        )
        siteverify.assert_not_called()

    def test_existing_public_and_auth_routes_remain_available(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/games").status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)

    @patch("app.requests.post")
    def test_browser_cookie_requests_require_csrf(self, siteverify):
        siteverify.return_value = FakeTurnstileResponse({"success": True})
        response = self.client.post(
            "/api/register",
            json=self._signup_payload(email="csrf@example.com"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json["message"],
            "Your session expired. Refresh the page and try again.",
        )
        siteverify.assert_not_called()

    def test_login_dashboard_logout_and_daily_reward(self):
        self._create_user()
        login = self.client.post(
            "/api/login",
            json={"email": "player@example.com", "password": _test_password},
            headers=self._json_headers(),
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        first_reward = self.client.post(
            "/api/daily-reward",
            json={},
            headers=self._json_headers(),
        )
        second_reward = self.client.post(
            "/api/daily-reward",
            json={},
            headers=self._json_headers(),
        )
        self.assertEqual(first_reward.status_code, 200)
        self.assertTrue(first_reward.json["claimed"])
        self.assertEqual(second_reward.status_code, 200)
        self.assertFalse(second_reward.json["claimed"])

        with app.app_context():
            user = User.query.one()
            self.assertEqual(user.total_xp, 25)
            self.assertEqual(UserActivity.query.count(), 1)

        self.assertEqual(self.client.get("/logout").status_code, 302)
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)

    def test_neon_runner_session_accepts_one_score_only(self):
        self._create_user()
        start = self.client.post(
            "/api/play/neon-runner/start",
            json={"game": "neon-runner"},
            headers=self._json_headers(),
        )
        self.assertEqual(start.status_code, 201)
        token = start.json["session_token"]

        score = self.client.post(
            "/api/play/neon-runner/score",
            json={"session_token": token, "score": 0},
            headers=self._json_headers(),
        )
        duplicate = self.client.post(
            "/api/play/neon-runner/score",
            json={"session_token": token, "score": 0},
            headers=self._json_headers(),
        )

        self.assertEqual(score.status_code, 200)
        self.assertEqual(duplicate.status_code, 409)
        with app.app_context():
            session = PlaySession.query.one()
            self.assertEqual(session.status, "completed")
            self.assertEqual(UserActivity.query.count(), 1)

    def test_neon_runner_rejects_implausible_score_but_keeps_run_retryable(self):
        self._create_user()
        start = self.client.post(
            "/api/play/neon-runner/start",
            json={"game": "neon-runner"},
            headers=self._json_headers(),
        )
        token = start.json["session_token"]

        invalid = self.client.post(
            "/api/play/neon-runner/score",
            json={"session_token": token, "score": 1_000_001},
            headers=self._json_headers(),
        )
        valid = self.client.post(
            "/api/play/neon-runner/score",
            json={"session_token": token, "score": 0},
            headers=self._json_headers(),
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)

    def test_expired_neon_runner_session_is_rejected(self):
        self._create_user()
        start = self.client.post(
            "/api/play/neon-runner/start",
            json={"game": "neon-runner"},
            headers=self._json_headers(),
        )
        token = start.json["session_token"]
        with app.app_context():
            play_session = PlaySession.query.one()
            play_session.expires_at = utc_now() - timedelta(seconds=1)
            db.session.commit()

        response = self.client.post(
            "/api/play/neon-runner/score",
            json={"session_token": token, "score": 0},
            headers=self._json_headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.json["message"])

    def test_active_template_has_one_shared_main_script_and_one_signup_listener(self):
        root = Path(__file__).resolve().parents[1]
        index_template = (root / "templates/index.html").read_text()
        base_template = (root / "templates/base.html").read_text()
        main_script = (root / "static/js/main.js").read_text()

        self.assertEqual(index_template.count("filename='js/main.js'"), 1)
        self.assertEqual(base_template.count("filename='js/main.js'"), 1)
        self.assertEqual(
            main_script.count('signupForm?.addEventListener("submit"'),
            1,
        )
        self.assertEqual(main_script.count('loginForm?.addEventListener("submit"'), 1)


if __name__ == "__main__":
    unittest.main()
