from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from publisher.campaign_auth import (
    FORM_ACCESS_TOKEN_FIELD,
    get_publisher_claims,
    make_campaign_form_access_token,
    publisher_required,
)
from publisher.forms import DoctorRecordForm, FieldRepRecordForm, MasterCampaignRecordForm


class DoctorRecordFormTests(SimpleTestCase):
    def test_accepts_master_schema_sized_values(self) -> None:
        form = DoctorRecordForm(
            data={
                "first_name": "Aarav",
                "last_name": "Menon",
                "email": "doctor.demo@pedsedu.local",
                "whatsapp_no": "919876543210",
                "clinic_name": "L" * 150,
                "clinic_phone": "02041234567",
                "clinic_appointment_number": "02041234567",
                "clinic_address": "123 Demo Street",
                "postal_code": "411001",
                "state": "Maharashtra",
                "district": "Pune",
                "receptionist_whatsapp_number": "919980011223",
                "imc_registration_number": "123456789012345678901234567890",
                "field_rep_id": "FR-DEMO-001",
                "recruited_via": "FIELD_REP_IMPORTER",
                "clinic_user1_name": "Front Desk",
                "clinic_user1_email": "frontdesk.demo@pedsedu.local",
                "clinic_user2_name": "",
                "clinic_user2_email": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)


class FieldRepRecordFormTests(SimpleTestCase):
    def test_accepts_master_schema_sized_values(self) -> None:
        form = FieldRepRecordForm(
            data={
                "full_name": "A" * 230,
                "phone_number": "919876543210",
                "brand_supplied_field_rep_id": "F" * 80,
                "state": "Maharashtra",
                "is_active": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)


class MasterCampaignRecordFormTests(SimpleTestCase):
    def test_accepts_master_campaign_schema_values(self) -> None:
        form = MasterCampaignRecordForm(
            data={
                "name": "Asthma Care Spring 2026",
                "num_doctors_supported": 25,
                "add_to_campaign_message": "Hello doctor",
                "register_message": "Welcome to the campaign",
                "banner_small_url": "https://example.com/small.png",
                "banner_large_url": "https://example.com/large.png",
                "banner_target_url": "https://example.com/landing",
                "brand_id": 7,
                "system_pe": "on",
                "start_date": "2026-04-11",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)


class PublisherCampaignAuthTests(SimpleTestCase):
    def test_staff_user_can_open_campaign_step_with_stale_token(self) -> None:
        request = RequestFactory().get(
            "/add-campaign-details/?campaign-id=abc123&token=expired-token"
        )
        request.session = {}
        request.user = SimpleNamespace(
            pk=1,
            email="admin@pedsedu.local",
            is_authenticated=True,
            is_staff=True,
            is_superuser=True,
        )

        @publisher_required
        def protected_view(request):
            return HttpResponse("ok")

        response = protected_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @override_settings(
        PUBLISHER_TRUST_VERIFIED_SSO=True,
        SSO_EXPECTED_ISSUER="project1",
        SSO_EXPECTED_AUDIENCE="project2",
        SSO_SESSION_KEY_IDENTITY="sso_identity",
        SSO_SESSION_KEY_CAMPAIGN="campaign_id",
    )
    def test_campaign_form_token_authorizes_post_when_session_claims_are_missing(self) -> None:
        campaign_id = "dc54892f-1410-4eea-b371-32c25309c604"
        token = make_campaign_form_access_token(
            campaign_id,
            {
                "sub": "publisher_1",
                "username": "khushan.poptani",
                "roles": ["publisher"],
                "iss": "project1",
                "aud": "project2",
                "email": "khushan.poptani@inditech.co.in",
            },
        )
        request = RequestFactory().post(
            f"/add-campaign-details/?campaign-id={campaign_id}",
            {"campaign_id": campaign_id, FORM_ACCESS_TOKEN_FIELD: token},
        )
        request.session = {}
        request.user = SimpleNamespace(is_authenticated=False)

        @publisher_required
        def protected_view(request):
            return HttpResponse("ok")

        response = protected_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(request.session["campaign_id"], campaign_id)
        self.assertEqual(
            request.session["sso_identity"]["email"],
            "khushan.poptani@inditech.co.in",
        )

    @override_settings(
        PUBLISHER_TRUST_VERIFIED_SSO=True,
        SSO_EXPECTED_ISSUER="project1",
        SSO_EXPECTED_AUDIENCE="project2",
        SSO_SESSION_KEY_IDENTITY="sso_identity",
        SSO_SESSION_KEY_CAMPAIGN="campaign_id",
    )
    @patch("publisher.campaign_auth.master_db.authorized_publisher_exists", return_value=False)
    def test_verified_rfa_sso_identity_is_authorized_without_local_allowlist(self, authorized_mock) -> None:
        request = RequestFactory().get("/publisher-landing-page/")
        request.session = {
            "sso_identity": {
                "sub": "publisher_1",
                "username": "khushan.poptani",
                "roles": ["publisher"],
                "iss": "project1",
                "aud": "project2",
                "email": "khushan.poptani@inditech.co.in",
            },
            "campaign_id": "dc54892f-1410-4eea-b371-32c25309c604",
        }
        request.user = SimpleNamespace(is_authenticated=False)

        claims = get_publisher_claims(request)

        self.assertIsNotNone(claims)
        self.assertEqual(claims["email"], "khushan.poptani@inditech.co.in")
        authorized_mock.assert_not_called()


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
)
class PERecordsLoginFlowTests(SimpleTestCase):
    @patch("publisher.views.authenticate")
    def test_superuser_can_open_pe_records_session(self, authenticate_mock) -> None:
        mock_user = SimpleNamespace(
            pk=7,
            email="will.superuser@pedsedu.local",
            is_authenticated=True,
            is_active=True,
            is_superuser=True,
        )
        authenticate_mock.return_value = mock_user
        response = self.client.post(
            reverse("publisher:pe_records_login"),
            {"email": mock_user.email, "password": "Admin123!"},
        )

        self.assertRedirects(response, reverse("publisher:pe_records_dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.session.get("pe_records_user_id"), mock_user.pk)

    @patch("publisher.views.authenticate")
    def test_regular_user_is_rejected_from_pe_records_login(self, authenticate_mock) -> None:
        mock_user = SimpleNamespace(
            pk=8,
            email="publisher.user@pedsedu.local",
            is_authenticated=True,
            is_active=True,
            is_superuser=False,
        )
        authenticate_mock.return_value = mock_user
        response = self.client.post(
            reverse("publisher:pe_records_login"),
            {"email": mock_user.email, "password": "Publisher123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only a system superuser can access the PE records dashboard.")
        self.assertIsNone(self.client.session.get("pe_records_user_id"))
