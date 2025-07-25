#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Variables
PROJECT_NAME="hsc-results"
ENV=${ENV:-dev}  # Use ENV variable or default to dev
SRC_DIR="$SCRIPT_DIR/src"
DIST_DIR="$SCRIPT_DIR/dist"
COMMON_DIR="$SRC_DIR/common"

# Lambda function directories
LAMBDAS=("parser" "validation" "batch-processor" "email-notifier" "sms-notifier")

# Create dist directory if it doesn't exist
mkdir -p $DIST_DIR

# Clean up old zip files
echo "Cleaning up old zip files..."
rm -f $DIST_DIR/*.zip

# Loop through each lambda function and build it
for LAMBDA_NAME in "${LAMBDAS[@]}"; do
  FUNCTION_NAME="$PROJECT_NAME-$LAMBDA_NAME-$ENV"
  LAMBDA_SRC_DIR="$SRC_DIR/$LAMBDA_NAME"
  PACKAGE_DIR="$DIST_DIR/package"
  ZIP_FILE="$DIST_DIR/$FUNCTION_NAME.zip"

  echo "--------------------------------------------------"
  echo "Building $FUNCTION_NAME"
  echo "--------------------------------------------------"

  # Clean up previous build artifacts
  rm -rf $PACKAGE_DIR
  rm -f $ZIP_FILE

  # Create packaging directory
  mkdir -p $PACKAGE_DIR

  # Install dependencies for all lambdas
  if [ -f "$LAMBDA_SRC_DIR/requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r "$LAMBDA_SRC_DIR/requirements.txt" -t "$PACKAGE_DIR"
  else
    echo "No requirements.txt found for $LAMBDA_NAME."
  fi

  # Copy lambda handler and source files
  echo "Copying handler code..."
  cp "$LAMBDA_SRC_DIR/handler.py" "$PACKAGE_DIR/"

  # Special handling for the parser lambda - include pre-installed dependencies
  if [ "$LAMBDA_NAME" == "parser" ]; then
    echo "Packaging pre-installed dependencies for parser..."
    cp -r "$LAMBDA_SRC_DIR/"* "$PACKAGE_DIR/"
  fi

  # Copy common utilities if they exist
  if [ -d "$COMMON_DIR" ]; then
    echo "Copying common utilities..."
    cp -r "$COMMON_DIR" "$PACKAGE_DIR/"
  fi

  # Create zip file
  echo "Creating deployment package: $ZIP_FILE"
  (cd "$PACKAGE_DIR" && zip -r "$ZIP_FILE" .)

  # Clean up
  echo "Cleaning up..."
  rm -rf $PACKAGE_DIR

  echo "Build complete for $FUNCTION_NAME"
  echo "--------------------------------------------------"
done

echo "All Lambda functions have been built successfully."