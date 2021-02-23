import ffmpeg
import sys

from pathlib import Path


def convert_file(input_file_string):
    # Get full path to input file.
    #   .expanduser() expands out possible "~"
    #   .resolve() expands relative paths and symlinks
    input_file = Path(input_file_string).expanduser().resolve()
    if not input_file.is_file():
        print(f"Error: invalid input file: {file_path}")
        return

    # Create output_file name by adding "_norm" to input_file name.
    output_file = input_file.with_name(f"{input_file.stem}.n{input_file.suffix}")

    # Execute command sequence.
    stream = ffmpeg.input(str(input_file))
    stream = ffmpeg.output(
        stream,
        str(output_file),
        # Set output video bitrate to 500kbps for projection.
        video_bitrate=500000,
        # Set output audio bitrate to 128kbps for projection.
        audio_bitrate=128000,
        format='mp4',
    )
    ffmpeg.run(stream)


input_files = sys.argv[1:]
for input_file in input_files:
    convert_file(input_file)
