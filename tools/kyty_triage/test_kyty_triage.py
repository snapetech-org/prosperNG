#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from kyty_triage import build_report_data, parse_log, render_markdown  # noqa: E402


class KytyTriageTests(unittest.TestCase):
    def test_parses_ktyy_build_host_shader_and_vulkan_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "astro.log"
            log.write_text(
                "\n".join(
                    (
                        "Build",
                        "  version: Official build KytyPS5-2026-09-05-74a78f3",
                        "Host",
                        "  os:      Windows 11",
                        "  cpu:     AMD Ryzen 9 9950X3D",
                        "Loading: C:\\Games\\Astro Bot\\eboot.bin",
                        "Select device: AMD Radeon RX 7900 XT",
                        "ShaderRecompiler phase end: stage=CS hash=0x0000000012345678 decode instructions=42",
                        "--- Error ---",
                        "unsupported sampled depth target: resource=1 descriptor=1 in C:\\work\\src\\graphics\\host_gpu\\renderer\\pipeline\\descriptors.cpp:342",
                    )
                ),
                encoding="utf-8",
            )

            report = parse_log(log, root)

            self.assertEqual(report.game, "Astro Bot")
            self.assertEqual(report.build, "Official build KytyPS5-2026-09-05-74a78f3")
            self.assertEqual(report.os, "Windows 11")
            self.assertEqual(report.cpu, "AMD Ryzen 9 9950X3D")
            self.assertEqual(report.gpu, "AMD Radeon RX 7900 XT")
            self.assertEqual(report.shader_hashes, ["0x0000000012345678"])
            self.assertEqual(report.shader_stages, ["CS"])
            self.assertEqual(report.last_successful_stage, "shader CS decode")
            self.assertEqual(report.primary_category, "vulkan_descriptor")
            self.assertEqual(report.primary_signature, "unsupported sampled-depth target")
            self.assertEqual(report.source_location, "C:\\work\\src\\graphics\\host_gpu\\renderer\\pipeline\\descriptors.cpp:342")

    def test_resource_tracking_signature_wins_over_later_audio_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "trails.log"
            log.write_text(
                "\n".join(
                    (
                        "Game title: Trails in the Sky: First Chapter",
                        "game id: PPSA00000",
                        "Build",
                        "  version: Source build 74a78f3",
                        "Host",
                        "  os:      Linux",
                        "  cpu:     Test CPU",
                        "ShaderRecompiler phase end: stage=PS hash=0x34348712 IR TranslateProgram",
                        "ShaderRecompiler PS failed hash=0x34348712: shader resource tracking: hash=0x34348712 stage=pixel pc=0x1e4 GetBufferResource dword 0 contains a control-dependent phi",
                        "in /work/src/graphics/shader/shader.cpp:248",
                        "It runs almost perfect until the main menu, no audio at all.",
                    )
                ),
                encoding="utf-8",
            )

            report = parse_log(log, root)

            self.assertEqual(report.game_id, "PPSA00000")
            self.assertEqual(report.primary_category, "shader_resource_tracking")
            self.assertEqual(report.primary_signature, "control-dependent phi")
            self.assertEqual(report.last_successful_stage, "shader PS IR TranslateProgram")
            self.assertEqual(report.source_location, "/work/src/graphics/shader/shader.cpp:248")

    def test_one_line_failure_with_source_location_is_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "one-line.log"
            log.write_text(
                "ShaderRecompiler PS failed: shader resource tracking: control-dependent phi in /work/src/resource.cpp:77\n",
                encoding="utf-8",
            )

            report = parse_log(log, root)

            self.assertEqual(report.primary_category, "shader_resource_tracking")
            self.assertEqual(report.primary_signature, "control-dependent phi")
            self.assertEqual(report.source_location, "/work/src/resource.cpp:77")

    def test_metadata_sidecar_and_report_grouping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("run-a.log", "run-b.log"):
                (root / name).write_text(
                    "ShaderRecompiler PS failed: shader resource tracking: GetBufferResource contains a control-dependent phi\n",
                    encoding="utf-8",
                )
            (root / "run-a.json").write_text(
                json.dumps({"game": "Game A", "ram_vram": "32 GB / 16 GB", "status": "Main menu"}),
                encoding="utf-8",
            )
            (root / "run-b.json").write_text(json.dumps({"game": "Game B"}), encoding="utf-8")

            reports = [parse_log(path, root) for path in sorted(root.glob("*.log"))]
            data = build_report_data(reports, root, Path(__file__).resolve().parents[2])
            markdown = render_markdown(reports, root, Path(__file__).resolve().parents[2])

            self.assertEqual(data["runs_analyzed"], 2)
            self.assertEqual(data["highest_leverage_signature"]["signature"], "control-dependent phi")
            self.assertEqual(data["highest_leverage_signature"]["games_affected"], 2)
            self.assertIn("Game A", markdown)
            self.assertIn("control-dependent phi", markdown)
            self.assertRegex(
                markdown,
                r"`(?:prosper/)?tests/(?:ResourceTrackingTests\.cpp|gpu/resources/test_shader_resources\.cpp)`",
            )

    def test_classifies_opcode_guest_gpu_and_hle_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "opcode.log").write_text(
                "--- Fatal Error ---\nNot implemented (opcode V_CMP_GT_U64)\n",
                encoding="utf-8",
            )
            (root / "gpu.log").write_text(
                "unsupported DMA_DATA size=4\nunknown PM4 packet: data=0x1\n",
                encoding="utf-8",
            )
            (root / "hle.log").write_text(
                "Unresolved import stub called [0]: symbol=sceKernelFoo\n",
                encoding="utf-8",
            )
            (root / "diagnostic.log").write_text(
                "Vulkan: sampleRateShading is not supported\n",
                encoding="utf-8",
            )

            reports = [parse_log(path, root) for path in sorted(root.glob("*.log"))]
            by_name = {report.source_file: report for report in reports}

            self.assertEqual(by_name["opcode.log"].primary_category, "unsupported_shader_opcode")
            self.assertEqual(by_name["opcode.log"].assertion, "Not implemented (opcode V_CMP_GT_U64)")
            self.assertEqual(by_name["gpu.log"].primary_category, "guest_gpu_command_processor")
            self.assertEqual(by_name["gpu.log"].primary_signature, "PM4 command packet handling")
            self.assertEqual(by_name["hle.log"].primary_category, "missing_hle_export")
            self.assertEqual(by_name["hle.log"].primary_signature, "unresolved HLE export: sceKernelFoo")
            self.assertIsNone(by_name["diagnostic.log"].primary_category)

    def test_metadata_manifest_applies_defaults_and_run_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "run.log"
            log.write_text("No blocker here\n", encoding="utf-8")
            metadata = root / "metadata.json"
            metadata.write_text(
                json.dumps(
                    {
                        "defaults": {"os": "Linux", "gpu": "default GPU"},
                        "runs": {"run.log": {"game": "Metadata Game", "gpu": "override GPU"}},
                    }
                ),
                encoding="utf-8",
            )

            from kyty_triage import _load_metadata  # noqa: PLC0415

            report = parse_log(log, root, _load_metadata(metadata))

            self.assertEqual(report.game, "Metadata Game")
            self.assertEqual(report.os, "Linux")
            self.assertEqual(report.gpu, "override GPU")


if __name__ == "__main__":
    unittest.main()
