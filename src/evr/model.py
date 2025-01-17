"""A data model and loader for event venues."""

import csv
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Latitude, Longitude
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2
from semantic_pydantic import SemanticField
from tqdm.auto import tqdm

from evr.data import VENUES_PATH

__all__ = [
    "Venue",
    "append_venue",
    "load_venues",
]

COLUMNS = [
    "id",
    "name",
    "local_name",
    "lang",
    "country",
    "city_label",
    "city_geonames",
    "latitude",
    "longitude",
    "wikidata",
    "osm_way",
    "address",
    "creator",
    "date",
    "homepage",
]


class Venue(BaseModel):
    """A model for an event venue."""

    id: str = Field(..., pattern="^\\d{7}$", description="The EVR numeric identifier")
    name: str = Field(..., description="An english name for the venue")
    local_name: str | None = Field(None, description="The non-english local name for the venue")
    lang: LanguageAlpha2 | None = Field(
        None, description="The language of the non-english local name for the venue"
    )
    country: CountryAlpha2 = Field(..., description="A two letter country code")
    city_geonames: str = SemanticField(prefix="geonames")  # type:ignore[assignment]
    city_label: str | None = Field(None, description="The label for the city")
    latitude: Latitude = Field(..., description="The latitude of the venue")
    longitude: Longitude = Field(..., description="The longitude of the venue")
    wikidata: str | None = SemanticField(default=None, prefix="wikidata")  # type:ignore[assignment]
    osm_way: str | None = Field(None, description="A link to the OSM Way record")
    address: str = Field(..., description="The street address for the venue, ideally in english")
    creator: str = SemanticField(prefix="orcid")  # type:ignore[assignment]
    date: str = Field(
        ...,
        pattern="^\\d{4}-\\d{2}-\\d{2}$",
        description="A date in YYYY-MM-DD format when the venue was added to the registry",
    )
    homepage: str | None = Field(
        None, description="The homepage for the venue, ideally in english, if available"
    )

    @property
    def google_maps_link(self) -> str:
        """Get a google maps link."""
        return f"https://maps.google.com/?q={self.latitude},{self.longitude}"


def load_venues(*, path: Path | None = None, show_progress: bool = False) -> list[Venue]:
    """Load venues curated in EVR."""
    if path is None:
        path = VENUES_PATH
    rv = []
    with path.open() as file:
        reader = csv.DictReader(file, delimiter="\t")
        for data in tqdm(reader, unit="venue", disable=not show_progress):
            data = {k: v for k, v in data.items() if k and v}
            venue = Venue.model_validate(data)
            rv.append(venue)
    return rv


def append_venue(venue: Venue, *, path: Path | None = None) -> None:
    """Append a venue."""
    if path is None:
        path = VENUES_PATH
    data = venue.model_dump()
    with path.open("a") as out_file:
        print(*(data[column] or "" for column in COLUMNS), sep="\t", file=out_file)
