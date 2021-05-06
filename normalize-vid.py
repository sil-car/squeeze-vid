#!/usr/bin/env python3

import argparse
import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python
import sys

from pathlib import Path


def convert_file(input_file_string, rates):
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
    stream = build_command(input_file, output_file, rates)
    ffmpeg.run(stream)

def build_command(infile, outfile, rates):
    # Get input file details.
    file_info = get_properties(infile)
    if file_info:
        audio_streams = [a for a in file_info if a['codec_type'] == 'audio']
        video_streams = [v for v in file_info if v['codec_type'] == 'video']
    else:
        audio_streams = None
        video_streams = None

    # Build command sequence.
    stream = ffmpeg.input(str(infile))
    video = stream['v']
    audio = stream['a']

    # Define other output constants.
    bufsize = 100000
    audio_bitrate = 128000
    format = 'mp4'

    # Tailor command depending on whether there are 0 or 1 audio and video input streams.
    if video_streams:
        # Determine maxiumum frame rate from first video stream in input file.
        avg_fps_str = video_streams[0]['avg_frame_rate'] # picks 1st video stream in list
        avg_fps = round(int(avg_fps_str.split('/')[0]) / int(avg_fps_str.split('/')[1]))
        fps = min([avg_fps, rates[1]])

        # Define video max height to 720p (nominal HD).
        video = ffmpeg.filter(video, 'scale', -1, 'min(720, ih)')
        # Define max framerate.
        video = ffmpeg.filter(video, 'fps', fps)

        if audio_streams: # video + audio
            stream = ffmpeg.output(
                video, audio,
                str(outfile),
                # Set output video bitrate to 500kbps for projection.
                video_bitrate=rates[0],
                maxrate=rates[0],
                bufsize=bufsize,
                # Set output audio bitrate to 128kbps for projection.
                audio_bitrate=audio_bitrate,
                format=format,
            )
        else: # video only
            stream = ffmpeg.output(
                video,
                str(outfile),
                # Set output video bitrate to 500kbps for projection.
                video_bitrate=rates[0],
                maxrate=rates[0],
                bufsize=bufsize,
                format=format,
            )
    elif audio_streams: # audio only
        stream = ffmpeg.output(
            audio,
            str(outfile),
            # Set output video bitrate to 500kbps for projection.
            #video_bitrate=rates[0],
            #maxrate=rates[0],
            #bufsize=bufsize,
            # Set output audio bitrate to 128kbps for projection.
            audio_bitrate=audio_bitrate,
            format=format,
        )
    else: # neither audio nor video: command output option
        stream = ffmpeg.output(
            video, audio,
            str(outfile),
            # Set output video bitrate to 500kbps for projection.
            video_bitrate=rates[0],
            maxrate=rates[0],
            bufsize=bufsize,
            # Set output audio bitrate to 128kbps for projection.
            audio_bitrate=audio_bitrate,
            format=format,
        )
    return stream

def show_command(rates):
    stream = build_command('<infile>', '<outfile.mp4>', rates)
    print(f"NOTE: If you run the ffmpeg command directly, the term after -filter_complex need to be quoted because of special characters:\n")
    print(f"ffmpeg {' '.join(ffmpeg.get_args(stream))}\n")
    exit(0)

def get_properties(infile):
    if infile == '<infile>':
        # Dummy file for printing command.
        return None
    try:
        probe = ffmpeg.probe(infile)
    except ffmpeg._run.Error:
        print("Error: Not an audio or video file?")
        exit(1)
    return probe['streams']

def show_properties(infile):
    streams = get_properties(infile)
    print()
    for stream in streams:
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
    dest='rates',
    action='store_const',
    const=(200000, 10),
    default=(500000, 25),
    help="Use lower bitrate and fewer fps for short tutorial videos."
)
parser.add_argument(
    "video",
    nargs='*',
    help="Space-separated list of video files to normalize."
)

args = parser.parse_args()
if args.command:
    # Show the ffmpeg bash command and exit.
    show_command(args.rates)
    exit(0)

if args.infovid:
    # Show the video file info and exit.
    show_properties(args.infovid[0])
    exit(0)

if args.video:
    # Attempt to normalize all passed video files.
    for input_file in args.video:
        convert_file(input_file, args.rates)
