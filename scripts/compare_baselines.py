"""Compare two baseline event files with type-agnostic temporal matching.

Usage:
    python scripts/compare_baselines.py baselines/travel_expert_veronika_bak/events.json baselines/travel_expert_veronika/events.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.similarity import string_similarity


def match_by_time(
    ref: list[dict],
    cand: list[dict],
    tolerance_ms: float = 5000,
) -> list[tuple[int, int, float]]:
    """Two-pass matching: same-type first, then remaining by time only."""
    used_ref: set[int] = set()
    used_cand: set[int] = set()
    matches: list[tuple[int, int, float]] = []

    # Pass 1: match same-type events by closest time
    ref_sorted = sorted(range(len(ref)), key=lambda i: ref[i]["time_start"])
    for ri in ref_sorted:
        best_ci: int | None = None
        best_gap = float("inf")
        for ci in range(len(cand)):
            if ci in used_cand:
                continue
            if ref[ri]["type"] != cand[ci]["type"]:
                continue
            gap = abs(ref[ri]["time_start"] - cand[ci]["time_start"])
            if gap < best_gap and gap <= tolerance_ms:
                best_gap = gap
                best_ci = ci
        if best_ci is not None:
            used_ref.add(ri)
            used_cand.add(best_ci)
            matches.append((ri, best_ci, best_gap))

    # Pass 2: match remaining events type-agnostic
    remaining_ref = sorted(
        [i for i in range(len(ref)) if i not in used_ref],
        key=lambda i: ref[i]["time_start"],
    )
    for ri in remaining_ref:
        best_ci: int | None = None
        best_gap = float("inf")
        for ci in range(len(cand)):
            if ci in used_cand:
                continue
            gap = abs(ref[ri]["time_start"] - cand[ci]["time_start"])
            if gap < best_gap and gap <= tolerance_ms:
                best_gap = gap
                best_ci = ci
        if best_ci is not None:
            used_cand.add(best_ci)
            matches.append((ri, best_ci, best_gap))

    return matches


def fmt_time(ms: float) -> str:
    s = ms / 1000
    return f"{int(s // 60)}:{s % 60:04.1f}"


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ref_path, cand_path = Path(sys.argv[1]), Path(sys.argv[2])
    tolerance_ms = float(sys.argv[3]) if len(sys.argv) > 3 else 5000

    ref = json.loads(ref_path.read_text())
    cand = json.loads(cand_path.read_text())

    matches = match_by_time(ref, cand, tolerance_ms)
    matched_ref = {m[0] for m in matches}
    matched_cand = {m[1] for m in matches}

    type_agree = []
    type_disagree = []
    for ri, ci, gap in sorted(matches, key=lambda x: ref[x[0]]["time_start"]):
        if ref[ri]["type"] == cand[ci]["type"]:
            type_agree.append((ri, ci, gap))
        else:
            type_disagree.append((ri, ci, gap))

    # --- Summary ---
    print("=" * 90)
    print(f"Reference:  {ref_path}  ({len(ref)} events)")
    print(f"Candidate:  {cand_path}  ({len(cand)} events)")
    print(f"Tolerance:  {tolerance_ms/1000:.0f}s")
    print(f"Matched:    {len(matches)}/{len(ref)} reference events  "
          f"({len(matches)}/{len(cand)} candidate events)")
    print(f"Type agree: {len(type_agree)}  disagree: {len(type_disagree)}")
    print("=" * 90)

    # --- Type agrees ---
    print(f"\nTYPE AGREES ({len(type_agree)})")
    print("-" * 90)
    for ri, ci, gap in type_agree:
        r, c = ref[ri], cand[ci]
        sim = string_similarity(r.get("description", ""), c.get("description", ""))
        print(f"  {r['type']:18s} @ {fmt_time(r['time_start'])}  gap={gap/1000:.1f}s  sim={sim:.2f}")
        print(f"    REF: {r['description'][:85]}")
        print(f"    CAN: {c['description'][:85]}")

    # --- Type disagrees ---
    print(f"\nTYPE DISAGREES ({len(type_disagree)})")
    print("-" * 90)
    for ri, ci, gap in type_disagree:
        r, c = ref[ri], cand[ci]
        print(f"  REF[{ri:2d}] {r['type']:18s}  vs  CAN[{ci:2d}] {c['type']:18s}  "
              f"@ {fmt_time(r['time_start'])}  gap={gap/1000:.1f}s")
        print(f"    REF: {r['description'][:85]}")
        print(f"    CAN: {c['description'][:85]}")

    # --- Unmatched reference ---
    unmatched_ref = [i for i in range(len(ref)) if i not in matched_ref]
    print(f"\nUNMATCHED REFERENCE ({len(unmatched_ref)})")
    print("-" * 90)
    for ri in sorted(unmatched_ref, key=lambda i: ref[i]["time_start"]):
        r = ref[ri]
        target = r.get("interaction_target", "")
        target_str = f"  target={target}" if target else ""
        print(f"  [{ri:2d}] {r['type']:18s} @ {fmt_time(r['time_start'])}"
              f"  {r['description'][:65]}{target_str}")

    # --- Unmatched candidate ---
    unmatched_cand = [i for i in range(len(cand)) if i not in matched_cand]
    print(f"\nUNMATCHED CANDIDATE ({len(unmatched_cand)})")
    print("-" * 90)
    for ci in sorted(unmatched_cand, key=lambda i: cand[i]["time_start"]):
        c = cand[ci]
        print(f"  [{ci:2d}] {c['type']:18s} @ {fmt_time(c['time_start'])}"
              f"  {c['description'][:75]}")

    # --- Type disagreement summary ---
    print(f"\nTYPE CONFUSION MATRIX")
    print("-" * 50)
    confusion: dict[tuple[str, str], int] = {}
    for ri, ci, _ in type_disagree:
        pair = (ref[ri]["type"], cand[ci]["type"])
        confusion[pair] = confusion.get(pair, 0) + 1
    for (rt, ct), count in sorted(confusion.items(), key=lambda x: -x[1]):
        print(f"  {rt:18s} -> {ct:18s}  x{count}")


if __name__ == "__main__":
    main()
