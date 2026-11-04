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

# Linux DAW acceptance. Ardour renders a session headlessly. Carla renders both
# VST3 and CLAP through its no-gui mode, JACK and the OSC control API. Carla is
# built from the pinned main commit because the 2.5.x releases lack CLAP.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ardour xvfb xauth libopengl0 libegl1 libgles2 \
        libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1 \
        libxcb-shape0 \
        pkg-config jackd2 jack-example-tools liblo-tools python3-liblo \
        python3-pyqt5 python3-pyqt5.qtsvg python3-rdflib pyqt5-dev-tools \
        libmagic-dev liblo-dev libasound2-dev libpulse-dev libx11-dev \
        libxcursor-dev libxext-dev qtbase5-dev libfluidsynth-dev \
        libjack-jackd2-dev \
        libfreetype-dev libfontconfig1-dev libxrandr-dev libxinerama-dev \
        libxcomposite-dev libxrender-dev libxfixes-dev libgl1-mesa-dev \
        libxkbcommon-dev \
    && rm -rf /var/lib/apt/lists/*

ARG CARLA_COMMIT=97a9e0740baf6df2df942495c02532a624c44682
RUN git init /tmp/carla-src \
    && cd /tmp/carla-src \
    && git remote add origin https://github.com/falkTX/Carla.git \
    && git fetch --depth 1 origin "${CARLA_COMMIT}" \
    && git checkout FETCH_HEAD \
    && make -j"$(nproc)" \
    && make install PREFIX=/opt/carla \
    && rm -rf /tmp/carla-src
ENV PATH="/opt/carla/bin:${PATH}"

# Login shells rebuild PATH from /etc/profile, which drops /opt/carla/bin.
RUN printf '%s\n' 'export PATH="/opt/carla/bin:$PATH"' \
        > /etc/profile.d/carla.sh

ENV LANG=C.UTF-8

WORKDIR /work
CMD ["/bin/bash"]
