#!/bin/bash
# Pre-build Docker images before EB's 300s timeout build step
# This hook runs without the 300s limit, so large builds can complete
cd /var/app/staging
docker compose build --parallel 2>&1 | tee /var/log/docker-prebuild.log
