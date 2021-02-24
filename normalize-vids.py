#!/usr/bin/env python3

import argparse
import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python
import sys

from pathlib import Path


def convert_file(input_file_string, bitrate):
    # Get full path to input file.
    #   .expanduser() expands out possible "~"
    #   .resolve() expands relative paths and symlinks
    input_file = Path(input_file_string).expanduser().resolve()
    if not input_file.is_file():
        print(f"Error: invalid input file: {file_path}")
        return

    # Create output_file name by adding ".n" to input_file name.
    #   Output to same directory as input_file.
    output_file = input_file.with_name(f"{input_file.stem}.n.mp4")

    # Execute command sequence.
    stream = ffmpeg.input(str(input_file))
    video = stream['v']
    audio = stream['a']
    # Set video max height to 720p (nominal HD).
    video = ffmpeg.filter(video, 'scale', -1, 'min(720, ih)')
    # Set max framerate to 25fps.
    video = ffmpeg.filter(video, 'fps', 25)
    stream = ffmpeg.output(
        video, audio,
        str(output_file),
        # Set output video bitrate to 500kbps for projection.
        video_bitrate=bitrate,
        # Set output audio bitrate to 128kbps for projection.
        audio_bitrate=128000,
        format='mp4',
    )
    ffmpeg.run(stream)

parser = argparse.ArgumentParser()
parser.add_argument(
    '-t', '--tutorial',
    dest='vidbps',
    action='store_const',
    const=100000,
    default=500000,
    help="Use a lower bitrate for a short tutorial video."
)
parser.add_argument(
    "video",
    nargs='+',
    help="Space-separated list of video files to normalize."
)

args = parser.parse_args()
for input_file in args.video:
    convert_file(input_file, args.vidbps)
