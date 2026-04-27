import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_COLOR = "white"
DEFAULT_SUFFIX = "_youtube"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create a horizontal copy of an MP4 by placing it on a larger canvas. "
            "Useful for avoiding YouTube Shorts classification on vertical videos."
        )
    )
    parser.add_argument(
        "input_file",
        help="Path to the input MP4 file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output path for the converted video. "
            "If omitted, <input_name>_youtube.mp4 is created next to the original."
        ),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Output canvas width. Default: {DEFAULT_WIDTH}.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Output canvas height. Default: {DEFAULT_HEIGHT}.",
    )
    parser.add_argument(
        "--color",
        default=DEFAULT_COLOR,
        help=f"Background color for the canvas. Default: {DEFAULT_COLOR}.",
    )
    parser.add_argument(
        "--suffix",
        default=DEFAULT_SUFFIX,
        help=(
            "Suffix used when --output is not provided. "
            f"Default: {DEFAULT_SUFFIX}."
        ),
    )
    return parser.parse_args()


def build_output_path(input_path: Path, output: Optional[str], suffix: str) -> Path:
    if output is not None:
        return Path(output).expanduser().resolve()

    return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


def validate_args(input_path: Path, output_path: Path, width: int, height: int):
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed or is not available in PATH.")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    if input_path.suffix.lower() != ".mp4":
        raise ValueError("The input file must be an .mp4 file.")

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers.")

    if input_path == output_path:
        raise ValueError("Output file must be different from the input file.")

    output_path.parent.mkdir(parents=True, exist_ok=True)


def ffmpeg_command(input_path: Path, output_path: Path, width: int, height: int, color: str):
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:{color},setsar=1"
    )

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_path),
    ]


def main():
    args = parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    output_path = build_output_path(input_path, args.output, args.suffix)

    try:
        validate_args(input_path, output_path, args.width, args.height)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    command = ffmpeg_command(
        input_path=input_path,
        output_path=output_path,
        width=args.width,
        height=args.height,
        color=args.color,
    )

    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print("Running ffmpeg...")

    result = subprocess.run(command)

    if result.returncode != 0:
        print("Error: ffmpeg failed to convert the video.", file=sys.stderr)
        return result.returncode

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
