# MRI_Scan

## Description

Fun analysis on my brain. Feel free to check it out!

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
- **Scanner**: Philips (inferred from file naming convention)
- **Functional runs**: 3 task-based fMRI sessions
- **Repetition Time (TR)**: 1000ms for fMRI sequences
- **File naming**: BIDS-compatible structure with timestamp information

### Outside Data Sources
- ADHD-200: http://fcon_1000.projects.nitrc.org/indi/adhd200/
- OpenNeuro

### Pre-Processed Datasets
- The ADHD200/WashU preprocessed dataset was downloaded at this link (9GB): https://www.nitrc.org/frs/downloadlink.php/3270
- For a custom preprocessing pieline, the run.sh script can be run.

## Table of Contents

- [Dataset](#dataset)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Built With](#built-with)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Changelog](#changelog)
- [Roadmap](#roadmap)

## Features

- Feature 1: Description of key feature
- Feature 2: Description of another feature
- Feature 3: Description of additional functionality
- Cross-platform compatibility
- Easy to use interface

## Installation

### Prerequisites

```bash
# Example prerequisites
python >= 3.8
pip
git
```

### Quick Start

```bash
# Clone the repository
git clone https://github.com/username/MRI_Scan.git

# Navigate to the project directory
cd MRI_Scan

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### Basic Usage

```python
# Basic usage example
from mri_scan import MRIProcessor

processor = MRIProcessor()
result = processor.process_scan("path/to/scan.nii")
print(f"Processing complete: {result}")
```

### Command Line Interface

```bash
# Command line usage examples
mri_scan --input data/scan.nii --output results/
mri_scan --help
```

## Built With

- [Python](https://python.org/) - Programming language
- [NumPy](https://numpy.org/) - Numerical computing
- [NiBabel](https://nipy.org/nibabel/) - Neuroimaging file I/O
- [SciPy](https://scipy.org/) - Scientific computing
- [Matplotlib](https://matplotlib.org/) - Plotting library

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Shoutout to ZK, who provided me with my data
- ADHD200 Dataset ()
- OpenNeuro Dataset ()

## Changelog

### [1.0.0] - 2025-10-30
- Initial release
- Basic MRI scan processing functionality
- Support for NIfTI file format

### [0.2.0] - 2025-10-15
- Added batch processing
- Improved error handling
- Added configuration file support

### [0.1.0] - 2025-10-01
- Initial development version
- Basic file loading capabilities

## Roadmap

- [ ] Review and customize WashU data preprocessing
- [ ] Outline ADHD analysis workflow