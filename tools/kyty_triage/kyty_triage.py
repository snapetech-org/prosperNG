#!/usr/bin/env python3
"""Turn KytyPS5 run logs into deterministic blocker summaries.

The parser is deliberately conservative.  It only reads local files, does not
launch games, and never sends logs anywhere.  A report is a prioritization aid,
not a compatibility verdict: every proposed fix still needs a reproducer,
tests, and an emulator run.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping


LOG_SUFFIXES = frozenset({".err", ".log", ".out", ".txt"})

CATEGORY_LABELS = {
    "shader_resource_tracking": "Shader/resource tracking",
    "unsupported_shader_opcode": "Unsupported shader opcode",
    "vulkan_descriptor": "Vulkan image/descriptor",
    "guest_gpu_command_processor": "Guest GPU / command processor",
    "missing_hle_export": "Missing HLE export",
    "video": "Video",
    "audio": "Audio",
    "filesystem": "Filesystem",
    "shader_recompiler": "Shader recompiler",
    "runtime_loader": "Runtime / loader",
    "other": "Other / needs investigation",
}

CATEGORY_CODE = {
    "shader_resource_tracking": (
        "src/graphics/shader/shader.cpp",
        "src/graphics/shader/recompiler/ir/passes/ResourceTracking.cpp",
        "src/graphics/shader/recompiler/ir/passes/ResourceMaterialization.cpp",
        "src/graphics/shader/recompiler/ir/passes/SrtWalker.cpp",
        "src/gpu/resources/shader_resources.cpp",
        "src/gpu/resources",
        "src/gpu/recompiler",
    ),
    "unsupported_shader_opcode": (
        "src/graphics/shader/recompiler/frontend/decode",
        "src/graphics/shader/recompiler/frontend/translate",
        "src/graphics/shader/recompiler/ir/opcodes",
        "src/gpu/recompiler",
        "src/gpu/agc",
    ),
    "vulkan_descriptor": (
        "src/graphics/host_gpu/renderer/pipeline/descriptors.cpp",
        "src/graphics/host_gpu/renderer/pipeline",
        "src/graphics/host_gpu/renderer/image",
        "src/graphics/presentation/window/vulkanWindow.cpp",
        "src/gpu/resources",
        "src/gpu/state",
        "frontends/shared",
    ),
    "guest_gpu_command_processor": (
        "src/graphics/guest_gpu/command_processor",
        "src/graphics/guest_gpu/graphicsRun.cpp",
        "src/graphics/guest_gpu/pm4.cpp",
        "src/gpu/pm4",
        "src/gpu/agc",
        "src/hle/graphics",
    ),
    "missing_hle_export": (
        "src/loader/runtimeLinker.cpp",
        "src/libs/libs.cpp",
        "src/libs",
        "src/hle/dispatch",
        "src/hle",
        "src/loader",
    ),
    "video": (
        "src/libs/videoDec2Decoder.cpp",
        "src/libs/libVideoDec2.cpp",
        "src/libs/avPlayer.cpp",
        "src/hle/video",
        "frontends/shared",
    ),
    "audio": (
        "src/libs/audio.cpp",
        "src/libs/libAudio.cpp",
        "src/libs/libAudio2.cpp",
        "src/hle/audio",
        "src/hle",
    ),
    "filesystem": (
        "src/kernel/fileSystem.cpp",
        "src/loader/systemContent.cpp",
        "src/loader/elf.cpp",
        "src/hle/fs",
        "src/loader",
    ),
    "shader_recompiler": (
        "src/graphics/shader/recompiler",
        "src/graphics/shader/shader.cpp",
        "src/gpu/recompiler",
        "src/gpu/agc",
    ),
    "runtime_loader": (
        "src/loader/runtimeLinker.cpp",
        "src/loader/elf.cpp",
        "src/kernel",
        "src/loader",
        "src/host/abi",
    ),
    "other": (),
}

CATEGORY_TESTS = {
    "shader_resource_tracking": (
        "tests/ResourceTrackingTests.cpp",
        "tests/ResourceMaterializationTests.cpp",
        "tests/ScalarProvenanceTests.cpp",
        "tests/gpu/resources/test_shader_resources.cpp",
        "tests/gpu/agc/test_build_shader_resources.cpp",
        "tests/gpu/recompiler/test_direct_descriptor_copy.cpp",
        "tests/gpu/recompiler/test_shader_property_scans.cpp",
    ),
    "unsupported_shader_opcode": (
        "tests/ShaderRecompilerComputeTests.cpp",
        "tests/shaderCfgTests.cpp",
        "tests/gpu/recompiler/test_recompiled_shaders.cpp",
        "tests/gpu/recompiler/test_shader_property_scans.cpp",
        "tests/gpu/test_agc_shader.cpp",
    ),
    "vulkan_descriptor": (
        "tests/ShaderRecompilerComputeTests.cpp",
        "tests/ResourceTrackingTests.cpp",
        "tests/gpu/resources/test_shader_resources.cpp",
        "tests/gpu/recompiler/test_image_descriptor_class_lookup.cpp",
        "tests/gpu/state/test_descriptor_array_render.cpp",
        "tests/gpu/test_descriptor_array_emit.cpp",
    ),
    "guest_gpu_command_processor": (
        "tests/ShaderRecompilerComputeTests.cpp",
        "tests/gpu/pm4/test_command_processor.cpp",
        "tests/gpu/pm4/test_pm4_decode.cpp",
        "tests/gpu/agc/test_agc_submit.cpp",
    ),
    "missing_hle_export": (
        "tests/KernelFileSystemTests.cpp",
        "tests/hle/test_hle_registered.cpp",
        "tests/hle/dispatch/test_nid.cpp",
        "tests/loader/test_support_modules.cpp",
    ),
    "video": (
        "tests/hle/video/test_videodec2_decode.cpp",
        "tests/hle/video/test_h264_sps.cpp",
    ),
    "audio": (
        "tests/AudioOut2PortTests.cpp",
        "tests/hle/audio/test_audio.cpp",
        "tests/hle/audio/test_audiodec.cpp",
    ),
    "filesystem": (
        "tests/KernelFileSystemTests.cpp",
        "tests/hle/test_file_binary.cpp",
        "tests/hle/test_savedata_dirname.cpp",
    ),
    "shader_recompiler": (
        "tests/ShaderRecompilerComputeTests.cpp",
        "tests/shaderCfgTests.cpp",
        "tests/gpu/recompiler/test_recompiled_shaders.cpp",
        "tests/gpu/recompiler/test_shader_property_scans.cpp",
    ),
    "runtime_loader": (
        "tests/KernelFileSystemTests.cpp",
        "tests/VirtualMemoryAllocationTests.cpp",
        "tests/loader/test_guest_tls_align.cpp",
        "tests/loader/test_support_modules.cpp",
    ),
    "other": (),
}

CATEGORY_MISSING_COVERAGE = {
    "shader_resource_tracking": "control-flow merges of resource descriptors, including control-dependent phi values",
    "unsupported_shader_opcode": "one regression per documented opcode, operand width, and VCC/SCC side effect",
    "vulkan_descriptor": "sampled, storage, depth, comparison, and multisample descriptor combinations under validation",
    "guest_gpu_command_processor": "DMA data sizes, DMA control packets, and unknown/partial PM4 packet handling",
    "missing_hle_export": "per-export ABI, arguments, and return-value smoke tests for the affected symbol",
    "video": "decoder initialization, access-unit rejection, flush, and frame-lifetime paths",
    "audio": "device-unavailable behavior, queue timing, and no-audio fallback paths",
    "filesystem": "missing or malformed metadata, mount lifecycle, and path/error handling",
    "shader_recompiler": "a minimized shader fixture that reaches the failing recompiler phase",
    "runtime_loader": "a minimized ELF/import/kernel fixture that reaches the failing loader path",
    "other": "a minimized reproducer for the captured failure before choosing an owner",
}

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
HEX_VALUE = re.compile(r"0x[0-9a-fA-F]+")
SOURCE_LOCATION = re.compile(r"\bin\s+(.+?):(\d+)\s*$")

FAILURE_WORDS = re.compile(
    r"\b(?:failed|failure|error|fatal|crash|exception|assert(?:ion)?|terminate|"
    r"unsupported|unimplemented|unknown|unresolved|missing|not implemented)\b",
    re.IGNORECASE,
)
STRONG_FAILURES = (
    "shaderrecompiler ",
    "shader resource tracking:",
    "spir-v validation failed",
    "unsupported sampled depth target",
    "control-dependent phi",
    "indirect image table",
    "unresolved import stub called",
    "not implemented (",
    "assertion failed",
    "segmentation fault",
    "access violation",
    "illegal instruction",
)

OPCODE_TOKEN = re.compile(
    r"\b(?:V|S|BUFFER|IMAGE|FLAT|DS|MUBUF|MTBUF|SMEM|EXP|VOP|SOP)_[A-Z0-9_]+\b",
    re.IGNORECASE,
)
STAGE_TOKEN = re.compile(
    r"(?:\bstage\s*=\s*|\bShaderRecompiler\s+)(CS|VS|PS|compute|vertex|pixel|fetch)",
    re.IGNORECASE,
)
HASH_TOKEN = re.compile(
    r"\b(?:shader_?hash|hash|shader|cs|vs|ps)\s*=\s*(0x[0-9a-fA-F]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Evidence:
    line_number: int
    category: str
    severity: str
    message: str
    signature: str


@dataclass
class RunReport:
    source_file: str
    game: str | None = None
    game_id: str | None = None
    build: str | None = None
    os: str | None = None
    cpu: str | None = None
    gpu: str | None = None
    ram_vram: str | None = None
    status: str | None = None
    last_successful_stage: str | None = None
    exception: str | None = None
    shader_hashes: list[str] | None = None
    shader_stages: list[str] | None = None
    assertion: str | None = None
    source_location: str | None = None
    primary_category: str | None = None
    primary_signature: str | None = None
    evidence: list[Evidence] | None = None

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence"] = [asdict(item) for item in self.evidence or []]
        return result


def _clean(value: str) -> str:
    return ANSI_ESCAPE.sub("", value).strip()


def _first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _stage_name(value: str) -> str:
    normalized = value.strip().lower()
    return {
        "compute": "CS",
        "vertex": "VS",
        "pixel": "PS",
        "fetch": "FETCH",
    }.get(normalized, value.strip().upper())


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _infer_game_from_loading(value: str) -> str | None:
    normalized = value.strip().rstrip("/\\")
    pieces = re.split(r"[/\\]", normalized)
    if not pieces:
        return None
    name = pieces[-1]
    if name.lower() in {"eboot.bin", "eboot.elf"} and len(pieces) > 1:
        name = pieces[-2]
    return name or None


def _fallback_game(path: Path) -> str | None:
    stem = path.stem
    for suffix in ("_kyty", "-kyty"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem or None


def _normalize_signature(message: str) -> str:
    normalized = _clean(message)
    normalized = re.sub(r"\bin\s+(?:[A-Za-z]:[\\/]|/).*$", "", normalized)
    normalized = HEX_VALUE.sub("<hex>", normalized)
    normalized = re.sub(r"\b\d+\b", "<num>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def _signature_for(category: str, message: str) -> str:
    lower = message.lower()
    if "control-dependent phi" in lower:
        return "control-dependent phi"
    if "indirect image table" in lower and "incompatible" in lower:
        return "incompatible indirect-image-table candidates"
    if "sampled depth target" in lower:
        return "unsupported sampled-depth target"
    if "spir-v validation" in lower:
        return "SPIR-V validation failure"

    if category == "unsupported_shader_opcode":
        opcode = OPCODE_TOKEN.search(message)
        if opcode is not None:
            return f"unsupported shader opcode: {opcode.group(0).lower()}"
        return "unsupported shader opcode"

    if category == "guest_gpu_command_processor":
        if "dma_data" in lower or "dma data" in lower:
            return "DMA_DATA size handling"
        if "dma" in lower and "control" in lower:
            return "DMA control packet handling"
        if "pm4" in lower or "packet" in lower:
            return "PM4 command packet handling"

    if category == "missing_hle_export":
        symbol = re.search(r"(?:symbol|export)\s*=\s*([^\s]+)", message, re.IGNORECASE)
        if symbol is None and ":" in message:
            symbol_text = message.split(":", 1)[1].strip().split()[0]
            if symbol_text:
                symbol = re.match(r"(.+)", symbol_text)
        if symbol is not None:
            return f"unresolved HLE export: {symbol.group(1)}"
        return "unresolved HLE export"

    if category == "vulkan_descriptor":
        if "descriptor" in lower or "image" in lower:
            return "Vulkan image/descriptor handling"
        return "Vulkan host failure"

    return _normalize_signature(message)


def _category_for_line(message: str) -> str:
    lower = message.lower()

    if (
        "control-dependent phi" in lower
        or "shader resource tracking" in lower
        or "indirect image table" in lower
        or "getbufferresource" in lower
        or "getimageresource" in lower
        or "getsamplerresource" in lower
    ):
        return "shader_resource_tracking"

    if ("opcode" in lower or OPCODE_TOKEN.search(message)) and (
        "unsupported" in lower
        or "unknown" in lower
        or "unimplemented" in lower
        or "not implemented" in lower
        or "failed" in lower
    ):
        return "unsupported_shader_opcode"

    if (
        "sampled depth target" in lower
        or "spir-v" in lower
        or "vulkan" in lower
        or "descriptor" in lower
        or "image descriptor" in lower
    ):
        return "vulkan_descriptor"

    if any(
        token in lower
        for token in (
            "agc",
            "pm4",
            "command processor",
            "dma_data",
            "dma data",
            "indirect buffer",
            "cp packet",
        )
    ):
        return "guest_gpu_command_processor"

    if (
        "unresolved import" in lower
        or "missing export" in lower
        or "unresolved export" in lower
        or "stubbed import" in lower
    ):
        return "missing_hle_export"

    if any(token in lower for token in ("videodec", "video decoder", "avcodec", "avplayer")):
        return "video"

    if any(token in lower for token in ("audio", "audiodec", "atrac", "audioout", "mp3", "aac")):
        return "audio"

    if any(
        token in lower
        for token in (
            "file system",
            "filesystem",
            "can't open",
            "cannot open",
            "no such file",
            "mount failed",
            "invalid file",
        )
    ):
        return "filesystem"

    if "shaderrecompiler" in lower or "shader recompiler" in lower:
        return "shader_recompiler"

    if any(token in lower for token in ("runtime linker", "relocate:", "elf ", "kernel")):
        return "runtime_loader"

    return "other"


def _severity_for_line(message: str) -> str | None:
    lower = message.lower()
    if lower.startswith("---"):
        return None
    if not FAILURE_WORDS.search(message):
        return None

    if any(token in lower for token in STRONG_FAILURES):
        return "fatal"

    if "--- fatal error ---" in lower or "--- error ---" in lower:
        return "fatal"

    # These are useful compatibility signals but are not by themselves proof
    # that the run stopped.  Keep them in evidence without making them the
    # primary blocker when a fatal report is also present.
    if "temporary:" in lower or "fallback" in lower or "not supported" in lower:
        return "diagnostic"

    return "warning"


def _evidence_for_line(line_number: int, message: str) -> Evidence | None:
    clean_message = _clean(message)
    severity = _severity_for_line(clean_message)
    if severity is None:
        return None
    category = _category_for_line(clean_message)
    return Evidence(
        line_number=line_number,
        category=category,
        severity=severity,
        message=clean_message,
        signature=_signature_for(category, clean_message),
    )


def _stage_events(lines: list[str]) -> list[tuple[int, str]]:
    events: list[tuple[int, str]] = []
    phase_names = (
        ("spir-v emitprogram", "SPIR-V EmitProgram"),
        ("ir translateprogram", "IR TranslateProgram"),
        ("cfg structurize", "CFG Structurize"),
        ("cfg buildgraph", "CFG BuildGraph"),
        ("decode", "decode"),
    )

    for line_number, raw_line in enumerate(lines, start=1):
        line = _clean(raw_line)
        lower = line.lower()
        stage_match = re.search(r"phase end:\s*stage=([^\s]+)(.*)$", line, re.IGNORECASE)
        if stage_match:
            body = stage_match.group(2).lower()
            for needle, phase in phase_names:
                if needle in body:
                    events.append((line_number, f"shader {_stage_name(stage_match.group(1))} {phase}"))
                    break
            continue

        if "structured cfg success" in lower:
            events.append((line_number, "shader CFG Structurize"))
        elif line.lower().startswith("select device:"):
            events.append((line_number, "Vulkan device selection"))
        elif line.lower().startswith("loading:"):
            events.append((line_number, "game load"))
        elif "mounted " in lower:
            events.append((line_number, "filesystem mount"))
        elif "flip done:" in lower:
            events.append((line_number, "presentation"))
        elif "queuepoint dispatch" in lower or "graphicsrender" in lower:
            events.append((line_number, "GPU submission"))

    return events


def _value_after_label(lines: Iterable[str], label: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", re.IGNORECASE)
    for line in lines:
        match = pattern.match(_clean(line))
        if match:
            return match.group(1).strip()
    return None


def _parse_build(lines: list[str]) -> str | None:
    build_label: str | None = None
    version: str | None = None
    git_hash: str | None = None

    for raw_line in lines:
        line = _clean(raw_line)
        if re.match(r"^(?:Source|Official|Fork) build\s+", line, re.IGNORECASE):
            build_label = line
        version_match = re.match(r"^version\s*:\s*(.+)$", line, re.IGNORECASE)
        if version_match:
            version = version_match.group(1).strip()
        help_match = re.search(
            r"\bver\s*=\s*([^,]+),\s*git\s*=\s*([^,\s]+)", line, re.IGNORECASE
        )
        if help_match:
            version = version or help_match.group(1).strip()
            git_hash = git_hash or help_match.group(2).strip()
        git_match = re.search(r"\bgit\s*=\s*([^,\s]+)", line, re.IGNORECASE)
        if git_match:
            git_hash = git_hash or git_match.group(1).strip()

    if build_label:
        return build_label
    if version and git_hash and git_hash.lower() not in version.lower():
        return f"{version} ({git_hash})"
    return version or git_hash


def _parse_game(lines: list[str], path: Path) -> str | None:
    for label in ("game title", "game"):
        value = _value_after_label(lines, label)
        if value:
            return value

    for raw_line in lines:
        line = _clean(raw_line)
        match = re.match(r"^Loading:\s*(.+)$", line, re.IGNORECASE)
        if match:
            game = _infer_game_from_loading(match.group(1))
            if game:
                return game

    return _fallback_game(path)


def _parse_gpu(lines: list[str]) -> str | None:
    for raw_line in lines:
        match = re.match(r"^\s*Select device:\s*(.+?)\s*$", _clean(raw_line), re.IGNORECASE)
        if match:
            return match.group(1)
    return _value_after_label(lines, "gpu")


def _parse_ram_vram(lines: list[str]) -> str | None:
    for raw_line in lines:
        line = _clean(raw_line)
        match = re.match(r"^\s*RAM\s*/\s*VRAM\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.match(r"^\s*RAM\s*:\s*(.+?)\s+VRAM\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if match:
            return f"{match.group(1)} / {match.group(2)}"
    return _value_after_label(lines, "ram_vram")


def _parse_exception(lines: list[str]) -> str | None:
    patterns = (
        "segmentation fault",
        "access violation",
        "illegal instruction",
        "sigsegv",
        "sigbus",
        "sigill",
        "terminate called",
        "exception:",
    )
    for raw_line in lines:
        line = _clean(raw_line)
        lower = line.lower()
        if any(pattern in lower for pattern in patterns):
            return line
    return None


def _parse_assertion(lines: list[str]) -> str | None:
    for raw_line in lines:
        line = _clean(raw_line)
        lower = line.lower()
        if (
            "assertion failed" in lower
            or "not implemented (" in lower
            or "error: condition (" in lower
            or "assert(" in lower
        ):
            return line
    return None


def _parse_source_location(lines: list[str], primary_line: int | None) -> str | None:
    if primary_line is None:
        search_order = range(len(lines))
    else:
        start = max(primary_line - 1, 0)
        search_order = list(range(start, min(start + 5, len(lines)))) + list(
            range(max(start - 3, 0), start)
        )

    for index in search_order:
        match = SOURCE_LOCATION.search(_clean(lines[index]))
        if match:
            return f"{match.group(1)}:{match.group(2)}"
    return None


def _sidecar_for(path: Path) -> dict[str, Any]:
    candidates = (path.with_suffix(".json"), Path(f"{path}.json"))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return {}


def _load_metadata(path: Path | None) -> Mapping[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("runs"), dict):
        runs = dict(payload["runs"])
        if isinstance(payload.get("defaults"), dict):
            runs["defaults"] = payload["defaults"]
        return runs
    if isinstance(payload, dict):
        return payload
    raise ValueError("metadata must be a JSON object or an object containing a 'runs' map")


def _metadata_for(
    path: Path, input_root: Path, metadata: Mapping[str, Any], sidecar: Mapping[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    defaults = metadata.get("defaults") if isinstance(metadata, dict) else None
    if isinstance(defaults, dict):
        result.update(defaults)

    relative = path.name
    if input_root.is_dir():
        try:
            relative = path.relative_to(input_root).as_posix()
        except ValueError:
            relative = path.name

    candidates = {path.name, path.stem, relative, str(path), str(path).replace("\\", "/")}
    for key, value in metadata.items():
        if key == "defaults" or not isinstance(value, dict):
            continue
        normalized_key = str(key).replace("\\", "/")
        if normalized_key in candidates or Path(normalized_key).name in candidates:
            result.update(value)

    if isinstance(sidecar, dict):
        result.update(sidecar)
    return result


def _apply_metadata(report: RunReport, metadata: Mapping[str, Any]) -> None:
    aliases = {
        "title": "game",
        "game_title": "game",
        "serial": "game_id",
        "ram / vram": "ram_vram",
        "ram-vram": "ram_vram",
    }
    for raw_key, raw_value in metadata.items():
        key = aliases.get(str(raw_key).lower(), str(raw_key).lower())
        if not hasattr(report, key) or raw_value in (None, ""):
            continue
        if key in {"shader_hashes", "shader_stages"}:
            if isinstance(raw_value, list):
                setattr(report, key, [str(item) for item in raw_value])
            continue
        if isinstance(raw_value, (str, int, float, bool)):
            setattr(report, key, str(raw_value))


def parse_log(
    path: Path,
    input_root: Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RunReport:
    """Parse one local KytyPS5 log into a structured run report."""

    input_root = input_root or path.parent
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    lines = raw_text.splitlines()

    evidence = [
        item
        for line_number, line in enumerate(lines, start=1)
        if (item := _evidence_for_line(line_number, line)) is not None
    ]
    primary_candidates = [item for item in evidence if item.severity in {"fatal", "warning"}]
    primary = max(
        primary_candidates,
        key=lambda item: (item.severity == "fatal", item.line_number),
        default=None,
    )

    source_file = path.name
    if input_root.is_dir():
        try:
            source_file = path.relative_to(input_root).as_posix()
        except ValueError:
            pass

    hashes = _unique(match.group(1).lower() for match in HASH_TOKEN.finditer(raw_text))
    stages = _unique(_stage_name(match.group(1)) for match in STAGE_TOKEN.finditer(raw_text))

    failure_line = primary.line_number if primary is not None else None
    successful_stages = [
        stage for line_number, stage in _stage_events(lines) if failure_line is None or line_number <= failure_line
    ]

    report = RunReport(
        source_file=source_file,
        game=_parse_game(lines, path),
        game_id=_first_nonempty(_value_after_label(lines, "game id"), _value_after_label(lines, "serial")),
        build=_parse_build(lines),
        os=_value_after_label(lines, "os"),
        cpu=_value_after_label(lines, "cpu"),
        gpu=_parse_gpu(lines),
        ram_vram=_parse_ram_vram(lines),
        status=_value_after_label(lines, "compatibility status"),
        last_successful_stage=successful_stages[-1] if successful_stages else None,
        exception=_parse_exception(lines),
        shader_hashes=hashes,
        shader_stages=stages,
        assertion=_parse_assertion(lines),
        source_location=_parse_source_location(lines, failure_line),
        primary_category=primary.category if primary is not None else None,
        primary_signature=primary.signature if primary is not None else None,
        evidence=evidence,
    )
    overrides = _metadata_for(path, input_root, metadata or {}, _sidecar_for(path))
    _apply_metadata(report, overrides)
    return report


def collect_logs(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and (path.suffix.lower() in LOG_SUFFIXES or not path.suffix)
    )


def _existing_paths(paths: Iterable[str], repo_root: Path) -> list[str]:
    result: list[str] = []
    for value in paths:
        for prefix, candidate_root in (("", repo_root), ("prosper/", repo_root / "prosper")):
            if (candidate_root / value).exists():
                result.append(f"{prefix}{value}")
                break
    return result


def _group_games(reports: Iterable[RunReport]) -> int:
    return len({report.game or report.source_file for report in reports})


def _category_summary(reports: list[RunReport], repo_root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[RunReport]] = defaultdict(list)
    for report in reports:
        if report.primary_category is not None:
            grouped[report.primary_category].append(report)

    result: list[dict[str, Any]] = []
    for category, category_reports in grouped.items():
        result.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "runs": len(category_reports),
                "games_affected": _group_games(category_reports),
                "signals": sum(
                    1 for report in category_reports for item in report.evidence or [] if item.category == category
                ),
                "relevant_code": _existing_paths(CATEGORY_CODE.get(category, ()), repo_root),
                "existing_tests": _existing_paths(CATEGORY_TESTS.get(category, ()), repo_root),
                "likely_missing_coverage": CATEGORY_MISSING_COVERAGE.get(category),
            }
        )
    return sorted(result, key=lambda item: (-item["runs"], item["label"]))


def _signature_summary(reports: list[RunReport], repo_root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[RunReport]] = defaultdict(list)
    categories: dict[str, set[str]] = defaultdict(set)
    for report in reports:
        if report.primary_signature:
            grouped[report.primary_signature].append(report)
            if report.primary_category:
                categories[report.primary_signature].add(report.primary_category)

    result: list[dict[str, Any]] = []
    for signature, signature_reports in grouped.items():
        category_names = sorted(categories[signature])
        code: list[str] = []
        tests: list[str] = []
        missing: list[str] = []
        for category in category_names:
            code.extend(_existing_paths(CATEGORY_CODE.get(category, ()), repo_root))
            tests.extend(_existing_paths(CATEGORY_TESTS.get(category, ()), repo_root))
            coverage = CATEGORY_MISSING_COVERAGE.get(category)
            if coverage and coverage not in missing:
                missing.append(coverage)
        result.append(
            {
                "signature": signature,
                "runs": len(signature_reports),
                "games_affected": _group_games(signature_reports),
                "categories": category_names,
                "relevant_code": _unique(code),
                "existing_tests": _unique(tests),
                "likely_missing_coverage": missing,
                "runs_detail": [report.source_file for report in signature_reports],
            }
        )

    return sorted(result, key=lambda item: (-item["runs"], item["signature"]))


def build_report_data(
    reports: list[RunReport], input_root: Path, repo_root: Path | None = None
) -> dict[str, Any]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    signatures = _signature_summary(reports, repo_root)
    return {
        "schema_version": 1,
        "input": str(input_root),
        "runs_analyzed": len(reports),
        "blocker_runs": sum(1 for report in reports if report.primary_category is not None),
        "categories": _category_summary(reports, repo_root),
        "signatures": signatures,
        "highest_leverage_signature": signatures[0] if signatures else None,
        "runs": [report.as_dict() for report in reports],
    }


def _display(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(
    reports: list[RunReport], input_root: Path, repo_root: Path | None = None
) -> str:
    data = build_report_data(reports, input_root, repo_root)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# KytyPS5 blocker report",
        "",
        f"Generated: `{generated_at}`",
        f"Input: `{input_root}`",
        f"Runs analyzed: **{data['runs_analyzed']}**; blocker runs: **{data['blocker_runs']}**",
        "",
        "This report is a deterministic triage aid. It counts one input log as one run and does not establish compatibility or causality.",
        "",
        "## Category summary",
        "",
    ]

    if data["categories"]:
        lines.extend(
            [
                "| Category | Runs | Games affected | Signals |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for item in data["categories"]:
            lines.append(
                f"| {item['label']} | {item['runs']} | {item['games_affected']} | {item['signals']} |"
            )
    else:
        lines.append("No blocker signals were recognized.")

    highest = data["highest_leverage_signature"]
    lines.extend(["", "## Highest-leverage signature", ""])
    if highest is None:
        lines.append("No signature is available yet.")
    else:
        lines.extend(
            [
                f"`{highest['signature']}`",
                "",
                f"- Runs: **{highest['runs']}**",
                f"- Games affected: **{highest['games_affected']}**",
                f"- Categories: {', '.join(CATEGORY_LABELS.get(name, name) for name in highest['categories'])}",
                "- Relevant code:",
            ]
        )
        lines.extend(f"  - `{path}`" for path in highest["relevant_code"])
        lines.append("- Existing tests:")
        if highest["existing_tests"]:
            lines.extend(f"  - `{path}`" for path in highest["existing_tests"])
        else:
            lines.append("  - None mapped yet")
        lines.append("- Likely missing coverage:")
        lines.extend(f"  - {coverage}" for coverage in highest["likely_missing_coverage"])

    lines.extend(
        [
            "",
            "## Run details",
            "",
            "| Game | Build | CPU | GPU | Last successful stage | Primary blocker | Source |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for report in reports:
        lines.append(
            "| "
            + " | ".join(
                (
                    _display(report.game),
                    _display(report.build),
                    _display(report.cpu),
                    _display(report.gpu),
                    _display(report.last_successful_stage),
                    _display(report.primary_signature),
                    f"`{report.source_file}`",
                )
            )
            + " |"
        )

    lines.extend(["", "## Primary evidence", ""])
    for report in reports:
        primary = next(
            (item for item in reversed(report.evidence or []) if item.signature == report.primary_signature),
            None,
        )
        if primary is None:
            continue
        location = f"; source `{report.source_location}`" if report.source_location else ""
        lines.append(f"- `{report.source_file}:{primary.line_number}` ({primary.category}){location}: {primary.message}")

    return "\n".join(lines) + "\n"


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize local KytyPS5 logs into blocker categories and signatures."
    )
    parser.add_argument("logs", type=Path, help="A log file or directory containing log files.")
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Optional JSON map of log names to metadata; per-log <name>.json sidecars are also read.",
    )
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Report format (default: markdown)."
    )
    parser.add_argument("-o", "--output", type=Path, help="Write the report to this file instead of stdout.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root used to filter code/test hints (default: this checkout).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    root = args.logs.expanduser()
    if not root.exists():
        print(f"log input does not exist: {root}", file=sys.stderr)
        return 2

    paths = collect_logs(root)
    if not paths:
        print(f"no log files found under: {root}", file=sys.stderr)
        return 1

    try:
        metadata = _load_metadata(args.metadata.expanduser() if args.metadata else None)
        reports = [parse_log(path, root if root.is_dir() else root.parent, metadata) for path in paths]
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"could not parse triage input: {error}", file=sys.stderr)
        return 2

    repo_root = args.repo_root.expanduser() if args.repo_root else None
    if args.format == "json":
        output = json.dumps(build_report_data(reports, root, repo_root), indent=2, sort_keys=True) + "\n"
    else:
        output = render_markdown(reports, root, repo_root)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
