#!/usr/bin/env bash
# Single place for the kernel make flags, so configure, build and
# kernelversion all run with identical settings.
#
# Usage: bash .github/scripts/kmake.sh [make args or targets...]
# Requires CLANG_DIR to point at the toolchain root.

set -euo pipefail

: "${CLANG_DIR:?CLANG_DIR is not set}"

TC_DIR="${CLANG_DIR}/bin"
export PATH="${TC_DIR}:/usr/bin:${PATH}"

exec make \
  O=out \
  ARCH=arm64 \
  SUBARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- \
  CROSS_COMPILE_ARM32=arm-linux-gnueabi- \
  CLANG_TRIPLE=aarch64-linux-gnu- \
  CC="${TC_DIR}/clang" \
  LD="${TC_DIR}/ld.lld" \
  AR="${TC_DIR}/llvm-ar" \
  NM="${TC_DIR}/llvm-nm" \
  OBJCOPY="${TC_DIR}/llvm-objcopy" \
  OBJDUMP="${TC_DIR}/llvm-objdump" \
  STRIP="${TC_DIR}/llvm-strip" \
  READELF="${TC_DIR}/llvm-readelf" \
  OBJSIZE="${TC_DIR}/llvm-size" \
  LLVM_AR="${TC_DIR}/llvm-ar" \
  LLVM_DIS="${TC_DIR}/llvm-dis" \
  HOSTCC=/usr/bin/gcc \
  HOSTCXX=/usr/bin/g++ \
  HOSTLD=/usr/bin/ld \
  HOSTAR=/usr/bin/ar \
  LLVM=1 \
  LLVM_IAS=0 \
  KCFLAGS="-w -pipe -O2 -Wno-error -Wno-error=incompatible-pointer-types" \
  CONFIG_SECTION_MISMATCH_WARN_ONLY=y \
  "$@"
