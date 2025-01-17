"""Data resources for EVR."""

from pathlib import Path

__all__ = [
    "VENUES_PATH",
]

HERE = Path(__file__).parent.resolve()
VENUES_PATH = HERE.joinpath("venues.tsv")
