/*
 * Stub implementation of YabauseDynarecOneFrameExec for arm64.
 * The actual dynarec execution on arm64 is handled by the devmiyax dynarec
 * (sh2_dynarec_devmiyax/DynarecSh2.cpp). This stub is needed because
 * sh2_dynarec.c references this function and there's no arm64 assembly
 * linkage file.
 */
#include "sh2_dynarec.h"

void YabauseDynarecOneFrameExec(int m68kcycles, int m68kcenticycles)
{
    /* No-op: dynarec execution is handled by devmiyax dynarec on arm64 */
}
