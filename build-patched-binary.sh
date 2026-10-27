#!/bin/bash
# Build the patched dictate binary (upstream + absolute-silence VAD gate).
# Uses distrobox if available; otherwise it expects the build deps locally.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$HOME/low_latency_dictation"
OUT="$HOME/dictate-trial/patched"

if command -v distrobox >/dev/null; then
    echo "== building inside distrobox container 'dictate-build' =="
    distrobox create -Y --name dictate-build --image registry.fedoraproject.org/fedora:42 2>/dev/null || true
    distrobox enter dictate-build -- bash -c "
        set -e
        sudo dnf install -y golang gcc gcc-c++ cmake make git patch \
            SDL2-devel vulkan-headers vulkan-loader-devel libshaderc-devel \
            libshaderc-static glslc VulkanMemoryAllocator-devel \
            spirv-headers-devel libstdc++-static libstdc++-devel
        rm -rf $SRC
        git clone --recursive https://github.com/electronstudio/low_latency_dictation.git $SRC
        cd $SRC && git submodule update --init --recursive
        python3 $REPO_DIR/patch/apply_gate.py $SRC
        make
    "
else
    echo "== distrobox not found - building with local toolchain =="
    rm -rf "$SRC"
    git clone --recursive https://github.com/electronstudio/low_latency_dictation.git "$SRC"
    cd "$SRC" && git submodule update --init --recursive
    python3 "$REPO_DIR/patch/apply_gate.py" "$SRC"
    make
fi

mkdir -p "$OUT"
cp "$SRC/dictate" "$OUT/dictate"
echo "patched binary installed: $OUT/dictate"
