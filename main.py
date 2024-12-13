from pathlib import Path
import csv

from pydantic import BaseModel, Field
from pydantic_extra_types.country import CountryAlpha2
from semantic_pydantic import SemanticField
from pydantic_extra_types.coordinate import Latitude, Longitude
from pydantic_extra_types.language_code import LanguageAlpha2
from tqdm import tqdm
from pyobo import get_name
from bioontologies import robot

HERE = Path(__file__).parent.resolve()
ENTRIES = HERE.joinpath("venues.tsv")
OUTPUT = HERE.joinpath("output")
OUTPUT.mkdir(exist_ok=True)
ONTOLOGY_TTL_PATH = OUTPUT.joinpath("venues.ttl")
ONTOLOGY_OWL_PATH = OUTPUT.joinpath("venues.owl")
ONTOLOGY_OBO_PATH = OUTPUT.joinpath("venues.obo")

PREFIX = "EVR"
BASE_IRI = "https://w3id.org/venue/id/"
ONTOLOGY_IRI = "https://w3id.org/venue/venue.ttl"


class Venue(BaseModel):
    id: str = Field(..., pattern="^\\d{7}$")
    name: str = Field(..., description="An english name for the venue")
    local_name: str | None = Field(None, description="The non-english local name for the venue")
    lang: LanguageAlpha2 | None = Field(None, description="The language of the non-english local name for the venue")
    country: CountryAlpha2
    city_geonames: str = SemanticField(prefix="geonames")
    latitude: Latitude
    longitude: Longitude
    wikidata: str | None = SemanticField(default=None, prefix="wikidata")
    osm_way: str | None = Field(None)
    address: str
    creator: str = SemanticField(prefix="orcid")
    date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$", description="A date in YYYY-MM-DD format")


PREAMBLE = f"""\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix terms: <http://purl.org/dc/terms/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix oboInOwl: <http://www.geneontology.org/formats/oboInOwl#> .
@prefix wikidata: <http://www.wikidata.org/entity/> .
@prefix RO: <http://purl.obolibrary.org/obo/RO_> .
@prefix IAO: <http://purl.obolibrary.org/obo/IAO_> .
@prefix orcid: <https://orcid.org/> .
@prefix geonames: <https://www.geonames.org/> .
@prefix schema: <https://schema.org/> .
@prefix osmw: <https://www.openstreetmap.org/way/> .
@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .

@prefix evr: <{BASE_IRI}> .
@prefix venue: <http://purl.obolibrary.org/obo/ENVO_03501127> .
@prefix city: <http://purl.obolibrary.org/obo/ENVO_00000856> .
@prefix human: <http://purl.obolibrary.org/obo/NCBITaxon_9606> .
@prefix address: <https://schema.org/streetAddress> .

<{ONTOLOGY_IRI}> a owl:Ontology ;
    terms:title "Event Venue Registry" ;
    terms:description "An ontology representation of the Event Venue Registry" ;
    terms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    IAO:0000700 venue: ;
    terms:creator orcid:0000-0003-4423-4370 ;
    rdfs:comment "Built by https://github.com/cthoyt/event-venue-registry"^^xsd:string .

IAO:0000700 a owl:AnnotationProperty;
    rdfs:label "ontology root"^^xsd:string .

RO:0001025 a owl:ObjectProperty;
    rdfs:label "located in"^^xsd:string .

rdfs:label a owl:AnnotationProperty;
    rdfs:label "label"^^xsd:string .

skos:exactMatch a owl:AnnotationProperty;
    rdfs:label "exact match"^^xsd:string .

geo:lat a owl:AnnotationProperty;
    rdfs:label "latitude"^^xsd:string ;
    owl:equivalentProperty schema:latitude ;
    rdfs:range xsd:decimal .

geo:long a owl:AnnotationProperty;
    rdfs:label "longitude"^^xsd:string ;
    owl:equivalentProperty schema:longitude ;
    rdfs:range xsd:decimal .

address: a owl:AnnotationProperty;
    rdfs:label "street address"^^xsd:string .

venue: a owl:Class;
    rdfs:label "conference venue"^^xsd:string .

city: a owl:Class;
    rdfs:label "city"^^xsd:string .

human: a owl:Class;
    rdfs:label "Homo sapiens"^^xsd:string .

"""


def _get_orcid_name(orcid: str) -> str | None:
    # TODO implement w/ orcid_downloader
    if orcid == "0000-0003-4423-4370":
        return "Charles Tapley Hoyt"
    return None


def main():
    with ENTRIES.open() as file, ONTOLOGY_TTL_PATH.open("w") as outfile:
        reader = csv.DictReader(file, delimiter="\t")
        print(PREAMBLE, file=outfile)
        city_geonames_ids: set[str] = set()
        creator_orcids: set[str] = set()
        for data in tqdm(reader, unit="venue"):
            data = {k: v for k, v in data.items() if k and v}
            venue = Venue.model_validate(data)
            parts = [
                "a venue:",
                f"rdfs:label \"{venue.name}\"@en",
                f"address: \"{venue.address}\"",
                f"RO:0001025 geonames:{venue.city_geonames}",
                f"geo:lat {venue.latitude}",
                f"geo:long {venue.longitude}",
                f"terms:creator orcid:{venue.creator}",
            ]
            city_geonames_ids.add(venue.city_geonames)
            creator_orcids.add(venue.creator)
            if venue.wikidata:
                parts.append(f"skos:exactMatch wikidata:{venue.wikidata}")
            if venue.local_name and venue.lang:
                parts.insert(2, f"rdfs:label \"{venue.local_name}\"@{venue.lang}")
            if venue.osm_way:
                parts.append(f"skos:exactMatch osmw:{venue.osm_way}")
            outfile.write(f"evr:{venue.id} " + " ;\n    ".join(parts) + " .\n\n")

        for city_geonames_id in tqdm(sorted(city_geonames_ids), unit="city"):
            city_name = get_name("geonames", city_geonames_id)
            outfile.write(f"geonames:{city_geonames_id} a city: ; rdfs:label \"{city_name}\" .\n\n")

        for orcid in tqdm(sorted(creator_orcids), unit="person"):
            person_name = _get_orcid_name(orcid)
            if person_name:
                outfile.write(f"orcid:{orcid} a human: ; rdfs:label \"{person_name}\" .\n\n")
            else:
                outfile.write(f"orcid:{orcid} a human: .\n\n")

    robot.convert(ONTOLOGY_TTL_PATH, ONTOLOGY_OWL_PATH)
    robot.convert(ONTOLOGY_TTL_PATH, ONTOLOGY_OBO_PATH)


if __name__ == '__main__':
    main()
