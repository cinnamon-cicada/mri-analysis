import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from utils import run_fastsurfer, human_readable_cols, aseg_mapping
from freesurfer_stats import iter_measure_comments, iter_region_thickness_rows, iter_structure_rows
from stats_math import zscore_to_percentile

# ----------------------------------------------------------------------
# 2. Preprocessing function for HCP-YA - OUTSIDE DATASET
# ----------------------------------------------------------------------

# Define thickness regions to extract
thickness_regions = [
        'caudalanteriorcingulate',
        'caudalmiddlefrontal',
        'cuneus',
        'entorhinal',
        'fusiform',
        'inferiorparietal',
        'inferiortemporal',
        'isthmuscingulate',
        'lateraloccipital',
        'lateralorbitofrontal',
        'lingual',
        'medialorbitofrontal',
        'middletemporal',
        'parahippocampal',
        'paracentral',
        'pericalcarine',
        'postcentral',
        'posteriorcingulate',
        'precentral',
        'precuneus',
        'rostralanteriorcingulate',
        'rostralmiddlefrontal',
        'superiorfrontal',
        'superiorparietal',
        'superiortemporal',
        'supramarginal',
        'insula'
    ]

def extract_aseg_stats(subject_id: str, subjects_path: str = None) -> Dict[str, float]:
    """
    Extract subcortical volumes from aseg.stats file.
    
    Args:
        subject_id: Subject identifier
        
    Returns:
        Dictionary of volume measurements
    """
    if not subjects_path:
        print(f"Warning: No path provided for {subject_id}, skipping aseg.stats")
        return {}
    stats_file = Path(subjects_path) / 'stats' / 'aseg.stats'
    volumes = {}

    if not stats_file.exists():
        print(f"Warning: aseg.stats not found for {subject_id}")
        return volumes

    for measure_name, value in iter_measure_comments(stats_file):
        if measure_name in aseg_mapping:
            volumes[aseg_mapping[measure_name]] = value

    for struct_name, volume in iter_structure_rows(stats_file):
        if struct_name in aseg_mapping:
            volumes[aseg_mapping[struct_name]] = volume

    return volumes

def extract_aparc_stats(subject_id: str, hemisphere: str, subjects_path: str = None) -> Dict[str, float]:
    """
    Extract cortical thickness from aparc.stats files.
    
    Args:
        subject_id: Subject identifier
        hemisphere: 'lh' or 'rh'
        
    Returns:
        Dictionary of thickness measurements
    """
    if not subjects_path:
        print(f"Warning: No path provided for {subject_id}, skipping aparc.stats")
        return {}
    # FastSurfer writes the DKT parcellation as *.aparc.DKTatlas.mapped.stats;
    # fall back to the unmapped name for FreeSurfer-style outputs.
    stats_dir = Path(subjects_path) / 'stats'
    stats_file = stats_dir / f'{hemisphere}.aparc.DKTatlas.mapped.stats'
    if not stats_file.exists():
        stats_file = stats_dir / f'{hemisphere}.aparc.DKTatlas.stats'
    thickness = {}

    if not stats_file.exists():
        print(f"Warning: {hemisphere}.aparc.DKTatlas[.mapped].stats not found for {subject_id}")
        return thickness
    
    prefix = 'FS_L_' if hemisphere == 'lh' else 'FS_R_'

    for region_name, thick_mean in iter_region_thickness_rows(stats_file):
        if region_name in thickness_regions:
            col_name = f"{prefix}{region_name.capitalize()}_Thck"
            thickness[col_name] = thick_mean

    return thickness

def extract_all_measurements(subject_id: str, subject_path = None) -> Dict[str, float]:
    """
    Extract all measurements for a subject.
    
    Args:
        subject_id: Subject identifier
        
    Returns:
        Dictionary with all measurements
    """
    measurements = {'Subject': subject_id}
    
    # Extract volumes
    volumes = extract_aseg_stats(subject_id, subject_path)
    measurements.update(volumes)
    
    # Extract thickness for both hemispheres
    lh_thickness = extract_aparc_stats(subject_id, 'lh', subject_path)
    measurements.update(lh_thickness)
    
    rh_thickness = extract_aparc_stats(subject_id, 'rh', subject_path)
    measurements.update(rh_thickness)
    
    return measurements

def run_outlier_analysis(data_path: str) -> Dict[str, List]:
    # Get measurements for self-subject
    lab_data = extract_all_measurements("Karas_262199", data_path)

    csv_path = Path(__file__).parent / "benchmark" / "HCP_YA_ALL.csv"
    ref_df = pd.read_csv(csv_path).drop(
        columns=['Subject', 'Release', 'Acquisition', 'Gender', 'Age',
                '3T_Full_MR_Compl', '7T_Full_MR_Compl', 'MEG_FullProt_Compl']
    )

    # For each subject, get percentile
    z_scores = {'volume_percentiles': [], 'thickness_percentiles': []}

    for part in ref_df.columns:
        if part not in lab_data:
            continue
        mean = ref_df[part].mean()
        std = ref_df[part].std()
        percentile = zscore_to_percentile(lab_data[part], mean, std)

        if '_Vol' in part:
            z_scores['volume_percentiles'].append([human_readable_cols[part], percentile])
        elif '_Thck' in part:
            z_scores['thickness_percentiles'].append([human_readable_cols[part], percentile])

    return z_scores
