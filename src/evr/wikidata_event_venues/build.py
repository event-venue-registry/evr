"""Curation of Wikidata event venues."""

import re
from pathlib import Path
from textwrap import dedent

import click
import pandas as pd
from quickstatements_client.sources.utils import query_wikidata
from tqdm import tqdm

HERE = Path(__file__).parent.resolve()
QID_RE = re.compile("^Q\\d+$")

EVENT_VENUE_CLASSES_PATH = HERE.joinpath("event_venue_classes.tsv")
EVENT_VENUES_PATH = HERE.joinpath("event_venues.tsv")

EVENT_VENUE_CLASSES_SPARQL = """\
    SELECT DISTINCT ?venueType ?venueTypeLabel ?venueTypeDescription
    WHERE
    {
      ?venueType wdt:P279* wd:Q18674739 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en,de,fr,es,pt".
      }
    }
"""


def query_event_venue_classes() -> None:
    """Get an initial dataframe of event venue classes."""
    # TODO make it append to existing one.
    df = df_from_sparql(EVENT_VENUE_CLASSES_SPARQL)
    df["curation"] = ""
    write_df(df)


def df_from_sparql(sparql: str) -> pd.DataFrame:
    """Get a dataframe from the results of a SPARQL query."""
    return pd.DataFrame(query_wikidata(sparql))


def _sort_key(v: str | None) -> tuple[int, str]:
    if v == "yes":
        return 0, ""
    if pd.isna(v) or v is None:
        return 1, ""
    else:
        return 2, v


def read_df() -> pd.DataFrame:
    """Read the Wikidata event venue classes curation sheet."""
    return pd.read_csv(EVENT_VENUE_CLASSES_PATH, sep="\t")


def write_df(df: pd.DataFrame) -> None:
    """Write the Wikidata event venue classes curation sheet."""
    df.to_csv(EVENT_VENUE_CLASSES_PATH, index=False, sep="\t")


def lint() -> None:
    """Lint the event venue class curation sheet."""
    df = read_df()
    df.sort_values(["curation"], inplace=True, key=lambda x: x.map(_sort_key))
    write_df(df)


def get_class_sparql(event_venue_class_qid: str) -> str:
    """Get SPARQL for the given event venue class."""
    return (
        dedent("""\
        SELECT ?venue ?venueLabel
        WHERE
        {
          ?venue wdt:P31/wdt:P279* wd:%s .
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en".
          }
        }
    """)
        % event_venue_class_qid
    )


def get_event_venues_df() -> pd.DataFrame:
    """Get the SPARQL query for instances of relevant event venues."""
    _df = read_df()
    qids = _df[_df["curation"] == "yes"][["venueType", "venueTypeLabel"]].values
    it = tqdm(qids, unit="event venue class")
    dfs = []
    for qid, label in it:
        df = df_from_sparql(get_class_sparql(qid))
        df["eventVenueType"] = qid
        df["eventVenueTypeLabel"] = label
        # throw away ones w/o english labels
        df = df[df["venueLabel"].map(lambda x: not QID_RE.match(x))]
        dfs.append(df)
    rv = pd.concat(dfs)
    rv = rv.sort_values("venue").drop_duplicates()
    rv.to_csv(EVENT_VENUES_PATH, sep="\t", index=False)
    return rv


@click.command()
def main() -> None:
    """Run everything."""
    click.echo(get_event_venues_df())


if __name__ == "__main__":
    main()
