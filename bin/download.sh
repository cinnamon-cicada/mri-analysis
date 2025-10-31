#!/bin/bash

###############################################################################
# Dataset Download Script for ADHD-200 and OpenNeuro
# Downloads neuroimaging datasets for comparison and analysis
#
# Usage:
#   ./download_datasets.sh [--test] [--adhd] [--openneuro] [--all]
#   
# Options:
#   --test       Download only sample data (~50MB per dataset, 2-3 subjects)
#   --adhd       Download only ADHD-200 dataset
#   --openneuro  Download only OpenNeuro dataset
#   --all        Download both datasets (default)
#   --help       Show this help message
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default settings
TEST_MODE=false
DOWNLOAD_ADHD=false
DOWNLOAD_OPENNEURO=false
BASE_DIR="./outside_data"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_MODE=true
            shift
            ;;
        --adhd)
            DOWNLOAD_ADHD=true
            shift
            ;;
        --openneuro)
            DOWNLOAD_OPENNEURO=true
            shift
            ;;
        --all)
            DOWNLOAD_ADHD=true
            DOWNLOAD_OPENNEURO=true
            shift
            ;;
        --help)
            grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //g' | sed 's/^#//g'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If no specific dataset selected, download all
if [ "$DOWNLOAD_ADHD" = false ] && [ "$DOWNLOAD_OPENNEURO" = false ]; then
    DOWNLOAD_ADHD=true
    DOWNLOAD_OPENNEURO=true
fi

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for required tools
    command -v curl >/dev/null 2>&1 || missing_deps+=("curl")
    command -v aws >/dev/null 2>&1 || missing_deps+=("aws-cli")
    command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "Installation instructions:"
        echo "  - curl: apt-get install curl (Ubuntu/Debian) or brew install curl (macOS)"
        echo "  - aws-cli: pip install awscli or see https://aws.amazon.com/cli/"
        echo "  - python3: apt-get install python3 (Ubuntu/Debian) or brew install python3 (macOS)"
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Function to download ADHD-200 dataset
download_adhd200() {
    print_info "Downloading ADHD-200 dataset..."
    
    local ADHD_DIR="$BASE_DIR/adhd200"
    mkdir -p "$ADHD_DIR"
    
    # Download phenotypic data (always needed)
    print_info "Downloading phenotypic data..."
    curl -o "$ADHD_DIR/adhd200_phenotypics.csv" \
        "https://fcon_1000.projects.nitrc.org/indi/adhd200/ADHD200_40sub_preprocessed/phenotypic/ADHD200_40sub_preprocessed_phenotypics.csv" \
        2>/dev/null || print_warning "Could not download phenotypic file"
    
    if [ "$TEST_MODE" = true ]; then
        print_info "TEST MODE: Downloading 5 sample subjects from Peking University site..."
        
        # Download 5 subjects from Peking University site (preprocessed with Athena pipeline)
        local test_subjects=("0010001" "0010002" "0010003" "0010004" "0010005")
        
        for subject in "${test_subjects[@]}"; do
            print_info "Downloading subject $subject..."
            
            local subject_dir="$ADHD_DIR/Peking_1/$subject"
            mkdir -p "$subject_dir/func"
            mkdir -p "$subject_dir/anat"
            
            # Download functional (resting-state) data from AWS S3
            print_info "  Downloading functional scan..."
            aws s3 cp \
                "s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/Peking_1/sub-${subject}/func/sub-${subject}_task-rest_bold.nii.gz" \
                "$subject_dir/func/rest_bold.nii.gz" \
                --no-sign-request 2>/dev/null || \
                print_warning "Could not download functional data for $subject"
            
            # Download anatomical data from AWS S3
            print_info "  Downloading anatomical scan..."
            aws s3 cp \
                "s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/Peking_1/sub-${subject}/anat/sub-${subject}_T1w.nii.gz" \
                "$subject_dir/anat/T1w.nii.gz" \
                --no-sign-request 2>/dev/null || \
                print_warning "Could not download anatomical data for $subject"
        done
        
        print_success "ADHD-200 test dataset downloaded to $ADHD_DIR"
        
    else
        print_info "FULL MODE: Downloading complete ADHD-200 dataset..."
        print_warning "This will download ~100GB of data and may take several hours"
        
        # Use AWS S3 for faster download of full dataset
        print_info "Using AWS S3 public bucket for Peking University site..."
        
        # Download Peking_1 site from S3 bucket (BIDS format)
        aws s3 sync \
            s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/Peking_1 \
            "$ADHD_DIR/Peking_1" \
            --no-sign-request \
            --exclude "*" \
            --include "*/func/*_task-rest_bold.nii.gz" \
            --include "*/anat/*_T1w.nii.gz"
        
        print_success "ADHD-200 full dataset downloaded to $ADHD_DIR"
    fi
    
    # Calculate and display size
    local size=$(du -sh "$ADHD_DIR" 2>/dev/null | cut -f1)
    print_info "ADHD-200 dataset size: $size"
}

# Function to download OpenNeuro dataset
download_openneuro() {
    print_info "Downloading OpenNeuro dataset..."
    
    local OPENNEURO_DIR="$BASE_DIR/openneuro"
    mkdir -p "$OPENNEURO_DIR"
    
    # We'll use a popular task fMRI dataset that matches your data type
    # ds000109: False belief task fMRI study
    local DATASET_ID="ds000109"
    
    if [ "$TEST_MODE" = true ]; then
        print_info "TEST MODE: Downloading 2 subjects from OpenNeuro dataset $DATASET_ID..."
        
        # Download using OpenNeuro API
        print_info "Downloading dataset descriptor..."
        curl -o "$OPENNEURO_DIR/dataset_description.json" \
            "https://openneuro.org/crn/datasets/$DATASET_ID/files/dataset_description.json" \
            2>/dev/null
        
        # Download specific subjects (sub-01 - sub-05)
        local test_subjects=("01" "02" "03" "04" "05")
        
        for subject in "${test_subjects[@]}"; do
            print_info "Downloading subject sub-$subject..."
            
            local subject_dir="$OPENNEURO_DIR/sub-$subject"
            mkdir -p "$subject_dir/anat"
            mkdir -p "$subject_dir/func"
            
            # Download anatomical T1w
            print_info "  Downloading anatomical scan..."
            curl -f -o "$subject_dir/anat/sub-${subject}_T1w.nii.gz" \
                "https://openneuro.org/crn/datasets/$DATASET_ID/files/sub-${subject}:anat:sub-${subject}_T1w.nii.gz" \
                2>/dev/null || print_warning "Could not download T1w for sub-$subject"
            
            curl -f -o "$subject_dir/anat/sub-${subject}_T1w.json" \
                "https://openneuro.org/crn/datasets/$DATASET_ID/files/sub-${subject}:anat:sub-${subject}_T1w.json" \
                2>/dev/null
            
            # Download functional task runs (usually multiple runs)
            for run in {1..2}; do
                print_info "  Downloading functional run $run..."
                curl -f -o "$subject_dir/func/sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_bold.nii.gz" \
                    "https://openneuro.org/crn/datasets/$DATASET_ID/files/sub-${subject}:func:sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_bold.nii.gz" \
                    2>/dev/null || print_warning "Could not download run $run for sub-$subject"
                
                curl -f -o "$subject_dir/func/sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_bold.json" \
                    "https://openneuro.org/crn/datasets/$DATASET_ID/files/sub-${subject}:func:sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_bold.json" \
                    2>/dev/null
                
                curl -f -o "$subject_dir/func/sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_events.tsv" \
                    "https://openneuro.org/crn/datasets/$DATASET_ID/files/sub-${subject}:func:sub-${subject}_task-theoryofmindwithplausibleevents_run-0${run}_events.tsv" \
                    2>/dev/null
            done
        done
        
        print_success "OpenNeuro test dataset downloaded to $OPENNEURO_DIR"
        
    else
        print_info "FULL MODE: Downloading complete OpenNeuro dataset $DATASET_ID..."
        print_warning "This will download ~5-20GB depending on the dataset"
        
        # Install openneuro-cli if not present
        if ! command -v openneuro &> /dev/null; then
            print_info "Installing openneuro-cli..."
            pip3 install openneuro-cli
        fi
        
        # Download using openneuro-cli
        openneuro download --dataset="$DATASET_ID" "$OPENNEURO_DIR"
        
        print_success "OpenNeuro full dataset downloaded to $OPENNEURO_DIR"
    fi
    
    # Calculate and display size
    local size=$(du -sh "$OPENNEURO_DIR" 2>/dev/null | cut -f1)
    print_info "OpenNeuro dataset size: $size"
}

# Function to create download summary
create_summary() {
    local SUMMARY_FILE="$BASE_DIR/download_summary.txt"
    
    print_info "Creating download summary..."
    
    {
        echo "=========================================="
        echo "Dataset Download Summary"
        echo "=========================================="
        echo ""
        echo "Date: $(date)"
        echo "Mode: $([ "$TEST_MODE" = true ] && echo "TEST" || echo "FULL")"
        echo ""
        
        if [ "$DOWNLOAD_ADHD" = true ]; then
            echo "ADHD-200 Dataset:"
            echo "  Location: $BASE_DIR/adhd200"
            if [ -d "$BASE_DIR/adhd200" ]; then
                echo "  Size: $(du -sh "$BASE_DIR/adhd200" 2>/dev/null | cut -f1)"
                echo "  Subjects: $(find "$BASE_DIR/adhd200" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)"
            fi
            echo ""
        fi
        
        if [ "$DOWNLOAD_OPENNEURO" = true ]; then
            echo "OpenNeuro Dataset:"
            echo "  Location: $BASE_DIR/openneuro"
            if [ -d "$BASE_DIR/openneuro" ]; then
                echo "  Size: $(du -sh "$BASE_DIR/openneuro" 2>/dev/null | cut -f1)"
                echo "  Subjects: $(find "$BASE_DIR/openneuro" -mindepth 1 -maxdepth 1 -name "sub-*" -type d 2>/dev/null | wc -l)"
            fi
            echo ""
        fi
        
        echo "=========================================="
        echo "Next Steps:"
        echo "=========================================="
        echo "1. Verify data integrity"
        echo "2. Run preprocessing scripts:"
        echo "   - For ADHD-200: preprocess_adhd200()"
        echo "   - For OpenNeuro: preprocess_openneuro()"
        echo "3. Compare datasets using standardized formats"
        echo ""
        
    } > "$SUMMARY_FILE"
    
    cat "$SUMMARY_FILE"
    print_success "Summary saved to $SUMMARY_FILE"
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "Neuroimaging Dataset Downloader"
    echo "=========================================="
    echo ""
    
    if [ "$TEST_MODE" = true ]; then
        print_warning "Running in TEST mode - downloading sample data only"
    else
        print_warning "Running in FULL mode - this will download large datasets"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Download cancelled"
            exit 0
        fi
    fi
    
    echo ""
    
    # Check dependencies
    check_dependencies
    
    # Create base directory
    mkdir -p "$BASE_DIR"
    
    # Download datasets
    if [ "$DOWNLOAD_ADHD" = true ]; then
        download_adhd200
        echo ""
    fi
    
    if [ "$DOWNLOAD_OPENNEURO" = true ]; then
        download_openneuro
        echo ""
    fi
    
    # Create summary
    create_summary
    
    echo ""
    print_success "All downloads complete!"
    echo ""
}

# Run main function
main