# fpgaboards

Board packs for FPGALab, the native macOS IDE for open-source FPGA flows. A pack describes boards
— part, clocks, named pins, programmer, USB ids — so FPGALab can detect a board, create a project
for it from its templates, build it and program it.

FPGALab reads the published index at `https://richardklingler.github.io/fpgaboards/index.json`
(Settings ▸ Packages). The index is signed; FPGALab checks the signature and every download's
checksum, and packs contain data only (JSON, Verilog, constraints, Markdown) — never scripts.

## Layout

```
packs/<pack id>/
    pack.json                     id, name, version, description, maintainer, documentation
    boards/<board id>.fpgaboard   one board definition per file
    templates/<id>/…              optional own project templates
scripts/check_packs.py            the format check (Python 3, nothing to install)
```

## Checking a pack

```sh
python3 scripts/check_packs.py
```

checks every pack's files: valid JSON, the fields and their types, signal names, USB ids, ids that
match their file names, no duplicate boards, data-only files. Pull requests run the same check.

Before a pack is published, the maintainer checks it with FPGALab itself: every board against
FPGALab's device database, every template that fits each board must place all its pins and build
with the toolchain FPGALab tests against, and the published archive must install. FPGALab's board
editor (Window ▸ Boards) shows a board's problems while you define it.

See [CONTRIBUTING.md](CONTRIBUTING.md) to add a board.

## Licence

[CC0 1.0 Universal](LICENSE): the packs are in the public domain. Contributions are accepted
under the same terms (see [CONTRIBUTING.md](CONTRIBUTING.md)).
