#!/bin/bash

###############################################################################
# Wrapper Script for Neuroimaging Dataset Processing Pipeline
#
# Usage:
#   ./run.sh [OPTIONS] [ANALYSIS_NUMBERS...]

# Options:
#   --test       Run in test mode (downloads sample data if needed)
#   --help       Show this help message

# Analysis Numbers:
#   1            Run ADHD analysis (uses ADHD-200 dataset)
#   2            Run uniqueness analysis (uses HCP-YA dataset)
#   3            Reserved for future use

# Examples:
#   ./run.sh 1              # Run analysis 1, download ADHD-200 if needed
#   ./run.sh --test 1 2     # Run analyses 1 and 2 in test mode
#   ./run.sh 2 1            # Run analysis 2 then analysis 1
#   ./run.sh 1 1 2          # Run analysis 1 twice, then analysis 2
###############################################################################

set -e  # Exit on error

# set number of threads for libraries to 1 to avoid oversubscription
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/outside_data"
DOWNLOAD_SCRIPT="$SCRIPT_DIR/download.sh"
MAIN_SCRIPT="$SCRIPT_DIR/../scripts/main.py"

# Default settings
TEST_MODE=""
ANALYSIS_NUMBERS=()
SHOW_HELP=false

# Print functions
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

# Show help message
show_help() {
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //g' | sed 's/^#//g'
    exit 0
}

# Parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        print_error "No arguments provided"
        echo "Use --help for usage information"
        exit 1
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test)
                TEST_MODE="--test"
                print_info "Test mode enabled"
                shift
                ;;
            --help)
                show_help
                ;;
            [0-9]*)
                ANALYSIS_NUMBERS+=("$1")
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    if [ ${#ANALYSIS_NUMBERS[@]} -eq 0 ]; then
        print_error "No analysis numbers provided"
        echo "Please specify at least one analysis number (1, 2, or 3)"
        exit 1
    fi
}

# Check if directory exists and is not empty
is_directory_empty() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        return 0  # Directory doesn't exist, consider it empty
    fi
    
    # Check if directory has any files/subdirectories
    if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        return 0  # Directory is empty
    fi
    
    return 1  # Directory is not empty
}

# Download ADHD-200 dataset if needed
ensure_adhd200() {
    local adhd_dir="$DATA_DIR/adhd200"
    
    # Make download script executable if needed
    chmod +x "$DOWNLOAD_SCRIPT"

    # Run download script
    "$DOWNLOAD_SCRIPT" $TEST_MODE --adhd

}

# Download HCP-YA dataset if needed
ensure_hcpya() {
    local hcpya_dir="$DATA_DIR/hcp-ya"

    # Make download script executable if needed
    chmod +x "$DOWNLOAD_SCRIPT"
    
    # Run download script. This will also check if download is needed.
    "$DOWNLOAD_SCRIPT" $TEST_MODE --hcp-ya
}

# Prepare datasets based on which analyses are requested
prepare_datasets() {
    echo ""
    echo "=========================================="
    echo "Neuroimaging Dataset Downloader"
    echo "=========================================="
    echo ""
    print_info "Determining required datasets..."
    
    local needs_adhd=false
    local needs_hcpya=false
    
    # Check which datasets are needed based on analysis numbers
    for analysis_num in "${ANALYSIS_NUMBERS[@]}"; do
        case $analysis_num in
            1)
                needs_adhd=true
                ;;
            2)
                needs_hcpya=true
                ;;
            3)
                print_warning "Analysis 3 is reserved for future use"
                ;;
            *)
                print_error "Invalid analysis number: $analysis_num"
                print_error "Valid options are: 1 (ADHD analysis), 2 (HCP-YA analysis), 3 (reserved)"
                exit 1
                ;;
        esac
    done
    
    # Download required datasets
    if [ "$needs_adhd" = true ]; then
        print_info "Analysis 1 requires ADHD-200 dataset"
        ensure_adhd200
    fi
    
    if [ "$needs_hcpya" = true ]; then
        print_info "Analysis 2 requires HCP-YA dataset"
        ensure_hcpya
    fi
    
    print_success "All required datasets are ready"
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "Neuroimaging Processing Pipeline"
    echo "=========================================="
    echo ""
    
    # Parse arguments
    parse_args "$@"
    
    # Display configuration
    print_info "Configuration:"
    echo "  Test mode: $([ -n "$TEST_MODE" ] && echo "ENABLED" || echo "DISABLED")"
    echo "  Analyses to run: ${ANALYSIS_NUMBERS[*]}"
    echo "  Data directory: $DATA_DIR"
    echo "  Main script: $MAIN_SCRIPT"
    
    # Prepare all required datasets (download if needed)
    prepare_datasets
    echo ""

    # Run main.py with all analysis numbers as arguments
    echo ""
    echo "=========================================="
    echo "Run Details"
    echo "=========================================="
    echo ""
    print_info "Running main.py with analysis: ${ANALYSIS_NUMBERS[*]}"
    echo ""
    
    taskset -c 0 python3 "$MAIN_SCRIPT" "${ANALYSIS_NUMBERS[@]}"
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "All analyses complete!"
    else
        echo ""
        print_error "Analysis failed"
        exit 1
    fi
    
    # Final summary
    print_info "Analysis(es) completed: ${ANALYSIS_NUMBERS[*]}"
    
    # Create processing log
    local log_file="$SCRIPT_DIR/processing_log.txt"
    {
        echo "Processing Log"
        echo "=============="
        echo "Date: $(date)"
        echo "Test Mode: $([ -n "$TEST_MODE" ] && echo "YES" || echo "NO")"
        echo "Analysis Array: ${ANALYSIS_NUMBERS[*]}"
        echo ""
        echo "Analysis Details:"
        
        for i in "${!ANALYSIS_NUMBERS[@]}"; do
            local analysis_num="${ANALYSIS_NUMBERS[$i]}"
            case $analysis_num in
                1) echo "  Index $i: Analysis $analysis_num (ADHD-200 dataset)" ;;
                2) echo "  Index $i: Analysis $analysis_num (HCP-YA dataset)" ;;
                3) echo "  Index $i: Analysis $analysis_num (Reserved)" ;;
                *) echo "  Index $i: Analysis $analysis_num (Unknown)" ;;
            esac
        done
        
        echo ""
        echo "Status: SUCCESS"
    } > "$log_file"
    
    print_info "Log saved to: $log_file"
    echo ""
}

# Check if script is being sourced or executed
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Script is being executed directly
    main "$@"
else
    # Script is being sourced
    print_warning "Script is being sourced. Please execute it directly."
fi