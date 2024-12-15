"""A data model and loader for event venues."""

import csv
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Latitude, Longitude
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2
from semantic_pydantic import SemanticField
from tqdm.auto import tqdm

__all__ = [
    "Venue",
    "load_venues",
]

HERE = Path(__file__).parent.resolve()
VENUES_PATH = HERE.joinpath("venues.tsv")


class Venue(BaseModel):
    """A model for an event venue."""

    id: str = Field(..., pattern="^\\d{7}$")
    name: str = Field(..., description="An english name for the venue")
    local_name: str | None = Field(None, description="The non-english local name for the venue")
    lang: LanguageAlpha2 | None = Field(
        None, description="The language of the non-english local name for the venue"
    )
    country: CountryAlpha2
    city_geonames: str = SemanticField(prefix="geonames")
    latitude: Latitude
    longitude: Longitude
    wikidata: str | None = SemanticField(default=None, prefix="wikidata")
    osm_way: str | None = Field(None)
    address: str
    creator: str = SemanticField(prefix="orcid")
    date: str = Field(
        ..., pattern="^\\d{4}-\\d{2}-\\d{2}$", description="A date in YYYY-MM-DD format"
    )
    homepage: str | None = Field(None)

    @property
    def google_maps_link(self) -> str:
        """Get a google maps link."""
        return f"https://maps.google.com/?q={self.latitude},{self.longitude}"


def load_venues(*, path: Path | None = None) -> list[Venue]:
    """Load venues curated in EVR."""
    if path is None:
        path = VENUES_PATH
    rv = []
    with path.open() as file:
        reader = csv.DictReader(file, delimiter="\t")
        for data in tqdm(reader, unit="venue"):
            data = {k: v for k, v in data.items() if k and v}
            venue = Venue.model_validate(data)
            rv.append(venue)
    return rv
