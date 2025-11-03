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
                if not os.path.exists("./processed_data/adhd200"):
                    os.makedirs("./processed_data/adhd200")
                    preprocess_adhd200(
                        input_dir="./outside_data/adhd200",
                        output_dir="./analysis/adhd200",
                        phenotypic_file="./outside_data/adhd200_phenotypics.csv",
                        pipeline="athena",
                        create_bids=True
                    )
                    

                else:
                    print("Processed data directory already exists. Skipping preprocessing.")
                    result = {"status": "skipped", "reason": "processed_data/adhd200 already exists"}
                
                print("\nFinished analysis. Processing summary:")
                print(json.dumps(result, indent=2))

            elif analysis == "2":
                # Exceptions Analysis
                print("Performing Analysis 2...")
                # Analysis 2 code here
            else:
                print(f"Analysis {analysis} is not recognized.")

if __name__ == "__main__":
    main()