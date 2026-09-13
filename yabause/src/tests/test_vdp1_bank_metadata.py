#!/usr/bin/env python3
"""Exercise real 256-colour bank decoders; optional user savestates stay local."""
import argparse
from pathlib import Path
import struct
import tempfile
from test_vdp1_rgb_metadata import build, chunks, commands, decode


def check(lib):
    # VDP2 manual 9.1, sprite types 0..7: priority shift/mask, CC shift/mask.
    layouts = [(14, 3, 11, 7), (13, 7, 11, 3), (14, 1, 11, 7),
               (13, 3, 11, 3), (13, 3, 10, 7), (12, 7, 11, 1),
               (12, 7, 10, 3), (12, 7, 9, 7)]
    ram, regs = bytearray(0x80000), bytearray(288)
    dots = [0, 1, 2, 16, 32, 64, 128, 253]
    ram[0x800:0x808] = bytes(dots)
    cmd = [0] * 16
    cmd[2:6] = [0xa0, 0, 0x100, 0x0101]
    for sprite_type, (ps, pm, cs, cm) in enumerate(layouts):
        struct.pack_into('<H', regs, 0xe0, sprite_type)
        for priority in range(pm + 1):
            for ratio in range(cm + 1):
                cmd[3] = (priority << ps) | (ratio << cs) | 0x100
                pixels = decode(lib, ram, regs, cmd)
                expected = [0 if dot == 0 else
                            ((0xc0 | (ratio << 3) | priority) << 24) | 0x100 | dot
                            for dot in dots]
                assert pixels == expected, (sprite_type, hex(cmd[3]),
                                            hex(pixels[1]), hex(expected[1]))


def check_states(lib, paths):
    total = 0
    for path in paths:
        state = chunks(path)
        ram = state[b'VDP1'][52:52+0x80000]
        regs = state[b'VDP2'][:288]
        assert struct.unpack_from('<H', regs, 0xe0)[0] == 0x1235
        count, draws = 0, 0
        for address, cmd in commands(ram):
            if cmd[2] != 0xa0 or cmd[3] != 0x5e00:
                continue
            draws += 1
            for pixel in decode(lib, ram, regs, cmd):
                if pixel:
                    assert pixel >> 24 == 0xcd, (path.name, hex(address), hex(pixel))
                    assert pixel & 0xffff < 0x800
                    count += 1
        print(f'  {path.name}: {draws} overlay commands, {count} pixels select ratio 1')
        total += count
    if paths:
        assert total > 0, 'No affected bank sprites in the supplied states'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('states', nargs='*', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='vdp1-bank-test-') as directory:
        for backend in ('OpenGL', 'Vulkan'):
            lib = build(Path(directory), backend)
            check(lib)
            check_states(lib, args.states)
            print(backend + ': bank sprite metadata regression tests passed')


if __name__ == '__main__':
    main()
