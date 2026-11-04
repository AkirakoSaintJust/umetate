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

# Linux DAW acceptance. Ardour renders a session headlessly. Zrythm is an
# AppImage because Debian trixie does not package it. Both scan $HOME/.vst3, and
# Zrythm also scans $HOME/.clap, which the linux_daws CTest fills from the build
# tree.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ardour xvfb xauth libopengl0 libegl1 libgles2 \
        libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1 \
        libxcb-shape0 \
    && rm -rf /var/lib/apt/lists/*

ARG ZRYTHM_VERSION=2.0.0-alpha.7
ARG ZRYTHM_SHA256=7d9c7c01da93841c55d1703ad04ea66e633319ed1808c3a55d72789bd9d3b9d9
RUN curl -L --fail -o /tmp/Zrythm.AppImage \
        "https://github.com/zrythm/zrythm/releases/download/v${ZRYTHM_VERSION}/Zrythm-${ZRYTHM_VERSION}-Linux-x86_64.AppImage" \
    && echo "${ZRYTHM_SHA256}  /tmp/Zrythm.AppImage" | sha256sum -c - \
    && chmod +x /tmp/Zrythm.AppImage \
    && mkdir -p /opt/zrythm \
    && cd /opt/zrythm \
    && /tmp/Zrythm.AppImage --appimage-extract >/dev/null \
    && rm /tmp/Zrythm.AppImage \
    && printf '%s\n' '#!/bin/sh' \
        'exec /opt/zrythm/squashfs-root/AppRun "$@"' \
        > /usr/local/bin/zrythm \
    && chmod +x /usr/local/bin/zrythm

ENV LANG=C.UTF-8

WORKDIR /work
CMD ["/bin/bash"]
