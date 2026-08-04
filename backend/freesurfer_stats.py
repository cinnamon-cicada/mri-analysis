"""
Low-level line parsing for FreeSurfer/FastSurfer stats files (aseg.stats,
{lh,rh}.aparc*.stats).

Shared by analysis.py (get_volume/get_thickness — internal ADHD-200 region
keys) and preprocess.py (extract_aseg_stats/extract_aparc_stats — HCP-YA CSV
column keys). Both parse the same file formats but map matched lines to
different output keys for different consumers, so only the line-parsing
mechanics are factored out here — the region-name mappings stay with their
respective callers.
"""
from pathlib import Path
from typing import Iterator, Tuple, Union

PathLike = Union[str, Path]


def iter_measure_comments(path: PathLike) -> Iterator[Tuple[str, float]]:
    """Yield (name, value) for each '# Measure Name, Label, Description,
    Value, Unit' summary line in an aseg.stats-style file, e.g.:

      # Measure EstimatedTotalIntraCranialVol, eTIV, ..., 1500000.0, mm^3

    yields ("eTIV", 1500000.0).
    """
    with open(path, "r") as f:
        for line in f:
            if not line.startswith("# Measure"):
                continue
            parts = line.split(",")
            if len(parts) >= 4:
                yield parts[1].strip(), float(parts[3].strip())


def iter_structure_rows(path: PathLike) -> Iterator[Tuple[str, float]]:
    """Yield (structure_name, volume_mm3) for each whitespace-delimited
    structure table row in an aseg.stats-style file (name in column 4,
    volume in column 3), skipping comment/blank lines."""
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                yield parts[4], float(parts[3])


def iter_region_thickness_rows(path: PathLike) -> Iterator[Tuple[str, float]]:
    """Yield (region_name, thickness_mm) for each whitespace-delimited row
    in an aparc.stats-style file (region in column 0, ThickAvg in column 4),
    skipping comment/blank lines."""
    with open(path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                yield parts[0], float(parts[4])
