# ==================== CONFIGURATION ====================
export PROJECT_ID="brain_project"
export PROJECT_NAME="The Brain Benchmark Project"
export REGION="us-east1"
# =======================================================

# 1. Authenticate your local terminal terminal with Google
gcloud auth login && \
gcloud auth application-default login && \

# 2. Create the raw Google Cloud Project
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME" && \

# 3. Link your billing account (Required to use Firebase features)
# This automatically grabs your first available billing account. 
# If you have multiple, replace the $(...) part with your exact billing account ID number.
gcloud beta billing projects link $PROJECT_ID --billing-account=$(gcloud beta billing accounts list --format="value(name)" --limit=1) && \

# 4. Enable the necessary APIs for Firebase and Firestore database routing
gcloud services enable ://googleapis.com ://googleapis.com --project=$PROJECT_ID && \

# 5. Spin up the actual Firestore Native Database instance inside the project
gcloud alpha firestore databases create --project=$PROJECT_ID --location=$REGION --type=firestore-native

echo "--------------------------------------------------------"
echo "🎉 Setup Complete!"
echo "View your new Firebase console here: https://google.com"
echo "--------------------------------------------------------"
