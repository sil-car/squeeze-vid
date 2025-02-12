import sys
from ffmpeg import FFmpegError, Progress
from pathlib import Path

from . import config


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


def print_command(stream):
    command = stream.arguments[1:]  # omit 'ffmpeg'
    # Add quotes around iffy command arg. options.
    for i, item in enumerate(command.copy()):
        if item == '-filter_complex' or item == '-i':
            command[i+1] = f"\"{command[i+1]}\""
    command[-1] = f"\"{command[-1]}\""  # outfile
    command_str = f"squeeze-vid.ffmpeg {' '.join(command)}\n"
    print(command_str)
    return command_str


def run_conversion(output_stream, duration):
    duration = float(duration)
    if config.DEBUG:
        print(f"{duration=}")
    print(output_stream.arguments[-1])

    def get_progressbar(p_pct, w=60, suffix=''):
        suffix = f" {int(p_pct):>3}%"
        end = '\n' if config.VERBOSE or config.DEBUG else '\r'

        ci = '\u23b8'
        cf = '\u23b9'
        d = '█'
        u = ' '
        d_ct = min(int(w*p_pct/100), w)
        u_ct = min(int(w - d_ct - 1), w - 1)

        if config.DEBUG:
            print(f"{p_pct=}")
            print(f"{d_ct=}")
            print(f"{u_ct=}")

        bar = '  '
        if d_ct == 0:
            bar += ci + u*(u_ct - 1) + cf
        elif d_ct < w:
            bar += str(d*d_ct) + str(u*u_ct) + cf
        else:
            bar += str(d*d_ct)
        bar += suffix + end
        return bar

    @output_stream.on('progress')
    def on_progress(progress: Progress):
        percent = progress.time.total_seconds() * 100 / duration
        if config.DEBUG or config.VERBOSE:
            print(progress)
        sys.stdout.write(get_progressbar(percent))

    try:
        output_stream.execute()
        sys.stdout.write(get_progressbar(100)) # for a nice, cleann finish
        print()
    except FFmpegError as e:
        print(f"{e.message}: {e.arguments}")
