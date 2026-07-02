import subprocess
import os
from pathlib import Path
from typing import Dict, Optional
import nibabel as nib

human_readable_cols = {
    '7T_Full_MR_Compl': '7T Full MR Complete',
    'MEG_FullProt_Compl': 'MEG Full Protocol Complete',
    'FS_IntraCranial_Vol': 'FS Intracranial',
    'FS_BrainSeg_Vol': 'FS Brain Segment',
    'FS_LCort_GM_Vol': 'FS Left Cortex Gray Matter',
    'FS_RCort_GM_Vol': 'FS Right Cortex Gray Matter',
    'FS_TotCort_GM_Vol': 'FS Total Cortex Gray Matter',
    'FS_SubCort_GM_Vol': 'FS Subcortical Gray Matter',
    'FS_Total_GM_Vol': 'FS Total Gray Matter',
    'FS_L_WM_Vol': 'FS Left White Matter',
    'FS_R_WM_Vol': 'FS Right White Matter',
    'FS_Tot_WM_Vol': 'FS Total White Matter',
    'FS_L_LatVent_Vol': 'FS Left Lateral Ventricle',
    'FS_L_Cerebellum_Cort_Vol': 'FS Left Cerebellum Cortex',
    'FS_L_ThalamusProper_Vol': 'FS Left Thalamus Proper',
    'FS_L_Caudate_Vol': 'FS Left Caudate',
    'FS_L_Putamen_Vol': 'FS Left Putamen',
    'FS_L_Pallidum_Vol': 'FS Left Pallidum',
    'FS_3rdVent_Vol': 'FS 3rd Ventricle',
    'FS_4thVent_Vol': 'FS 4th Ventricle',
    'FS_BrainStem_Vol': 'FS Brain Stem',
    'FS_L_Hippo_Vol': 'FS Left Hippocampus',
    'FS_L_Amygdala_Vol': 'FS Left Amygdala',
    'FS_L_AccumbensArea_Vol': 'FS Left Accumbens Area',
    'FS_R_LatVent_Vol': 'FS Right Lateral Ventricle',
    'FS_R_Cerebellum_Cort_Vol': 'FS Right Cerebellum Cortex',
    'FS_R_ThalamusProper_Vol': 'FS Right Thalamus Proper',
    'FS_R_Caudate_Vol': 'FS Right Caudate',
    'FS_R_Putamen_Vol': 'FS Right Putamen',
    'FS_R_Pallidum_Vol': 'FS Right Pallidum',
    'FS_R_Hippo_Vol': 'FS Right Hippocampus',
    'FS_R_Amygdala_Vol': 'FS Right Amygdala',
    'FS_R_AccumbensArea_Vol': 'FS Right Accumbens Area',
    'FS_L_Caudalanteriorcingulate_Thck': 'FS Left Caudal Anterior Cingulate',
    'FS_L_Caudalmiddlefrontal_Thck': 'FS Left Caudal Middle Frontal',
    'FS_L_Cuneus_Thck': 'FS Left Cuneus',
    'FS_L_Entorhinal_Thck': 'FS Left Entorhinal',
    'FS_L_Fusiform_Thck': 'FS Left Fusiform',
    'FS_L_Inferiorparietal_Thck': 'FS Left Inferior Parietal',
    'FS_L_Inferiortemporal_Thck': 'FS Left Inferior Temporal',
    'FS_L_Isthmuscingulate_Thck': 'FS Left Isthmus Cingulate',
    'FS_L_Lateraloccipital_Thck': 'FS Left Lateral Occipital',
    'FS_L_Lateralorbitofrontal_Thck': 'FS Left Lateral Orbitofrontal',
    'FS_L_Lingual_Thck': 'FS Left Lingual',
    'FS_L_Medialorbitofrontal_Thck': 'FS Left Medial Orbitofrontal',
    'FS_L_Middletemporal_Thck': 'FS Left Middle Temporal',
    'FS_L_Parahippocampal_Thck': 'FS Left Parahippocampal',
    'FS_L_Paracentral_Thck': 'FS Left Paracentral',
    'FS_L_Pericalcarine_Thck': 'FS Left Pericalcarine',
    'FS_L_Postcentral_Thck': 'FS Left Postcentral',
    'FS_L_Precentral_Thck': 'FS Left Precentral',
    'FS_L_Precuneus_Thck': 'FS Left Precuneus',
    'FS_L_Rostralanteriorcingulate_Thck': 'FS Left Rostral Anterior Cingulate',
    'FS_L_Rostralmiddlefrontal_Thck': 'FS Left Rostral Middle Frontal',
    'FS_L_Superiorfrontal_Thck': 'FS Left Superior Frontal',
    'FS_L_Superiorparietal_Thck': 'FS Left Superior Parietal',
    'FS_L_Superiortemporal_Thck': 'FS Left Superior Temporal',
    'FS_L_Supramarginal_Thck': 'FS Left Supramarginal',
    'FS_L_Insula_Thck': 'FS Left Insula',
    'FS_R_Caudalanteriorcingulate_Thck': 'FS Right Caudal Anterior Cingulate',
    'FS_R_Caudalmiddlefrontal_Thck': 'FS Right Caudal Middle Frontal',
    'FS_R_Cuneus_Thck': 'FS Right Cuneus',
    'FS_R_Entorhinal_Thck': 'FS Right Entorhinal',
    'FS_R_Fusiform_Thck': 'FS Right Fusiform',
    'FS_R_Inferiorparietal_Thck': 'FS Right Inferior Parietal',
    'FS_R_Inferiortemporal_Thck': 'FS Right Inferior Temporal',
    'FS_R_Isthmuscingulate_Thck': 'FS Right Isthmus Cingulate',
    'FS_R_Lateraloccipital_Thck': 'FS Right Lateral Occipital',
    'FS_R_Lateralorbitofrontal_Thck': 'FS Right Lateral Orbitofrontal',
    'FS_R_Lingual_Thck': 'FS Right Lingual',
    'FS_R_Medialorbitofrontal_Thck': 'FS Right Medial Orbitofrontal',
    'FS_R_Middletemporal_Thck': 'FS Right Middle Temporal',
    'FS_R_Parahippocampal_Thck': 'FS Right Parahippocampal',
    'FS_R_Paracentral_Thck': 'FS Right Paracentral',
    'FS_R_Pericalcarine_Thck': 'FS Right Pericalcarine',
    'FS_R_Postcentral_Thck': 'FS Right Postcentral',
    'FS_R_Posteriorcingulate_Thck': 'FS Right Posterior Cingulate',
    'FS_R_Precentral_Thck': 'FS Right Precentral',
    'FS_R_Precuneus_Thck': 'FS Right Precuneus',
    'FS_R_Rostralanteriorcingulate_Thck': 'FS Right Rostral Anterior Cingulate',
    'FS_R_Rostralmiddlefrontal_Thck': 'FS Right Rostral Middle Frontal',
    'FS_R_Superiorfrontal_Thck': 'FS Right Superior Frontal',
    'FS_R_Superiorparietal_Thck': 'FS Right Superior Parietal',
    'FS_R_Superiortemporal_Thck': 'FS Right Superior Temporal',
    'FS_R_Supramarginal_Thck': 'FS Right Supramarginal',
    'FS_R_Insula_Thck': 'FS Right Insula'
}

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


def run_fastsurfer_docker(subjects: list, 
                          input_dir: str, output_dir: str, 
                          freesurfer_license: str, 
                          n_threads=4
                          ) -> Dict:
    """
    Run FastSurfer using Docker directly after preprocessing.
    
    Parameters:
    -----------
    subjects : list
        List of subject IDs to process
    input_dir : str or Path
        Directory containing organized subject data (for Docker mount)
    output_dir : str or Path
        Directory for FastSurfer output
    freesurfer_license : str or Path
        Path to FreeSurfer license file
    n_threads : int, default=4
        Number of threads to use
    
    Returns:
    --------
    dict : Results of FastSurfer processing for each subject
    """
    
    input_dir = Path(input_dir).resolve()
    output_dir = Path(output_dir).resolve()
    freesurfer_license = Path(freesurfer_license).resolve()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get current user ID and group ID
    uid = str(os.getuid())
    gid = str(os.getgid())
    print("=" * 60)
    print("Running FastSurfer with Docker")
    print("=" * 60)
    print("")

    for subject_id in subjects:        
        # Get T1 file path relative to input_dir
        subj_dir = input_dir / subject_id
        
        # Find the T1 file in the subject's anat directory
        anat_dir = subj_dir / "anat"
        t1_files = list(anat_dir.glob(f"{subject_id}_T1w.nii.gz"))
        
        if not t1_files:
            print(f"  ✗ T1w file not found in {anat_dir}")
            continue

        t1_filename = t1_files[0].name

        docker_cmd = [
            "docker", "run", "--rm",
            # "--gpus", "all",                     # GPU access
            "-u", f"{uid}:{gid}",                # Run as current user
            "-e", "HOME=/tmp",
            "-e", f"OMP_NUM_THREADS={n_threads}",
            "-e", "FS_LICENSE=/opt/freesurfer/license.txt",
            "-v", f"{input_dir}:/input:ro",
            "-v", f"{output_dir}:/output",
            "-v", f"{freesurfer_license}:/opt/freesurfer/license.txt:ro",
            "deepmi/fastsurfer:latest",
            "--t1", f"/input/{subject_id}/anat/{t1_filename}",
            "--sid", subject_id,
            # "--sd", f"{output_dir}",
            "--sd", "/output",
            "--threads", str(n_threads),
            "--viewagg_device", "cpu",
            "--vox_size", "1.0",
        ]

        print(f"  Running FastSurfer...")
        print(f"  Command:\n    " + " \\\n    ".join(docker_cmd))

        try:
            subprocess.run(
                docker_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=86400  # 24h ceiling — FastSurfer runs can take many hours per subject
            )

            print(f"  ✓ FastSurfer completed successfully!")
            print(f"  Output: {output_dir / subject_id}")

        except subprocess.CalledProcessError as e:
            print(f"  ✗ FastSurfer failed (exit {e.returncode})")
            if e.stdout:
                print("  STDOUT:\n", e.stdout[-3000:])
            if e.stderr:
                print("  STDERR:\n", e.stderr[-3000:])
            raise
        except Exception as e:
            print(f"  ✗ FastSurfer failed: {str(e)}")
            raise
        
        print("")

    print(f"FastSurfer processing complete")
    print("=" * 60)


def prepare_for_fastsurfer(input_dir):
    """
    Prepare organized T1w scans for FastSurfer processing.
    
    - Reads from organized subject directories
    - Checks orientation (converts to RAS if needed)
    - Compresses to .nii.gz format
    - Generates FastSurfer command scripts
    
    Parameters:
    -----------
    input_dir : str or Path
        Directory containing organized subject folders (e.g., organized_lab_data/)
    
    Returns:
    --------
    dict : Dictionary with FastSurfer commands and ready files
    """
    input_dir = Path(input_dir)
    
    print("=" * 60)
    print("Preparing zipped T1w scans for FastSurfer...")
    print("=" * 60)
    print(f"Input: {input_dir}")
    print("")
    
    subjects = []
    
    # Scan input directory for subject folders
    for subject_dir in sorted(input_dir.iterdir()):
        if not subject_dir.is_dir():
            continue
        
        subject_id = subject_dir.name
        subjects.append(subject_id)
        anat_dir = subject_dir / "anat"

        # Prepare FastSurfer-ready file     
        t1_ready = anat_dir / f"{subject_id}_T1w.nii.gz"
        if t1_ready.exists():
            print(f"FastSurfer-ready file already exists: {t1_ready.name}")
            continue
        
        # Look for T1w file
        t1_files = list(anat_dir.glob(f"{subject_id}_T1w.nii"))
        if not t1_files:
            print(f"⚠ Skipping {subject_id}: No unzipped T1w scan found")
            continue

        t1_file = t1_files[0]

        print(f"[{subject_id}]")
        
        # Load and check T1w scan
        img = nib.load(t1_file)
        header = img.header
        affine = img.affine
        
        voxel_sizes = header.get_zooms()[:3]
        orientation = nib.aff2axcodes(affine)
        
        # Check if resolution is suitable for FastSurfer
        if max(voxel_sizes) > 1.5:
            print(f"  ⚠ Warning: Voxel size > 1.5mm may reduce accuracy")
        elif min(voxel_sizes) < 0.7:
            print(f"  ℹ Very high resolution (will increase processing time)")
        else:
            print(f"  ✓ Resolution optimal for FastSurfer (0.7-1.5mm)")
        
        # Reorient to RAS if needed
        if orientation != ('R', 'A', 'S'):
            print(f"  Reorienting from {orientation} to RAS...")
            img_reoriented = nib.as_closest_canonical(img)
            nib.save(img_reoriented, t1_ready)
            print(f"  ✓ Reoriented and saved")
        else:
            print(f"  ✓ Already in RAS orientation")
            nib.save(img, t1_ready)
        
    
    print(f"✓ {len(subjects)} subject(s) are ready for FastSurfer")
    print("")
    
    return subjects


def preprocess_lab_data(input_dir: str = '/lab_data',
                        output_dir: str = '/processed_data/adhd_lab',
                        freesurfer_license: Optional[str] = None):
    subjects = prepare_for_fastsurfer(input_dir=input_dir)
    output_dir = os.path.abspath(output_dir)
    run_fastsurfer_docker(
        subjects=subjects,
        input_dir=input_dir,
        output_dir=output_dir,
        freesurfer_license=freesurfer_license,
        n_threads=8
    )


def process_upload_job(job: dict) -> dict:
    job_id = job.get("job_id")
    file_path = job.get("file_path")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    img = nib.load(file_path)
    # TODO: Run FastSurfer preprocessing and analysis on this file
    return {
        "shape": list(img.shape),
        "dtype": str(img.get_data_dtype())
    }