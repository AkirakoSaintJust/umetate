# umetate-host-build — the pinned Linux dev container that owns the host + web
# toolchain. The JieLi toolchain + AC79 SDK are NOT in this image; they live in the
# `umetate-target` Docker volume at /opt/jieli (populated by `umetate setup`).

FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

# Host toolchain + build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build git \
        python3 python3-pip python3-venv \
        nodejs npm curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python packages for the host checks (lint/type-check pins in env.lock)
RUN pip3 install --no-cache-dir --break-system-packages \
        pillow==13.0.0 jsonschema==4.26.0 \
        ruff==0.17.2 mypy==2.4.0

# Emscripten (version pinned in env.lock)
ARG EMSDK_VERSION=6.0.13
RUN git clone --depth 1 --branch "${EMSDK_VERSION}" https://github.com/emscripten-core/emsdk.git /opt/emsdk \
    && /opt/emsdk/emsdk install "${EMSDK_VERSION}" \
    && /opt/emsdk/emsdk activate "${EMSDK_VERSION}"
ENV PATH="/opt/emsdk:/opt/emsdk/upstream/emscripten:${PATH}"

WORKDIR /work
CMD ["/bin/bash"]
