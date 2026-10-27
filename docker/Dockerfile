# umetate-host-build — the pinned Linux dev container that owns the host + web
# toolchain. The JieLi toolchain + AC79 SDK are NOT in this image; they live in the
# `umetate-target` Docker volume at /opt/jieli (populated by `umetate setup`).

FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

# Host toolchain + build essentials. Node comes from emsdk's own pinned node (see
# below), not from apt: the Debian nodejs/npm are EOL and pull a large tree of
# vulnerable npm packages that emcc never uses.
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build git \
        python3 python3-pip python3-venv \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python packages for the host checks (lint/type-check pins in env.lock); setuptools
# is upgraded past the flagged CVEs (CVE-2024-6345, CVE-2025-47273). pyright is the
# second type-checker (its "partially unknown" diagnostics catch what mypy can't).
RUN pip3 install --no-cache-dir --break-system-packages \
        setuptools pillow==13.0.0 jsonschema==4.26.0 \
        ruff==0.17.2 mypy==2.4.0 pyright==1.1.414

# Emscripten (version pinned in env.lock). Its bundled node/npm (not the apt ones)
# are what emcc runs; add them to PATH so `node`/`npm` resolve to the pinned node.
ARG EMSDK_VERSION=6.0.13
RUN git clone --depth 1 --branch "${EMSDK_VERSION}" https://github.com/emscripten-core/emsdk.git /opt/emsdk \
    && /opt/emsdk/emsdk install "${EMSDK_VERSION}" \
    && /opt/emsdk/emsdk activate "${EMSDK_VERSION}"
ENV PATH="/opt/emsdk:/opt/emsdk/upstream/emscripten:/opt/emsdk/node/24.19.0_64bit/bin:${PATH}"

WORKDIR /work
CMD ["/bin/bash"]
