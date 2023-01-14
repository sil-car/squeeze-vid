#!/usr/bin/env python3

import os

from pathlib import Path

# Ensure that virutal environment is activated.
if not os.environ.get('SNAP') and not os.environ.get('VIRTUAL_ENV'):
    repo_root = Path(__file__).resolve().parents[1]
    auto_activate_file = Path(f"{(repo_root)}/env/bin/auto_activate.py")
    if not auto_activate_file.is_file():
        print(f"Info: {auto_activate_file} doesn't exist.")
        print(f"Info: Need to install and/or activate virtual env to use this script.")
        exit(1)
    with open(auto_activate_file) as f:
        exec(f.read(), {'__file__': auto_activate_file})
        print(f"Info: Virtual environment activated automatically.")

import argparse

from media import convert_file
from media import MediaObject
from util import validate_file


def main():
    # Build arguments and options list.
    description = "Convert video file to MP4, ensuring baseline video quality:\n\
  * Default:  720p, 2 Mbps, 25 fps for projected video\n\
  * Tutorial: 720p, 500 Kbps, 10 fps for tutorial video\n\
\n\
Also perform other useful operations on media files."

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        '-a', '--audio',
        action='store_true',
        # help="Convert file(s) to MP3 audio.",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '-c', '--command',
        action='store_true',
        help="Print the equivalent ffmpeg bash command and exit."
    )
    parser.add_argument(
        '-i', '--info',
        action='store_true',
        help="Show stream properties of given file (only 1 accepted)."
    )
    parser.add_argument(
        '-k', '--trim',
        nargs=2,
        type=str,
        help="Trim the file to keep content between given timestamps (HH:MM:SS)."
    )
    parser.add_argument(
        '-n', '--normalize',
        action='store_true',
        help="Normalize video reslution, bitrate, and framerate. This is also the default action if no options are given."
    )
    parser.add_argument(
        '-s', '--speed',
        type=float,
        help="Change the playback speed of the video using the given factor (0.5 to 100).",
    )
    parser.add_argument(
        '-t', '--tutorial',
        dest='rates',
        action='store_const',
        const=(128000, 500000, 10),
        default=(128000, 2000000, 25),
        help="Use lower bitrate and fewer fps for short tutorial videos."
    )
    parser.add_argument(
        '-x', '--experimental',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "file",
        nargs='*',
        help="Space-separated list of media files to modify."
    )

    args = parser.parse_args()

    # Set normalized output properties.
    media_out = MediaObject()
    media_out.abr_norm = args.rates[0]
    media_out.vbr_norm = args.rates[1]
    media_out.fps_norm = args.rates[2]
    media_out.acodec_norm = 'aac'
    media_out.vcodec_norm = 'libx264'
    media_out.height_norm = 720
    media_out.format_norm_a = 'mp3'
    media_out.suffix_norm_a = '.mp3'
    media_out.format_norm_v = 'mp4'
    media_out.suffix_norm_v = '.mp4'

    for input_file_string in args.file:
        # Validate input_file.
        input_file = validate_file(input_file_string)
        mod_file = Path()
        mod_file_prev = Path()
        if not input_file:
            print(f"Skipped invalid input file: {input_file_string}")
            continue
        media_in = MediaObject(input_file)

        if args.experimental:
            # Try out new, experimental features.
            # show_command = True
            show_command = False
            media_out.factor = 0.5
            media_out.endpoints = ['3', '13']
            mod_file = convert_file(show_command, media_in, 'normalize', media_out)
            continue
        if args.info:
            # Show the video file info.
            media_in = MediaObject(input_file)
            media_in.show_properties()
            continue
        if args.trim:
            # Trim the file using given timestamps.
            media_out.endpoints = args.trim
            mod_file = convert_file(args.command, media_in, 'trim', media_out)
        if args.speed:
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                mod_file_prev = mod_file
            # Attempt to change the playback speed of all passed video files.
            media_out.factor = float(args.speed)
            mod_file = convert_file(args.command, media_in, 'change_speed', media_out)
        if args.audio:
            print("Needs work.")
            continue
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                mod_file_prev = mod_file
            # Convert file(s) to normalized MP3.
            media_out.suffix = '.mp3'
            mod_file = convert_file(args.command, media_in, 'export_audio', media_out)
        if (args.normalize or args.rates[2] == 10 or
                (not args.info and not args.trim and not args.speed and not args.audio)):
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                mod_file_prev = mod_file
            # Attempt to normalize all passed files.
            mod_file = convert_file(args.command, media_in, 'normalize', media_out)


if __name__ == '__main__':
    main()