#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from build_cheat_catalog import build, normalize_code, parse, OUTPUT, ROOT


class CatalogTest(unittest.TestCase):
    def test_consecutive_titles_keep_groups(self):
        games = parse("-游戏A\n金钱\n16000000 FFFF\n16000002 0001\n体力\n36000004 63\n"
                      "-游戏B\n条件\nD6000000 0001\n16000002 0002\n", "test")
        self.assertEqual([len(g["entries"]) for g in games], [2, 1])
        self.assertEqual(games[0]["entries"][0]["code"], "16000000 FFFF\n16000002 0001")
        self.assertEqual(games[1]["entries"][0]["code"], "D6000000 0001\n16000002 0002")

    def test_choices_are_independent_and_keep_instructions(self):
        game = parse("-游戏\n[选关，用完关闭]\n第1关=1604EAF4 0001\n第2关=1604EAF4 0002\n", "t")[0]
        self.assertEqual(len(game["entries"]), 2)
        self.assertIn("用完关闭", game["entries"][1]["title"])
        self.assertEqual(game["entries"][1]["code"], "1604EAF4 0002")

    def test_no_partial_unsupported_or_broken_import(self):
        for lines in ["16000000 0001\nB6002800 0000", "16000000 0001\n16000002 ????",
                      "16000000 0001\n16320B4 0063", "D6000000 0001"]:
            entry = parse("-游戏\n效果\n" + lines, "t")[0]["entries"][0]
            self.assertEqual(entry["code"], "")
            self.assertEqual(entry["raw"], lines)
            self.assertTrue(entry["reason"])

    def test_notes_and_compact_codes(self):
        game = parse("\ufeff-游戏\r\n按键秘籍\r\n按 A 和 B\r\n\r\n金钱\r\n160000000001\r\n", "t")[0]
        self.assertIn("按 A 和 B", game["notes"][0])
        self.assertEqual(game["entries"][0]["code"], "16000000 0001")
        self.assertEqual(normalize_code("16000000\tff"), "16000000 00FF")

    def test_real_collection_is_reproducible_and_versioned(self):
        catalog = build()
        self.assertEqual(catalog, json.loads(OUTPUT.read_text()))
        self.assertEqual(len(catalog["games"]), 759)
        self.assertEqual(len({g["id"] for g in catalog["games"]}), 759)
        sf3 = [g for g in catalog["games"] if "GS-9203" in g["name"]]
        self.assertTrue(sf3 and sf3[0]["entries"])
        stages = [e for e in catalog["games"][0]["entries"] if "选关" in e["title"]]
        self.assertEqual(len(stages), 41)
        self.assertTrue(all(len(e["code"].splitlines()) == 1 for e in stages))
        for game in catalog["games"]:
            for entry in game["entries"]:
                if not entry["reason"]:
                    self.assertTrue(entry["code"])
                    for line in entry["code"].splitlines():
                        self.assertEqual(normalize_code(line), line)
                        self.assertIn(line[0], "13D")

    def test_native_parser_rejects_invalid_input(self):
        source = (ROOT / "yabause/src/cheat.c").read_text()
        start = source.index("int CheatAddARCode(")
        end = source.index("\n}", start) + 2
        test = r'''
#include <stdio.h>
#include <assert.h>
typedef unsigned int u32;
enum { CHEATTYPE_WORDWRITE, CHEATTYPE_BYTEWRITE, CHEATTYPE_ENABLE };
static int writes;
static int CheatAddCode(int type, u32 addr, u32 val) {
    (void)type; (void)addr; (void)val; ++writes; return 0;
}
''' + source[start:end] + r'''
int main(void) {
    assert(CheatAddARCode(NULL) == -1);
    assert(CheatAddARCode("") == -1);
    assert(CheatAddARCode("not a code") == -1);
    assert(CheatAddARCode("16000000") == -1);
    assert(CheatAddARCode("F6000914 C305") == -1);
    assert(writes == 0);
    assert(CheatAddARCode("1603E9D6 FFFF") == 0);
    assert(CheatAddARCode("36000000 0063") == 0);
    assert(CheatAddARCode("D6000000 0001") == 0);
    assert(writes == 3);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "test.c").write_text(test)
            subprocess.run(["cc", "-fsanitize=undefined", "-Wall", "-Werror", str(path / "test.c"), "-o", str(path / "test")], check=True)
            subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    unittest.main()
