"""Apply the metadata-only Darktide navigation generator."""

import argparse
from pathlib import Path

try:
    from darktide_navigation import generate_and_apply
except ModuleNotFoundError as error:
    if error.name != "darktide_navigation":
        raise
    from scripts.darktide_navigation import generate_and_apply


def apply_reader(site):
    """Keep the existing callable entry point for the production generator."""
    return generate_and_apply(Path(site).resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    apply_reader(parser.parse_args().site)
