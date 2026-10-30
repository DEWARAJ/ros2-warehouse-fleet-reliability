from __future__ import annotations

import argparse
import json

from .scenario import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic warehouse fleet reliability benchmark")
    parser.add_argument("--missions", type=int, default=250)
    parser.add_argument("--robots", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    summary = run_benchmark(args.missions, args.robots, args.seed, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
