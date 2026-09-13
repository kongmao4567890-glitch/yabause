#!/usr/bin/env python3
"""Compile and render the shipped shaders with a headless EGL GLES 3 context.

Needs Mesa EGL, numpy and Pillow. --preview-dir writes optional visual QA images.
"""
import argparse
import ast
import ctypes as C
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("--preview-dir", type=Path)
args = parser.parse_args()
os.environ.setdefault("EGL_PLATFORM", "surfaceless")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
egl = C.CDLL("libEGL.so.1")
I, U, F, P = C.c_int, C.c_uint, C.c_float, C.c_void_p
egl.eglGetProcAddress.argtypes = [C.c_char_p]
egl.eglGetProcAddress.restype = P


def fn(name, result, *params):
    address = egl.eglGetProcAddress(name.encode())
    if not address:
        raise RuntimeError("Missing GL/EGL function: " + name)
    return C.CFUNCTYPE(result, *params)(address)


def ints(*values):
    return (I * len(values))(*values)


display = fn("eglGetDisplay", P, P)(None)
major, minor = I(), I()
assert fn("eglInitialize", U, P, P, P)(display, C.byref(major), C.byref(minor)), "EGL initialization failed"
assert fn("eglBindAPI", U, U)(0x30A0)  # EGL_OPENGL_ES_API
config, count = P(), I()
assert fn("eglChooseConfig", U, P, P, P, I, P)(display,
    ints(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038),
    C.byref(config), 1, C.byref(count)) and count.value
surface = fn("eglCreatePbufferSurface", P, P, P, P)(display, config, ints(0x3057, 960, 0x3056, 720, 0x3038))
context = fn("eglCreateContext", P, P, P, P, P)(display, config, None, ints(0x3098, 3, 0x3038))
assert surface and context
assert fn("eglMakeCurrent", U, P, P, P, P)(display, surface, surface, context)

create_shader = fn("glCreateShader", U, U)
shader_source = fn("glShaderSource", None, U, I, P, P)
compile_shader = fn("glCompileShader", None, U)
get_shader = fn("glGetShaderiv", None, U, U, P)
get_shader_log = fn("glGetShaderInfoLog", None, U, I, P, P)
create_program = fn("glCreateProgram", U)
attach_shader = fn("glAttachShader", None, U, U)
link_program = fn("glLinkProgram", None, U)
get_program = fn("glGetProgramiv", None, U, U, P)
get_program_log = fn("glGetProgramInfoLog", None, U, I, P, P)
use_program = fn("glUseProgram", None, U)
get_uniform = fn("glGetUniformLocation", I, U, C.c_char_p)
uniform1 = fn("glUniform1i", None, I, I)
uniform2 = fn("glUniform2f", None, I, F, F)
bind_texture = fn("glBindTexture", None, U, U)
texture_image = fn("glTexImage2D", None, U, I, I, I, I, I, U, U, P)
texture_param = fn("glTexParameteri", None, U, U, I)
viewport = fn("glViewport", None, I, I, I, I)
clear_color = fn("glClearColor", None, F, F, F, F)
clear = fn("glClear", None, U)
draw = fn("glDrawArrays", None, U, I, I)
read = fn("glReadPixels", None, I, I, I, I, U, U, P)
get_error = fn("glGetError", U)

header = (Path(__file__).resolve().parents[1] / "shaders/DisplayFilters.h").read_text()

# Compile the actual C renderer against the system GL dispatch library. Small
# declarations let this regression test run without a complete Android SDK.
native_source = (Path(__file__).resolve().parents[1] / "yglshaderes.c").read_text()
native_source = native_source[native_source.index("/* Display post-processing is compiled lazily"):]
native_prefix = r'''
#include <stdio.h>
#include <stdint.h>
#include "shaders/DisplayFilters.h"
typedef unsigned int GLuint, GLenum, u32;
typedef int GLint, GLsizei;
typedef unsigned char GLboolean;
typedef char GLchar;
typedef float GLfloat;
#define GL_FALSE 0
#define GL_VERTEX_SHADER 0x8B31
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_CURRENT_PROGRAM 0x8B8D
#define GL_VERTEX_ARRAY_BINDING 0x85B5
#define GL_ACTIVE_TEXTURE 0x84E0
#define GL_TEXTURE0 0x84C0
#define GL_TEXTURE_BINDING_2D 0x8069
#define GL_DEPTH_TEST 0x0B71
#define GL_BLEND 0x0BE2
#define GL_STENCIL_TEST 0x0B90
#define GL_TEXTURE_2D 0x0DE1
#define GL_TRIANGLES 0x0004
#define AA_CRT_LOTTES 4
#define AA_DOT_CLEAR 9
#define GL_SRGB8_ALPHA8 0x8C43
#define GL_RGBA8 0x8058
#define GL_RGBA 0x1908
#define GL_UNSIGNED_BYTE 0x1401
#define GL_DRAW_FRAMEBUFFER 0x8CA9
#define GL_DRAW_FRAMEBUFFER_BINDING 0x8CA6
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_SAMPLER_BINDING 0x8919
#define GL_VIEWPORT 0x0BA2
#define GL_SCISSOR_TEST 0x0C11
#define GL_TEXTURE_MIN_FILTER 0x2801
#define GL_TEXTURE_MAG_FILTER 0x2800
#define GL_TEXTURE_WRAP_S 0x2802
#define GL_TEXTURE_WRAP_T 0x2803
#define GL_CLAMP_TO_EDGE 0x812F
#define GL_LINEAR 0x2601
extern void glGenTextures(GLsizei, GLuint*);
extern void glDeleteTextures(GLsizei, const GLuint*);
extern void glGenFramebuffers(GLsizei, GLuint*);
extern void glDeleteFramebuffers(GLsizei, const GLuint*);
extern void glGenSamplers(GLsizei, GLuint*);
extern void glDeleteSamplers(GLsizei, const GLuint*);
extern void glSamplerParameteri(GLuint, GLenum, GLint);
extern void glBindSampler(GLuint, GLuint);
extern void glTexImage2D(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*);
extern void glBindFramebuffer(GLenum, GLuint);
extern void glFramebufferTexture2D(GLenum, GLenum, GLenum, GLuint, GLint);
extern GLenum glCheckFramebufferStatus(GLenum);
extern void glViewport(GLint, GLint, GLsizei, GLsizei);
#define RES_NATIVE 0
#define YGLLOG printf
extern void glDeleteProgram(GLuint);
extern void glDeleteVertexArrays(GLsizei, const GLuint*);
extern GLuint glCreateShader(GLenum);
extern void glShaderSource(GLuint, GLsizei, const GLchar *const*, const GLint*);
extern void glCompileShader(GLuint);
extern void glGetShaderiv(GLuint, GLenum, GLint*);
extern void glDeleteShader(GLuint);
extern GLuint glCreateProgram(void);
extern void glAttachShader(GLuint, GLuint);
extern void glLinkProgram(GLuint);
extern void glGetProgramiv(GLuint, GLenum, GLint*);
extern void glGenVertexArrays(GLsizei, GLuint*);
extern void glGetIntegerv(GLenum, GLint*);
extern void glActiveTexture(GLenum);
extern GLboolean glIsEnabled(GLenum);
extern void glDisable(GLenum);
extern void glEnable(GLenum);
extern void glUseProgram(GLuint);
extern void glBindVertexArray(GLuint);
extern void glBindTexture(GLenum, GLuint);
extern GLint glGetUniformLocation(GLuint, const GLchar*);
extern void glUniform1i(GLint, GLint);
extern void glUniform2f(GLint, GLfloat, GLfloat);
extern void glDrawArrays(GLenum, GLint, GLsizei);
static void Ygl_printShaderError(int unused, GLuint handle) { (void)unused; (void)handle; }
static struct { int width, height, rwidth, rheight, rotate_screen, resolution_mode; } state, *_Ygl = &state;
void set_filter_sizes(int w, int h, int rw, int rh) {
    state.width=w; state.height=h; state.rwidth=rw; state.rheight=rh;
}
void set_filter_rotation(int enabled) { state.rotate_screen=enabled; state.resolution_mode=enabled; }
'''
native_tmp = tempfile.TemporaryDirectory(prefix="display-filter-test-")
native_path = Path(native_tmp.name) / "renderer.c"
native_path.write_text(native_prefix + native_source)
native_library = Path(native_tmp.name) / "renderer.so"
subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", "-D_OGLES3_", "-Wall", "-Wextra", "-Werror",
                "-I", str(Path(__file__).resolve().parents[1]), str(native_path),
                "-l:libGL.so.1", "-o", str(native_library)], check=True)
renderer = C.CDLL(str(native_library))
renderer.YglBlitDisplayFilter.argtypes = [U, I, I, I]
renderer.YglBlitDisplayFilter.restype = I


def shader_body(name):
    match = re.search(r"static const char " + name + r"\[\]\s*=\s*((?:\"(?:[^\"\\]|\\.)*\"\s*)+);", header)
    assert match, name
    return "".join(ast.literal_eval(part) for part in re.findall(r'"(?:[^"\\]|\\.)*"', match[1]))


def shader(kind, body, mode):
    handle = create_shader(kind)
    data = ("#version 300 es\n#define FILTER_MODE %d\n" % mode + body).encode()
    strings = (C.c_char_p * 1)(data)
    shader_source(handle, 1, strings, None)
    compile_shader(handle)
    ok = I()
    get_shader(handle, 0x8B81, C.byref(ok))
    log = C.create_string_buffer(8192)
    get_shader_log(handle, len(log), None, log)
    assert ok.value, "Filter %d compile: %s" % (mode, log.value.decode())
    return handle


display_header = header
header = (Path(__file__).resolve().parents[1] / "shaders/DotClearShaders.h").read_text()
for pass_index in range(3):
    handle = shader(0x8B30, shader_body("dot_clear_fragment_%d" % pass_index), 9)
    fn("glDeleteShader", None, U)(handle)
header = display_header

programs = {}
for mode in [0, 4, 5, 6, 7, 8, 9]:
    v = shader(0x8B31, shader_body("display_filter_vertex"), mode)
    f = shader(0x8B30, shader_body("display_filter_fragment"), mode)
    program = create_program()
    attach_shader(program, v)
    attach_shader(program, f)
    link_program(program)
    ok, log = I(), C.create_string_buffer(8192)
    get_program(program, 0x8B82, C.byref(ok))
    get_program_log(program, len(log), None, log)
    assert ok.value, log.value.decode()
    programs[mode] = program
    fn("glDeleteShader", None, U)(v)
    fn("glDeleteShader", None, U)(f)

vao, texture = U(), U()
fn("glGenVertexArrays", None, I, P)(1, C.byref(vao))
fn("glBindVertexArray", None, U)(vao)
fn("glGenTextures", None, I, P)(1, C.byref(texture))
bind_texture(0x0DE1, texture)
for key, val in [(0x2801, 0x2601), (0x2800, 0x2601), (0x2802, 0x812F), (0x2803, 0x812F)]:
    texture_param(0x0DE1, key, val)

pattern = Image.new("RGBA", (320, 224), (130, 130, 130, 255))
d = ImageDraw.Draw(pattern)
for box, color in [((0, 0, 159, 111), (240, 35, 35)), ((160, 0, 319, 111), (35, 240, 35)),
                   ((0, 112, 159, 223), (35, 35, 240))]:
    d.rectangle(box, fill=color + (255,))
for x in range(0, 320, 4):
    d.line((x, 96, x, 127), fill=(240, 240, 240, 255), width=1)
d.text((83, 36), "SATURN FILTER TEST", fill=(255, 255, 255, 255))
for radius in [8, 16, 24, 32]:
    d.ellipse((240-radius, 170-radius, 240+radius, 170+radius), outline=(255, 220, 30, 255))

previews = {}
for native, source, output in [((320, 224), (320, 224), (960, 672)),
                                ((320, 224), (640, 448), (640, 448)),
                                ((320, 224), (320, 224), (853, 699)),
                                ((320, 240), (320, 240), (640, 480)),
                                ((640, 448), (640, 448), (320, 224)),
                                ((320, 224), (320, 224), (160, 112))]:
    pixels = np.asarray(pattern.resize(source, Image.Resampling.NEAREST)).copy()
    texture_image(0x0DE1, 0, 0x1908, *source, 0, 0x1908, 0x1401, pixels.ctypes.data)
    renderer.set_filter_sizes(*source, *native)
    results = {}
    for mode, program in programs.items():
        use_program(program)
        uniform1(get_uniform(program, b"uSource"), 0)
        for key, size in [(b"uNativeSize", native), (b"uTextureSize", source), (b"uOutputSize", output)]:
            uniform2(get_uniform(program, key), *size)
        clear_color(0.2, 0.1, 0.3, 1.0)
        clear(0x4000)
        x = 0 if output[0] == 960 else 11
        viewport(x, 13, *output)
        if mode == 0:
            draw(0x0004, 0, 3)
        else:
            assert renderer.YglBlitDisplayFilter(texture, mode, *output) == 0
            for key, expected in [(0x8B8D, program), (0x85B5, vao.value), (0x8069, texture.value)]:
                current = I()
                fn("glGetIntegerv", None, U, P)(key, C.byref(current))
                assert current.value == expected, "Renderer leaked GL state"
        image = np.zeros((output[1], output[0], 4), np.uint8)
        read(x, 13, *output, 0x1908, 0x1401, image.ctypes.data)
        assert get_error() == 0, (mode, native, output)
        assert image[:, :, 3].min() == 255, "Opaque output required"
        assert image[:, :, :3].mean() > 30, "Filter produced a black frame"
        # Verify orientation and channel order against the raw frame.
        for fx, fy, channel in [(0.2, 0.2, 0), (0.7, 0.2, 1), (0.2, 0.7, 2)]:
            pixel = image[int(output[1]*fy), int(output[0]*fx), :3]
            assert pixel.argmax() == channel, (mode, pixel)
        outside = np.zeros(4, np.uint8)
        read(0, 0, 1, 1, 0x1908, 0x1401, outside.ctypes.data)
        assert np.allclose(outside, [51, 26, 76, 255], atol=1), "Viewport leaked into letterbox"
        results[mode] = image
        if output == (960, 672):
            previews[mode] = image
    if output == (960, 672):
        for mode in [4, 5, 6, 7, 8, 9]:
            assert np.any(results[mode] != results[0]), "Filter has no effect: %d" % mode
        assert np.any(results[4] != results[5]), "Bloom and light presets must differ"
        assert results[4][0, 0, :3].max() == 0, "CRT curvature should blank corners"

renderer.set_filter_rotation(1)
renderer.set_filter_sizes(320, 224, 320, 224)
pixels = np.asarray(pattern).copy()
texture_image(0x0DE1, 0, 0x1908, 320, 224, 0, 0x1908, 0x1401, pixels.ctypes.data)
viewport(0, 0, 448, 640)
for mode in [4, 5, 6, 7, 8, 9]:
    assert renderer.YglBlitDisplayFilter(texture, mode, 448, 640) == 0
    rotated = np.zeros((640, 448, 4), np.uint8)
    read(0, 0, 448, 640, 0x1908, 0x1401, rotated.ctypes.data)
    for fx, fy, channel in [(0.2, 0.2, 2), (0.8, 0.2, 0), (0.8, 0.8, 1)]:
        assert rotated[int(640*fy), int(448*fx), :3].argmax() == channel, "Rotation lost"
renderer.set_filter_rotation(0)

# Independent reference: compile the original three GLSL passes with uniforms,
# without using the generated strings or the native C presentation pipeline.
source_dir = Path(__file__).resolve().parents[1] / "shaders/phosphor-dot-v3.3"
originals = [(source_dir / "passes" / (name + ".glsl")).read_text()
             for name in ["color-adjust", "phosphor-dot", "rgb-offset"]]
parameters = {}
for original in originals:
    parameters.update({k: float(v) for k, v in
        re.findall(r'#pragma parameter (\w+) "[^"]*" ([\d.-]+)', original)})
parameters.update({k: float(v) for k, v in re.findall(r'^(\w+) = "([\d.-]+)"',
                  (source_dir / "Dot-clear.glslp").read_text(), re.M)})
ref_programs = []
for original in originals:
    before = original.split("#if defined(VERTEX)")[0]
    fragment = before + original.split("#elif defined(FRAGMENT)", 1)[1].rsplit("#endif", 1)[0]
    fragment = "precision highp float;\nprecision highp int;\n" + fragment
    fragment = re.sub(r'^#pragma.*\n', '', fragment, flags=re.M)
    fragment = fragment.replace("COMPAT_VARYING vec4 TEX0;", "in vec2 vTexCoord;")
    fragment = fragment.replace("#define vTexCoord TEX0.xy", "")
    # Match RetroArch's desktop full precision; no algorithm or default substitution.
    fragment = fragment.replace("#define COMPAT_PRECISION mediump", "#define COMPAT_PRECISION highp")
    v = shader(0x8B31, shader_body("display_filter_vertex"), 9)
    f = shader(0x8B30, fragment, 9)
    program = create_program()
    attach_shader(program, v); attach_shader(program, f); link_program(program)
    ok = I(); get_program(program, 0x8B82, C.byref(ok)); assert ok.value
    fn("glDeleteShader", None, U)(v); fn("glDeleteShader", None, U)(f)
    ref_programs.append(program)
    use_program(program)
    for key, value in parameters.items():
        fn("glUniform1f", None, I, F)(get_uniform(program, key.encode()), value)

for ref_output in [(960, 672), (853, 699)]:
    viewport(0, 0, *ref_output)
    assert renderer.YglBlitDisplayFilter(texture, 9, *ref_output) == 0
    ported = np.zeros((ref_output[1], ref_output[0], 4), np.uint8)
    read(0, 0, *ref_output, 0x1908, 0x1401, ported.ctypes.data)
    ref_textures, ref_fbos = (U * 3)(), (U * 3)()
    fn("glGenTextures", None, I, P)(3, ref_textures)
    fn("glGenFramebuffers", None, I, P)(3, ref_fbos)
    framebuffer = fn("glBindFramebuffer", None, U, U)
    for i in range(3):
        bind_texture(0x0DE1, ref_textures[i])
        for key, value in [(0x2801, 0x2601), (0x2800, 0x2601), (0x2802, 0x812D), (0x2803, 0x812D)]:
            texture_param(0x0DE1, key, value)
        w, h = (320, 224) if i == 0 else ref_output
        texture_image(0x0DE1, 0, 0x8C43 if i == 0 else 0x8058, w, h, 0, 0x1908, 0x1401, None)
        framebuffer(0x8D40, ref_fbos[i])
        fn("glFramebufferTexture2D", None, U, U, U, U, I)(0x8D40, 0x8CE0, 0x0DE1, ref_textures[i], 0)
        assert fn("glCheckFramebufferStatus", U, U)(0x8D40) == 0x8CD5
        use_program(ref_programs[i])
        bind_texture(0x0DE1, texture if i == 0 else ref_textures[i - 1])
        uniform1(get_uniform(ref_programs[i], b"Texture"), 0)
        for key, size in [(b"InputSize", ref_output if i == 2 else (320, 224)),
                          (b"TextureSize", ref_output if i == 2 else (320, 224)),
                          (b"OrigInputSize", (320, 224)), (b"OutputSize", (w, h))]:
            uniform2(get_uniform(ref_programs[i], key), *size)
        viewport(0, 0, w, h); draw(0x0004, 0, 3)
    reference = np.zeros((ref_output[1], ref_output[0], 4), np.uint8)
    read(0, 0, *ref_output, 0x1908, 0x1401, reference.ctypes.data)
    error = np.abs(reference[:, :, :3].astype(int) - ported[:, :, :3].astype(int))
    assert error.max() <= 1, ("Dot-clear differs from original preset", error.max(), error.mean())
    print("PASS: original Dot-clear three-pass reference, maximum RGB error:", error.max())
    framebuffer(0x8D40, 0)
    fn("glDeleteTextures", None, I, P)(3, ref_textures)
    fn("glDeleteFramebuffers", None, I, P)(3, ref_fbos)
    bind_texture(0x0DE1, texture)
for program in ref_programs:
    fn("glDeleteProgram", None, U)(program)

if args.preview_dir:
    args.preview_dir.mkdir(parents=True, exist_ok=True)
    for mode, image in previews.items():
        Image.fromarray(image).save(args.preview_dir / ("filter-%d.png" % mode))

use_program(0)
for program in programs.values():
    fn("glDeleteProgram", None, U)(program)
renderer.YglDeleteDisplayFilters()
assert renderer.YglBlitDisplayFilter(texture, 4, 160, 112) == 0, "Filters must rebuild after teardown"
assert renderer.YglBlitDisplayFilter(texture, 9, 160, 112) == 0, "Dot-clear must rebuild after teardown"
assert renderer.YglBlitDisplayFilter(texture, 99, 160, 112) == -1
assert get_error() == 0
renderer.YglDeleteDisplayFilters()
fn("glDeleteTextures", None, I, P)(1, C.byref(texture))
fn("glDeleteVertexArrays", None, I, P)(1, C.byref(vao))
fn("eglMakeCurrent", U, P, P, P, P)(display, None, None, None)
fn("eglDestroyContext", U, P, P)(display, context)
fn("eglDestroySurface", U, P, P)(display, surface)
fn("eglTerminate", U, P)(display)
native_tmp.cleanup()
print("PASS: C renderer and six GLES 3 filters (including three-pass Dot-clear); PAL/NTSC, scaling, viewport, colours, bloom, GL state and teardown")
