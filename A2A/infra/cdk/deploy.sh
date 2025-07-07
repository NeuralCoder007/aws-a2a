#!/bin/bash
set -e
cd "$(dirname "$0")"

# Install Python dependencies
pip install -r requirements.txt

# Bootstrap and deploy CDK stack
cdk bootstrap
cdk deploy --require-approval never 