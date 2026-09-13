#!/usr/bin/env python3
"""Run the real OpenGL/Vulkan texture decoders without a GPU or game image.

Optional .yss inputs stay local: only synthetic pixels are used by CI.
SEGA VDP2 manual section 9.2: RGB pixels select priority and CC ratio register 0.
"""
import argparse
import ctypes as C
from pathlib import Path
import re
import struct
import subprocess
import tempfile

SRC = Path(__file__).resolve().parents[1]


def function(source, signature):
    start = re.search(re.escape(signature) + r'[^;{]*\{', source).start()
    brace = source.index('{', start)
    # Ignore braces inside comments and strings while locating the function end.
    masked = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                    lambda m: ' ' * len(m[0]), source, flags=re.S)
    level = 1
    end = brace + 1
    while level:
        level += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    return source[start:end]


def structure(source, name):
    end = source.index('} ' + name + ';') + len(name) + 3
    start = source.rfind('typedef struct', 0, end)
    return source[start:end]


def build(directory, backend):
    ogl = (SRC / 'vidogl.c').read_text()
    vk = (SRC / 'vulkan/Vdp1Renderer.cpp').read_text()
    shared = (SRC / 'vidshared.h').read_text()
    ygl = (SRC / 'ygl.h').read_text()
    source = '''#include <stdint.h>
#include <string.h>
typedef uint8_t u8; typedef uint16_t u16; typedef int16_t s16;
typedef uint32_t u32; typedef uint64_t u64;
#define INLINE inline
#define FASTCALL
#define VDP1LOG(...) ((void)0)
static u8 *Vdp1Ram;
static u8 T1ReadByte(u8 *ram, u32 addr) { return ram[addr]; }
static u16 T1ReadWord(u8 *ram, u32 addr) { return ((u16)ram[addr]<<8)|ram[addr+1]; }
'''
    source += structure((SRC / 'vdp2.h').read_text(), 'Vdp2') + '\n'
    source += structure((SRC / 'vdp1.h').read_text(), 'vdp1cmd_struct') + '\n'
    source += structure(shared, 'spritepixelinfo_struct') + '\n'
    source += '''static Vdp2 registers, *fixVdp2Regs = &registers, *Vdp2Regs = &registers;
typedef struct { int w, h; } YglSprite;
typedef struct { int w; u32 *textdata; } YglTexture;
typedef YglTexture CharTexture;
static struct { int msb_shadow_count_[2], drawframe; } state, *_Ygl = &state;
static int msbShadowCount[2], drawframe;
'''
    for signature in ('static INLINE u32 VDP1COLOR(', 'static INLINE u32 VDP1COLOR16TO24('):
        source += function(ygl, signature) + '\n'
    for signature in ('static INLINE void Vdp1GetSpritePixelInfo(', 'static INLINE void Vdp1ProcessSpritePixel('):
        source += function(shared, signature) + '\n'
    if backend == 'OpenGL':
        for signature in ('static INLINE void Vdp1MaskSpritePixel(',
                          'static void FASTCALL Vdp1ReadPriority(',
                          'static void FASTCALL Vdp1ReadTexture('):
            source += function(ogl, signature) + '\n'
        decoder = 'Vdp1ReadTexture'
    else:
        for signature in ('static INLINE void maskSpritePixel(', 'void Vdp1Renderer::readPriority(',
                          'void Vdp1Renderer::readTexture('):
            part = function(vk, signature)
            source += part.replace('Vdp1Renderer::', '') + '\n'
        decoder = 'readTexture'
    source += '''
#ifdef __cplusplus
extern "C"
#endif
void decode(u8 *ram, const void *regs, const void *command,
                                        int w, int h, u32 *output) {
    Vdp1Ram = ram; memcpy(&registers, regs, sizeof(registers));
    vdp1cmd_struct cmd; memcpy(&cmd, command, sizeof(cmd));
    YglSprite sprite = {w, h}; YglTexture texture = {0, output};
    DECODER(&cmd, &sprite, &texture);
}
'''.replace('DECODER', decoder)
    code = directory / (backend + ('.c' if backend == 'OpenGL' else '.cpp'))
    code.write_text(source)
    library = code.with_suffix('.so')
    compiler = ['cc', '-std=c11', '-Wno-incompatible-pointer-types'] if backend == 'OpenGL' else ['g++', '-std=c++11']
    subprocess.run(compiler + ['-shared', '-fPIC', '-O1',
                    '-fsanitize=undefined', '-fno-sanitize-recover=undefined',
                    str(code), '-o', str(library)], check=True)
    lib = C.CDLL(str(library))
    lib.decode.argtypes = [C.c_void_p] * 3 + [C.c_int, C.c_int, C.c_void_p]
    return lib


def decode(lib, ram, regs, command):
    w, h = ((command[5] >> 8) & 63) * 8, command[5] & 255
    output = (C.c_uint32 * (w * h))()
    lib.decode(C.create_string_buffer(bytes(ram)), C.create_string_buffer(bytes(regs)),
               (C.c_uint16 * 15)(*command[:15]), w, h, output)
    return list(output)


def commands(ram):
    addr, ret, visited = 0, None, set()
    while addr not in visited and addr + 32 <= len(ram):
        visited.add(addr)
        words = struct.unpack_from('>16H', ram, addr)
        ctrl = words[0]
        if ctrl & 0x8000:
            return
        if not ctrl & 0x4000 and ctrl & 15 in (0, 1, 2):
            yield addr, words
        jump = (ctrl >> 12) & 3
        if jump == 0:
            addr += 32
        elif jump == 1:
            addr = words[1] * 8
        elif jump == 2:
            if ret is None:
                ret = addr + 32
            addr = words[1] * 8
        elif ret is not None:
            addr, ret = ret, None
        else:
            addr += 32


def chunks(path):
    data = path.read_bytes()
    assert data[:8] == b'YSS\x01\x02\x00\x00\x00', 'Expected little-endian YSS v2'
    offset, result = 20, {}
    while offset + 12 <= len(data):
        tag, version, size = struct.unpack_from('<4sII', data, offset)
        end = offset + 12 + size
        assert end <= len(data), 'Truncated savestate chunk'
        result[tag] = data[offset+12:end]
        offset = end
    return result


def check(lib, paths):
    # Vdp2 SPCTL uses sprite type 4 with RGB/palette mixing, as in the report.
    regs = bytearray(288)
    struct.pack_into('<H', regs, 0xe0, 0x2024)
    ram = bytearray(0x80000)
    command = [0] * 16
    command[2:6] = [0x142c, 0x7fff, 0x100, 0x0101]
    for i in range(8):
        struct.pack_into('>H', ram, 0x800 + 2*i, 0x8c63)
    rgb = decode(lib, ram, regs, command)
    assert all((pixel >> 24) == 0x80 for pixel in rgb), (
        'RGB16 inherited CMDCOLR priority/CC bits: ' + hex(rgb[0]))

    # Mixed LUT: palette pixel selecting ratio 7 followed by RGB, in both nibbles.
    command[2:6] = [0x00c8, 0x20, 0x100, 0x0101]
    ram[0x800:0x804] = bytes([0x12, 0x21, 0x12, 0x21])
    struct.pack_into('>HH', ram, 0x102, 0x3c01, 0x8c63)
    pixels = decode(lib, ram, regs, command)
    for i, index in enumerate([1, 2, 2, 1, 1, 2, 2, 1]):
        assert (pixels[i] >> 24) == (0xf9 if index == 1 else 0x80), (
            'Mixed LUT leaked metadata: ' + hex(pixels[i]))

    # A pure palette sprite still retains its explicit priority and ratio index.
    command[2:6] = [0x00d0, 0x3c00, 0x100, 0x0101]
    ram[0x800:0x808] = bytes([1] * 8)
    assert all(pixel >> 24 == 0xf9 for pixel in decode(lib, ram, regs, command))

    # Transparent pixels remain transparent when SPD is clear.
    command[2:6] = [0x0028, 0, 0x100, 0x0101]
    struct.pack_into('>8H', ram, 0x800, 0, 0x7fff, 0x8c63, 0x7fff,
                     0x8c63, 0x8c63, 0x8c63, 0x8c63)
    pixels = decode(lib, ram, regs, command)
    assert pixels[0] == pixels[1] == 0 and pixels[2] != 0
    # Exercise the existing two-end-code path with SPD enabled.
    command[2] = 0x0068
    pixels = decode(lib, ram, regs, command)
    assert pixels[1] == 0 and pixels[2] != 0 and pixels[3:] == [0]*5

    for path in paths:
        state = chunks(path)
        assert len(state[b'VDP1']) == 52 + 0x80000 + 0x40000
        assert len(state[b'VDP2']) == 288 + 0x80000 + 0x1000 + 4
        ram = state[b'VDP1'][52:52+0x80000]
        regs = state[b'VDP2'][:288]
        count = 0
        for addr, cmd in commands(ram):
            # Focus on direct RGB16 with a nonzero, unused CMDCOLR field.
            if (cmd[2] >> 3) & 7 != 5 or cmd[3] != 0x7fff or cmd[2] & 0x8000:
                continue
            pixels = decode(lib, ram, regs, cmd)
            for pixel in pixels:
                if pixel and not pixel & 0x40800000:
                    assert pixel >> 24 == 0x80, f'{path.name} command {addr:#x}: {pixel:#x}'
                    count += 1
        assert count, 'No affected RGB16 pixels found in supplied snapshot'
        print(f'  {path.name}: {count} RGB pixels select register 0')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('states', nargs='*', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='vdp1-rgb-test-') as directory:
        for backend in ('OpenGL', 'Vulkan'):
            lib = build(Path(directory), backend)
            check(lib, args.states)
            print(backend + ': RGB metadata regression tests passed')


if __name__ == '__main__':
    main()
