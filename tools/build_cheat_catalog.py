#!/usr/bin/env python3
"""Build a version-aware offline catalogue from the user's SS text and .cht collections.

Do not guess missing addresses, convert other consoles' formats, or split a
conditional/multi-line cheat into independent writes. Keep rejected groups as
readable reference entries, with all of their original lines.
"""
import hashlib
import json
from pathlib import Path
import re
import zipfile

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


def parse_cht(text, source, name):
    """Read the supplied SS .cht export without executing config values.

    Commas join writes belonging to one effect; hyphens separate address/value.
    The source enable flag never enables an imported cheat automatically.
    """
    records = {}
    notes = []
    for raw in text.lstrip("\ufeff").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            notes.append(line[1:].strip())
            continue
        match = re.fullmatch(r'cheat(\d+)_(desc|code|enable)\s*=\s*"(.*)"', line)
        if not match:
            raise ValueError(f"Unrecognized .cht field in {source}")
        record = records.setdefault(int(match[1]), {})
        if match[2] in record:
            raise ValueError(f"Duplicate .cht field in {source}")
        record[match[2]] = match[3]
    entries = []
    for index, record in sorted(records.items()):
        raw = record.get("code", "")
        codes = [normalize_code(part.strip().replace("-", " ")) for part in raw.split(",")]
        reason = ""
        if any(code is None for code in codes):
            reason = "incomplete"
        elif any(code[0] not in "13D" for code in codes):
            reason = "unsupported"
        elif codes[-1].startswith("D"):
            reason = "incomplete"
        entries.append({"title": record.get("desc") or f"金手指 {index + 1}",
                        "code": "\n".join(codes) if not reason else "",
                        "raw": raw, "reason": reason})
    return {"id": hashlib.sha256(source.encode()).hexdigest()[:16],
            "name": name, "source": source, "entries": entries, "notes": notes}


def build():
    games = []
    for index, name in enumerate(SOURCES):
        games.extend(parse((ROOT / f"tools/cheat_catalog_sources/ss-cheats-{index}.txt")
                           .read_text(encoding="utf-8-sig"), name))
    with zipfile.ZipFile(ROOT / "tools/cheat_catalog_sources/SS.zip") as archive:
        for member in sorted(archive.namelist()):
            if member.endswith(".cht"):
                name = Path(member).stem.removeprefix("SS_")
                games.append(parse_cht(archive.read(member).decode("utf-8-sig"),
                                       "SS.zip / " + Path(member).name, name))
    return {"format": 1, "games": games}


if __name__ == "__main__":
    catalog = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n")
    entries = [e for g in catalog["games"] for e in g["entries"]]
    print(f"{len(catalog['games'])} game records; {sum(not e['reason'] for e in entries)} "
          f"importable groups; {sum(bool(e['reason']) for e in entries)} reference-only groups")
