#!/usr/bin/env python3
"""Checks the board packs' files: format, ids and names. Python 3 standard library only.

    python3 scripts/check_packs.py [packs]

This is the quick check every pull request runs. It catches malformed JSON, missing or
mistyped fields, ids that don't match their file, and duplicate boards. Whether every
template places and builds on a board is checked by the maintainer with FPGALab before
publishing (the board editor in FPGALab shows a board's problems too).
"""

import json
import os
import re
import sys

ID = re.compile(r"[a-z0-9]+([._-][a-z0-9]+)*")
SIGNAL = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*(\[[0-9]+\])?")
HEX4 = re.compile(r"0[xX][0-9A-Fa-f]{4}")
HEX8 = re.compile(r"0[xX][0-9A-Fa-f]{8}")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}")
FAMILIES = {"ice40", "ecp5", "gowin", "gatemate"}
PULLS = {"up", "down", "keeper", "none"}
TARGETS = {"sram", "flash"}
# What a pack may contain: data only (FPGALab refuses anything else). Text only for now.
ALLOWED = {".json", ".fpgaboard", ".v", ".sv", ".vh", ".svh", ".pcf", ".lpf", ".cst", ".ccf", ".sdc", ".md", ".txt"}
MAX_FILE = 10 * 1024 * 1024

errors = 0
warnings = 0


def report(kind, path, message):
    global errors, warnings
    if kind == "error":
        errors += 1
    else:
        warnings += 1
    print(f"  {'✗' if kind == 'error' else '⚠︎'} {path}: {message}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{kind} file={path}::{message}")


class Checker:
    """Checks one JSON object against a field table: {name: (required, kind, extra check)}."""

    def __init__(self, path):
        self.path = path

    def fields(self, value, table, where):
        if not isinstance(value, dict):
            report("error", self.path, f"{where} must be an object")
            return
        for name, (required, kind, check) in table.items():
            if name not in value:
                if required:
                    report("error", self.path, f"{where}: '{name}' is missing")
                continue
            item = value[name]
            if not self.kind(item, kind):
                report("error", self.path, f"{where}.{name} must be {kind}")
            elif check:
                problem = check(item)
                if problem:
                    report("error", self.path, f"{where}.{name}: {problem}")
        for name in value:
            if name not in table:
                # FPGALab ignores unknown fields; here they are most likely typos.
                report("warning", self.path, f"{where}: unknown field '{name}'")

    @staticmethod
    def kind(item, kind):
        return {
            "a string": lambda v: isinstance(v, str),
            "a whole number": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "a number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "true or false": lambda v: isinstance(v, bool),
            "a list": lambda v: isinstance(v, list),
            "an object": lambda v: isinstance(v, dict),
        }[kind](item)


def matching(pattern, what):
    return lambda v: None if pattern.fullmatch(v) else f"'{v}' isn't a valid {what}"


def one_of(choices):
    return lambda v: None if v in choices else f"'{v}' must be one of {', '.join(sorted(choices))}"


def non_empty(v):
    return None if v.strip() else "must not be empty"


def positive(v):
    return None if v > 0 else "must be positive"


def strings(v):
    return None if all(isinstance(s, str) for s in v) else "must be a list of strings"


def string_map(v):
    return None if all(isinstance(k, str) and isinstance(x, str) for k, x in v.items()) else "keys and values must be strings"


MANIFEST = {
    "schema": (True, "a whole number", lambda v: None if v == 1 else "must be 1"),
    "id": (True, "a string", matching(ID, "pack id (lowercase, e.g. sipeed.tang)")),
    "name": (True, "a string", non_empty),
    "version": (True, "a string", matching(VERSION, "version (e.g. 1.0.0)")),
    "type": (True, "a string", lambda v: None if v == "boards" else "must be boards"),
    "maintainer": (False, "a string", None),
    "description": (False, "a string", None),
    "documentation": (False, "a string", None),
}

TARGET = {
    "family": (True, "a string", one_of(FAMILIES)),
    "device": (True, "a string", non_empty),
    "package": (False, "a string", None),
    "speed": (False, "a string", None),
}

CLOCK = {
    "name": (True, "a string", matching(SIGNAL, "signal name")),
    "pin": (True, "a string", non_empty),
    "frequencyMHz": (True, "a number", positive),
    "ioStandard": (False, "a string", None),
    "attributes": (False, "an object", string_map),
}

SIGNAL_FIELDS = {
    "name": (True, "a string", matching(SIGNAL, "signal name (e.g. led[0], uart_tx)")),
    "pin": (True, "a string", non_empty),
    "group": (False, "a string", None),
    "label": (False, "a string", None),
    "activeLow": (False, "true or false", None),
    "ioStandard": (False, "a string", None),
    "pull": (False, "a string", one_of(PULLS)),
    "drive": (False, "a whole number", positive),
    "attributes": (False, "an object", string_map),
}

PROGRAMMER = {
    "tool": (True, "a string", non_empty),
    "args": (False, "a list", strings),
    "target": (False, "a string", one_of(TARGETS)),
    "cable": (False, "a string", None),
    "cableIndex": (False, "a whole number", None),
    "usbSerial": (False, "a string", None),
    "frequencyHz": (False, "a whole number", positive),
    "flashOffset": (False, "a whole number", None),
    "verify": (False, "true or false", None),
}

USB = {
    "vid": (True, "a string", matching(HEX4, "USB id (0x + 4 hex digits)")),
    "pid": (True, "a string", matching(HEX4, "USB id (0x + 4 hex digits)")),
    "product": (False, "a string", None),
    "serial": (False, "a string", None),
}

BOARD = {
    "schema": (True, "a whole number", lambda v: None if v == 1 else "must be 1"),
    "id": (True, "a string", matching(ID, "board id (lowercase, e.g. sipeed.tang-primer-20k)")),
    "name": (True, "a string", non_empty),
    "vendor": (True, "a string", non_empty),
    "revision": (False, "a string", None),
    "target": (True, "an object", None),
    "clocks": (False, "a list", None),
    "signals": (False, "a list", None),
    "programmer": (False, "an object", None),
    "usb": (False, "a list", None),
    "idcode": (False, "a string", matching(HEX8, "JTAG IDCODE (0x + 8 hex digits)")),
    "documentation": (False, "a string", None),
    "sources": (False, "a list", strings),
    "note": (False, "a string", None),
}


def load(path):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except UnicodeDecodeError:
        report("error", path, "isn't UTF-8 text")
    except json.JSONDecodeError as error:
        report("error", path, f"isn't valid JSON: {error}")
    return None


def check_board(path, board):
    checker = Checker(path)
    checker.fields(board, BOARD, "board")
    if not isinstance(board, dict):
        return
    checker.fields(board.get("target", {}), TARGET, "target")
    names = {}
    pins = {}
    for key, table in (("clocks", CLOCK), ("signals", SIGNAL_FIELDS)):
        for index, item in enumerate(board.get(key) or []):
            checker.fields(item, table, f"{key}[{index}]")
            if isinstance(item, dict):
                name, pin = item.get("name"), str(item.get("pin", "")).strip()
                if name in names:
                    report("error", path, f"signal '{name}' is defined twice")
                names[name] = True
                if pin:
                    pins.setdefault(pin, []).append(name)
    for pin, users in pins.items():
        if len(users) > 1:
            report("warning", path, f"pin {pin} is used by {', '.join(map(str, users))}")
    if "programmer" in board:
        checker.fields(board["programmer"], PROGRAMMER, "programmer")
    else:
        report("warning", path, "no programmer")
    usb = board.get("usb") or []
    for index, match in enumerate(usb):
        checker.fields(match, USB, f"usb[{index}]")
    if not usb:
        report("warning", path, "no usb match: FPGALab can't detect the board")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "packs"
    boards = {}
    packs = sorted(name for name in os.listdir(root) if not name.startswith(".") and os.path.isdir(os.path.join(root, name)))
    if not packs:
        print(f"no packs in {root}")
    for pack in packs:
        folder = os.path.join(root, pack)
        print(f"pack {pack}")
        # Data only: FPGALab refuses the whole pack otherwise.
        for directory, subfolders, files in os.walk(folder):
            subfolders[:] = [s for s in subfolders if not s.startswith(".")]
            for name in files:
                path = os.path.join(directory, name)
                if name.startswith("."):
                    continue
                if os.path.islink(path):
                    report("error", path, "symbolic links aren't allowed")
                elif os.path.splitext(name)[1].lower() not in ALLOWED:
                    report("error", path, "file type not allowed in packs (data only: JSON, Verilog, constraints, Markdown, text)")
                elif os.path.getsize(path) > MAX_FILE:
                    report("error", path, "larger than 10 MB")
            for name in subfolders:
                if os.path.islink(os.path.join(directory, name)):
                    report("error", os.path.join(directory, name), "symbolic links aren't allowed")

        manifest_path = os.path.join(folder, "pack.json")
        if not os.path.exists(manifest_path):
            report("error", folder, "pack.json is missing")
        else:
            manifest = load(manifest_path)
            if manifest is not None:
                Checker(manifest_path).fields(manifest, MANIFEST, "pack")
                if isinstance(manifest, dict) and manifest.get("id") != pack:
                    report("error", manifest_path, f"id '{manifest.get('id')}' must match the folder name '{pack}'")

        board_folder = os.path.join(folder, "boards")
        board_files = sorted(f for f in os.listdir(board_folder) if f.endswith(".fpgaboard")) if os.path.isdir(board_folder) else []
        if not board_files:
            report("error", folder, "no boards in boards/")
        for name in board_files:
            path = os.path.join(board_folder, name)
            board = load(path)
            if board is None:
                continue
            check_board(path, board)
            board_id = board.get("id") if isinstance(board, dict) else None
            if board_id and name != f"{board_id}.fpgaboard":
                report("error", path, f"the file must be named {board_id}.fpgaboard")
            if board_id in boards:
                report("error", path, f"board id '{board_id}' is already used in {boards[board_id]}")
            elif board_id:
                boards[board_id] = path
    print(f"{'✓' if errors == 0 else '✗'} {len(boards)} boards in {len(packs)} packs: {errors} errors, {warnings} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
