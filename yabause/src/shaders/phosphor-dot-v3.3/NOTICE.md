# Phosphor Dot v3.3 — Dot-clear

Author: Roc-Y (脑浆油条), rocky02009@163.com.
Copyright (C) 2022–2023 Roc-Y. Shader header dated January 2024.

These third-party GLSL files and their generated shader strings retain the
author's terms. They are **not** relicensed under the surrounding GPL license.
The original `phosphor-dot.glsl` states:

> STATEMENT:The following core algorithms are original, and anyone is prohibited from using them to obtain commercial benefits without the formal permission of the author.
>
> 声明：以下核心算法为独创，任何人未经书面允许，不得用于获取商业利益。

This integration is for the user's personal emulator build. Do not represent
this shader as unrestricted or use it commercially without the author's permission.

Source mirror (downloaded 2026-09-13):
https://github.com/beiklive/GBAStation_Release/blob/main/emu_res/shader/shader.zip

ZIP SHA-256: `a2dff850ed44cfaf38a6d452510dd903eb974fb2ff396c435ff81311d7e12c49`

Archive directory: `shaders_glsl/phosphor-dot v3.3/`.
Only `Dot-clear.glslp` and its three required passes are included, unchanged.
Author's video: https://www.bilibili.com/video/BV16s4y1T7Qa

`../generate_dot_clear.py` creates the embedded compatibility adaptation:
original parameter defaults plus preset overrides, high precision on GLES,
defined zero-blur sampling, defined temperature interpolation, explicit black
borders and opaque final alpha. The original color-adjust, phosphor-dot and
RGB-offset/stretch algorithms are retained as three separate GPU passes.
