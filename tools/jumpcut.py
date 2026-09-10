#!/usr/bin/env python3
"""
Detect or remove silence/dead-air using auto-editor's VAD-based silence
detection (Silero VAD under the hood) — more robust than hand-tuning
ffmpeg's silencedetect dB threshold, since it reacts to actual speech
presence rather than a fixed loudness cutoff.

Added via skill-discovery audit, 2026-09-10 — see pyproject.toml's `editing`
extra (`uv sync --extra editing`). auto-editor downloads its own compiled
binary from https://github.com/WyattBlue/auto-editor on first run; nothing
else to install.

Two modes:

  Detect-only (default, no --output) — produces an edit-decision list
  (start/end/action per segment, in seconds) without touching the source
  file. Use this to review cuts before committing, or to feed timestamps
  into another tool (e.g. trimming a still-image timeline to match).

  Render (--output/-o given) — actually cuts the silence out and writes a
  new video file.

Usage:
    # Just see what would be cut (prints a JSON edit-decision list)
    uv run tools/jumpcut.py --input raw.mp4 --json

    # Same, human-readable
    uv run tools/jumpcut.py --input raw.mp4

    # Actually render the cut version
    uv run tools/jumpcut.py --input raw.mp4 --output raw_cut.mp4

    # Tighter/looser silence threshold, more margin around speech
    uv run tools/jumpcut.py --input raw.mp4 --threshold 6% --margin 0.3s -o cut.mp4

    # Use a preset tuned for a specific source type
    uv run tools/jumpcut.py --input screencast.mp4 --preset screencast -o cut.mp4
    uv run tools/jumpcut.py --list-presets

    # Motion-based instead of audio-based (b-roll with no narration)
    uv run tools/jumpcut.py --input broll.mp4 --edit-method "motion:threshold=2%" -o cut.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Threshold/margin tuned per source type. `threshold` is auto-editor's
# audio-loudness-percentage cutoff (of the file's peak); `margin` pads
# every kept segment so words aren't clipped at the edges.
PRESETS = {
    "podcast": {
        "threshold": "4%",
        "margin": "0.2s",
        "note": "Single/dual mic voice, moderate room noise (default-ish).",
    },
    "screencast": {
        "threshold": "2%",
        "margin": "0.3s",
        "note": "Screen recording narration — usually quieter/more even levels.",
    },
    "interview": {
        "threshold": "6%",
        "margin": "0.15s",
        "note": "Multiple speakers/handoffs — tighter margin avoids overlap bleed.",
    },
    "noisy": {
        "threshold": "10%",
        "margin": "0.25s",
        "note": "Room tone, AC hum, outdoor recording — needs a higher floor.",
    },
}

CUT_SPEED = 99999.0  # auto-editor's "cut" sentinel speed in v1 export chunks


def parse_args():
    parser = argparse.ArgumentParser(
        description="Detect or remove silence/dead-air with auto-editor (Silero VAD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  uv run tools/jumpcut.py --input raw.mp4 --json
  uv run tools/jumpcut.py --input raw.mp4 --output cut.mp4
  uv run tools/jumpcut.py --input raw.mp4 --preset screencast -o cut.mp4

Available presets: {', '.join(PRESETS.keys())}
        """,
    )
    parser.add_argument("--input", "-i", help="Source video/audio file (required unless --list-presets)")
    parser.add_argument("--output", "-o", help="If set, render the cut video to this path. Omit for detect-only.")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Use a tuned threshold/margin pair")
    parser.add_argument("--threshold", "-t", help="Audio loudness threshold, e.g. '4%%' (default: 4%%, or preset value)")
    parser.add_argument("--margin", "-m", help="Padding kept around loud sections, e.g. '0.2s' (default: 0.2s, or preset value)")
    parser.add_argument(
        "--edit-method",
        help="Override the full --edit expression passed to auto-editor "
        "(e.g. 'motion:threshold=2%%' for motion-based cuts on b-roll with no narration). "
        "Overrides --threshold.",
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON (for machine parsing)")
    parser.add_argument("--dry-run", action="store_true", help="Show the auto-editor command without running it")
    parser.add_argument("--list-presets", action="store_true", help="List available presets and exit")
    return parser.parse_args()


def get_media_duration(path: str) -> float | None:
    """Get media duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (FileNotFoundError, ValueError):
        pass
    return None


def get_video_fps(path: str) -> float:
    """Get the source's frame rate via ffprobe (auto-editor's v1 export uses
    this as its implicit timeline timebase when none is passed explicitly)."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", path,
            ],
            capture_output=True,
            text=True,
        )
        raw = result.stdout.strip()
        if result.returncode == 0 and raw:
            if "/" in raw:
                num, den = raw.split("/")
                return float(num) / float(den)
            return float(raw)
    except (FileNotFoundError, ValueError, ZeroDivisionError):
        pass
    return 30.0  # toolkit-wide default (see CLAUDE.md: "All videos use 30fps")


def check_auto_editor() -> str | None:
    path = shutil.which("auto-editor")
    if path:
        return path
    print(
        "Error: auto-editor not found on PATH.\n"
        "\n"
        "It's an optional dependency — install it with:\n"
        '  uv sync --extra editing\n'
        "\n"
        "First run downloads its own compiled binary from\n"
        "https://github.com/WyattBlue/auto-editor/releases (one-time, needs network).",
        file=sys.stderr,
    )
    return None


def build_edit_expr(args) -> str:
    if args.edit_method:
        return args.edit_method
    threshold = args.threshold or (PRESETS[args.preset]["threshold"] if args.preset else "4%")
    return f"audio:threshold={threshold}"


def build_margin(args) -> str:
    if args.margin:
        return args.margin
    if args.preset:
        return PRESETS[args.preset]["margin"]
    return "0.2s"


def run_detect(input_path: str, edit_expr: str, margin: str, dry_run: bool) -> dict:
    """Run auto-editor with the v1 (chunks) export and turn frame-index chunks
    into a plain-language, timestamped edit-decision list. Never touches the
    source file — a temp .v1 JSON sidecar is the only output written."""
    fps = get_video_fps(input_path)

    with tempfile.TemporaryDirectory() as tmp:
        v1_path = Path(tmp) / "edl.v1"
        cmd = [
            "auto-editor", input_path,
            "--edit", edit_expr,
            "--margin", margin,
            "--export", "v1",
            "-o", str(v1_path),
            "--no-open",
        ]
        if dry_run:
            return {"dry_run": True, "command": " ".join(cmd)}

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not v1_path.exists():
            raise RuntimeError(f"auto-editor failed (exit {proc.returncode}):\n{proc.stderr.strip() or proc.stdout.strip()}")

        chunks = json.loads(v1_path.read_text())["chunks"]

    segments = []
    total_kept = 0.0
    total_cut = 0.0
    for start_frame, end_frame, speed in chunks:
        start_s = start_frame / fps
        end_s = end_frame / fps
        dur = end_s - start_s
        action = "cut" if speed >= CUT_SPEED else ("speed" if speed != 1.0 else "keep")
        if action == "cut":
            total_cut += dur
        else:
            total_kept += dur
        segments.append({
            "start": round(start_s, 3),
            "end": round(end_s, 3),
            "duration": round(dur, 3),
            "action": action,
            "speed": speed,
        })

    return {
        "input": input_path,
        "fps": fps,
        "edit_method": edit_expr,
        "margin": margin,
        "segments": segments,
        "total_duration": round(total_kept + total_cut, 3),
        "kept_duration": round(total_kept, 3),
        "cut_duration": round(total_cut, 3),
    }


def run_render(input_path: str, output_path: str, edit_expr: str, margin: str, dry_run: bool) -> dict:
    cmd = [
        "auto-editor", input_path,
        "--edit", edit_expr,
        "--margin", margin,
        "-o", output_path,
        "--no-open",
    ]
    if dry_run:
        return {"dry_run": True, "command": " ".join(cmd)}

    input_dur = get_media_duration(input_path)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not Path(output_path).exists():
        raise RuntimeError(f"auto-editor failed (exit {proc.returncode}):\n{proc.stderr.strip() or proc.stdout.strip()}")
    output_dur = get_media_duration(output_path)

    result = {
        "success": True,
        "input": input_path,
        "output": output_path,
        "edit_method": edit_expr,
        "margin": margin,
    }
    if input_dur:
        result["input_duration"] = round(input_dur, 3)
    if output_dur:
        result["output_duration"] = round(output_dur, 3)
    if input_dur and output_dur:
        result["removed_duration"] = round(input_dur - output_dur, 3)
        result["removed_pct"] = round(100 * (input_dur - output_dur) / input_dur, 1)
    return result


def main():
    args = parse_args()

    if args.list_presets:
        print("Available presets:")
        for name, preset in PRESETS.items():
            print(f"  {name}: threshold={preset['threshold']} margin={preset['margin']} — {preset['note']}")
        return

    if not args.input:
        print("Error: --input/-i is required", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and check_auto_editor() is None:
        sys.exit(1)

    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    edit_expr = build_edit_expr(args)
    margin = build_margin(args)

    try:
        if args.output:
            result = run_render(args.input, args.output, edit_expr, margin, args.dry_run)
        else:
            result = run_detect(args.input, edit_expr, margin, args.dry_run)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    if result.get("dry_run"):
        print("Would run:")
        print(f"  {result['command']}")
        return

    if args.output:
        print(f"Rendered: {result['output']}", file=sys.stderr)
        if "input_duration" in result and "output_duration" in result:
            print(
                f"Duration: {result['input_duration']:.2f}s -> {result['output_duration']:.2f}s "
                f"(removed {result['removed_duration']:.2f}s, {result['removed_pct']:.1f}%)",
                file=sys.stderr,
            )
    else:
        print(f"Input: {result['input']} ({result['total_duration']:.2f}s, {result['fps']:.2f}fps)")
        print(f"Edit method: {result['edit_method']}  Margin: {result['margin']}")
        print(f"Kept: {result['kept_duration']:.2f}s   Cut: {result['cut_duration']:.2f}s")
        print()
        for seg in result["segments"]:
            tag = seg["action"].upper()
            print(f"  [{tag:>5}] {seg['start']:>7.2f}s - {seg['end']:>7.2f}s  ({seg['duration']:.2f}s)")


if __name__ == "__main__":
    main()
