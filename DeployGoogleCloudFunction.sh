deploy() {
    FUNCTION_NAME=dynamicQnA
    gcloud beta run deploy python-http-function --source . --function $FUNCTION_NAME --base-image python312 --region us-central1 --allow-unauthenticated
}