import os
import glob
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from utils import run_fastsurfer_docker, human_readable_cols
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
        run_fastsurfer_docker(subj, input_dir, output_dir, freesurfer_license, n_threads)



# ----------------------------------------------------------------------
# 2. Preprocessing function for HCP-YA - OUTSIDE DATASET
# ----------------------------------------------------------------------

"""
FreeSurfer/FastSurfer preprocessing script for lab MRI data.
Processes T1-weighted structural scans and extracts volumetric and cortical thickness measurements.
"""

# TODO: Incorporate ADHD analysis into class below
class FreeSurferExtractor:
    """Extract measurements from FreeSurfer/FastSurfer output."""
    
    def __init__(self, subjects_dir: str):
        """
        Initialize extractor.

        Args:
            subjects_dir: Directory containing FreeSurfer output
        """
        self.subjects_dir = Path(subjects_dir)
        
        # Define thickness regions to extract
        self.thickness_regions = [
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
    
    def extract_aseg_stats(self, subject_id: str, subjects_path: str = None) -> Dict[str, float]:
        """
        Extract subcortical volumes from aseg.stats file.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            Dictionary of volume measurements
        """
        stats_file = None
        if not subjects_path:
            stats_file = self.subjects_dir / subject_id / 'stats' / 'aseg.stats'
        else:
            stats_file = subjects_path / 'stats' / 'aseg.stats'
        volumes = {}
        
        if not stats_file.exists():
            print(f"Warning: aseg.stats not found for {subject_id}")
            return volumes
        
        # Mapping from FreeSurfer names to HCP column names
        aseg_mapping = {
            'eTIV': 'FS_IntraCranial_Vol',
            'BrainSegVol': 'FS_BrainSeg_Vol',
            'lhCortexVol': 'FS_LCort_GM_Vol',
            'rhCortexVol': 'FS_RCort_GM_Vol',
            'CortexVol': 'FS_TotCort_GM_Vol',
            'SubCortGrayVol': 'FS_SubCort_GM_Vol',
            'TotalGrayVol': 'FS_Total_GM_Vol',
            'lhCerebralWhiteMatterVol': 'FS_L_WM_Vol',
            'rhCerebralWhiteMatterVol': 'FS_R_WM_Vol',
            'CerebralWhiteMatterVol': 'FS_Tot_WM_Vol',
            'Left-Lateral-Ventricle': 'FS_L_LatVent_Vol',
            'Left-Cerebellum-Cortex': 'FS_L_Cerebellum_Cort_Vol',
            'Left-Thalamus': 'FS_L_ThalamusProper_Vol',
            'Left-Caudate': 'FS_L_Caudate_Vol',
            'Left-Putamen': 'FS_L_Putamen_Vol',
            'Left-Pallidum': 'FS_L_Pallidum_Vol',
            '3rd-Ventricle': 'FS_3rdVent_Vol',
            '4th-Ventricle': 'FS_4thVent_Vol',
            'Brain-Stem': 'FS_BrainStem_Vol',
            'Left-Hippocampus': 'FS_L_Hippo_Vol',
            'Left-Amygdala': 'FS_L_Amygdala_Vol',
            'Left-Accumbens-area': 'FS_L_AccumbensArea_Vol',
            'Right-Lateral-Ventricle': 'FS_R_LatVent_Vol',
            'Right-Cerebellum-Cortex': 'FS_R_Cerebellum_Cort_Vol',
            'Right-Thalamus': 'FS_R_ThalamusProper_Vol',
            'Right-Caudate': 'FS_R_Caudate_Vol',
            'Right-Putamen': 'FS_R_Putamen_Vol',
            'Right-Pallidum': 'FS_R_Pallidum_Vol',
            'Right-Hippocampus': 'FS_R_Hippo_Vol',
            'Right-Amygdala': 'FS_R_Amygdala_Vol',
            'Right-Accumbens-area': 'FS_R_AccumbensArea_Vol'
        }
        
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
    
    def extract_aparc_stats(self, subject_id: str, hemisphere: str, subjects_path: str = None) -> Dict[str, float]:
        """
        Extract cortical thickness from aparc.stats files.
        
        Args:
            subject_id: Subject identifier
            hemisphere: 'lh' or 'rh'
            
        Returns:
            Dictionary of thickness measurements
        """
        stats_file = None
        if not subjects_path:
            stats_file = self.subjects_dir / subject_id / 'stats' / f'{hemisphere}.aparc.DKTatlas.stats'
        else:
            stats_file = subjects_path / 'stats' / f'{hemisphere}.aparc.DKTatlas.stats'
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
                    for region in self.thickness_regions:
                        if region_name == region:
                            col_name = f"{prefix}{region.capitalize()}_Thck"
                            thickness[col_name] = thick_mean
                            break
        
        return thickness
    
    def extract_all_measurements(self, subject_id: str, subject_path = None) -> Dict[str, float]:
        """
        Extract all measurements for a subject.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            Dictionary with all measurements
        """
        measurements = {'Subject': subject_id}
        
        # Extract volumes
        volumes = self.extract_aseg_stats(subject_id, subject_path)
        measurements.update(volumes)
        
        # Extract thickness for both hemispheres
        lh_thickness = self.extract_aparc_stats(subject_id, 'lh', subject_path)
        measurements.update(lh_thickness)
        
        rh_thickness = self.extract_aparc_stats(subject_id, 'rh', subject_path)
        measurements.update(rh_thickness)
        
        return measurements
    
    def get_comparison_results(self):
        # Get measurements for self-subject
        lab_data = self.extract_all_measurements("Karas_262199")

        # TODO: Change. Currently assumes CSV output format
        ref_df = pd.read_csv("./outside_data/hcp-ya/HCP_YA_81.csv").drop(
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
