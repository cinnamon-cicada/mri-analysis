from typing import Dict, List
import numpy as np
from pathlib import Path

from stats_math import zscore_to_percentile

_HCP_YA_CSV = Path(__file__).parent / "benchmark" / "HCP_YA_ALL.csv"


def compare_to_benchmark(subject_dir: str) -> dict:
    """
    Compare a single subject's FastSurfer output against the HCP-YA general
    population (N=889).

    Loads the subject's FreeSurfer measurements via extract_all_measurements(),
    then computes a percentile for every matching column in the HCP-YA CSV.

    Parameters
    ----------
    subject_dir : str
        Path to the FastSurfer output directory for one subject.

    Returns
    -------
    dict
        {
          "volume_percentiles": [[label, percentile, measured_value], ...],
          "thickness_percentiles": [[label, percentile, measured_value], ...],
        }
        Sorted descending by percentile within each category.
    """
    import pandas as pd
    from preprocess import extract_all_measurements
    from utils import human_readable_cols

    ref_df = pd.read_csv(_HCP_YA_CSV)
    subject_id = Path(subject_dir).name
    measurements = extract_all_measurements(subject_id, subject_dir)

    volume_percentiles = []
    thickness_percentiles = []

    for col in ref_df.columns:
        if "_Vol" not in col and "_Thck" not in col:
            continue
        if col not in measurements:
            continue
        col_data = ref_df[col].dropna()
        if len(col_data) == 0:
            continue
        value = float(measurements[col])
        pct = zscore_to_percentile(value, col_data.mean(), col_data.std())
        label = human_readable_cols.get(col, col)
        if "_Vol" in col:
            volume_percentiles.append([label, pct, value])
        else:
            thickness_percentiles.append([label, pct, value])

    volume_percentiles.sort(key=lambda x: (x[1] is not None, x[1] or 0), reverse=True)
    thickness_percentiles.sort(key=lambda x: (x[1] is not None, x[1] or 0), reverse=True)

    return {
        "volume_percentiles": volume_percentiles,
        "thickness_percentiles": thickness_percentiles,
    }

def list_population_segments() -> List[Dict]:
    """
    List brain segments available in the HCP-YA reference population, for
    the /data population-stats dropdown.
    """
    import pandas as pd
    from utils import human_readable_cols

    ref_df = pd.read_csv(_HCP_YA_CSV)
    segments = []
    for col in ref_df.columns:
        if "_Vol" not in col and "_Thck" not in col:
            continue
        if ref_df[col].dropna().empty:
            continue
        segments.append({
            "key": col,
            "label": human_readable_cols.get(col, col),
            "kind": "volume" if "_Vol" in col else "thickness",
        })
    segments.sort(key=lambda s: s["label"])
    return segments


def get_population_distribution(segment: str, bins: int = 20) -> dict:
    """
    Bin the HCP-YA reference population's values for one segment into a
    count-distribution histogram, for the /data population-stats chart.
    """
    import pandas as pd
    from utils import human_readable_cols

    ref_df = pd.read_csv(_HCP_YA_CSV)
    if segment not in ref_df.columns:
        raise KeyError(f"Unknown segment: {segment}")

    values = ref_df[segment].dropna().astype(float)
    counts, edges = np.histogram(values, bins=bins)

    return {
        "segment": segment,
        "label": human_readable_cols.get(segment, segment),
        "n": int(len(values)),
        "edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
    }
