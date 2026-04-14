# MRI_Scan

## Description

An analysis on my brain, and potential app. Check it out!

## Table of Contents

- [Dataset](#dataset)
- [Pipeline](#pipeline)
- [Installation](#installation)
- [Usage](#usage)
- [Built With](#built-with)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Roadmap](#roadmap)

## Dataset

This project includes MRI scan data from subject cinnamon-cicada, containing multiple sequences acquired during a single scanning session:

### Data Files

The `Data/` directory contains the following MRI sequences:

| Sequence | Description | Files |
|----------|-------------|-------|
| **Survey** | Initial survey/localizer scan | `cinnamon-cicada.01.01.08-11-13.WIP_SURVEY.01.nii/.json` |
| **T1-weighted 3D** | High-resolution structural scan (cs_2.8_T1W_3D_TFE) | `cinnamon-cicada.02.01.08-12-58.WIP_cs_2.8_T1W_3D_TFE.01.nii/.json` |
| **fMRI Task v0 (Run 1)** | Functional MRI with TR=1000ms | `cinnamon-cicada.03.01.08-18-02.WIP_fMRI_task_v0_TR1000.01.nii/.json` |
| **fMRI Task v0 (Run 2)** | Functional MRI with TR=1000ms | `cinnamon-cicada.05.01.08-40-45.WIP_fMRI_task_v0_TR1000.01.nii/.json` |
| **fMRI Task v0 (Run 3)** | Functional MRI with TR=1000ms | `cinnamon-cicada.06.01.08-50-26.WIP_fMRI_task_v0_TR1000.01.nii/.json` |

### File Formats

- **`.nii` files**: NIfTI format containing the actual MRI image data
- **`.json` files**: BIDS-style sidecar files with acquisition parameters and metadata

### Data Specifications

- **Subject ID**: cinnamon-cicada
- **Scanner**: Philips
- **Functional runs**: 3 task-based fMRI sessions
- **Repetition Time (TR)**: 1000ms for fMRI sequences
- **File naming**: BIDS-compatible structure with timestamp information

### Outside Data Sources
- ADHD-200: http://fcon_1000.projects.nitrc.org/indi/adhd200/
- HCP-YA subset: young adult Americans, female

### Pre-Processed Datasets
- The ADHD200/WashU preprocessed dataset was downloaded at this link (9GB): https://www.nitrc.org/frs/downloadlink.php/3270
- For a custom preprocessing pipeline, the run.sh script can be run.

## Pipeline

1. MRI inputs: `./outside_data/[analysis name]`, `./lab_data/[analysis name]`
  1. Each should be organized by subject, with two subdirectories: `anat`, `func`
2. Process using Fastsurfer: `preprocess.py` -> `./processed_data/[analysis name]`
3. Collect final statistics and report: `analysis.py` -> `analysis/[analysis name].json`

## Installation

### FreeSurfer Setup (via Docker)

This project uses FreeSurfer for structural MRI analysis. The library is run through Docker to avoid dependency issues.

#### 1. Install Docker
```bash
# Update package list
sudo apt-get update

# Install Docker. Do NOT use `snap`.
sudo apt-get install -y docker.io

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker

# Verify Docker installation
docker --version
```

#### 2. Pull FreeSurfer Docker Image
```bash
# Pull FreeSurfer 7.4.1 container
docker pull freesurfer/freesurfer:7.4.1

# Verify the image was downloaded
docker images | grep freesurfer
```

#### 3. Get FreeSurfer License (Free)

FreeSurfer requires a free license to run:

1. Register at: https://surfer.nmr.mgh.harvard.edu/registration.html
2. You'll receive a `license.txt` file via email
3. Save it to your project directory or `~/.freesurfer/license.txt`
```bash
# Create FreeSurfer config directory (optional)
mkdir -p ~/.freesurfer

# Move your license file there
mv license.txt ~/.freesurfer/
```

### Project Setup
```bash
# Clone the repository
git clone https://github.com/cinnamon-cicada/mri-analysis

# Navigate to the project directory
cd MRI_Scan

# Create virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Make bash script executable
chmod +x ./bin/run.sh

```

## Usage
// WIP
```bash
Usage:
  ./run.sh [OPTIONS] [ANALYSIS_NUMBERS...]

Options:
  --test       Run in test mode (downloads sample data instead of full)
  --help       Show this help message

Analysis Numbers:
  1            Run ADHD analysis (uses ADHD-200 dataset)
  2            Run uniqueness analysis (uses HCP-YA dataset)
  3            Reserved for future use

Examples:
  ./run.sh 1              # Run analysis 1, download ADHD-200 if needed
  ./run.sh --test 1 2     # Run analyses 1 and 2 in test mode
  ./run.sh 2 1            # Run analysis 2 then analysis 1
  ./run.sh 1 1 2          # Run analysis 1 twice, then analysis 2


# Run the application
python scripts/main.py
```

## Built With

- [Python](https://python.org/) - Programming language
- [NumPy](https://numpy.org/) - Numerical computing
- [NiBabel](https://nipy.org/nibabel/) - Neuroimaging file I/O
- [SciPy](https://scipy.org/) - Scientific computing
- [Matplotlib](https://matplotlib.org/) - Plotting library
- [FreeSurfer](https://surfer.nmr.mgh.harvard.edu/) - Structural MRI analysis (via Docker)
- [Docker](https://www.docker.com/) - Container platform

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Shoutout to ZK, who provided me with my data
- ADHD200 Dataset ()
- OpenNeuro Dataset ()
- FreeSurfer Development Team

## Roadmap

- [ ] Review and customize WashU data preprocessing
- [ ] Outline ADHD analysis workflow
