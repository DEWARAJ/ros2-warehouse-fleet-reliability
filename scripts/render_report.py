from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "benchmark_summary.json"
OUTPUT = ROOT / "docs" / "dashboard-preview.svg"


def main() -> None:
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    cards = [
        ("MISSIONS", str(data["missions_total"]), "deterministic workload"),
        ("COMPLETION", f'{data["mission_completion_pct"]:.1f}%', "completed missions"),
        ("AUTO RECOVERY", f'{data["automatic_recovery_pct"]:.1f}%', f'{data["faults_recovered"]} of {data["faults_injected"]} faults'),
        ("MEAN RECOVERY", f'{data["mean_time_to_recovery_ms"] / 1000:.2f}s', "detect to re-register"),
    ]
    blocks = []
    for index, (label, value, note) in enumerate(cards):
        x = 36 + index * 286
        blocks.append(
            f'<g transform="translate({x},105)"><rect width="250" height="145" rx="16" fill="#13243b" stroke="#2c4868"/>'
            f'<text x="20" y="35" class="label">{label}</text><text x="20" y="88" class="value">{value}</text>'
            f'<text x="20" y="119" class="note">{note}</text></g>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">
<style>.title{{font:700 28px Arial;fill:#f7fafc}}.subtitle{{font:15px Arial;fill:#9fb3c8}}.label{{font:700 13px Arial;fill:#6ee7b7;letter-spacing:1px}}.value{{font:700 38px Arial;fill:#fff}}.note{{font:14px Arial;fill:#9fb3c8}}.footer{{font:13px monospace;fill:#6f8aa5}}</style>
<rect width="1200" height="420" rx="24" fill="#0a1525"/>
<text x="36" y="48" class="title">Warehouse Fleet Reliability Benchmark</text>
<text x="36" y="75" class="subtitle">5 simulated robot workers · seed {data['seed']} · reproducible incident evidence</text>
{''.join(blocks)}
<line x1="36" y1="294" x2="1164" y2="294" stroke="#2c4868"/>
<text x="36" y="330" class="label">RECOVERY PATH</text>
<text x="36" y="360" class="subtitle">detect fault  →  quarantine robot  →  requeue mission  →  recover worker  →  re-register</text>
<text x="36" y="396" class="footer">python -m warehouse_fleet.cli --missions 250 --robots 5 --seed 2026</text>
</svg>'''
    OUTPUT.write_text(svg, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
