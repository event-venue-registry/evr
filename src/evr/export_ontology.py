"""A data model and export scripts for EVR."""

from __future__ import annotations

from pathlib import Path

import click
from pyobo import Reference, Term, TypeDef
from pyobo.ssg import make_site
from pyobo.struct import make_ad_hoc_ontology
from pyobo.struct.typedef import exact_match

from evr import Venue
from evr.model import load_venues

__all__ = [
    "main",
]

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.resolve()
OUTPUT = ROOT.joinpath("output")
OUTPUT.mkdir(exist_ok=True)
ONTOLOGY_OBO_PATH = OUTPUT.joinpath("venues.obo")
ONTOLOGY_TTL_PATH = OUTPUT.joinpath("venues.ttl")
ONTOLOGY_OWL_PATH = OUTPUT.joinpath("venues.owl")

HTML_DIRECTORY = ROOT.joinpath("docs")

PREFIX = "evr"
BASE_IRI = "https://w3id.org/evr/venue/"
ONTOLOGY_IRI = "https://w3id.org/evr/evr.ttl"

CONFERENCE_VENUE_TERM = Term.from_triple("ENVO", "03501127", name="conference venue")
CONFERENCE_CITY_TERM = Term.from_triple("ENVO", "00000856", name="city")

LOCATED_IN = TypeDef(
    reference=Reference(prefix="RO", identifier="0001025", name="located in"),
)
HAS_LATITUDE = TypeDef(
    reference=Reference(prefix="wgs84", identifier="latititude"),
    range=Reference(prefix="xsd", identifier="decimal"),
    is_metadata_tag=True,
)
# .append_equivalent(Reference(prefix="schema", identifier="latitude")))

HAS_LONGITUDE = TypeDef(
    reference=Reference(prefix="wgs84", identifier="longitude"),
    range=Reference(prefix="xsd", identifier="decimal"),
    is_metadata_tag=True,
)
# .append_equivalent(Reference(prefix="schema", identifier="longitude"))

HAS_ADDRESS = TypeDef(
    reference=Reference(prefix="schema", identifier="streetAddress"),
    is_metadata_tag=True,
)

HAS_HOMEPAGE = TypeDef(
    reference=Reference(prefix="foaf", identifier="homepage"),
    is_metadata_tag=True,
)


def get_terms() -> list[Term]:
    """Get PyOBO terms."""
    from pyobo.struct import CHARLIE_TERM, HUMAN_TERM

    rv: list[Term] = [CONFERENCE_VENUE_TERM, HUMAN_TERM, CHARLIE_TERM, CONFERENCE_CITY_TERM]
    venues = load_venues()
    rv.extend(_get_term(t) for t in venues)

    cities = {}
    contributors = {}
    for venue in venues:
        if venue.city_geonames not in cities:
            cities[venue.city_geonames] = Term(
                reference=Reference(
                    prefix="geonames", identifier=venue.city_geonames, name=venue.city_label
                ),
                type="Instance",
            ).append_parent(CONFERENCE_CITY_TERM)

        if venue.creator:
            contributors[venue.creator] = Term(
                reference=Reference(prefix="orcid", identifier=venue.creator), type="Instance"
            ).append_parent(HUMAN_TERM)

    rv.extend(cities.values())
    rv.extend(contributors.values())
    return rv


def _get_term(venue: Venue) -> Term:
    """Convert a venue into a term."""
    term = Term(
        reference=Reference(prefix="evr", identifier=venue.id, name=venue.name),
        type="Instance",
    )
    term.append_parent(CONFERENCE_VENUE_TERM)
    term.annotate_literal(HAS_ADDRESS, venue.address)
    term.annotate_decimal(HAS_LONGITUDE, venue.longitude)
    term.annotate_decimal(HAS_LATITUDE, venue.latitude)
    term.append_relationship(
        LOCATED_IN,
        Reference(prefix="geonames", identifier=venue.city_geonames, name=venue.city_label),
    )
    term.append_contributor(Reference(prefix="orcid", identifier=venue.creator))
    term.append_see_also_uri(venue.google_maps_link)
    # TODO add OSM to bioregistry! osmw: <https://www.openstreetmap.org/way/> .
    # TODO add exact match for venue.osm_way
    if venue.homepage:
        term.annotate_uri(HAS_HOMEPAGE, venue.homepage)
    if venue.wikidata:
        term.append_exact_match(Reference(prefix="wikidata", identifier=venue.wikidata))
    # TODO if venue.local_name and venue.lang:
    return term


def _get_orcid_name(orcid: str) -> str | None:
    # TODO implement w/ orcid_downloader
    if orcid == "0000-0003-4423-4370":
        return "Charles Tapley Hoyt"
    return None


@click.command()
@click.option("--path", type=Path)
def main(path: Path | None) -> None:
    """Export EVR as an ontology."""
    from pyobo.struct import OBOLiteral
    from pyobo.struct import vocabulary as v
    from pyobo.struct.struct_utils import Annotation

    ontology = make_ad_hoc_ontology(
        PREFIX,
        _name="Event Venue Registry",
        terms=get_terms(),
        _typedefs=[LOCATED_IN, HAS_LONGITUDE, HAS_ADDRESS, HAS_LATITUDE, HAS_HOMEPAGE, exact_match],
        _root_terms=[
            CONFERENCE_CITY_TERM.reference,
            CONFERENCE_VENUE_TERM.reference,
        ],
        _property_values=[
            Annotation(
                v.comment,
                OBOLiteral.string("Built by https://github.com/cthoyt/event-venue-registry"),
            ),
            Annotation(v.has_license, Reference(prefix="spdx", identifier="CCO-1.0")),
        ],
    )
    ontology.write_obo(ONTOLOGY_OBO_PATH)
    ontology.write_rdf(ONTOLOGY_TTL_PATH)

    from bioontologies import robot

    robot.convert(ONTOLOGY_TTL_PATH, ONTOLOGY_OWL_PATH)

    make_site(ontology, HTML_DIRECTORY, manifest=True)


if __name__ == "__main__":
    main()
