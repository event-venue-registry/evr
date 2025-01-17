"""Tests for data integrity."""

import tempfile
import unittest
from pathlib import Path

from evr import Venue, load_venues
from evr.model import COLUMNS, VENUES_PATH, append_venue

CHARLIE_ORCID = "0000-0003-4423-4370"

TEST_LONG = 1.234
TEST_LAT = 5.678
TEST_VENUE = Venue(
    id="0000000",
    name="Test Venue",
    country="DE",
    city_geonames="2946447",  # bonn
    address="Kaiserplatz 1, Bonn 53121, Germany",
    latitude=TEST_LAT,
    longitude=TEST_LONG,
    date="2025-01-17",
    creator=CHARLIE_ORCID,
)


class TestIntegrity(unittest.TestCase):
    """Tests for data integrity."""

    def test_columns(self) -> None:
        """Test the columns in the curated file are in sync."""
        with VENUES_PATH.open() as file:
            header = next(file).strip().split("\t")
        self.assertEqual(COLUMNS, header)

    def test_load(self) -> None:
        """Test loading venues works."""
        venues = {v.id: v for v in load_venues()}
        self.assertIn("0000001", venues)
        self.assertEqual("Cultural Center Altinate/San Gaetano", venues["0000001"].name)

    def test_model_dump(self) -> None:
        """Test that longitude and latitude are dumped properly."""
        self.assertEqual(TEST_LAT, TEST_VENUE.latitude)
        self.assertEqual(TEST_LONG, TEST_VENUE.longitude)

        data = TEST_VENUE.model_dump()
        self.assertIn("longitude", data)
        self.assertIn("latitude", data)
        self.assertEqual(TEST_LONG, data["longitude"])
        self.assertEqual(TEST_LAT, data["latitude"])

    def test_append(self) -> None:
        """Test appending a record."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).joinpath("test.tsv")
            with path.open("w") as file:
                print(*COLUMNS, sep="\t", file=file)

            append_venue(TEST_VENUE, path=path)

            venues = load_venues(path=path)
            self.assertEqual(1, len(venues))
