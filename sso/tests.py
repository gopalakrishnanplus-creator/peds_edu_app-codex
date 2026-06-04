from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase, override_settings

from sso.views import consume


class DummySession(dict):
    modified = False
    expiry = None

    def set_expiry(self, value):
        self.expiry = value


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _issue_hs256(payload: dict, secret: str) -> str:
    header = {"typ": "JWT", "alg": "HS256"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


@override_settings(
    SSO_SHARED_SECRET="CHANGE-ME-TO-A-LONG-RANDOM-STRING",
    SSO_EXPECTED_ISSUER="project1",
    SSO_EXPECTED_AUDIENCE="project2",
    SSO_SESSION_KEY_IDENTITY="sso_identity",
    SSO_SESSION_KEY_CAMPAIGN="campaign_id",
    SSO_SESSION_AGE_SECONDS=3600,
)
class SSOConsumeTests(SimpleTestCase):
    def test_valid_rfa_dev_token_creates_campaign_session(self) -> None:
        now = int(time.time())
        token = _issue_hs256(
            {
                "iss": "project1",
                "aud": "project2",
                "sub": "publisher_1",
                "username": "khushan.poptani",
                "roles": ["publisher"],
                "iat": now,
                "exp": now + 360,
                "email": "khushan.poptani@inditech.co.in",
            },
            "CHANGE-ME-TO-A-LONG-RANDOM-STRING",
        )
        campaign_id = "dc54892f-1410-4eea-b371-32c25309c604"
        next_url = f"/publisher-landing-page/?campaign-id={campaign_id}"
        request = RequestFactory().get(
            "/sso/consume/",
            {"token": token, "campaign_id": campaign_id, "next": next_url},
        )
        request.session = DummySession()
        request.user = SimpleNamespace(is_authenticated=False)

        response = consume(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(request.session["campaign_id"], campaign_id)
        self.assertEqual(
            request.session["sso_identity"]["email"],
            "khushan.poptani@inditech.co.in",
        )

    def test_logged_in_staff_can_resume_campaign_when_token_is_stale(self) -> None:
        campaign_id = "dc54892f-1410-4eea-b371-32c25309c604"
        next_url = f"/publisher-landing-page/?campaign-id={campaign_id}"
        request = RequestFactory().get(
            "/sso/consume/",
            {"token": "expired-token", "campaign_id": campaign_id, "next": next_url},
        )
        request.session = DummySession()
        request.user = SimpleNamespace(
            pk=1,
            email="admin@pedsedu.local",
            is_authenticated=True,
            is_staff=True,
            is_superuser=True,
        )

        response = consume(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(request.session["campaign_id"], campaign_id)
        self.assertEqual(request.session["sso_identity"]["auth_source"], "django_staff")
