import argparse
import sys
from pathlib import Path

from . import config
from .media import MediaObject
from .task import SqueezeTask
from .util import validate_file


def get_parser():
    # Build arguments and options list.
    description = (
        "Convert video file to MP4, ensuring baseline video quality:\n"
        "  * Default:  720p, CRF=27 (H.264), 25 fps for projected video\n"
        "  * Tutorial: Only use 10 fps for tutorial video\n"
        "\n"
        "Also perform other useful operations on media files."
    )

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        '-a', '--audio',
        action='store_true',
        help="convert file(s) to MP3 audio",
    )
    parser.add_argument(
        '-c', '--command',
        action='store_true',
        help="print the equivalent ffmpeg bash command and exit"
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '-i', '--info',
        action='store_true',
        help="show stream properties of given file (only 1 accepted)"
    )
    parser.add_argument(
        '-k', '--trim',
        nargs=2,
        type=str,
        help="trim the file to keep content between given timestamps (HH:MM:SS)",  # noqa: E501
    )
    parser.add_argument(
        '-m', '--rate-control-mode',
        type=str,
        help="specify the rate control mode [CRF]: CBR, CRF; if CBR is specified, the video bitrate is set to 2Mbps",  # noqa: E501
    )
    parser.add_argument(
        '-n', '--normalize',
        action='store_true',
        help="normalize video resolution, bitrate, and framerate; this is the default action if no options are given",  # noqa: E501
    )
    parser.add_argument(
        '-s', '--speed',
        type=float,
        help="change the playback speed of the video using the given factor (0.5 to 100)",  # noqa: E501
    )
    parser.add_argument(
        '-t', '--tutorial',
        dest='rates',
        action='store_const',
        const=(128000, 500000, 10),
        default=(128000, 2000000, 25),
        help="use lower bitrate and fewer fps for short tutorial videos"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="give verbose output"
    )
    parser.add_argument(
        '-V', '--version',
        action='store_true',
        help="show version number and exit"
    )
    parser.add_argument(
        '--av1',
        action='store_true',
        help="shortcut to use libsvtav1 video encoder"
    )
    parser.add_argument(
        '--video_encoder',
        type=str,
        help=(
            "specify video encoder [libx264]: "
            "use 'squeeze-vid.ffmpeg -encoders' for details"
        )
    )
    parser.add_argument(
        '-x', '--experimental',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "file",
        nargs='*',
        help="space-separated list of media files to modify"
    )
    return parser


def main():
    args = get_parser().parse_args()
    if args.version:
        print(config.VERSION)
        sys.exit()
    if args.verbose:
        config.VERBOSE = True
    if args.debug:
        config.DEBUG = True

    for input_file_string in args.file:
        # Validate input_file.
        input_file = validate_file(input_file_string)
        if args.verbose:
            print(f"input file: {input_file}")
        mod_file = Path()
        # mod_file_prev = Path()
        if not input_file:
            print(f"Skipped invalid input file: {input_file_string}")
            continue
        media_in = MediaObject(input_file)
        task = SqueezeTask(args=args, media_in=media_in)

        if args.experimental:
            # Try out new, experimental features.
            task.action = 'trim'
            task.setup()
            mod_file = task.run()
            sys.exit()

        if args.info:
            # Show the video file info.
            media_in = MediaObject(input_file)
            media_in.show_properties()
            continue

        if args.trim:
            # Trim the file using given timestamps.
            task.trim()

        if args.speed:
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                task = SqueezeTask(args=args, media_in=media_in)
                # mod_file_prev = mod_file
            # Attempt to change the playback speed of all passed video files.
            mod_file = task.change_speed()

        if args.audio:
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                task = SqueezeTask(args=args, media_in=media_in)
                task.media_out.suffix = '.mp3'
                # mod_file_prev = mod_file
            # Convert file(s) to normalized MP3.
            mod_file = task.export_audio()

        if (args.normalize or args.rates[2] == 10 or
                (not args.info and not args.trim and not args.speed and not args.audio)):  # noqa: E501
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                media_in = MediaObject(input_file)
                task = SqueezeTask(args=args, media_in=media_in)
                # mod_file_prev = mod_file
            # Attempt to normalize all passed files.
            task.normalize()


if __name__ == '__main__':
    main()
