#!/bin/bash

# Build script for DWChem deployment
# This script builds the frontend with dwchem-specific environment variables

echo "🏗️  Building MAX Platform Frontend for DWChem deployment..."

# Copy dwchem environment file as the active .env file
cp .env.dwchem .env

# Export environment variables so Vite can access them
set -a
source .env
set +a

# Build the application
npm run build

# Clean up
rm .env

echo "✅ Build completed for DWChem deployment"
echo "🚀 Deploy the 'dist' directory to https://maxlab.dwchem.co.kr"