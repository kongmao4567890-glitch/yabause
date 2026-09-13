#!/usr/bin/env python3
"""Compile the real limiter with a deterministic clock, without an Android SDK."""
from pathlib import Path
import subprocess
import tempfile

src = Path(__file__).resolve().parents[1]
vdp2 = (src / "vdp2.cpp").read_text()
limiter = vdp2[vdp2.index("void VDP2SetFrameLimit(int mode)"):
               vdp2.index("void vdp2VBlankIN(void) {")]
linux = (src / "thr-linux.cpp").read_text()
sleep_start = linux.index("int YabNanosleep(u64 ns) {")
sleep_function = linux[sleep_start:linux.index("\n}", sleep_start) + 2]

harness = r'''
#include <cassert>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <time.h>
#include "frame_limit.h"
using u32 = uint32_t;
using u64 = uint64_t;
using s64 = int64_t;
static s64 clockTicks = 1000000, lastticks, onesecondticks, curticks, diffticks;
static u32 framecount;
static int frameLimitPercent = 100, enableFrameLimit = 1, FrameAdvanceVariable = 0;
static int skipnextframe, framestoskip, autoframeskipenab = 1, rendererMode;
static int sleepCalls;
static const int VDP_SETTING_FRAMELIMIT_MODE = 0;
static struct { bool IsPal; u64 tickfreq; } yabsys = {false, 1000000};
static s64 YabauseGetTicks() { return ++clockTicks; }
static int YabNanosleep(u64 micros) { clockTicks += micros; ++sleepCalls; return 0; }
static void VideoSetSetting(int, int mode) { rendererMode = mode; }
'''

checks = r'''
int main() {
  assert(FrameLimitPercentForMode(0) == 100);
  assert(FrameLimitPercentForMode(1) == 0);
  for (int mode = 2; mode <= 14; ++mode)
    assert(FrameLimitPercentForMode(mode) == (mode + 2) * 50);
  assert(FrameLimitPercentForMode(15) == 1000);
  assert(FrameLimitPercentForMode(16) == 2000);
  assert(FrameLimitPercentForMode(99) == 100);
  assert(FrameLimitPercentForMode(INT_MIN) == 2000);
  for (int percent = 1; percent <= 2000; ++percent)
    assert(FrameLimitPercentForMode(-percent) == percent);

  for (bool pal : {false, true}) {
    yabsys.IsPal = pal;
    const unsigned fps = pal ? 50 : 60;
    for (int percent : {1, 50, 99, 100, 101, 137, 199, 250, 333, 700, 2000}) {
      VDP2SetFrameLimit(-percent);
      const s64 start = lastticks;
      s64 previous = start;
      const s64 interval = FrameLimitTargetTicks(yabsys.tickfreq, fps, percent, 1);
      for (unsigned frame = 1; frame <= fps * 3; ++frame) {
        frameSkipAndLimit();
        const s64 expected = FrameLimitTargetTicks(yabsys.tickfreq, fps, percent, frame);
        // No drift at fractional speeds or signed wrap at a batch boundary.
        assert(std::llabs((clockTicks - start) - expected) <= interval / 10 + 5);
        if (frame > 1) assert(std::llabs((clockTicks - previous) - interval) <= 5);
        previous = clockTicks;
      }
      assert(rendererMode == (percent == 100 ? 0 : 1));
    }
  }
  VDP2SetFrameLimit(-2000);
  clockTicks += 100000;
  frameSkipAndLimit();
  assert(skipnextframe == 1 && framestoskip == 4);
  VDP2SetFrameLimit(0);
  assert(skipnextframe == 0 && framestoskip == 0);
  assert(framecount == 0 && onesecondticks == 0 && rendererMode == 0);
  VDP2SetFrameLimit(1);
  int before = sleepCalls;
  for (int i = 0; i < 120; ++i) frameSkipAndLimit();
  assert(!enableFrameLimit && sleepCalls == before);
  VDP2SetFrameLimit(-137);
  assert(enableFrameLimit && frameLimitPercent == 137);
  FrameAdvanceVariable = 1;
  frameSkipAndLimit();
  assert(sleepCalls == before);
  FrameAdvanceVariable = 0;
  yabsys.tickfreq = 1000;
  VDP2SetFrameLimit(-2000);
  frameSkipAndLimit(); // Coarse clocks must not cause unsigned underflow/hangs.
  std::cout << "PASS: legacy modes, all percentages, PAL/NTSC timing, batch boundaries, "
               "skip reset, unlimited, frame advance, coarse clocks\n";
}
'''

sleep_harness = r'''
#include <cassert>
#include <cstdint>
#include <time.h>
using u64 = uint64_t;
static timespec captured;
static int captureSleep(const timespec *ts, timespec *) { captured = *ts; return 0; }
#define nanosleep captureSleep
'''
sleep_checks = r'''
int main() {
  for (u64 us : {0ULL, 999999ULL, 1000000ULL, 1666666ULL, 2000000ULL}) {
    YabNanosleep(us);
    assert(captured.tv_nsec >= 0 && captured.tv_nsec < 1000000000);
    assert(captured.tv_sec * 1000000ULL + captured.tv_nsec / 1000 == us);
  }
}
'''

with tempfile.TemporaryDirectory(prefix="frame-limit-test-") as tmp:
    for name, code in [("limiter", harness + limiter + checks),
                       ("sleep", "#include <initializer_list>\n" + sleep_harness + sleep_function + sleep_checks)]:
        source = Path(tmp) / (name + ".cpp")
        binary = Path(tmp) / name
        source.write_text(code)
        subprocess.run(["g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-I", str(src), str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=20)
print("PASS: slow-speed sleeps over one second")
