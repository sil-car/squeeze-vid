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
    stream = build_command(input_file, output_file, bitrate)
    ffmpeg.run(stream)

def build_command(infile, outfile, bitrate):
    # Execute command sequence.
    stream = ffmpeg.input(str(infile))
    video = stream['v']
    audio = stream['a']
    # Set video max height to 720p (nominal HD).
    video = ffmpeg.filter(video, 'scale', -1, 'min(720, ih)')
    # Set max framerate to 25fps.
    video = ffmpeg.filter(video, 'fps', 25)
    stream = ffmpeg.output(
        video, audio,
        str(outfile),
        # Set output video bitrate to 500kbps for projection.
        video_bitrate=bitrate,
        # Set output audio bitrate to 128kbps for projection.
        audio_bitrate=128000,
        format='mp4',
    )
    return stream

def show_command(bitrate):
    stream = build_command('<infile>', '<outfile.mp4>', bitrate)
    print(f"NOTE: If you run the ffmpeg command directly, the term after -filter_complex need to be quoted because of special characters:\n")
    print(f"ffmpeg {' '.join(ffmpeg.get_args(stream))}\n")
    exit(0)

def show_properties(infile):
    try:
        probe = ffmpeg.probe(infile)
    except ffmpeg._run.Error:
        print("Error: Not an audio or video file?")
        exit(1)
    print()
    for stream in probe['streams']:
        for k, v in stream.items():
            skip = ['disposition', 'tags']
            if k in skip:
                continue
            print(f"{k:<24} {v}")
        print()


# Build arguments and options list.
parser = argparse.ArgumentParser()
parser.add_argument(
    '-c', '--command',
    action='store_true',
    help="Print the equivalent ffmpeg bash command."
)
parser.add_argument(
    '-i', '--info',
    nargs=1,
    dest='infovid',
    metavar='video',
    help="Show audio and video properties of given file."
)
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
    nargs='*',
    help="Space-separated list of video files to normalize."
)

args = parser.parse_args()
if args.command:
    # Show the ffmpeg bash command and exit.
    show_command(args.vidbps)
    exit(0)

if args.infovid:
    # Show the video file info and exit.
    show_properties(args.infovid[0])
    exit(0)

if args.video:
    # Attempt to normalize all passed video files.
    for input_file in args.video:
        convert_file(input_file, args.vidbps)
