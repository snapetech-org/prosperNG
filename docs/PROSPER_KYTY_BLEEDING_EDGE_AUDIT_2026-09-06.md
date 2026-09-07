# Prosper / KytyPS5 bleeding-edge audit

**Snapshot:** September 6, 2026

This is the anti-duplication gate for our Prosper work. Before changing Prosper behavior, we check
the current Prosper tree, its open and recently merged work, and the relevant KytyPS5 main/PR/issue
history. A KytyPS5 idea is evidence about a problem shape, not an implementation to copy: Prosper's
charter requires re-deriving behavior in Prosper's own architecture and tests.

## Decision

Prosper is the primary development target. KytyPS5 is an independent implementation and compatibility
oracle. Demon's Souls is the first local target; Ghost of Yōtei remains deferred until its download is
complete and verified.

The default test device is the **RX 7900 XT / RADV NAVI31**. Use the process-local Mesa selector below
for ordinary builds, Vulkan tests, game launches, and captures:

```bash
MESA_VK_DEVICE_SELECT=1002:744c!
```

The RX 9070 XT is reserved for explicit comparison runs. This keeps an experimental Vulkan process
off the desktop GPU by default. The machine-local policy is recorded in `LOCAL.md`, which is ignored
by git and exists in the ProsperNG checkout and the upstream reference worktree.

## Pinned snapshots

| Project | Checkout | Snapshot fact |
| --- | --- | --- |
| Prosper | `88aba88c1c3f9d667ec9e665551b5e32cb29a80a` | `Restore Sonic audio, retain render targets on GPU, and adopt Vulkan 1.4 (#3418)`; this is also the remote `main` head observed for this audit. |
| KytyPS5 | `74a78f37d08fabae0a37e621ef209786796c37fe` | current remote `main`; `renderer: grow repeatedly joined buffer ranges (perf)`. |
| KytyPS5 Demon's Souls branch | `7c21b713d2f706f6d761fd0cd5ec53dbce6dd399` | head of open PR [#477](https://github.com/KytyPS5/KytyPS5/pull/477); it conflicts with current main and is not a mergeable base. |

GitHub state is time-sensitive. The matrix below is a dated research record, not a promise that a
remote branch or issue will remain in the same state.

## Fork target and branch audit

The active writable target is the user fork [snapetech/ProsperNG](https://github.com/snapetech/ProsperNG).
At this snapshot its `main` is the same commit as upstream `main`. The original
[mattias800/prosper](https://github.com/mattias800/prosper) checkout remains an upstream reference;
its branch tips were fetched into ProsperNG under `refs/remotes/upstream/*` and were not merged.

Every branch advertised by upstream was compared with `upstream/main`. The `behind/ahead` column is
`git rev-list --left-right --count upstream/main...branch`. “Squash-merged” means the branch tip is
not an ancestor of main, but its associated PR is merged; that is normal history, not missing work.

| Upstream branch | Behind / ahead | Association or state | Audit disposition |
| --- | ---: | --- | --- |
| `fix-gta5-pad-route` | 55 / 1 | PR [#3302](https://github.com/mattias800/prosper/pull/3302), merged | Squash-merged; no outstanding branch work. |
| `fix/3142-review-notes-tail` | 77 / 2 | PR [#3252](https://github.com/mattias800/prosper/pull/3252), merged | Review/instrumentation notes; squash-merged, retain as project memory. |
| `fix/htile-depth-dual-title` | 62 / 1 | PR [#3281](https://github.com/mattias800/prosper/pull/3281), merged | Squash-merged; do not re-harvest. |
| `fix/issue-2926-ampr-gather` | 73 / 3 | PR [#3262](https://github.com/mattias800/prosper/pull/3262), merged | APR reachability/hygiene; squash-merged, unrelated to the current DS fault. |
| `fix/issue-2944-host-read-barrier` | 81 / 1 | PR [#3250](https://github.com/mattias800/prosper/pull/3250), merged | Squash-merged readback availability fix; no current DS evidence. |
| `fix/issue-2953-texture-cache-race` | 84 / 2 | PR [#3241](https://github.com/mattias800/prosper/pull/3241), merged | Squash-merged cache-domain fix; no current DS evidence. |
| `fix/issue-2955-trampoline-floats` | 81 / 5 | PR [#3242](https://github.com/mattias800/prosper/pull/3242), merged | Squash-merged Windows ABI work; irrelevant to the integer/pointer Fiber calls now observed. |
| `fix/issue-3065-resource-costs` | 8 / 1 | PR [#3399](https://github.com/mattias800/prosper/pull/3399), open | Open host VMA performance work; do not mix into a DS compatibility patch. |
| `fix/issue-3407-renderer-owned-conversion-cache` | 1 / 6 | No associated PR | **Unmerged near-head WIP**: renderer conversion cache, typed-target experiments, and readback-shape diagnostics. Inspect for relevant evidence, but do not merge wholesale. |
| `perf-compute-cache-sampled-textures` | 54 / 1 | PR [#3305](https://github.com/mattias800/prosper/pull/3305), merged | Squash-merged; no outstanding branch work. |
| `perf/compute-graphics-import-float16` | 60 / 2 | PR [#3286](https://github.com/mattias800/prosper/pull/3286), merged | Squash-merged aliasing work; no current DS evidence. |
| `perf/compute-untouched-storage-skip` | 60 / 1 | PR [#3289](https://github.com/mattias800/prosper/pull/3289), merged | Squash-merged; do not re-harvest. |
| `perf/render-memoize-mid-submit-redecode` | 60 / 2 | PR [#3287](https://github.com/mattias800/prosper/pull/3287), merged | Squash-merged performance work; no current DS evidence. |
| `perf/tile-surface-vectorize-sw64kb` | 60 / 3 | PR [#3288](https://github.com/mattias800/prosper/pull/3288), merged | Squash-merged; do not re-harvest. |
| `work/3378-3419-3407` | 0 / 3 | No associated PR | **Unmerged near-head WIP**: driver compilation-cache reuse, dynamic render state, and RGBA8→typed-UINT target copies. Treat as a separate comparison point, not a base for DS HLE work. |

This branch audit is why ProsperNG starts from upstream `main` plus our own small documentation and
triage changes, rather than from an arbitrary “work” branch. A future implementation can compare its
commit against these refs without silently losing or duplicating unmerged experiments.

## Local target and baseline

The home rip was extracted from:

```text
~/Downloads/Demon's Souls v01.005.000.rar
```

The verified package is `~/Downloads/PPSA01342-app`:

```text
title:          Demon's Souls
title ID:       PPSA01342
content version:01.005.000
eboot:          present; 46,574,897 bytes
```

The dump is user-supplied and was not added to either repository. Ghost of Yōtei was not scanned or
modified while its multipart download was incomplete.

Prosper was configured with Vulkan and the Demon's Souls dump, built successfully, and registered
**368 CTest tests; all 368 passed**. The three Messenger-specific cases were intentionally skipped
for this dump, and the PSN plugin wiring arm was skipped because this package does not contain that
Messenger plugin. Those are test-selection facts, not failures.

The first RX 7900 XT game run used the normal screenshot harness with structured fault diagnostics.
It exited with code 90 before producing a usable screenshot. The repeatable fault is:

```text
SIGSEGV, address 0x8f
guest RIP 0x410820f48 (eboot + 0x820f48)
r15 = 0xffffffffffffffff
instruction: mov rsi, QWORD PTR [r15 + 0x90]
```

The guest reaches initialization and starts a large set of BPE worker fibers. The Fiber trace shows
real initialize/run/yield activity, so the old “Prosper has no libSceFiber” diagnosis from historical
Astro Bot issue [#825](https://github.com/mattias800/prosper/issues/825) is already superseded by the
merged implementation from [#876](https://github.com/mattias800/prosper/pull/876).

The dump imports nine `libSceFiber` NIDs. Current Prosper registers six of them:

| Imported NID | Current Prosper status |
| --- | --- |
| `hVYD7Ou2pCQ` | registered: Fiber initialization |
| `JeNX5F-NzQU` | registered: Fiber finalization |
| `a0LLrZWac0M` | registered: Fiber run |
| `PFT2S-tJ7Uk` | registered: Fiber switch |
| `B0ZX2hx9DMw` | registered: return to thread |
| `p+zLIOg27zU` | registered: get current Fiber |
| `asjUJJ+aa8s` | **unregistered**; Fiber option-parameter initialization |
| `uq2Y5BFz0PE` | **unregistered**; Fiber information query |
| `JzyT91ucGDc` | **unregistered**; Fiber rename |

The three unregistered calls occur before the repeated worker-fiber activity. They are the first
bounded HLE investigation, not yet a proven explanation for the later queue-item sentinel
(`r15 == -1`) fault. The next change must establish what each caller expects in its output structure
and return value before adding a handler.

Run evidence is kept outside git under `<ARTIFACT_ROOT>`, including the RX 7900 manifest and the
fiber-instrumented `run.log`. The flattened ELF used for address analysis is an analysis artifact,
not a modified game dump.

## Research coverage

### KytyPS5

We checked current `main`, the open title-relevant PRs, the open Demon's Souls compatibility report,
the aggregate missing-opcode issue, and the relevant comments. The most important result is [Kyty
PR #477](https://github.com/KytyPS5/KytyPS5/pull/477): it reports Demon's Souls reaching gameplay,
but it changes 97 files, is based on an older tree, is currently conflicting, and the maintainer said
the useful fixes would be cherry-picked rather than merged as a branch. It is a list of hypotheses to
decompose, not a patch to transplant.

The current Kyty Demon's Souls report [#316](https://github.com/KytyPS5/kytyps5.github.io/issues/316)
records a main-menu run that later fails on incompatible indirect-image-table candidates. That is a
useful cross-project problem shape, but Prosper's resource materialization and descriptor model have
different names, invariants, and tests.

### Prosper

Prosper has **no GitHub Discussions enabled** as of this snapshot. The exact API search returned no
Demon's Souls (`PPSA01342`) or Yōtei (`PPSA26344`) tracker. The only two open PRs are:

* [#3399](https://github.com/mattias800/prosper/pull/3399), a Linux writable-VMA query optimization;
  it is host-performance work, not a guest/HLE/GPU compatibility fix.
* [#3316](https://github.com/mattias800/prosper/pull/3316), an `sceNetPoolCreate` error-code fix;
  it is unrelated to the current title and graphics path.

Prosper issue [#3033](https://github.com/mattias800/prosper/issues/3033) is the project’s best
anti-duplication precedent. It recovered useful pieces from old unmerged PR #2984, explicitly listed
what current master had already superseded, and recorded measured designs that were rejected. We will
use that same recovered/superseded/rejected classification rather than re-opening a large historical
branch.

## Cross-project matrix

“Already covered” means the current Prosper tree has a comparable implementation or proof path; it
does not mean the exact Demon's Souls workload is solved. “Candidate” means the feature may be worth
implementing only after the dump produces matching evidence.

| Area | KytyPS5 bleeding-edge signal | Prosper at pinned main | Demon's Souls relevance | Disposition |
| --- | --- | --- | --- | --- |
| Indirect image/resource candidates | [#477](https://github.com/KytyPS5/KytyPS5/pull/477) adds direct one-level indirect-image materialization and candidate harmonization; [#316](https://github.com/KytyPS5/kytyps5.github.io/issues/316) names an incompatible-candidate failure. | Prosper has `ShaderResourceTable`, runtime resource materialization, scalar and indirect-pointer paths, class-filtered lookups, and focused descriptor/resource tests. | **Possible later blocker**, but no Prosper DS shader has yet reached a resource-recompiler failure; the current guest fault is earlier. | Do not port the branch. Map the DS shader/call path in Prosper, then add a minimal failing fixture if the same invariant fails. |
| Fiber HLE | Kyty exposes a broader Fiber export set in `libKernel.cpp`; Prosper’s historical Astro implementation came from #825/#876. | Core Fiber context switching and run/yield tests are present, but three DS-imported exports are not registered. | **Current first HLE lead.** The trace proves core Fiber activity but leaves the three missing calls load-bearing until their callers are inspected. | Re-derive the three ABI contracts, add focused tests, then rerun on RX 7900 XT. Do not copy Kyty code. |
| NGS2 audio | #477 includes broad NGS2 lifecycle/waveform work. | Prosper already has a substantial NGS2 lifecycle, silent mixer, callback, trace, and streaming-test path. | No audio evidence exists because the title faults during worker startup. | No port. Revisit only after the run reaches audio initialization. |
| Float image atomics | [#490](https://github.com/KytyPS5/KytyPS5/pull/490) redoes closed [#338](https://github.com/KytyPS5/KytyPS5/pull/338) for MIMG `0x1e/0x1f`, specifically for Yōtei. | Prosper has integer image-atomic staging/classification and float CAS lowering for other resource classes; no exact `IMAGE_ATOMIC_FMIN/FMAX` path was found in current source/tests. | No DS evidence; this is a Yōtei candidate. | Do not implement before Yōtei is verified and the exact shader is captured. Re-derive against RDNA2/SPIR-V and Prosper’s resource classes. |
| DPP8 | Dirty historical [#340](https://github.com/KytyPS5/KytyPS5/pull/340) combined DPP8 with Yōtei float atomics; its DPP8 half is not the current #490 patch. | Prosper decodes DPP8 as a two-dword modifier but does not provide complete DPP8 semantics in the emitter. | No DS evidence. | Keep as a future candidate only when a real dump and shader identify it. |
| WQM / wave ballots | Open Kyty [#468](https://github.com/KytyPS5/KytyPS5/pull/468) and draft [#470](https://github.com/KytyPS5/KytyPS5/pull/470) target Astro wave32/wave-wide control behavior. | No exact `S_WQM_B32` path was found in the current Prosper tree; existing control-flow and ballot coverage is separate. | No DS evidence. | Do not let Astro-specific PRs steer DS work; create a fixture only from a matching DS shader. |
| BVH image instruction | [#493](https://github.com/KytyPS5/KytyPS5/pull/493) adds decode plus an opt-in always-miss `--stub-bvh`, explicitly not real ray tracing. | Prosper already has a bounded `IMAGE_BVH_INTERSECT_RAY` lowering and real software-BVH tests. | No DS evidence for the MIMG `0xe6/0xe7` path. | Do not port the always-miss stub; a silent false result would invalidate rendering. |
| Sampled-depth / BC7 compare | [#491](https://github.com/KytyPS5/KytyPS5/pull/491) handles a Kyty depth-compare failure on a non-depth BC7_SRGB resource. | Prosper has generic depth-compare/resource paths and validation tests, but no DS title proof for this exact combination. | Unproven. | Keep as a comparison hypothesis, not a change request. |
| Descriptor/resource Phi and CFG | Kyty [#353](https://github.com/KytyPS5/KytyPS5/pull/353) and the aggregate [#281](https://github.com/KytyPS5/KytyPS5/issues/281) track unreachable descriptor inputs and resource-tracking failures. | Prosper validates resource snapshots and has CFG/resource tests; open Prosper [#2406](https://github.com/mattias800/prosper/issues/2406) records a different invalid-`OpPhi` risk. | This is the likely later GPU seam if the DS run gets past HLE, not the current proven fault. | Compare invariants and make a minimal Prosper regression test; do not copy a Kyty change or assume the same Phi bug. |
| Depth, write masks, vertex inputs, tiler | The remaining #477 body contains these broad renderer changes. | Prosper’s current renderer already has decoded per-target write masks, dynamic vertex-input assembly, depth/stencil fallbacks, generic tiling, and dedicated tests. | No DS-specific failure has reached any of these paths yet. | Treat the broad #477 changes as mostly superseded/analogous. Reopen one only with a DS capture and a failing Prosper test. |

## Prosper issue watchlist before GPU changes

These are not current Demon's Souls blockers. They are the existing Prosper records to read before
working in a related subsystem:

* [#2275](https://github.com/mattias800/prosper/issues/2275): image-atomic classification; part of the
  named classifier work landed, but end-to-end per-use proof remains the standard.
* [#2406](https://github.com/mattias800/prosper/issues/2406): invalid fragment `OpPhi` dominance.
* [#2545](https://github.com/mattias800/prosper/issues/2545): DS opcode fallback that must not silently
  become an LDS read.
* [#2818](https://github.com/mattias800/prosper/issues/2818): dynamic `IMAGE_LOAD_MIP` paths.
* [#2922](https://github.com/mattias800/prosper/issues/2922): generic NGG vertex `s_barrier`.
* [#3137](https://github.com/mattias800/prosper/issues/3137): a useful example where both proposed
  explanations were falsified and SRSRC provenance became the live question.

The open issue list is project memory, not a queue to blindly implement. Each proposed fix still needs
a current reproducer, a positive control, a negative control where appropriate, and a regression test.

## Working rules from this audit

1. Pin the Prosper and comparison commits in every run record.
2. Search current source, tests, open PRs, issue comments, and the relevant `## Ruled out` notes before
   opening a new hypothesis.
3. Split historical PRs into semantic claims. Mark each claim **already covered**, **superseded**,
   **candidate**, **title-specific**, or **rejected**.
4. Use Kyty, LLVM, AMD ISA, Vulkan, and live captures as evidence sources. Re-derive the behavior in
   Prosper; do not copy source, tests, prose, game files, or assets.
5. Test first: a proposed behavior change starts with a minimal regression test that fails for the
   demonstrated reason, followed by focused tests, all CTest tests, and a pinned game rerun.
6. Keep ordinary tests and experimental game runs on the RX 7900 XT. Use the RX 9070 XT only for an
   explicitly named A/B comparison, and treat a device difference as a clue rather than proof.
7. Record falsified hypotheses so later agents do not spend compute rediscovering them.

Prosper’s GitHub repository currently reports no declared license. This audit therefore makes no
redistribution or fork-licensing decision. It uses public PR/issue descriptions as research pointers
and has copied no implementation code, game data, keys, or assets. Any upstream contribution or
distribution question remains a separate human decision.

## Next gate

The first implementation task is now narrow enough to be testable:

1. Use `self_dump --import-slots` and `tools/re/xref.py` on the flattened Demon's Souls eboot to map
   the three missing Fiber callsites and inspect the caller’s output reads.
2. Define the smallest honest Prosper-side contracts for option initialization, information query,
   and rename; add unit tests for valid, null, alignment, and invalid-fiber cases.
3. Rebuild and run all 368 tests on the RX 7900 XT.
4. Rerun Demon's Souls with the same artifact naming and compare the fault/progression, without
   suppressing an unsupported or unimplemented operation.
5. Only after the guest reaches the next stable boundary, open a GPU/resource task from the new log
   and re-check this matrix against current remote history.
