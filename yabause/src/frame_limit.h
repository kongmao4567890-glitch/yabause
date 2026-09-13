#ifndef YABAUSE_FRAME_LIMIT_H
#define YABAUSE_FRAME_LIMIT_H

#include <stdint.h>

// Preserve the legacy enum for desktop ports and old Android preferences.
// Negative modes encode an integer percentage; zero percent means unlimited.
static inline int FrameLimitPercentForMode(int mode) {
  if (mode < 0) return mode < -2000 ? 2000 : -mode;
  if (mode == 1) return 0;
  if (mode >= 2 && mode <= 14) return (mode + 2) * 50;
  if (mode == 15) return 1000;
  if (mode == 16) return 2000;
  return 100;
}

// Divide only after multiplication so fractional target frame rates (e.g.
// 82.2 fps at NTSC 137%) keep their precision, including below 1 fps.
static inline uint64_t FrameLimitTargetTicks(uint64_t tickFrequency,
    unsigned int baseFps, int percent, unsigned int frameCount) {
  if (percent <= 0 || baseFps == 0) return 0;
  return tickFrequency * 100 * frameCount / (baseFps * (uint64_t)percent);
}

#endif
