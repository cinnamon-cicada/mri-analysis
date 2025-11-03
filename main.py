import os
import sys
import json
from analysis import run_adhd_analysis
from preprocess import preprocess_adhd200

def main(choice=[]):
    # Pre-process data in general
    print("Hello, World!")

    # Perform different analyses based on the input argument
    if not choice:
        print("No specific analysis chosen. Running default analysis...")
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
                if not os.listdir("./processed_data/adhd200"):
                    os.makedirs("./processed_data/adhd200")
                    preprocess_adhd200(
                        input_dir="./outside_data/adhd200",
                        output_dir="./processed_data/adhd200",
                        phenotypic_file="./outside_data/adhd200_phenotypics.csv",
                        pipeline="athena",
                        create_bids=True
                    )
                else:
                    print("Processed data directory already exists. Skipping preprocessing.")

                # Gather results
                # Get array of subject directories in analysis/adhd200
                subject_dirs = []
                adhd_analysis_dir = "./analysis/adhd200"
                if os.path.exists(adhd_analysis_dir):
                    subject_dirs = [d for d in os.listdir(adhd_analysis_dir) 
                                    if os.path.isdir(os.path.join(adhd_analysis_dir, d))]
                    print(f"Found {len(subject_dirs)} subject directories: {subject_dirs}")
                else:
                    print(f"Directory {adhd_analysis_dir} does not exist yet.")

                result = run_adhd_analysis(subject_dirs)

                print("\nFinished analysis. Processing summary:")
                print(json.dumps(result, indent=2))

            elif analysis == "2":
                # Exceptions Analysis
                print("Performing Analysis 2...")
                # Analysis 2 code here
            else:
                print(f"Analysis {analysis} is not recognized.")

if __name__ == "__main__":
    # Get command line arguments (excluding script name)
    analysis_numbers = sys.argv[1:]
    main(analysis_numbers)