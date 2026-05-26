#!/bin/bash

# Update dependencies
echo "Updating dependencies..."
npm install --save-dev @typescript-eslint/eslint-plugin eslint @typescript-eslint/parser \
    && yarn upgrade @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint \
    && yarn add @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint \
    && yarn install

# Run code formatters and linters
echo "Running code formatters and linters..."
npx prettier --write .
npx eslint .

# Check for security vulnerabilities
echo "Checking for security vulnerabilities..."
npm audit

# Report security vulnerabilities
echo "Security Vulnerabilities:"
npm audit --json | jq '.advisories[] | {title, vulnerabilityId, severity, package}' | sort -u