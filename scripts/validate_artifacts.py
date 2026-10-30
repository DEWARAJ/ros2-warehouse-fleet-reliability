"""Parse generated evidence artifacts to catch malformed JSON or SVG output."""

import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    json.loads((ROOT / "results" / "ros2" / "validation-summary.json").read_text(encoding="utf-8"))
    ElementTree.parse(ROOT / "docs" / "ros2-runtime-validation.svg")
    print("JSON_AND_SVG_VALIDATED")


if __name__ == "__main__":
    main()
