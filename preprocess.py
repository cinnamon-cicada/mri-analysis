import os
import glob
import json
import shutil
import nibabel as nib
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess
import re
from typing import Dict, List, Optional
from utils import run_fastsurfer_docker

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
    print(f"Using FreeSurfer license: {freesurfer_license}")

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

        t1_path = t1_files[0]
        print(f"Pre-processing {subj} with file: {os.path.basename(t1_path)}")

        # Run FastSurfer Docker command
        run_fastsurfer_docker(subj, input_dir, output_dir, freesurfer_license, n_threads)

# ----------------------------------------------------------------------
# 2. Preprocessing function for ADHD-200 dataset - LAB DATASET
# ----------------------------------------------------------------------

def extract_subject_info(filename):
    """
    Extract subject ID and scan info from your filename format.
    Example: SUBJECT_XXX.02.01.08-12-58.WIP_cs_2.8_T1W_3D_TFE.01.nii
    Returns: (subject_id, series_num, scan_type)
    """
    parts = filename.split('.')
    subject_id = parts[0]  # "SUBJECT_XXX"
    series_num = parts[1]   # "02", "03", etc.
    
    # Extract scan type from middle part
    scan_type = None
    if "SURVEY" in filename:
        scan_type = "localizer"
    elif "T1W_3D_TFE" in filename:
        scan_type = "T1w"
    elif "fMRI_task" in filename:
        scan_type = "func"
    
    return subject_id, series_num, scan_type

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

def preprocess_lab_data(input_dir: str = './lab_data',
                        output_dir: str = './processed_data/adhd_lab',
                        freesurfer_license: Optional[str] = None):
    # Pre-processing step 1: Prepare data for FastSurfer
    subjects = prepare_for_fastsurfer(
        input_dir=input_dir
    )

    output_dir = os.path.abspath(output_dir)
    
    # Pre-processing step 2: Run FastSurfer via Docker
    run_fastsurfer_docker(
        subjects=subjects,
        input_dir=input_dir,
        output_dir=output_dir,
        freesurfer_license=freesurfer_license,
        n_threads=8
    )


# ----------------------------------------------------------------------
# 3. Preprocessing function for OpenNeuro-Dataset - OUTSIDE DATASET
# ----------------------------------------------------------------------

def preprocess_openneuro(
    input_dir,
    output_dir,
    subject_id,
    session_id=None,
    dataset_description=None
):
    """
    Preprocess MRI data to match OpenNeuro BIDS format.
    
    Parameters:
    -----------
    input_dir : str or Path
        Directory containing raw NIfTI files and JSON sidecars
    output_dir : str or Path
        Output directory for BIDS-formatted dataset
    subject_id : str
        Subject identifier (e.g., '001', 'patient01')
    session_id : str, optional
        Session identifier if multiple sessions (e.g., '01', 'baseline')
    dataset_description : dict, optional
        Metadata for dataset_description.json
    
    Returns:
    --------
    dict : Summary of processed files and their BIDS paths
    """
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # Create BIDS directory structure
    subject_label = f"sub-{subject_id}"
    if session_id:
        session_label = f"ses-{session_id}"
        subject_dir = output_dir / subject_label / session_label
    else:
        subject_dir = output_dir / subject_label
    
    anat_dir = subject_dir / "anat"
    func_dir = subject_dir / "func"
    
    anat_dir.mkdir(parents=True, exist_ok=True)
    func_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dataset_description.json at root
    if dataset_description is None:
        dataset_description = {
            "Name": "Custom fMRI Dataset",
            "BIDSVersion": "1.9.0",
            "DatasetType": "raw",
            "Authors": ["Unknown"],
            "License": "CC0"
        }
    
    with open(output_dir / "dataset_description.json", 'w') as f:
        json.dump(dataset_description, f, indent=4)
    
    # Track processed files
    processed_files = {
        "anatomical": [],
        "functional": [],
        "localizer": []
    }
    
    # Process all JSON files in input directory
    for json_file in input_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            metadata = json.load(f)
        
        # Find corresponding NIfTI file
        nifti_file = json_file.with_suffix('.nii.gz')
        if not nifti_file.exists():
            nifti_file = json_file.with_suffix('.nii')
        
        if not nifti_file.exists():
            print(f"Warning: No NIfTI file found for {json_file}")
            continue
        
        # Determine file type and create BIDS filename
        series_desc = metadata.get("SeriesDescription", "")
        series_num = metadata.get("SeriesNumber", 0)
        
        # Build BIDS filename components
        base_name = subject_label
        if session_id:
            base_name += f"_{session_label}"
        
        # Classify and rename based on series description
        if "SURVEY" in series_desc.upper() or series_num == 101:
            # Localizer - store but not typically used in analysis
            bids_name = f"{base_name}_acq-localizer_T1w"
            target_dir = anat_dir
            file_type = "localizer"
            
        elif "T1W" in series_desc.upper() or "T1TFE" in metadata.get("PulseSequenceName", ""):
            # T1-weighted anatomical
            bids_name = f"{base_name}_T1w"
            target_dir = anat_dir
            file_type = "anatomical"
            
        elif "fMRI" in series_desc or "FEEPI" in metadata.get("PulseSequenceName", ""):
            # Functional MRI - determine run number
            if series_num == 301:
                run_num = 1
            elif series_num == 501:
                run_num = 2
            elif series_num == 601:
                run_num = 3
            else:
                run_num = (series_num // 100)
            
            # Extract task name from protocol
            task_name = "task"  # default
            if "task" in series_desc.lower():
                task_name = series_desc.split("task")[1].split("_")[0] if "_" in series_desc else "task"
            
            bids_name = f"{base_name}_task-{task_name}_run-{run_num:02d}_bold"
            target_dir = func_dir
            file_type = "functional"
        
        else:
            print(f"Warning: Unknown series type: {series_desc}")
            continue
        
        # Copy and rename NIfTI file
        target_nifti = target_dir / f"{bids_name}.nii.gz"
        shutil.copy2(nifti_file, target_nifti)
        
        # Create BIDS-compliant JSON sidecar
        bids_json = _create_bids_json(metadata)
        target_json = target_dir / f"{bids_name}.json"
        
        with open(target_json, 'w') as f:
            json.dump(bids_json, f, indent=4)
        
        # Track processed file
        processed_files[file_type].append({
            "original": str(json_file.name),
            "bids_path": str(target_nifti.relative_to(output_dir)),
            "series_number": series_num
        })
        
        print(f"Processed: {json_file.name} -> {target_nifti.relative_to(output_dir)}")
    
    # Create participants.tsv
    _create_participants_file(output_dir, subject_id)
    
    # Create task events files for functional runs (templates)
    for func_file in processed_files["functional"]:
        _create_events_template(
            output_dir,
            Path(func_file["bids_path"]).with_suffix('.tsv')
        )
    
    print(f"\nBIDS dataset created at: {output_dir}")
    print(f"Processed {len(processed_files['anatomical'])} anatomical, "
          f"{len(processed_files['functional'])} functional, "
          f"{len(processed_files['localizer'])} localizer scans")
    
    return processed_files


def _create_bids_json(philips_metadata):
    """Convert Philips JSON to BIDS-compliant JSON."""
    
    bids_json = {
        "Manufacturer": philips_metadata.get("Manufacturer"),
        "ManufacturersModelName": philips_metadata.get("ManufacturersModelName"),
        "MagneticFieldStrength": philips_metadata.get("MagneticFieldStrength"),
        "RepetitionTime": philips_metadata.get("RepetitionTime"),
        "EchoTime": philips_metadata.get("EchoTime"),
        "FlipAngle": philips_metadata.get("FlipAngle"),
        "SliceThickness": philips_metadata.get("SliceThickness"),
        "PhaseEncodingDirection": _get_phase_encoding_direction(philips_metadata),
        "EffectiveEchoSpacing": philips_metadata.get("EstimatedEffectiveEchoSpacing"),
        "TotalReadoutTime": philips_metadata.get("EstimatedTotalReadoutTime"),
    }
    
    # Add functional-specific fields
    if "FEEPI" in philips_metadata.get("PulseSequenceName", ""):
        bids_json.update({
            "TaskName": "task",  # Should be updated based on actual task
            "MultibandAccelerationFactor": philips_metadata.get("ParallelReductionFactorOutOfPlane"),
            "ParallelReductionFactorInPlane": philips_metadata.get("ParallelReductionFactorInPlane"),
        })
    
    # Remove None values
    bids_json = {k: v for k, v in bids_json.items() if v is not None}
    
    return bids_json


def _get_phase_encoding_direction(metadata):
    """Determine BIDS phase encoding direction from Philips metadata."""
    
    pe_axis = metadata.get("PhaseEncodingAxis", "")
    in_plane_dir = metadata.get("InPlanePhaseEncodingDirectionDICOM", "")
    
    # Map Philips encoding to BIDS
    if pe_axis == "j" or in_plane_dir == "COL":
        return "j"  # or "j-" depending on polarity
    elif pe_axis == "i" or in_plane_dir == "ROW":
        return "i"  # or "i-" depending on polarity
    
    return None


def _create_participants_file(output_dir, subject_id):
    """Create participants.tsv file."""
    
    participants_file = output_dir / "participants.tsv"
    
    if not participants_file.exists():
        with open(participants_file, 'w') as f:
            f.write("participant_id\n")
    
    # Append subject if not already present
    with open(participants_file, 'r') as f:
        existing = f.read()
    
    participant_label = f"sub-{subject_id}"
    if participant_label not in existing:
        with open(participants_file, 'a') as f:
            f.write(f"{participant_label}\n")


def _create_events_template(output_dir, events_path):
    """Create template events.tsv file for task fMRI."""
    
    events_file = output_dir / events_path
    
    with open(events_file, 'w') as f:
        f.write("onset\tduration\ttrial_type\n")
        f.write("# Add your task events here\n")
        f.write("# onset: time in seconds from start of acquisition\n")
        f.write("# duration: duration in seconds\n")
        f.write("# trial_type: condition/stimulus type\n")