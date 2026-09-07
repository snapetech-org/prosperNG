# kyty-triage

`kyty-triage` is the first behavior-neutral slice of the local KytyPS5 development harness. It reads a directory of local KytyPS5 logs and emits a Markdown or JSON report containing:

- inferred game, build, host OS, CPU, GPU, and shader metadata;
- the last successful emulator phase observed before the primary blocker;
- normalized blocker categories and signatures;
- affected-run/game counts; and
- source/test hints for the highest-leverage signature.

It is intentionally dependency-free and does not launch the emulator, inspect game files, or upload logs.

## Usage

```bash
python3 tools/kyty_triage/kyty_triage.py path/to/logs
python3 tools/kyty_triage/kyty_triage.py path/to/logs --format json --output triage.json
```

The scanner reads `.log`, `.txt`, `.out`, and `.err` files, plus files without an extension. A per-log JSON sidecar is read automatically, for example `Astro.log.json` or `Astro.json`:

```json
{
  "game": "Astro Bot",
  "game_id": "PPSA00000",
  "status": "Main menu",
  "ram_vram": "32 GB / 16 GB"
}
```

For a larger collection, `--metadata` accepts a JSON object keyed by log filename or relative path. A `defaults` object can provide shared values:

```json
{
  "defaults": {"os": "Windows 11"},
  "Astro.log": {"game": "Astro Bot", "gpu": "AMD Radeon RX 7900 XT"}
}
```

Run the parser tests with:

```bash
python3 tools/kyty_triage/test_kyty_triage.py
```

The report is a prioritization aid, not a compatibility verdict. Treat every signature as a hypothesis to reproduce with the complete log, shader/dump fixture, focused regression test, and full KytyPS5 test suite.
