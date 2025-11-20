import os
import sys
import json
from analysis import run_adhd_analysis
from preprocess import preprocess_adhd200, preprocess_lab_data

def main(choice=[], subjects=None):
    # Pre-process data in general
    print("Hello, World!")

    # Perform different analyses based on the input argument
    if not choice:
        print("No specific analysis chosen. Running default analysis.")
        # Default analysis code here
    else:
        for analysis in choice:
            print(f"Running analysis: {analysis}")
            # Specific analysis code here
            if analysis == "1":
                # ADHD Analysis
                print("Performing Analysis 1...")
                # Analyze ADHD-200 dataset
                # Run FreeSurfer preprocessing
                script_dir = os.path.dirname(os.path.abspath(__file__))
                license_path = os.path.join(script_dir, "license.txt")

                # Run preprocessing if not already done
                if not os.listdir("./processed_data/adhd200"):
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
                print("\nFinished analysis!")

            elif analysis == "2":
                # Exceptions Analysis
                print("Performing Analysis 2.")
                # Analysis 2 code here
            else:
                print(f"Analysis {analysis} is not recognized.")

if __name__ == "__main__":
    # Get command line arguments (excluding script name)
    analysis_numbers = sys.argv[1:]
    main(analysis_numbers)
