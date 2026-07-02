/*
 * Stub implementations for arm64 platform.
 * The old sh2_dynarec.c JIT is not portable to arm64.
 * The devmiyax dynarec (sh2_dynarec_devmiyax) handles actual SH2 emulation.
 * This file provides the symbols referenced by yabause.c and yui.cpp
 * to satisfy the linker. All functions are no-ops.
 */
#include "sh2core.h"
#include "sh2_dynarec.h"

/* Stub function prototypes */
static int stub_Init(void) { return 0; }
static void stub_DeInit(void) {}
static void stub_Reset(SH2_struct *context) { (void)context; }
static void FASTCALL stub_Exec(SH2_struct *context, u32 cycles) { (void)context; (void)cycles; }
static void stub_GetRegisters(SH2_struct *context, sh2regs_struct *regs) { (void)context; (void)regs; }
static u32 stub_GetGPR(SH2_struct *context, int num) { (void)context; (void)num; return 0; }
static u32 stub_GetSR(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetGBR(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetVBR(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetMACH(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetMACL(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetPR(SH2_struct *context) { (void)context; return 0; }
static u32 stub_GetPC(SH2_struct *context) { (void)context; return 0; }
static void stub_SetRegisters(SH2_struct *context, const sh2regs_struct *regs) { (void)context; (void)regs; }
static void stub_SetGPR(SH2_struct *context, int num, u32 value) { (void)context; (void)num; (void)value; }
static void stub_SetSR(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetGBR(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetVBR(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetMACH(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetMACL(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetPR(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_SetPC(SH2_struct *context, u32 value) { (void)context; (void)value; }
static void stub_OnFrame(SH2_struct *context) { (void)context; }
static void stub_SendInterrupt(SH2_struct *context, u8 vector, u8 level) { (void)context; (void)vector; (void)level; }
static void stub_RemoveInterrupt(SH2_struct *context, u8 vector, u8 level) { (void)context; (void)vector; (void)level; }
static int stub_GetInterrupts(SH2_struct *context, interrupt_struct interrupts[MAX_INTERRUPTS]) { (void)context; (void)interrupts; return 0; }
static void stub_SetInterrupts(SH2_struct *context, int num_interrupts, const interrupt_struct interrupts[MAX_INTERRUPTS]) { (void)context; (void)num_interrupts; (void)interrupts; }
static void stub_WriteNotify(u32 start, u32 length) { (void)start; (void)length; }
static void stub_AddCycle(SH2_struct *context, u32 value) { (void)context; (void)value; }

/* SH2Interface_struct for the old dynarec - registered but not used on arm64 */
SH2Interface_struct SH2Dynarec = {
   0x2000,
   "SH2 Dynamic Recompiler (stub)",
   stub_Init,
   stub_DeInit,
   stub_Reset,
   stub_Exec,
   stub_GetRegisters,
   stub_GetGPR,
   stub_GetSR,
   stub_GetGBR,
   stub_GetVBR,
   stub_GetMACH,
   stub_GetMACL,
   stub_GetPR,
   stub_GetPC,
   stub_SetRegisters,
   stub_SetGPR,
   stub_SetSR,
   stub_SetGBR,
   stub_SetVBR,
   stub_SetMACH,
   stub_SetMACL,
   stub_SetPR,
   stub_SetPC,
   stub_OnFrame,
   stub_SendInterrupt,
   stub_RemoveInterrupt,
   stub_GetInterrupts,
   stub_SetInterrupts,
   stub_WriteNotify,
   stub_AddCycle,
};

/* Old dynarec linkage stubs */
void sh2_dynarec_init(void) {}
void YabauseDynarecOneFrameExec(int m68kcycles, int m68kcenticycles)
{
    (void)m68kcycles; (void)m68kcenticycles;
}
