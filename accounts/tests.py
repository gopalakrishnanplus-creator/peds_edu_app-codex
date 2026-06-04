from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from accounts import master_db
from accounts.forms import normalize_login_identifier


class LoginIdentifierTests(SimpleTestCase):
    def test_admin_alias_maps_to_local_admin_email(self) -> None:
        self.assertEqual(
            normalize_login_identifier(" admin "),
            "admin@pedsedu.local",
        )

    def test_email_identifier_is_preserved_lowercase(self) -> None:
        self.assertEqual(
            normalize_login_identifier("Admin.User@Example.COM"),
            "admin.user@example.com",
        )


class FieldRepResolverTests(SimpleTestCase):
    def test_external_id_with_trailing_digits_is_not_treated_as_primary_key(self) -> None:
        class FakeOps:
            @staticmethod
            def quote_name(name):
                return f"`{name}`"

        class FakeCursor:
            def __init__(self):
                self.last_row = None
                self.queries = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params=None):
                self.queries.append((sql, list(params or [])))
                if "LOWER(`brand_supplied_field_rep_id`)" in sql:
                    self.last_row = (515, "Kiara Jain", "7294924104", 1, "FR-2026-001")
                elif "WHERE `id` = %s" in sql:
                    self.last_row = (1, "Wrong Rep", "9000000000", 1, "FR01")
                else:
                    self.last_row = None

            def fetchone(self):
                return self.last_row

        class FakeConnection:
            vendor = "mysql"
            ops = FakeOps()

            def __init__(self):
                self.cursor_instance = FakeCursor()

            def cursor(self):
                return self.cursor_instance

        fake_conn = FakeConnection()

        with patch("accounts.master_db.get_master_connection", return_value=fake_conn):
            rep = master_db.get_field_rep("FR-2026-001")

        self.assertIsNotNone(rep)
        self.assertEqual(rep.id, 515)
        self.assertEqual(rep.brand_supplied_field_rep_id, "FR-2026-001")
        self.assertNotIn("Wrong Rep", [rep.full_name])
        self.assertFalse(
            any("WHERE `id` = %s" in sql for sql, _params in fake_conn.cursor_instance.queries)
        )

    def test_enrollment_field_rep_resolution_prefers_campaign_assignment(self) -> None:
        class FakeOps:
            @staticmethod
            def quote_name(name):
                return f"`{name}`"

        class FakeCursor:
            def __init__(self):
                self.last_row = None
                self.queries = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params=None):
                self.queries.append((sql, list(params or [])))
                if "campaign_campaignfieldrep" in sql and "FR-2026-001" in list(params or []):
                    self.last_row = (515,)
                elif "LOWER(`brand_supplied_field_rep_id`)" in sql:
                    self.last_row = (4, "Duplicate Rep", "7294924104", 1, "FR-2026-001")
                else:
                    self.last_row = None

            def fetchone(self):
                return self.last_row

        class FakeConnection:
            vendor = "mysql"
            ops = FakeOps()

            def __init__(self):
                self.cursor_instance = FakeCursor()

            def cursor(self):
                return self.cursor_instance

        fake_conn = FakeConnection()

        with patch("accounts.master_db.get_master_connection", return_value=fake_conn):
            resolved_id = master_db._resolve_registered_by_fieldrep_id(
                fake_conn,
                campaign_id_norm="dc54892f14104eeab37132c25309c604",
                registered_by="FR-2026-001",
            )

        self.assertEqual(resolved_id, 515)
        self.assertTrue(
            fake_conn.cursor_instance.queries[0][0].strip().startswith("SELECT fr.`id`")
        )


class CampaignLookupTests(SimpleTestCase):
    def test_get_campaign_skips_optional_master_columns_that_do_not_exist(self) -> None:
        class FakeOps:
            @staticmethod
            def quote_name(name):
                return f"`{name}`"

        class FakeCursor:
            def __init__(self):
                self.last_row = None
                self.queries = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params=None):
                self.queries.append((sql, list(params or [])))
                self.last_row = (
                    "84eb443406464fb4b61a04721919db3f",
                    12,
                    "WhatsApp intro",
                    "Campaign Name",
                    "",
                    "",
                    "",
                    "https://example.com/banner",
                )

            def fetchone(self):
                return self.last_row

        class FakeConnection:
            vendor = "mysql"
            ops = FakeOps()

            def __init__(self):
                self.cursor_instance = FakeCursor()

            def cursor(self):
                return self.cursor_instance

        fake_conn = FakeConnection()
        master_columns = [
            "id",
            "name",
            "num_doctors_supported",
            "add_to_campaign_message",
            "banner_target_url",
        ]

        with (
            patch("accounts.master_db.get_master_connection", return_value=fake_conn),
            patch("accounts.master_db._get_table_columns", return_value=master_columns),
        ):
            campaign = master_db.get_campaign("84eb4434-0646-4fb4-b61a-04721919db3f")

        self.assertIsNotNone(campaign)
        self.assertEqual(campaign.campaign_id, "84eb443406464fb4b61a04721919db3f")
        self.assertEqual(campaign.doctors_supported, 12)
        self.assertEqual(campaign.wa_addition, "WhatsApp intro")
        self.assertEqual(campaign.new_video_cluster_name, "Campaign Name")
        self.assertEqual(campaign.email_registration, "")
        self.assertEqual(campaign.banner_target_url, "https://example.com/banner")

        sql, params = fake_conn.cursor_instance.queries[-1]
        self.assertEqual(params, ["84eb443406464fb4b61a04721919db3f"])
        self.assertIn("LOWER(REPLACE(`id`, '-', ''))", sql)
        self.assertNotIn("`register_message`", sql)
        self.assertNotIn("`banner_small_url` AS `banner_small_url`", sql)
        self.assertNotIn("`banner_large_url` AS `banner_large_url`", sql)
