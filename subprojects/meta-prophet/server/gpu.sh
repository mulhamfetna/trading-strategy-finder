#!/usr/bin/env bash
# Quick GPU snapshot (with the gfx1031 override so rocm-smi reads cleanly).
source "$(dirname "$0")/lib.sh"
srv 'HSA_OVERRIDE_GFX_VERSION=10.3.0 rocm-smi 2>/dev/null | sed -n "1,18p"'
