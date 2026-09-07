# LLM-assisted compatibility development: Prosper primary, KytyPS5 oracle

**Snapshot:** September 6, 2026

This began as a working plan for using KytyPS5 as a focused emulator-development target. The active
plan has since pivoted to Prosper, whose agent-oriented workflow and native Linux/Vulkan path match our
objective better. KytyPS5 remains an independent implementation and compatibility oracle. This file
keeps the Kyty research useful while separating verified facts from hypotheses and defining the evidence
required before changing either emulator.

## Objective and working hypothesis

Our objective is commercial PS5 game compatibility: getting real, legally obtained game files farther
through boot, rendering, audio, input, and gameplay. The current working hypothesis is that Prosper is
the best primary target for our agent-assisted work, with KytyPS5 providing an independent cross-check.
This is not an official ranking and should be revisited as projects change.

| Project | Snapshot assessment | Intended use |
| --- | --- | --- |
| [Prosper](https://github.com/mattias800/prosper) | Native PS5→PC compatibility layer with an agentic development charter, structured traces, Vulkan/SPIR-V execution tests, and many title-specific research lanes. | **Primary target** for compatibility work. |
| [KytyPS5](https://github.com/KytyPS5/KytyPS5) | Early-stage emulator that boots 2D games and a selection of 3D games; its active PR and issue history exposes useful independent hypotheses. | **Independent implementation/oracle** and bleeding-edge research source. |
| [SharpEmu](https://github.com/sharpemu/sharpemu) | Experimental C# PS5 emulator with real-game loading, native CPU execution, partial kernel support, initial shader/resource submits, AGC, and video-output stages. | Additional comparison point. |
| [RPCSX](https://github.com/RPCSX/rpcsx) | Experimental PS4/PS5 emulator with a large system-level codebase and VSH/kernel-oriented reference value. | Architecture and OS research reference. |

KytyPS5 is explicitly still in early development, and its own README identifies compatibility and boot
reliability as the current focus. The Kyty checkout used for the current audit is pinned at
`74a78f37d08fabae0a37e621ef209786796c37fe`. The Prosper audit and the cross-project matrix live in
`docs/PROSPER_KYTY_BLEEDING_EDGE_AUDIT_2026-09-06.md` in the Prosper worktree.

## Cross-project bleeding-edge gate

Before starting a Prosper or Kyty behavior change, inspect both projects' current main branches and
the relevant open, merged, closed, and dirty PR/issue history. Decompose a historical PR into individual
claims and classify each one as already covered, superseded, candidate, title-specific, or rejected.
Kyty PRs and issues are research signals, not code to transplant: Prosper's charter requires a clean
re-derivation in its own architecture and tests. The same rule applies in the other direction.

The first local target is Demon's Souls (`PPSA01342`) from `~/Downloads`; Ghost of Yōtei is deferred
until its multipart download is complete and verified. Ordinary tests and game attempts use the RX
7900 XT through `MESA_VK_DEVICE_SELECT=1002:744c!`, keeping the RX 9070 XT available for explicit A/B
comparisons. A device-dependent result is a clue, not proof of an emulator defect.

## What the current evidence says

The important distinction is “early real emulator” versus “generally playable.” KytyPS5 can reach meaningful stages in commercial games, but a game reaching a menu or gameplay does not imply broad compatibility, performance, or correctness.

The following are leads from the initial research pass. Issue state and behavior are time-sensitive, so each one must be reproduced against a pinned KytyPS5 commit before it becomes an engineering target:

- [Demon's Souls compatibility report #136](https://github.com/KytyPS5/kytyps5.github.io/issues/136) currently records a main-menu result and an `indirect image table` / incompatible-candidates shader failure.
- [Astro Bot issue #204](https://github.com/KytyPS5/KytyPS5/issues/204) records an unsupported sampled-depth-target failure in the Vulkan descriptor path.
- [Trails in the Sky: First Chapter issue #314](https://github.com/KytyPS5/KytyPS5/issues/314) records a main-menu result, no audio, and a shader resource-tracking failure involving a control-dependent phi.
- [PAC-MAN WORLD 2 Re-PAC issue #198](https://github.com/KytyPS5/KytyPS5/issues/198) was the source of a useful historical lead in the initial notes—bounded DMA, shader instruction, trap, and encoding fixes—but the issue is currently withdrawn by its author. Treat the exact FPS/shader-count claim and fix list as unverified until a complete log or commit reproduces it.

The project’s source and tests expose the same useful seams: `src/graphics/shader/recompiler`, `src/graphics/guest_gpu`, `src/graphics/host_gpu`, and focused executables under `tests`. The PS5 graphics model is treated as AMD RDNA 2; the [AMD RDNA 2 ISA reference guide (70648)](https://docs.amd.com/v/u/en-US/rdna2-shader-instruction-set-architecture) is the primary instruction reference, with [LLVM’s AMDGPU target](https://github.com/llvm/llvm-project/tree/main/llvm/lib/Target/AMDGPU) as an implementation cross-check.

## The contribution model

We should give an LLM small, falsifiable emulator questions instead of asking it to “implement PS5 GPU emulation.” A useful task packet contains:

- the complete unmodified log and the exact KytyPS5 commit;
- the offending shader dump, command-buffer dump, or HLE symbol;
- the smallest relevant source subtree and existing tests;
- the applicable RDNA 2, Vulkan, SPIR-V, or ABI reference;
- a request to explain the current path before proposing behavior; and
- an objective validation command and a game-level advancement criterion.

The required sequence is:

```text
game run/logs
      -> structured failure signature
      -> affected-game and subsystem cluster
      -> minimal reproducer
      -> regression test
      -> smallest semantically justified change
      -> build + focused tests + full regression suite
      -> affected-game rerun and regression check
      -> human review and contribution disclosure
```

The human remains responsible for the semantics. This matters in low-level work: [PR #419](https://github.com/KytyPS5/KytyPS5/pull/419) demonstrates both the value of automated bisection and the danger of stopping at a plausible game-derived fix when RDNA2/LLVM evidence points the other way. [PR #417](https://github.com/KytyPS5/KytyPS5/pull/417) is a positive example: it adds `--gpu <index>`, reports 35/35 CTest checks, and discloses AI assistance with human review and testing.

KytyPS5’s current contribution policy permits AI for research, reverse engineering, and development assistance, but requires contributors to understand, review, test, and disclose AI-assisted work. Any upstream communication must be written by the human contributor.

## Reference project: `kyty-triage`

The existing implementation is intentionally behavior-neutral. [`tools/kyty_triage`](../tools/kyty_triage)
reads local KytyPS5 logs and produces a Markdown or JSON report. It remains useful for independent
Kyty evidence and cross-project comparison, but Prosper's native structured logs and existing
orchestration are the primary workflow. The tool does not launch games, inspect game files, modify
emulator behavior, or upload data.

### Initial data contract

Each input log becomes one run record with these fields when available:

```text
source_file
game, game_id, status
build, os, cpu, gpu, ram_vram
last_successful_stage
exception, assertion, source_location
shader_hashes, shader_stages
primary_category, primary_signature
evidence (line, severity, category, message, signature)
```

KytyPS5 currently prints build, host CPU/OS, selected Vulkan device, game-loading paths, shader phase/hash/stage markers, fatal reports, and subsystem errors. A per-log JSON sidecar or a metadata manifest fills gaps such as the human-readable game title, serial, compatibility status, and RAM/VRAM.

The first taxonomy is deliberately small:

| Category | First source/test hints | Missing coverage suggested by the tool |
| --- | --- | --- |
| Shader/resource tracking | `shader.cpp`, `ResourceTracking.cpp`, `ResourceMaterialization.cpp`, `SrtWalker.cpp` | Control-flow merges of resource descriptors, including control-dependent phi values. |
| Unsupported shader opcode | decoder, translator, and IR opcode directories | One regression per documented opcode, operand width, and VCC/SCC side effect. |
| Vulkan image/descriptor | descriptor, image, and Vulkan-window paths | Sampled/storage/depth/comparison/multisample combinations under validation. |
| Guest GPU / command processor | AGC, PM4, DMA, and graphics-run paths | DMA sizes, control packets, and partial/unknown PM4 packets. |
| Missing HLE export | runtime linker and library registration paths | Per-export ABI, argument, and return-value smoke tests. |
| Video / Audio / Filesystem | existing decoder, audio, kernel, and loader paths | Lifecycle and error-path fixtures appropriate to the subsystem. |

The report counts one input log as one run. “Games affected” is the number of distinct inferred or supplied game names; it is not a causal estimate. The highest-leverage signature is a prioritization candidate, not proof that fixing it will advance every listed game.

### Local usage

```bash
python3 tools/kyty_triage/kyty_triage.py path/to/logs
python3 tools/kyty_triage/kyty_triage.py path/to/logs --format json --output triage.json
python3 tools/kyty_triage/test_kyty_triage.py
```

Keep real logs, shader dumps, game files, and generated reports outside the repository unless they have been deliberately sanitized. The parser is local-only, but logs can contain usernames, filesystem paths, serials, and other identifying details.

## Planned increments

1. **Log triage (current):** parse local logs, normalize signatures, count runs/games, and map clusters to source/test hints.
2. **Report ingestion:** ingest sanitized compatibility-report exports and issue-template fields while preserving the original source URL and tested build.
3. **Reproducer packets:** attach shader/command dumps, source locations, focused test names, and a machine-readable task bundle for bounded model work.
4. **Regression automation:** run focused tests, the complete CTest suite, and pinned game smoke runs; add build bisection where a reproducible executable/game oracle exists.
5. **Default GPU and opt-in matrix:** run ordinary Prosper/Kyty tests on the RX 7900 XT selected with `MESA_VK_DEVICE_SELECT=1002:744c!`. Run the same commit, game, cache state, settings, and test workload on the RX 9070 XT only as an explicitly named comparison. Compare validation output, render/frame progression, shader failures, and visual evidence. This can expose synchronization, descriptor, barrier, or shader-UB problems, but a cross-driver difference is not by itself proof of an emulator bug.
6. **First behavior change:** choose one cluster only after the cross-project audit and current data show leverage; require a minimal regression test and documentation-backed semantics before touching shader, HLE, AGC, Vulkan, audio, or video behavior.

## Verification gates

Every proposed emulator change should answer all of these:

- Does it compile with the affected platform/toolchain?
- Does the focused regression test fail before the change and pass after it?
- Does the full registered CTest suite pass?
- Does the affected game advance farther or render/audio behavior improve on a pinned build?
- Did any previously working game or test regress?
- Is the behavior supported by RDNA2/Vulkan/ABI evidence rather than only one game?
- Is the AI assistance and human review disclosed if this becomes an upstream contribution?

## References

- [KytyPS5 repository and developer information](https://github.com/KytyPS5/KytyPS5)
- [KytyPS5 releases](https://github.com/KytyPS5/KytyPS5/releases)
- [KytyPS5 compatibility list](https://kytyps5.github.io/)
- [SharpEmu repository](https://github.com/sharpemu/sharpemu)
- [RPCSX repository](https://github.com/RPCSX/rpcsx)
- [AMD RDNA 2 ISA reference guide 70648](https://docs.amd.com/v/u/en-US/rdna2-shader-instruction-set-architecture)
- [LLVM AMDGPU target](https://github.com/llvm/llvm-project/tree/main/llvm/lib/Target/AMDGPU)
- [KytyPS5 GPU selection PR #417](https://github.com/KytyPS5/KytyPS5/pull/417)
- [KytyPS5 shader regression/bisection PR #419](https://github.com/KytyPS5/KytyPS5/pull/419)
