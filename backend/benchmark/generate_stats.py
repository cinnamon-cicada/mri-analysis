"""
Generate adhd_stats.json from a directory of FastSurfer-processed ADHD-200 subjects.

Usage:
    python generate_stats.py ./processed_data/adhd200

Run this once after preprocessing the reference dataset. The output file is
loaded at startup by analysis.py for per-request percentile comparisons.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis import get_comparison_results

OUTPUT = Path(__file__).parent / "adhd_stats.json"


def main(processed_dir: str) -> None:
    subject_dirs = [
        str(p) for p in Path(processed_dir).iterdir() if p.is_dir()
    ]
    if not subject_dirs:
        print(f"No subject directories found in {processed_dir}")
        sys.exit(1)

    print(f"Aggregating stats from {len(subject_dirs)} subjects...")
    stats = get_comparison_results(subject_dirs)

    if "error" in stats:
        print(f"Error: {stats['error']}")
        sys.exit(1)

    output = {
        "source": "ADHD-200 dataset",
        "n_subjects": len(subject_dirs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "volumes": stats["volumes"],
        "thickness": stats["thickness"],
    }

    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"Written to {OUTPUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <processed_adhd200_dir>")
        sys.exit(1)
    main(sys.argv[1])
