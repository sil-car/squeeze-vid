#!/usr/bin/env python3

import os
import sys
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
import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python

def validate_file(input_file_string):
    # Get full path to input file.
    #   .expanduser() expands out possible "~"
    #   .resolve() expands relative paths and symlinks
    input_file = Path(input_file_string).expanduser().resolve()
    if not input_file.is_file():
        # print(f"Error: invalid input file: {input_file_string}")
        return None
    return input_file

def parse_timestamp(timestamp):
    """
    Return timestamp string HH:MM:SS as a float of total seconds.
    """
    parts = timestamp.split(':')
    seconds = 0.0
    for i in range(len(parts)):
        # Convert empty placeholder to zero.
        if parts[-(i+1)] == '':
            parts[-(i+1)] = 0
        seconds += float(parts[-(i+1)])*60**i if len(parts) > i else 0
    return seconds

def get_properties(infile):
    if infile == '<infile>':
        # Dummy file for printing command.
        return 'placeholder'
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

def get_outfile(input_file, details):
    # Output to same directory as input_file; i.e. only change the filename, not the path.
    if details.get('function') == 'change_playback_speed':
        # Use speed factor and suffix in outfile.
        return input_file.with_name(f"{input_file.stem}_{str(details.get('factor'))}x{input_file.suffix}")
    elif details.get('function') == 'convert_file':
        vbitrate = round(details.get('video_bitrate')/1000)
        abitrate = round(details.get('audio_bitrate')/1000)
        if details.get('suffix') == '.mp4':
            # Use video_bitrate, framerate, audio_bitrate, and suffix in outfile.
            specs_str = f"v{vbitrate}kbps_{details.get('framerate')}fps_a{abitrate}kbps"
        elif details.get('suffix') == '.mp3':
            # Use audio_bitrate and suffix in outfile.
            specs_str = f"a{round(abitrate)}kbps"
        return input_file.with_name(f"{input_file.stem}_{specs_str}{details.get('suffix')}")
    elif details.get('function') == 'trim_file':
        # Use duration and suffix in outfile.
        return input_file.with_name(f"{input_file.stem}_{details.get('duration')}s{details.get('suffix')}")

def split_into_streams(infile):
    # Get input file details.
    file_info = get_properties(infile)
    if file_info == 'placeholder':
        audio_streams = ['placeholder']
        video_streams = ['placeholder']
    else:
        audio_streams = [a for a in file_info if a['codec_type'] == 'audio']
        video_streams = [v for v in file_info if v['codec_type'] == 'video']

    # Split into streams.
    stream = ffmpeg.input(str(infile))
    video = stream.video #stream['v']
    audio = stream.audio #stream['a']
    return audio_streams, video_streams, audio, video

def change_playback_speed(input_file, factor, rates, cmd):
    details = {
        'factor': factor,
        'function': 'change_playback_speed',
        'suffix': input_file.suffix,
    }
    output_file = get_outfile(input_file, details)
    stream = build_speed_stream(input_file, output_file, factor, rates)
    if cmd:
        print_command(stream)
        return
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True)
    except ffmpeg._run.Error as e:
        exit(1)
    return output_file

def convert_file(input_file, rates, cmd, output_format='.mp4'):
    details = {
        'audio_bitrate': rates[0],
        'framerate': rates[2],
        'function': 'convert_file',
        'suffix': output_format,
        'video_bitrate': rates[1],
    }
    # TODO: Keep input_file bitrate if less than details['video_bitrate'].
    output_file = get_outfile(input_file, details)
    if output_format == '.mp4':
        stream = build_video_stream(input_file, output_file, rates)
    elif output_format == '.mp3':
        stream = build_audio_stream(input_file, output_file, rates)
    if cmd:
        print_command(stream)
        return
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True)
    except ffmpeg._run.Error as e:
        exit(1)
    return output_file

def trim_file(input_file, endpoints, cmd, output_format='.mp4'):
    # Convert timestamp(s) to seconds.
    endpoints = [parse_timestamp(e) for e in endpoints]
    duration = endpoints[1] -  endpoints[0]

    details = {
        'duration': duration,
        'function': 'trim_file',
        'suffix': output_format,
    }
    output_file = get_outfile(input_file, details)
    stream = build_trim_stream(input_file, output_file, endpoints)
    if cmd:
        print_command(stream)
        return
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True)
    except ffmpeg._run.Error as e:
        exit(1)
    return output_file

def generate_output_stream(vstreams, astreams, video, audio, rates, outfile):
    # Define output constants.
    audio_bitrate = rates[0]
    video_bitrate = rates[1]
    bufsize = video_bitrate/2 # allows for minimal variation in actual bitrate
    format = 'mp4'

    if vstreams and astreams:
        stream = ffmpeg.output(
            video, audio,
            str(outfile),
            # Set output video bitrate to 500kbps for projection.
            video_bitrate=video_bitrate,
            maxrate=video_bitrate,
            bufsize=bufsize,
            # Set output audio bitrate to 128kbps for projection.
            audio_bitrate=audio_bitrate,
            format=format,
        )
    elif vstreams and not astreams:
        stream = ffmpeg.output(
            video,
            str(outfile),
            # Set output video bitrate to 500kbps for projection.
            video_bitrate=video_bitrate,
            maxrate=video_bitrate,
            bufsize=bufsize,
            format=format,
        )
    elif astreams and not vstreams: # audio-only stream
        format = 'mp3'
        stream = ffmpeg.output(
            audio,
            str(outfile),
            # Set output audio bitrate to 128kbps for projection.
            audio_bitrate=audio_bitrate,
            format=format,
        )
    return stream

def build_audio_stream(infile, outfile, rates):
    # Get stream details.
    audio_streams, video_streams, audio, video = split_into_streams(infile)

    # Remove video streams.
    video_streams = None

    # Output correct stream.
    stream = generate_output_stream(video_streams, audio_streams, video, audio, rates, outfile)
    return stream

def build_video_stream(infile, outfile, rates):
    # Get stream details.
    audio_streams, video_streams, audio, video = split_into_streams(infile)

    # Determine frame rate of input video.
    fps = rates[2] # default value
    if video_streams and type(video_streams[0]) != str:
        # Determine maxiumum frame rate from first video stream in input file.
        avg_fps_str = video_streams[0]['avg_frame_rate'] # picks 1st video stream in list
        avg_fps = round(int(avg_fps_str.split('/')[0]) / int(avg_fps_str.split('/')[1]))
        fps = min([avg_fps, fps])

    # Define video max height to 720p (nominal HD).
    video = ffmpeg.filter(video, 'scale', -1, 'min(720, ih)')
    # Define max framerate.
    video = ffmpeg.filter(video, 'fps', fps)

    # Output correct stream.
    stream = generate_output_stream(video_streams, audio_streams, video, audio, rates, outfile)
    return stream

def build_speed_stream(infile, outfile, factor, rates):
    # Get stream details.
    audio_streams, video_streams, audio, video = split_into_streams(infile)

    # Set playback timestamps.
    if Path(infile).suffix == '.mp3':
        video = None
    else:
        video = ffmpeg.filter(video, 'setpts', f"{str(1 / factor)}*PTS")
    # Adjust audio speed.
    audio = ffmpeg.filter(audio, 'atempo', f"{str(factor)}")

    # Output correct stream.
    stream = generate_output_stream(video_streams, audio_streams, video, audio, rates, outfile)
    return stream

def build_trim_stream(infile, outfile, endpoints):
    # Get input file details.
    file_info = get_properties(infile)
    if file_info == 'placeholder':
        audio_streams = ['placeholder']
        video_streams = ['placeholder']
    else:
        audio_streams = [a for a in file_info if a['codec_type'] == 'audio']
        video_streams = [v for v in file_info if v['codec_type'] == 'video']

    # Get input stream details.
    stream = ffmpeg.input(str(infile))
    video = stream.video
    audio = stream.audio

    # Set correct output stream.
    #   The -ss and -to options are given here so that the subtitles are properly
    #   handled. This doesn't work correctly when the options are given to the
    #   input stream.
    #   Video is re-encoded to make beginning and end frames sync well, and to
    #       output as MP4 regardless of input file format.
    stream = ffmpeg.output(
        video, audio, str(outfile),
        **{'ss': endpoints[0]}, **{'to': endpoints[1]}, **{'c:a': 'copy'}, **{'c:v': 'libx264'},
    )
    return stream

def print_command(stream):
    command = ffmpeg.get_args(stream)
    for i, item in enumerate(ffmpeg.get_args(stream)):
        if item == '-filter_complex':
            command[i+1] = f"\"{command[i+1]}\""
            break
    print(f"ffmpeg {' '.join(command)}\n")

def main():
    # Build arguments and options list.
    description = "Convert video file to MP4, ensuring baseline video quality:\n\
  * Default:  720p, 500 Kbps, 25 fps for projected video\n\
  * Tutorial: 720p, 200 Kbps, 10 fps for tutorial video\n\
\n\
Also perform other useful operations on media files."

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        '-a', '--audio',
        action='store_true',
        help="Convert file(s) to MP3 audio."
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
        "file",
        nargs='*',
        help="Space-separated list of media files to modify."
    )

    args = parser.parse_args()

    for input_file_string in args.file:
        # Validate input_file.
        input_file = validate_file(input_file_string)
        mod_file = Path()
        mod_file_prev = Path()
        if not input_file:
            print(f"Skipped invalid input file: {input_file_string}")
            continue

        if args.info:
            # Show the video file info.
            show_properties(input_file)
            continue
        if args.trim:
            # Trim the file using given timestamps.
            mod_file = trim_file(input_file, args.trim, args.command)
        if args.speed:
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                mod_file_prev = mod_file
            # Attempt to change the playback speed of all passed video files.
            mod_file = change_playback_speed(input_file, args.speed, args.rates, args.command)
            # Delete any file from previous step.
            # if mod_file_prev.is_file(): mod_file_prev.unlink()
        if args.audio:
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                mod_file_prev = mod_file
            # Convert file(s) to normalized MP3.
            mod_file = convert_file(input_file, args.rates, args.command, output_format='.mp3')
            # Delete any file from previous step.
            # if mod_file_prev.is_file(): mod_file_prev.unlink()
        if (args.normalize or args.rates[2] == 10 or
                (not args.info and not args.trim and not args.speed and not args.audio)):
            # Use mod_file from previous step as input_file if it exists.
            if mod_file.is_file():
                input_file = mod_file
                mod_file_prev = mod_file
            # Attempt to normalize all passed files.
            # input_file = convert_file(input_file, args.rates, args.command, output_format=Path(input_file).suffix)
            mod_file = convert_file(input_file, args.rates, args.command)
            # Delete any file from previous step.
            # if mod_file_prev.is_file(): mod_file_prev.unlink()


if __name__ == '__main__':
    main()
