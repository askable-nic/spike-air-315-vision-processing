"""Calculate token usage and dollar costs for baseline analyses."""
from __future__ import annotations

import json
from pathlib import Path

BASELINES_DIR = Path(__file__).resolve().parent.parent / "baselines"

# Gemini Flash 3 Preview pricing
INPUT_COST_PER_TOKEN = 0.50 / 1_000_000
OUTPUT_COST_PER_TOKEN = 3.00 / 1_000_000


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n / 1_000:,.1f}k"


def fmt_duration(ms: float) -> str:
    minutes = ms / 60_000
    if minutes >= 60:
        return f"{minutes / 60:.1f}h"
    return f"{minutes:.1f}m"


def main() -> None:
    metadata_paths = sorted(BASELINES_DIR.glob("*/artifacts/run_metadata.json"))

    rows: list[dict] = []
    for path in metadata_paths:
        with open(path) as f:
            meta = json.load(f)

        input_tokens = meta["total_input_tokens"]
        output_tokens = meta["total_output_tokens"]
        total_tokens = input_tokens + output_tokens
        input_cost = input_tokens * INPUT_COST_PER_TOKEN
        output_cost = output_tokens * OUTPUT_COST_PER_TOKEN
        total_cost = input_cost + output_cost
        video_duration_ms = meta["video_duration_ms"]
        video_minutes = video_duration_ms / 60_000
        cost_per_minute = total_cost / video_minutes if video_minutes > 0 else 0

        rows.append({
            "session": meta["session"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "video_duration_ms": video_duration_ms,
            "video_minutes": video_minutes,
            "cost_per_minute": cost_per_minute,
            "segments": len(meta["segments"]),
        })

    # Print table
    name_w = max(len(r["session"]) for r in rows)
    header = (
        f"{'Session':<{name_w}}  {'Duration':>8}  {'Segments':>8}  "
        f"{'Input':>9}  {'Output':>9}  {'Total':>9}  "
        f"{'In $':>7}  {'Out $':>7}  {'Total $':>8}  {'$/min':>7}"
    )
    print(header)
    print("-" * len(header))

    totals = dict(
        input_tokens=0, output_tokens=0, total_tokens=0,
        input_cost=0.0, output_cost=0.0, total_cost=0.0,
        video_minutes=0.0, segments=0,
    )

    for r in rows:
        print(
            f"{r['session']:<{name_w}}  {fmt_duration(r['video_duration_ms']):>8}  "
            f"{r['segments']:>8}  "
            f"{fmt_tokens(r['input_tokens']):>9}  "
            f"{fmt_tokens(r['output_tokens']):>9}  "
            f"{fmt_tokens(r['total_tokens']):>9}  "
            f"${r['input_cost']:>6.3f}  ${r['output_cost']:>6.3f}  "
            f"${r['total_cost']:>7.4f}  ${r['cost_per_minute']:>6.4f}"
        )
        for k in totals:
            totals[k] += r[k]

    avg_cost_per_min = totals["total_cost"] / totals["video_minutes"] if totals["video_minutes"] > 0 else 0

    print("-" * len(header))
    print(
        f"{'TOTAL':<{name_w}}  {fmt_duration(totals['video_minutes'] * 60_000):>8}  "
        f"{totals['segments']:>8}  "
        f"{fmt_tokens(totals['input_tokens']):>9}  "
        f"{fmt_tokens(totals['output_tokens']):>9}  "
        f"{fmt_tokens(totals['total_tokens']):>9}  "
        f"${totals['input_cost']:>6.3f}  ${totals['output_cost']:>6.3f}  "
        f"${totals['total_cost']:>7.4f}  ${avg_cost_per_min:>7.4f}"
    )


if __name__ == "__main__":
    main()
