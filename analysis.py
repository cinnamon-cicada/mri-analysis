from typing import Dict, List, Optional
import os
import numpy as np
import json

# ----------------------------------
# ADHD Analysis Script
# ----------------------------------

def run_adhd_analysis() -> None:
    """
    Run ADHD-200 analysis and return summarized results.
    """
    outside_dirs = [os.listdir("./processed_data/adhd200/")]
    lab_dirs = [os.listdir("./processed_data/adhd_lab/")]
    outside_data = get_adhd_summarized(
        subject_dirs=outside_dirs
    )
    lab_data = get_adhd_summarized(
        subject_dirs=lab_dirs
    )

    percentile_results = {}

    # Get percentile based on z-score for each region
    for region in outside_data['volumes']:
        value = lab_data['volumes'][region]['mean']
        mean = outside_data['volumes'][region]['mean']
        std = outside_data['volumes'][region]['std']
        z_score = (value - mean) / std  # Example: compare to 1000 mm3
        percentile = 0.5 * (1 + np.math.erf(z_score / np.sqrt(2)))
        percentile_results[region]['volume'] = percentile
    for region in lab_data['thickness']:
        value = lab_data['thickness'][region]['mean']
        mean = outside_data['thickness'][region]['mean']
        std = outside_data['thickness'][region]['std']
        z_score = (value - mean) / std
        percentile = 0.5 * (1 + np.math.erf(z_score / np.sqrt(2)))
        percentile_results[region]['thickness'] = percentile

    # Write to JSON file
    with open("./analysis/adhd_analysis_results.json", "w") as f:
        json.dump(percentile_results, f, indent=2)

def get_adhd_summarized(subject_dirs: list) -> Dict:
    """
    Aggregate volume and thickness measurements across multiple subjects,
    within one dataset.

    Parameters
    ----------
    subject_dirs : list
        List of paths to FreeSurfer subject directories
        
    Returns
    -------
    dict
        Dictionary with mean and std for each brain region
    """
    try:        
        all_volumes = {}
        all_thickness = {}
        all_etiv = []
        
        for subject_dir in subject_dirs:
            print("Processing subject:", subject_dir)
            volumes = get_volume(subject_dir, analysis='adhd')
            thickness = get_thickness(subject_dir, analysis='adhd')
            print(json.dumps({'volumes': volumes, 'thickness': thickness}, indent=2))

            if 'error' not in volumes:
                for region, value in volumes['volumes'].items():
                    if region not in all_volumes:
                        all_volumes[region] = []
                    all_volumes[region].append(value)
                if volumes['eTIV']:
                    all_etiv.append(volumes['eTIV'])
                print("  Volumes processed.")

            if 'error' not in thickness:
                for region, value in thickness['thickness'].items():
                    if region not in all_thickness:
                        all_thickness[region] = []
                    all_thickness[region].append(value)
                print("  Thickness processed.")
        
        results = {
            'volumes': {},
            'thickness': {},
            'eTIV': {}
        }
        
        for region, values in all_volumes.items():
            results['volumes'][region] = {
                'mean': np.mean(values),
                'std': np.std(values)
            }
        
        for region, values in all_thickness.items():
            results['thickness'][region] = {
                'mean': np.mean(values),
                'std': np.std(values)
            }
        
        if all_etiv:
            results['eTIV'] = {
                'mean': np.mean(all_etiv),
                'std': np.std(all_etiv)
            }
        
        return results
        
    except Exception as e:
        return {'error': str(e)}


def get_volume(data_path: str = './analysis/freesurfer_washu',
    analysis: str = 'adhd'
) -> Dict:
    """
    Extract volume measurements for specific analyses.
    
    Parameters
    ----------
    data_path : str
        Path to FreeSurfer subject directory
        
    Returns
    -------
    dict
        Dictionary with volumes and eTIV
    """
    try:
        stats_dir = os.path.join(data_path, 'stats')
        
        volume_regions = {
            'Left-Caudate': 'caudate_left',
            'Right-Caudate': 'caudate_right',
            'Left-Putamen': 'putamen_left',
            'Right-Putamen': 'putamen_right',
            'Left-Accumbens-area': 'accumbens_left',
            'Right-Accumbens-area': 'accumbens_right',
            'Left-Cerebellum-Cortex': 'cerebellum_cortex_left',
            'Right-Cerebellum-Cortex': 'cerebellum_cortex_right',
            'Cerebellar-Vermal-Lobules-I-V': 'cerebellum_vermis_I-V',
            'Cerebellar-Vermal-Lobules-VI-VII': 'cerebellum_vermis_VI-VII',
            'Cerebellar-Vermal-Lobules-VIII-X': 'cerebellum_vermis_VIII-X'
        }

        results = {
            'volumes': {},
            'eTIV': None
        }
        
        aseg_file = os.path.join(stats_dir, 'aseg.stats')
        with open(aseg_file, 'r') as f:
            for line in f:
                if line.startswith('# Measure EstimatedTotalIntraCranialVol'):
                    parts = line.split(',')
                    if len(parts) >= 4:
                        results['eTIV'] = float(parts[3].strip())
                
                if line.startswith('#'):
                    continue
                    
                parts = line.strip().split()
                if len(parts) >= 5:
                    structure = parts[4]
                    if structure in volume_regions:
                        volume_mm3 = float(parts[3])
                        key = volume_regions[structure]
                        results['volumes'][key] = volume_mm3
                        if results['eTIV']:
                            results['volumes'][f"{key}_adjusted"] = volume_mm3 / results['eTIV']
        
        return results
        
    except Exception as e:
        return {
            'error': str(e),
            'volumes': {},
            'eTIV': None
        }

def get_thickness(data_path: str, analysis: str = 'adhd') -> Dict:
    """
    Extract thickness measurements for specific analyses.
    
    Parameters
    ----------
    data_path : str
        Path to FreeSurfer subject directory
    analysis : str
        Type of analysis ('adhd' supported)
        
    Returns
    -------
    dict
        Dictionary with thickness measurements
    """
    try:
        stats_dir = os.path.join(data_path, 'stats')
        
        if analysis == 'adhd':
            thickness_regions = {
                'superiorfrontal': 'dlpfc',
                'rostralmiddlefrontal': 'dlpfc',
                'caudalmiddlefrontal': 'dlpfc',
                'lateralorbitofrontal': 'ofc',
                'medialorbitofrontal': 'ofc',
                'rostralanteriorcingulate': 'acc',
                'caudalanteriorcingulate': 'acc'
            }
        else:
            raise ValueError(f"Analysis type '{analysis}' not supported")
        
        results = {'thickness': {}}
        
        for hemi in ['lh', 'rh']:
            aparc_file = os.path.join(stats_dir, f'{hemi}.aparc.DKTatlas.mapped.stats')
            if not os.path.exists(aparc_file):
                aparc_file = os.path.join(stats_dir, f'{hemi}.aparc.stats')

            with open(aparc_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                        
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        region = parts[0]
                        if region in thickness_regions:
                            thickness_mm = float(parts[4])
                            region_type = thickness_regions[region]
                            key = f"{hemi}_{region_type}_{region}"
                            results['thickness'][key] = thickness_mm
        
        return results
        
    except Exception as e:
        return {
            'error': str(e),
            'thickness': {}
        }







# ----------------------------------
# Outlier Analysis Script
# ----------------------------------