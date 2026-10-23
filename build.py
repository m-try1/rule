#!/usr/bin/env python3
"""Generate Clash rule-provider YAML from the Surge rule lists.

Surge/*.list is the single source of truth. Clash/*.yaml is generated output
and must never be edited by hand.

Usage:
    ./build.py           rewrite Clash/*.yaml
    ./build.py --check   exit 1 if any generated file is out of date
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "Surge"
OUT_DIR = ROOT / "Clash"

# Rule types Clash classical behaviour understands.
CLASH_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-WILDCARD",
    "IP-CIDR",
    "IP-CIDR6",
    "SRC-IP-CIDR",
    "GEOIP",
    "PROCESS-NAME",
    "DST-PORT",
    "SRC-PORT",
}

# Surge-only options that Clash has no concept of, so they are dropped.
SURGE_ONLY_OPTIONS = {"extended-matching", "pre-matching"}

# Options that carry over unchanged.
KEPT_OPTIONS = {"no-resolve"}

GEN_NOTE = "# Generated from Surge/{name}.list by build.py -- DO NOT EDIT"


def split_rule(text):
    return [part.strip() for part in text.split(",")]


def convert_rule(text, where):
    """Convert one Surge rule body to Clash form. Returns the body string."""
    parts = split_rule(text)
    if len(parts) < 2:
        raise ValueError(f"{where}: cannot parse rule {text!r}")

    rule_type = parts[0].upper()
    if rule_type not in CLASH_TYPES:
        raise ValueError(f"{where}: rule type {rule_type!r} has no Clash equivalent")

    out = [rule_type, parts[1]]

    for option in parts[2:]:
        if not option:
            continue
        if option in SURGE_ONLY_OPTIONS:
            continue
        if option in KEPT_OPTIONS:
            out.append(option)
            continue
        raise ValueError(f"{where}: unknown option {option!r} in {text!r}")

    return ",".join(out)


def looks_like_rule(text):
    first = text.split(",", 1)[0].strip().upper()
    return "," in text and first in CLASH_TYPES


def convert_line(line, lineno, where):
    stripped = line.strip()

    if not stripped:
        return ""

    if stripped.startswith("#"):
        body = stripped[1:].strip()
        if looks_like_rule(body):
            return f"#  - {convert_rule(body, f'{where}:{lineno}')}"
        return stripped

    return f"  - {convert_rule(stripped, f'{where}:{lineno}')}"


def build_one(src_path):
    name = src_path.stem
    lines = src_path.read_text(encoding="utf-8").splitlines()

    header = [f"# NAME: {name}"]
    body_start = 0

    # Carry over the leading "# NAME:" / "# Type:" preamble verbatim,
    # retitling NAME. The preamble ends at the first blank line.
    while body_start < len(lines):
        stripped = lines[body_start].strip()
        if not stripped:
            if header:
                body_start += 1
                break
            body_start += 1
            continue
        if not stripped.startswith("#"):
            break
        if stripped.upper().startswith("# NAME:"):
            header = [f"# NAME: {name}"]
            body_start += 1
            continue
        header.append(stripped)
        body_start += 1

    out = list(header)
    out.append(GEN_NOTE.format(name=name))
    out.append("")
    out.append("payload:")

    for offset, line in enumerate(lines[body_start:], start=body_start + 1):
        out.append(convert_line(line, offset, f"Surge/{src_path.name}"))

    # Collapse runs of blank lines and trim trailing blanks.
    cleaned = []
    for line in out:
        if not line and cleaned and not cleaned[-1]:
            continue
        cleaned.append(line)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return "\n".join(cleaned) + "\n"


def main():
    check = "--check" in sys.argv[1:]

    sources = sorted(SRC_DIR.glob("*.list"))
    if not sources:
        print(f"error: no *.list found in {SRC_DIR}", file=sys.stderr)
        return 1

    stale = []
    for src in sources:
        text = build_one(src)
        dst = OUT_DIR / f"{src.stem}.yaml"
        if check:
            old = dst.read_text(encoding="utf-8") if dst.exists() else None
            if old != text:
                stale.append(dst.name)
            continue
        dst.write_text(text, encoding="utf-8")
        print(f"wrote {dst.relative_to(ROOT)}")

    if check:
        if stale:
            print("out of date: " + ", ".join(stale), file=sys.stderr)
            print("run ./build.py and commit the result", file=sys.stderr)
            return 1
        print(f"all {len(sources)} generated files are up to date")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
