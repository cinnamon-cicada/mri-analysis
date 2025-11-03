import os
import json
import shutil
import nibabel as nib
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess
import re
from typing import Dict, List, Optional


# ----------------------------------------------------------------------
# Preprocessing functions for ADHD-200 dataset
# ----------------------------------------------------------------------
def preprocess_adhd200(
    input_dir: str,
    output_dir: str,
    subjects_dir: str = '../processed_data/freesurfer_washu',
    n_threads: int = 4
) -> Dict[str, str]:
    """
    Run FreeSurfer's complete recon-all pipeline for structural morphometry.
    
    Parameters
    ----------
    input_dir : str
        Directory containing input data (subject directories with anatomical files)
    output_dir : str
        Directory to save processed outputs (same as subjects_dir for FreeSurfer)
    subjects_dir : str
        Path to FreeSurfer subjects directory
    n_threads : int
        Number of parallel threads (default: 4)
        
    Returns: None.
    """    
    # List all subject directories
    children = [dir for dir in os.listdir(input_dir) 
                if os.path.isdir(os.path.join(input_dir, dir))]
    
    for child in children:
        subject_dir = os.path.join(input_dir, child)
        
        # Find the anatomical T1 file within this subject directory
        anat_files = [f for f in os.listdir(subject_dir) 
                        if re.match(r"wssd.*_session_.*_anat\.nii\.gz$", f)]
        
        if not anat_files:
            print(f"No anatomical file found for {child}, skipping...")
            continue
        
        # Use first matching file
        input_t1 = os.path.join(subject_dir, anat_files[0])
        subject_id = child  # Use directory name as subject ID
        
        print(f"Processing {subject_id}...")
        
        # Run FreeSurfer recon-all
        cmd = [
            'recon-all',
            '-i', input_t1,
            '-subjid', subject_id,
            '-sd', output_dir,
            '-openmp', str(n_threads),
            '-all',
            '-parallel',
            '-wsthresh', '25',
            '-3T'
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    return





# ----------------------------------------------------------------------
# Preprocessing functions for OpenNeuro BIDS conversion
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


# ----------------------------------------------------------------------
# ADHD-200 Pre-Processing
# ----------------------------------------------------------------------

def preprocess_adhd200(
    input_dir,
    output_dir,
    phenotypic_file=None,
    pipeline='athena',
    create_bids=True
):
    """
    Preprocess ADHD-200 dataset for analysis and comparison.
    
    The ADHD-200 dataset contains resting-state fMRI and structural MRI from
    973 participants across 8 sites. Data is typically preprocessed using
    Athena, NIAK, or Burner pipelines.
    
    Parameters:
    -----------
    input_dir : str or Path
        Directory containing ADHD-200 downloaded data
        Expected structure: input_dir/subject_id/
    output_dir : str or Path
        Output directory for standardized dataset
    phenotypic_file : str or Path, optional
        Path to phenotypic CSV file with participant metadata
    pipeline : str, default='athena'
        Preprocessing pipeline used ('athena', 'niak', or 'burner')
    create_bids : bool, default=True
        Whether to convert to BIDS format (recommended for comparison)
    
    Returns:
    --------
    dict : Summary of processed subjects with metadata
    """
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load phenotypic data if provided
    phenotypic_data = None
    if phenotypic_file:
        phenotypic_data = pd.read_csv(phenotypic_file)
    
    # Track processed subjects
    processed_subjects = []
    
    # Process each site
    for site_dir in input_dir.iterdir():
        if not site_dir.is_dir():
            continue

    # Process each subject in the site
    for subject_dir in site_dir.iterdir():
        if not subject_dir.is_dir():
            continue
        
        subject_id = subject_dir.name
        
        try:
            subject_info = _process_adhd_subject(
                subject_dir=subject_dir,
                output_dir=output_dir,
                subject_id=subject_id,
                site_name="WashU",  # Test site name; adapt as needed
                phenotypic_data=phenotypic_data,
                pipeline=pipeline,
                create_bids=create_bids
            )
            
            processed_subjects.append(subject_info)
            print(f"  ✓ Processed {subject_id}")
            
        except Exception as e:
            print(f"  ✗ Error processing {subject_id}: {str(e)}")
            continue
    
    # Create summary files
    summary_df = pd.DataFrame(processed_subjects)
    summary_df.to_csv(output_dir / "processing_summary.csv", index=False)
    
    # Create dataset description
    if create_bids:
        _create_adhd_dataset_description(output_dir, pipeline)
    
    # Generate QC report
    _generate_adhd_qc_report(summary_df, output_dir)
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"Total subjects processed: {len(processed_subjects)}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")
    
    return {
        'n_subjects': len(processed_subjects),
        'sites': summary_df['site'].unique().tolist() if 'site' in summary_df else [],
        'diagnosis_breakdown': summary_df['diagnosis'].value_counts().to_dict() if 'diagnosis' in summary_df else {},
        'summary_file': str(output_dir / "processing_summary.csv")
    }


def _process_adhd_subject(
    subject_dir,
    output_dir,
    subject_id,
    site_name,
    phenotypic_data,
    pipeline,
    create_bids
):
    """Process individual ADHD-200 subject."""
    
    # Get phenotypic info for this subject
    subject_pheno = None
    diagnosis = "unknown"
    age = None
    sex = None
    
    if phenotypic_data is not None:
        subject_row = phenotypic_data[
            (phenotypic_data['ScanDirID'] == int(subject_id)) | 
            (phenotypic_data['SubjectID'] == int(subject_id))
        ]
        if not subject_row.empty:
            subject_pheno = subject_row.iloc[0]
            diagnosis = subject_pheno.get('DX', 'unknown')
            age = subject_pheno.get('Age', None)
            sex = subject_pheno.get('Gender', None)
    
    # Find functional and anatomical files
    func_files = list(subject_dir.glob(f"**/func/*{pipeline}*.nii.gz"))
    anat_files = list(subject_dir.glob(f"**/anat/*.nii.gz"))
    
    if not func_files:
        func_files = list(subject_dir.glob("**/rest*.nii.gz"))
    if not anat_files:
        anat_files = list(subject_dir.glob("**/mprage*.nii.gz"))
    
    # Create output structure
    if create_bids:
        subject_label = f"sub-{site_name}{subject_id}"
        subject_out_dir = output_dir / subject_label
        func_out_dir = subject_out_dir / "func"
        anat_out_dir = subject_out_dir / "anat"
    else:
        subject_out_dir = output_dir / site_name / subject_id
        func_out_dir = subject_out_dir / "func"
        anat_out_dir = subject_out_dir / "anat"
    
    func_out_dir.mkdir(parents=True, exist_ok=True)
    anat_out_dir.mkdir(parents=True, exist_ok=True)
    
    # Process functional files
    func_processed = []
    for func_file in func_files:
        if create_bids:
            out_name = f"{subject_label}_task-rest_bold.nii.gz"
        else:
            out_name = func_file.name
        
        out_path = func_out_dir / out_name
        shutil.copy2(func_file, out_path)
        func_processed.append(str(out_path.relative_to(output_dir)))
        
        # Create JSON sidecar with metadata
        _create_adhd_json_sidecar(
            out_path.with_suffix('.json'),
            modality='func',
            site=site_name,
            pipeline=pipeline,
            diagnosis=diagnosis,
            age=age,
            sex=sex
        )
    
    # Process anatomical files
    anat_processed = []
    for anat_file in anat_files:
        if create_bids:
            out_name = f"{subject_label}_T1w.nii.gz"
        else:
            out_name = anat_file.name
        
        out_path = anat_out_dir / out_name
        shutil.copy2(anat_file, out_path)
        anat_processed.append(str(out_path.relative_to(output_dir)))
        
        # Create JSON sidecar
        _create_adhd_json_sidecar(
            out_path.with_suffix('.json'),
            modality='anat',
            site=site_name,
            pipeline=pipeline,
            diagnosis=diagnosis,
            age=age,
            sex=sex
        )
    
    return {
        'subject_id': subject_id,
        'site': site_name,
        'diagnosis': diagnosis,
        'age': age,
        'sex': sex,
        'n_func_files': len(func_processed),
        'n_anat_files': len(anat_processed),
        'func_files': func_processed,
        'anat_files': anat_processed
    }


def _create_adhd_json_sidecar(json_path, modality, site, pipeline, 
                               diagnosis, age, sex):
    """
    Create JSON sidecar for ADHD-200 data.
    
    Note: This reuses the concept from preprocess_openneuro() but adapts
    it for ADHD-200 specific metadata structure.
    """
    
    metadata = {
        "Dataset": "ADHD-200",
        "Site": site,
        "PreprocessingPipeline": pipeline,
    }
    
    # Add phenotypic data
    if diagnosis != "unknown":
        metadata["Diagnosis"] = diagnosis
    if age is not None:
        metadata["Age"] = float(age)
    if sex is not None:
        metadata["Sex"] = sex
    
    # Add modality-specific metadata
    if modality == 'func':
        metadata.update({
            "TaskName": "rest",
            "Modality": "resting-state fMRI",
            "Comments": "Preprocessed resting-state functional MRI"
        })
    elif modality == 'anat':
        metadata.update({
            "Modality": "T1-weighted structural MRI",
            "Comments": "Structural anatomical scan"
        })
    
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=4)


def _create_adhd_dataset_description(output_dir, pipeline):
    """
    Create dataset_description.json for ADHD-200.
    
    This function is similar to the one used in preprocess_openneuro(),
    demonstrating reuse of the BIDS structure concept.
    """
    
    description = {
        "Name": "ADHD-200 Preprocessed Dataset",
        "BIDSVersion": "1.9.0",
        "DatasetType": "derivative",
        "GeneratedBy": [{
            "Name": f"ADHD-200 {pipeline.upper()} Pipeline",
            "Description": f"Preprocessed using the {pipeline} pipeline"
        }],
        "SourceDatasets": [{
            "DOI": "10.1016/j.neuroimage.2016.06.034",
            "URL": "http://fcon_1000.projects.nitrc.org/indi/adhd200/",
            "Version": "1.0"
        }],
        "License": "CC0",
        "Authors": [
            "ADHD-200 Consortium",
            "Preprocessed Connectomes Project"
        ],
        "ReferencesAndLinks": [
            "http://preprocessed-connectomes-project.org/adhd200/",
            "http://fcon_1000.projects.nitrc.org/indi/adhd200/"
        ]
    }
    
    with open(output_dir / "dataset_description.json", 'w') as f:
        json.dump(description, f, indent=4)


def _generate_adhd_qc_report(summary_df, output_dir):
    """Generate quality control report for ADHD-200 processing."""
    
    report_path = output_dir / "qc_report.txt"
    
    with open(report_path, 'w') as f:
        f.write("ADHD-200 Processing Quality Control Report\n")
        f.write("=" * 60 + "\n\n")
        
        # Overall statistics
        f.write(f"Total subjects processed: {len(summary_df)}\n")
        
        if 'site' in summary_df:
            f.write(f"\nSubjects per site:\n")
            for site, count in summary_df['site'].value_counts().items():
                f.write(f"  {site}: {count}\n")
        
        if 'diagnosis' in summary_df:
            f.write(f"\nDiagnosis breakdown:\n")
            for dx, count in summary_df['diagnosis'].value_counts().items():
                f.write(f"  {dx}: {count}\n")
        
        if 'age' in summary_df:
            f.write(f"\nAge statistics:\n")
            f.write(f"  Mean: {summary_df['age'].mean():.2f}\n")
            f.write(f"  Std: {summary_df['age'].std():.2f}\n")
            f.write(f"  Range: {summary_df['age'].min():.0f}-{summary_df['age'].max():.0f}\n")
        
        if 'sex' in summary_df:
            f.write(f"\nSex distribution:\n")
            for sex, count in summary_df['sex'].value_counts().items():
                f.write(f"  {sex}: {count}\n")
        
        f.write(f"\nData completeness:\n")
        f.write(f"  Subjects with functional data: {(summary_df['n_func_files'] > 0).sum()}\n")
        f.write(f"  Subjects with anatomical data: {(summary_df['n_anat_files'] > 0).sum()}\n")
    
    print(f"\nQC report saved to: {report_path}")


# Additional utility functions for ADHD-200 specific processing

def download_adhd_phenotypic():
    """
    Helper function to download ADHD-200 phenotypic data.
    
    Returns the path to the downloaded CSV file.
    """
    import urllib.request
    
    phenotypic_url = "https://fcon_1000.projects.nitrc.org/indi/adhd200/ADHD200_40sub_preprocessed/phenotypic/ADHD200_40sub_preprocessed_phenotypics.csv"
    output_file = "adhd200_phenotypics.csv"
    
    print(f"Downloading phenotypic data from NITRC...")
    urllib.request.urlretrieve(phenotypic_url, output_file)
    print(f"Downloaded: {output_file}")
    
    return output_file


def align_adhd_to_openneuro_format(adhd_dir, subject_id):
    """
    Convert ADHD-200 subject to match OpenNeuro-compatible format.
    
    This function bridges the two preprocessing functions, allowing
    ADHD-200 data to be formatted like OpenNeuro data.
    
    Parameters:
    -----------
    adhd_dir : str or Path
        Directory with ADHD-200 BIDS-formatted subject
    subject_id : str
        Subject identifier
    
    Returns:
    --------
    dict : Mapping of files and metadata
    """
    
    adhd_dir = Path(adhd_dir)
    subject_dir = adhd_dir / f"sub-{subject_id}"
    
    # Load ADHD-200 metadata
    func_json = list((subject_dir / "func").glob("*.json"))
    anat_json = list((subject_dir / "anat").glob("*.json"))
    
    alignment_info = {
        'subject_id': subject_id,
        'functional': {},
        'anatomical': {}
    }
    
    # Map functional data
    if func_json:
        with open(func_json[0], 'r') as f:
            func_meta = json.load(f)
        alignment_info['functional'] = {
            'task': 'rest',
            'acquisition_type': 'resting-state',
            'original_site': func_meta.get('Site'),
            'preprocessing': func_meta.get('PreprocessingPipeline')
        }
    
    # Map anatomical data
    if anat_json:
        with open(anat_json[0], 'r') as f:
            anat_meta = json.load(f)
        alignment_info['anatomical'] = {
            'modality': 'T1w',
            'original_site': anat_meta.get('Site')
        }
    
    return alignment_info