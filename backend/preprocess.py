import os
import glob
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from utils import run_fastsurfer_docker, human_readable_cols, aseg_mapping
import scipy.stats as stats

# ----------------------------------------------------------------------
# 1. Preprocessing for ADHD Analysis - OUTSIDE DATASET
# ----------------------------------------------------------------------
def preprocess_adhd200(
    input_dir: str = './outside_data/adhd200',
    output_dir: str = './processed_data/adhd200_fastsurfer',
    n_threads: int = 4,
    freesurfer_license: Optional[str] = None
) -> None:
    """
    Run FastSurfer (GPU-accelerated FreeSurfer alternative) via Docker.

    Parameters
    ----------
    input_dir : str
        Directory containing subject directories (each with anat/*.nii.gz)
    output_dir : str
        Directory to save processed outputs
    n_threads : int
        Number of CPU threads for non-GPU tasks
    freesurfer_license : str, optional
        Path to FreeSurfer license file (still required)
    """
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Check for FreeSurfer license
    if freesurfer_license is None or not os.path.exists(freesurfer_license):
        print("FreeSurfer license file not found.")
        print("Get one free at: https://surfer.nmr.mgh.harvard.edu/registration.html")
        return
    freesurfer_license = os.path.abspath(freesurfer_license)

    subjects = [d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
    print(f"Found {len(subjects)} subjects to process in {input_dir}")

    for subj in subjects:
        anat_dir = os.path.join(input_dir, subj, "anat")
        if not os.path.exists(anat_dir):
            print(f"No anat directory found for {subj}, skipping...")
            continue

        t1_files = glob.glob(os.path.join(anat_dir, "sub-*_T1w.nii.gz"))
        if not t1_files:
            print(f"No T1w file found for {subj}, skipping...")
            continue

        print(f"Pre-processing subject: {subj}")

        # Run FastSurfer Docker command
        run_fastsurfer_docker([subj], input_dir, output_dir, freesurfer_license, n_threads)



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
            
    with open(stats_file, 'r') as f:
        for line in f:
            line = line.strip()
            if "Thalamus" in line:
                parts = line.split()
                measure_name = parts[4]
                value = float(parts[3])
                if measure_name in aseg_mapping:
                    volumes[aseg_mapping[measure_name]] = value

            if line.startswith('# Measure'):
                parts = line.split(',')

                if len(parts) >= 4:
                    measure_name = parts[1].strip()
                    value = float(parts[3].strip())
                    
                    if measure_name in aseg_mapping:
                        volumes[aseg_mapping[measure_name]] = value
            
            # Parse structure lines
            elif not line.startswith('#') and line:
                parts = line.split()
                if len(parts) >= 5:
                    struct_name = parts[4]
                    volume = float(parts[3])
                    
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
    stats_file = Path(subjects_path) / 'stats' / f'{hemisphere}.aparc.DKTatlas.stats'
    thickness = {}
    
    if not stats_file.exists():
        print(f"Warning: {hemisphere}.aparc.DKTatlas.stats not found for {subject_id}")
        return thickness
    
    prefix = 'FS_L_' if hemisphere == 'lh' else 'FS_R_'
    
    with open(stats_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split()
            if len(parts) >= 5:
                region_name = parts[0]
                thick_mean = float(parts[4])
                
                # Check if this region is in our list
                for region in thickness_regions:
                    if region_name == region:
                        col_name = f"{prefix}{region.capitalize()}_Thck"
                        thickness[col_name] = thick_mean
                        break
    
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

    csv_path = Path(__file__).parent.parent / "outside_data" / "hcp-ya" / "HCP_YA_ALL.csv"
    ref_df = pd.read_csv(csv_path).drop(
        columns=['Subject', 'Release', 'Acquisition', 'Gender', 'Age',
                '3T_Full_MR_Compl', '7T_Full_MR_Compl', 'MEG_FullProt_Compl']
    )

    # For each subject, get percentile
    z_scores = {'volume_percentiles': [], 'thickness_percentiles': []}

    for part in ref_df.columns:
        mean = ref_df[part].mean()
        std = ref_df[part].std()
        z_score = (lab_data[part] - mean) / std #TODO: debug. part not found.
        percentile = stats.norm.cdf(z_score)

        if '_Vol' in part:
            z_scores['volume_percentiles'].append([human_readable_cols[part], percentile])
        elif '_Thck' in part:
            z_scores['thickness_percentiles'].append([human_readable_cols[part], percentile])

    return z_scores
