#!/bin/bash

###############################################################################
# Wrapper Script for Neuroimaging Dataset Processing Pipeline
#
# Usage:
#   ./run.sh [OPTIONS] [ANALYSIS_NUMBERS...]
#
# Options:
#   --test       Run in test mode (downloads sample data if needed)
#   --help       Show this help message
#
# Analysis Numbers:
#   1            Run ADHD analysis (uses ADHD-200 dataset)
#   2            Run uniqueness analysis (uses OpenNeuro dataset)
#   3            Reserved for future use
#
# Examples:
#   ./run.sh 1              # Run analysis 1, download ADHD-200 if needed
#   ./run.sh --test 1 2     # Run analyses 1 and 2 in test mode
#   ./run.sh 2 1            # Run analysis 2 then analysis 1
#   ./run.sh 1 1 2          # Run analysis 1 twice, then analysis 2
###############################################################################

set -e  # Exit on error

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
MAIN_SCRIPT="$SCRIPT_DIR/../main.py"

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
    
    if is_directory_empty "$adhd_dir"; then
        print_info "ADHD-200 dataset not found or empty"
        print_info "Downloading ADHD-200 dataset..."
        
        if [ ! -f "$DOWNLOAD_SCRIPT" ]; then
            print_error "Download script not found: $DOWNLOAD_SCRIPT"
            exit 1
        fi

        # Make download script executable if needed
        chmod +x "$DOWNLOAD_SCRIPT"

        # Run download script
        "$DOWNLOAD_SCRIPT" $TEST_MODE --adhd
        
        if [ $? -ne 0 ]; then
            print_error "Failed to download ADHD-200 dataset"
            exit 1
        fi
        
        print_success "ADHD-200 dataset downloaded"
    else
        print_info "ADHD-200 dataset found at $adhd_dir"
    fi
}

# Download OpenNeuro dataset if needed
ensure_openneuro() {
    local openneuro_dir="$DATA_DIR/openneuro"
    
    if is_directory_empty "$openneuro_dir"; then
        print_info "OpenNeuro dataset not found or empty"
        print_info "Downloading OpenNeuro dataset..."
        
        if [ ! -f "$DOWNLOAD_SCRIPT" ]; then
            print_error "Download script not found: $DOWNLOAD_SCRIPT"
            exit 1
        fi
        
        # Make download script executable if needed
        chmod +x "$DOWNLOAD_SCRIPT"
        
        # Run download script
        "$DOWNLOAD_SCRIPT" $TEST_MODE --openneuro
        
        if [ $? -ne 0 ]; then
            print_error "Failed to download OpenNeuro dataset"
            exit 1
        fi
        
        print_success "OpenNeuro dataset downloaded"
    else
        print_info "OpenNeuro dataset found at $openneuro_dir"
    fi
}

# Prepare datasets based on which analyses are requested
prepare_datasets() {
    print_info "Determining required datasets..."
    
    local needs_adhd=false
    local needs_openneuro=false
    
    # Check which datasets are needed based on analysis numbers
    for analysis_num in "${ANALYSIS_NUMBERS[@]}"; do
        case $analysis_num in
            1)
                needs_adhd=true
                ;;
            2)
                needs_openneuro=true
                ;;
            3)
                print_warning "Analysis 3 is reserved for future use"
                ;;
            *)
                print_error "Invalid analysis number: $analysis_num"
                print_error "Valid options are: 1 (ADHD analysis), 2 (OpenNeuro analysis), 3 (reserved)"
                exit 1
                ;;
        esac
    done
    
    # Download required datasets
    if [ "$needs_adhd" = true ]; then
        print_info "Analysis 1 requires ADHD-200 dataset"
        ensure_adhd200
    fi
    
    if [ "$needs_openneuro" = true ]; then
        print_info "Analysis 2 requires OpenNeuro dataset"
        ensure_openneuro
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
    echo ""
    
    # Prepare all required datasets (download if needed)
    echo "=========================================="
    prepare_datasets
    echo "=========================================="
    echo ""

    # Run main.py with all analysis numbers as arguments
    print_info "Running main.py with analysis array: ${ANALYSIS_NUMBERS[*]}"
    echo ""
    
    python3 "$MAIN_SCRIPT" "${ANALYSIS_NUMBERS[@]}"
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "All analyses complete!"
    else
        echo ""
        print_error "Analysis failed"
        exit 1
    fi
    
    # Final summary
    echo ""
    echo "=========================================="
    print_success "All processing complete!"
    echo "=========================================="
    echo ""
    
    # Show summary
    print_info "Analyses completed: ${ANALYSIS_NUMBERS[*]}"
    
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
                2) echo "  Index $i: Analysis $analysis_num (OpenNeuro dataset)" ;;
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