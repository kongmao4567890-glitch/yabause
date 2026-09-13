# Dot-clear (Phosphor Dot v3.3)

Android OpenGL filter ID 9 is Roc-Y's `Dot-clear.glslp`, available in both the
global video settings and the in-game filter list. Existing filter IDs remain
unchanged. Vulkan retains its existing restriction on display filters.

The source was located in the RetroArch shader collection distributed by
[GBAStation_Release](https://github.com/beiklive/GBAStation_Release/blob/main/emu_res/shader/shader.zip).
The original author and noncommercial restriction are preserved in
`yabause/src/shaders/phosphor-dot-v3.3/NOTICE.md` and the original source files.

## Rendering

1. Color adjustment at source resolution, using an sRGB intermediate texture.
2. Phosphor dots at output resolution, using an RGBA8 intermediate texture.
3. RGB offset/stretch at output resolution, presented in the game viewport.

All declared parameter defaults are used, even when the preset omits them from
its UI list: exposure 1, black level 2, temperature offset 1000 K, gamma 2.2,
dot scale 1.1 on both axes and opacity 0.7. This fixed preset does not introduce
another parameter menu. Native Saturn dimensions determine dot spacing even
when the emulator renders at a higher resolution.

Programs, sampler and two intermediate textures are reused. Textures are resized
only when source/output dimensions change and released at GL teardown. Context
reset invalidates all handles. A shader/FBO failure falls back to the ordinary
framebuffer blit. The pipeline restores framebuffer, viewport, texture, sampler,
program, VAO and enable states, including the caller's scissor and active texture.

## Validation

`python3 yabause/src/tests/test_display_filters.py --preview-dir /tmp/filter-preview`

The test compiles and executes the actual C renderer in headless GLES 3, exercises
PAL/NTSC, up/downscaling, higher internal resolution, rotation, letterboxing,
resource recreation, and compares the three-pass port to the original GLSL.
The GitHub Android build also runs this test and verifies the fixed APK signing
certificate. Device-specific appearance/performance still needs real-device use.

Regenerate embedded strings after source adaptation changes:
`python3 yabause/src/shaders/generate_dot_clear.py`.
