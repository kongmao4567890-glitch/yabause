#!/usr/bin/env python3
"""Build a version-aware offline catalogue from the user's three SS collections.

Do not guess missing addresses, convert other consoles' formats, or split a
conditional/multi-line cheat into independent writes. Keep rejected groups as
readable reference entries, with all of their original lines.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "yabause/src/android/app/src/main/assets/cheats/catalog.json"
SOURCES = ["SS金手指和秘籍.txt", "SS金手指和秘籍1.txt", "SS金手指和秘籍2.txt"]


def normalize_code(line):
    match = re.fullmatch(r"([0-9a-fA-F]{8})\s+([0-9a-fA-F]{1,4})", line)
    if not match:
        match = re.fullmatch(r"([0-9a-fA-F]{8})([0-9a-fA-F]{4})", line)
    return f"{match[1].upper()} {int(match[2], 16):04X}" if match else None


def code_like(line):
    return bool(re.match(r"^[0-9A-Fa-f?]{6,}(?:\s|$)", line) or
                (re.fullmatch(r"[0-9A-Fa-f?\s]+", line) and re.search(r"[0-9?]", line)))


def parse(text, source):
    games = []
    game = None
    labels, raw_codes = [], []
    section = ""

    def flush():
        nonlocal labels, raw_codes
        if game is not None:
            if raw_codes:
                title = labels[-1] if labels else "未命名金手指"
                game["notes"].extend(labels[:-1])
                normalized = [normalize_code(line) for line in raw_codes]
                reason = ""
                if any(code is None for code in normalized):
                    reason = "incomplete"
                elif any(code[0] not in "13D" for code in normalized):
                    reason = "unsupported"
                elif normalized[-1].startswith("D"):
                    reason = "incomplete"
                game["entries"].append({"title": title,
                    "code": "\n".join(normalized) if not reason else "",
                    "raw": "\n".join(raw_codes), "reason": reason})
            elif labels:
                game["notes"].append("\n".join(labels))
        labels, raw_codes = [], []

    for raw in text.lstrip("\ufeff").splitlines():
        line = raw.strip()
        if line.startswith("-") and len(line) > 1:
            flush()
            game = {"name": line[1:].strip(), "source": source, "entries": [], "notes": []}
            games.append(game)
            section = ""
        elif game is None:
            continue
        elif not line:
            flush()
        elif "=" in line and normalize_code(line.rsplit("=", 1)[1].strip()):
            # Stage/item choices are mutually independent entries, never one giant cheat.
            if labels and labels[-1].startswith("[") and labels[-1].endswith("]"):
                section = labels[-1]
            flush()
            title, code = line.rsplit("=", 1)
            labels = [(section + " " + title.strip()).strip()]
            raw_codes = [code.strip()]
            flush()
        elif normalize_code(line) or code_like(line):
            raw_codes.append(line)
        else:
            if raw_codes:
                flush()
            labels.append(line)
    flush()
    for index, game in enumerate(games):
        game["id"] = hashlib.sha256(f"{source}:{index}:{game['name']}".encode()).hexdigest()[:16]
        seen = set()
        unique = []
        for entry in game["entries"]:
            key = (entry["title"], entry["raw"])
            if key not in seen:
                seen.add(key)
                unique.append(entry)
        game["entries"] = unique
    return games


def build():
    games = []
    for index, name in enumerate(SOURCES):
        games.extend(parse((ROOT / f"tools/cheat_catalog_sources/ss-cheats-{index}.txt")
                           .read_text(encoding="utf-8-sig"), name))
    return {"format": 1, "games": games}


if __name__ == "__main__":
    catalog = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n")
    entries = [e for g in catalog["games"] for e in g["entries"]]
    print(f"{len(catalog['games'])} game records; {sum(not e['reason'] for e in entries)} "
          f"importable groups; {sum(bool(e['reason']) for e in entries)} reference-only groups")
