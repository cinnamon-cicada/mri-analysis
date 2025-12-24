#!/bin/bash

###############################################################################
# Dataset Download Script for ADHD-200 and HCP-YA
# Downloads neuroimaging datasets for comparison and analysis
#
# Usage:
#   ./download_datasets.sh [--test] [--adhd] [--hcp-ya] [--all]
#   
# Options:
#   --test       Download only sample data (~50MB per dataset, 2-3 subjects)
#   --adhd       Download only ADHD-200 dataset
#   --hcp-ya     Download only HCP-YA dataset
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
DOWNLOAD_HCPYA=false
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
        --hcp-ya)
            DOWNLOAD_HCPYA=true
            shift
            ;;
        --all)
            DOWNLOAD_ADHD=true
            DOWNLOAD_HCPYA=true
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

# If no specific dataset selected, select all
if [ "$DOWNLOAD_ADHD" = false ] && [ "$DOWNLOAD_HCPYA" = false ]; then
    DOWNLOAD_ADHD=true
    DOWNLOAD_HCPYA=true
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
    print_info "Getting ADHD-200 dataset..."
    
    local ADHD_DIR="$BASE_DIR/adhd200"
    mkdir -p "$ADHD_DIR"

    # Check if WashU participants CSV exists
    if [ ! -f "$BASE_DIR/../outside_data/WashU_Participants.csv" ]; then
        print_error "WashU_Participants.csv not found at $BASE_DIR/../outside_data/WashU_Participants.csv"
        print_info "Please ensure the CSV file is available before running this script."
        return 1
    fi

    # Get metadata files
    META_DIR="$ADHD_DIR/meta"

    # Check if directory exists
    if [ ! -d "$META_DIR" ]; then
        echo "Directory '$META_DIR' not found. Creating and downloading..."
        mkdir -p "$META_DIR"

    aws s3 cp s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/WashU/T1w.json "$META_DIR"/ --no-sign-request
    aws s3 cp s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/WashU/dataset_description.json "$META_DIR"/ --no-sign-request
    aws s3 cp s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/WashU/participants.tsv "$META_DIR"/ --no-sign-request
    else
    echo "Directory '$META_DIR' already exists. Skipping download."
    fi
    
    # Download phenotypic data (always needed)
    print_info "Downloading phenotypic data..."
    curl -o "$ADHD_DIR/adhd200_phenotypics.csv" \
        "https://fcon_1000.projects.nitrc.org/indi/adhd200/ADHD200_40sub_preprocessed/phenotypic/ADHD200_40sub_preprocessed_phenotypics.csv" \
        2>/dev/null || print_warning "Could not download phenotypic file"

    if [ "$TEST_MODE" = true ]; then
        print_info "TEST MODE: Downloading 5 sample subjects from WashU..."
        
        # Download 5 subjects from WashU (preprocessed with Athena pipeline)
        local test_subjects=("15057" "15052" "15007" "15005" "15006")
        
        for subject in "${test_subjects[@]}"; do
            print_info "Downloading subject $subject..."
            
            local subject_dir="$ADHD_DIR/$subject"

            # Check if subject directory already exists
            if [ -d "$subject_dir" ]; then
                print_warning "Subject $subject already exists. Skipping download."
                continue
            fi

            # Else, proceed with download
            mkdir -p "$subject_dir/func"
            mkdir -p "$subject_dir/anat"
            
            # Get functional and anatomical files for this subject from CSV
            local func_files=($(grep "/sub-0*${subject}/" "$BASE_DIR/../outside_data/WashU_Participants.csv" | grep "/func/"))
            local anat_files=($(grep "/sub-0*${subject}/" "$BASE_DIR/../outside_data/WashU_Participants.csv" | grep "/anat/"))
            
            # Download functional data
            print_info "  Downloading ${#func_files[@]} functional scans..."
            for func_file in "${func_files[@]}"; do
                local filename=$(basename "$func_file")
                aws s3 cp \
                    "$func_file" \
                    "$subject_dir/func/$filename" \
                    --no-sign-request 2>/dev/null || \
                    print_warning "Could not download functional file: $filename"
            done
            
            # Download anatomical data
            print_info "  Downloading ${#anat_files[@]} anatomical scans..."
            for anat_file in "${anat_files[@]}"; do
                local filename=$(basename "$anat_file")
                aws s3 cp \
                    "$anat_file" \
                    "$subject_dir/anat/$filename" \
                    --no-sign-request 2>/dev/null || \
                    print_warning "Could not download anatomical file: $filename"
            done
        done
        
        print_success "ADHD-200 test dataset downloaded to $ADHD_DIR"
        
    elif [ -z "$(ls -A "$ADHD_DIR" 2>/dev/null)" ]; then
        print_info "FULL MODE: Downloading complete ADHD-200 dataset..."
        print_warning "This will download ~100GB of data and may take several hours"
        
        # Use AWS S3 for faster download of full dataset
        print_info "Using AWS S3 public bucket for Peking University site..."
        
        # Download WashU site from S3 bucket (BIDS format)
        aws s3 sync \
            s3://fcp-indi/data/Projects/ADHD200/RawDataBIDS/WashU \
            "$ADHD_DIR" \
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

# Function to download HCP-YA dataset

download_hcpya() {
    print_info "Getting HCP-YA dataset..."
    
    local HCPYA_DIR="$BASE_DIR/hcp-ya"
    mkdir -p "$HCPYA_DIR"
    
    # Check if directory exists
    if [ -d "$HCPYA_DIR" ]; then
        # If the directory already exists, skip the download
        print_warning "Directory '$HCPYA_DIR' already exists. Skipping download."
        return 0
    fi

    # Download HCP-YA dataset from HCP-YA website
    print_info "Downloading HCP-YA dataset from HCP-YA website..."
    curl -o "$HCPYA_DIR/HCP_YA_81.csv" "https://www.humanconnectome.org/study/hcp-young-adult/document/hcp-young-adult-data-release"
    print_success "HCP-YA dataset downloaded to $HCPYA_DIR"
}

# Function to create download summary
create_summary() {
    local SUMMARY_FILE="$BASE_DIR/download_summary.txt"
        
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
        
        if [ "$DOWNLOAD_HCPYA" = true ]; then
            echo "HCP-YA Dataset:"
            echo "  Location: $BASE_DIR/hcp-ya"
            if [ -d "$BASE_DIR/hcp-ya" ]; then
                echo "  Size: $(du -sh "$BASE_DIR/hcp-ya" 2>/dev/null | cut -f1)"
                echo "  Subjects: $(find "$BASE_DIR/hcp-ya" -mindepth 1 -maxdepth 1 -name "sub-*" -type d 2>/dev/null | wc -l)"
            fi
            echo ""
        fi
        
    } > "$SUMMARY_FILE"
    
    cat "$SUMMARY_FILE"
    print_success "Summary saved to $SUMMARY_FILE"
}

# Main execution
main() {
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
    
    # Check dependencies
    check_dependencies
    
    # Create base directory
    mkdir -p "$BASE_DIR"
    
    # Download datasets
    #TODO: Flesh out the placeholder sections below.
    if [ "$DOWNLOAD_ADHD" = true ]; then
        download_adhd200
        echo ""
    fi
    
    if [ "$DOWNLOAD_HCPYA" = true ]; then
        download_hcpya
        echo ""
    fi
    
    # Create summary
    create_summary
    print_success "All downloads complete!"
}

# Run main function
main