#!/usr/bin/env bash
# Linux only: turn Doosan's static libDRFL.a into libDRFL.so so Python ctypes can load it.
# Usage: bash python/build_linux_lib.sh [ubuntu_version]   (default: this machine's, e.g. 22.04)
set -euo pipefail
cd "$(dirname "$0")/.."

. /etc/os-release
VER="${1:-$VERSION_ID}"
case "$(uname -m)" in
    x86_64)  ARCH=amd64 ;;
    aarch64) ARCH=arm64 ;;
    *) echo "Unsupported CPU: $(uname -m)"; exit 1 ;;
esac
DIR="drfl/lib/linux/$ARCH/$VER"
[ -f "$DIR/libDRFL.a" ] || { echo "No DRFL library for $ARCH Ubuntu $VER in $DIR"; exit 1; }

g++ -shared -o "$DIR/libDRFL.so" \
    -Wl,--whole-archive "$DIR/libDRFL.a" -Wl,--no-whole-archive \
    -L"$DIR" -l:libPocoFoundation.so -l:libPocoNet.so -lpthread \
    -Wl,-rpath,'$ORIGIN'
echo "built $DIR/libDRFL.so"
