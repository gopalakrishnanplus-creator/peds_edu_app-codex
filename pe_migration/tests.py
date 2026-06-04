from __future__ import annotations

from django.test import SimpleTestCase

from .services import (
    canonical_uuid_from_row,
    normalize_campaign_id,
    normalize_content_code,
    normalize_email,
    normalize_name,
    normalize_phone,
)


class PeV2NormalizationTests(SimpleTestCase):
    def test_campaign_ids_compare_after_hyphen_removal_and_lowercase(self) -> None:
        dashed = "25ff17cd-9dac-4539-9608-6f18d6aa4d73"
        compact = "25FF17CD9DAC453996086F18D6AA4D73"

        self.assertEqual(normalize_campaign_id(dashed), normalize_campaign_id(compact))

    def test_phone_email_name_and_content_normalization(self) -> None:
        self.assertEqual(normalize_phone("+91 98765-43210"), "9876543210")
        self.assertEqual(normalize_email(" Doctor@Example.COM "), "doctor@example.com")
        self.assertEqual(normalize_name(" Dr.  Aarav   Menon "), "aarav menon")
        self.assertEqual(normalize_content_code(" VID_ABC_01 "), "vid_abc_01")

    def test_numeric_master_ids_are_not_promoted_to_canonical_uuid_for_people(self) -> None:
        self.assertIsNone(canonical_uuid_from_row({"id": 15}, "field_rep", "15"))
        self.assertIsNone(canonical_uuid_from_row({"id": 42}, "doctor", "42"))

    def test_campaign_id_can_be_canonical_campaign_uuid(self) -> None:
        campaign_id = "25ff17cd9dac453996086f18d6aa4d73"

        self.assertEqual(
            canonical_uuid_from_row({"id": campaign_id}, "campaign", campaign_id),
            campaign_id,
        )
