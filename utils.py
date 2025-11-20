import subprocess
import os
from pathlib import Path
from typing import Dict

def run_fastsurfer_docker(subjects: list, 
                          input_dir: str, output_dir: str, 
                          freesurfer_license: str, 
                          n_threads=8
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
    n_threads : int, default=8
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
    
    results = {}

    for subject_id in subjects:
        print(f"[{subject_id}]")
        
        # Get T1 file path relative to input_dir
        subj_dir = input_dir / subject_id
        
        # Find the T1 file in the subject's anat directory
        anat_dir = subj_dir / "anat"
        t1_files = list(anat_dir.glob(f"{subject_id}_T1w.nii.gz"))
        
        if not t1_files:
            print(f"  ✗ T1w file not found in {anat_dir}")
            results[subject_id] = {'status': 'failed', 'error': 'T1w file not found'}
            continue

        t1_filename = t1_files[0].name

        docker_cmd = [
            "docker", "run", "--rm",
            "--gpus", "all",                     # GPU access
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
        print(f"  Command: {' '.join(docker_cmd[:10])}...")

        try:
            subprocess.run(
                docker_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            print(f"  ✓ FastSurfer completed successfully!")

            results[subject_id] = {
                'status': 'success',
                'output_dir': str(output_dir / subject_id)
            }
            
        except Exception as e:
            print(f"  ✗ FastSurfer failed: {str(e)}")
            results[subject_id] = {'status': 'failed', 'error': str(e)}
        
        print("")

    print(f"FastSurfer processing complete")
    print("=" * 60)
    
    # Summary
    success_count = sum(1 for r in results.values() if r['status'] == 'success')
    print(f"Successful: {success_count}/{len(results)}")
    print("")
    
    return results
