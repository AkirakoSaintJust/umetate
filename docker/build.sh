#!/bin/sh
# Build the umetate-host-build image from the repository root.
set -eu
cd "$(dirname "$0")/.."
docker build -f docker/Dockerfile -t umetate-host-build:latest .
