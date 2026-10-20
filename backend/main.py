import os
import sys
from analysis import run_adhd_analysis
from preprocess import preprocess_adhd200, run_outlier_analysis
from utils import preprocess_lab_data
import json


# MAIN
def main(choice):
    # Data dirs (outside_data/, lab_data/, processed_data/, analysis/) and
    # license.txt live at the repo root; resolve every relative path below from
    # there so the pipeline works whether it's launched from the root or backend/.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)
    license_path = os.path.abspath(os.environ.get("FREESURFER_LICENSE", "license.txt"))
    os.makedirs("./analysis", exist_ok=True)

    # Perform different analyses based on the input argument
    if not choice:
        print("No specific analysis chosen. Running default analysis.")
        # Default analysis code here
    else:
        for analysis in choice:
            # Specific analysis code here
            if analysis == "1":
                # ADHD Analysis
                # Run preprocessing if not already done
                if (not os.path.exists("./processed_data/adhd200") or
                        not os.listdir("./processed_data/adhd200")):
                    preprocess_adhd200(
                        input_dir="./outside_data/adhd200",
                        output_dir="./processed_data/adhd200",
                        freesurfer_license=license_path
                    )
                else:
                    print("Skipped ADHD-200 preprocessing.")

                if not os.path.exists("./lab_data"):
                    print("Lab data directory not found. Cannot run analysis.")
                    sys.exit(1)

                if (not os.path.exists("./processed_data/adhd_lab") or
                        not os.listdir("./processed_data/adhd_lab")):
                    preprocess_lab_data(
                        input_dir="./lab_data",
                        output_dir="./processed_data/adhd_lab",
                        freesurfer_license=license_path
                    )
                else:
                    print("Skipped lab data preprocessing.")

                # Run ADHD analysis
                run_adhd_analysis()

            elif analysis == "2":
                # Exceptions Analysis
                # Preprocess as needed
                if not os.path.exists("./processed_data/outlier_lab"):
                    preprocess_lab_data(
                        input_dir="./lab_data",
                        output_dir="./processed_data/outlier_lab",
                        freesurfer_license=license_path
                    )
                else:
                    print("Skipped lab data preprocessing.")

                # Assume reference data is in ./outside_data/hcp-ya/HCP_YA.csv
                
                # Use extractor to get comparison results
                percentiles = run_outlier_analysis(data_path="./processed_data/outlier_lab")
                percentiles["thickness_percentiles"].sort(key=lambda x: x[1])

                # Save percentiles to JSON file
                with open("./analysis/outlier_analysis_results.json", "w") as f:
                    json.dump(percentiles, f, indent=4, sort_keys=True)

            else:
                print(f"Analysis {analysis} is not recognized.")

if __name__ == "__main__":
    # Get command line arguments (excluding script name)
    analysis_numbers = sys.argv[1:]
    main(analysis_numbers)
