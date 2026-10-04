# Adding a board

The easiest way: define the board in FPGALab (File ▸ New Board…, or File ▸ Import Board from
Constraints File… with your board's `.pcf`/`.lpf`/`.cst`/`.ccf`), test it on the hardware, then copy
the `.fpgaboard` file from `~/Library/Application Support/FPGALab/Boards/` into a pack here.

1. **Pick the pack.** Boards of one maker go into one pack: `packs/<vendor>.<family>/`, e.g.
   `packs/sipeed.tang/`. A new pack needs a `pack.json`:

   ```json
   {
     "schema": 1,
     "id": "sipeed.tang",
     "name": "Sipeed Tang",
     "version": "1.0.0",
     "type": "boards",
     "maintainer": "Your name",
     "description": "One sentence about the boards.",
     "documentation": "https://…"
   }
   ```

2. **Add the board** as `boards/<board id>.fpgaboard`. The id is `<vendor>.<board>` in lowercase
   (`sipeed.tang-primer-20k`) and must be unique across all packs and FPGALab's built-in boards.
   Name signals the way templates expect them: `clk`; `led[0]`, `led[1]` …; `btn[0]` …;
   `uart_tx`, `uart_rx`. Mark active-low LEDs and buttons (`"activeLow": true`), give the clock
   its frequency, and list the USB ids (`usb`) so FPGALab can detect the board — with the product
   string if the board's USB bridge reports one of its own.

3. **Cite your sources** in the board's `sources` (schematic, vendor constraint files, LiteX-boards,
   apicula examples …) and say in `note` what you checked and how. Use facts (pin numbers) from
   sources whose licence doesn't allow copying, not their files.

4. **Raise the pack's version** in `pack.json` for every change to a published pack. A published
   version is never changed: `fpgaboards site` refuses to overwrite it.

5. **Check it** with `python3 scripts/check_packs.py`, then open a pull request. CI runs the same
   check. Before publishing, the maintainer also checks the pack with FPGALab: the part, every
   template that fits the board (pins and a full build) and the installed archive.

What can't be checked automatically — whether the LEDs really are on those pins — is checked by
whoever has the board. Say in the pull request whether you programmed it.

## Publishing (maintainer)

Done from the FPGALab repo on the Mac that holds the index key, after merging:
`bash tools/publish-boards.sh ../fpgaboards` checks every pack with FPGALab, builds every board ×
template, writes the site into the `gh-pages` worktree (`../fpgaboards-site`), checks that it
installs, signs the index and commits. Pushing `gh-pages` is the last, separate step.

GitHub Pages serves the `gh-pages` branch (Settings ▸ Pages ▸ Deploy from a branch ▸ `gh-pages`,
`/ (root)`). FPGALab picks the new index up within a day, or at once with Refresh in
Settings ▸ Packages.
