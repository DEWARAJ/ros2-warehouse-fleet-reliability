"""Validate the checked-in Compose topology without requiring a Docker daemon."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "docker-compose.yml"
EXPECTED_SERVICES = {"fleet-api", "postgres", "prometheus", "grafana"}


def main() -> None:
    document = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AssertionError("Compose document must be a mapping")

    services = document.get("services")
    if not isinstance(services, dict):
        raise AssertionError("Compose document is missing a services mapping")

    missing = EXPECTED_SERVICES - set(services)
    if missing:
        raise AssertionError(f"Missing required services: {sorted(missing)}")

    api = services["fleet-api"]
    if "postgres" not in api.get("depends_on", {}):
        raise AssertionError("fleet-api must depend on postgres")

    prometheus = services["prometheus"]
    if not prometheus.get("volumes"):
        raise AssertionError("prometheus must mount its configuration")

    grafana = services["grafana"]
    if not grafana.get("volumes"):
        raise AssertionError("grafana must mount provisioning or dashboard files")

    print(
        "COMPOSE_STRUCTURE_VALIDATED: "
        + ", ".join(sorted(EXPECTED_SERVICES))
    )


if __name__ == "__main__":
    main()
