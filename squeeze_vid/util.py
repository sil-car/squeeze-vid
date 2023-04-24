import ffmpeg
import sys
import threading

from pathlib import Path
# https://docs.python.org/3/library/queue.html?highlight=queue#module-queue
from queue import Queue
from threading import Thread

import config


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

def get_file_out(media_in, action, media_out):
    spec_str = ''
    if action == 'change_speed':
        # Use speed factor and suffix in outfile.
        specs_str = f"{str(media_out.factor)}x"
    elif action == 'normalize':
        vbitrate = round(media_out.vbr/1000)
        abitrate = round(media_out.abr/1000)
        if media_out.suffix == '.mp4':
            # Use video_bitrate, framerate, audio_bitrate, and suffix in outfile.
            specs_str = f"v{vbitrate}kbps_{media_out.fps}fps_a{abitrate}kbps"
        elif media_out.suffix == '.mp3':
            # Use audio_bitrate and suffix in outfile.
            specs_str = f"a{round(abitrate)}kbps"
    elif action == 'trim':
        # Use duration and suffix in outfile.
        specs_str = f"{media_out.duration}s"
    media_out.file = media_in.file
    filename = f"{media_in.file.stem}_{specs_str}{media_out.suffix}"
    media_out.file = media_out.file.with_name(filename)
    return media_out.file

def print_command(stream):
    command = ffmpeg.get_args(stream)
    # Add quotes around iffy command arg. options.
    for i, item in enumerate(command.copy()):
        if item == '-filter_complex' or item == '-i':
            command[i+1] = f"\"{command[i+1]}\""
    command[-1] = f"\"{command[-1]}\"" # outfile
    print(f"squeeze-vid.ffmpeg {' '.join(command)}\n")

def run_conversion(output_stream, duration):
    duration = float(duration)
    if config.DEBUG:
        print(f"{duration = }")
    filepath = output_stream.node.kwargs.get('filename')
    print(filepath)

    def get_progressbar(p_pct, w=60, suffix=''):
        suffix = f" {int(p_pct):>3}%"
        end = '\n' if config.VERBOSE else '\r'

        ci = '\u23b8'
        cf = '\u23b9'
        d = '█'
        u = ' '
        d_ct = min(int(w*p_pct/100), w)
        u_ct = min(int(w - d_ct - 1), w - 1)

        if config.DEBUG:
            print(f"{p_pct = }")
            print(f"{d_ct = }")
            print(f"{u_ct = }")


        bar = '  '
        if d_ct == 0:
            bar += ci + u*(u_ct - 1) + cf
        elif d_ct < w:
            bar += str(d*d_ct) + str(u*u_ct) + cf
        else:
            bar += str(d*d_ct)
        bar += suffix + end
        return bar

    def read_output(pipe, q):
        for line in iter(pipe.readline, b''):
            text = line.decode('utf8')
            q.put(text)
        pipe.close()

    def write_output(duration, q):
        for text in iter(q.get, None):
            tokens = text.rstrip().split('=')
            if config.VERBOSE or len(tokens) == 1:
                sys.stdout.write(text)
            elif len(tokens) == 2:
                k, v = tokens
                if k == 'out_time_ms':
                    current = float(v) / 1000000 # convert to sec
                    if config.DEBUG:
                        print(f"{current = }")
                    # BUG: out_time_ms is initially a very large neg. number in ffmpeg6 output;
                    #   hacked workaround.
                    if abs(current) > duration:
                        current = 0
                    p_pct = int(round(current * 100 / duration, 0))
                    progressbar = get_progressbar(p_pct)
                    sys.stdout.write(progressbar)
                if config.VERBOSE:
                    # Only print most interesting progress attributes.
                    attribs = [
                        'frame',
                        'fps',
                        'total_size',
                        'out_time',
                        'speed',
                    ]
                    if k in attribs:
                        sys.stdout.write(text)
            q.task_done()
        q.task_done()

    def cleanup(threads, q):
        for t in threads:
            t.join()
        q.put(None)
        q.join()

    # Run ffmpeg command.
    try:
        with ffmpeg.run_async(
            output_stream,
            overwrite_output=True,
            pipe_stdout=True,
            pipe_stderr=True,
        ) as p:
            q_out = Queue()
            try:
                # Start progress queue & threads.
                t_out = Thread(name="T-stdout", target=read_output, args=(p.stdout, q_out))
                t_err = Thread(name="T-stderr", target=read_output, args=(p.stderr, q_out))
                t_write = Thread(name="T-write", target=write_output, args=(duration, q_out))
                for t in (t_out, t_err, t_write):
                    t.start()
                p.wait()
            except KeyboardInterrupt:
                print("\nInterrupted with Ctrl+C")
                p.kill()
                # Finish queue & progress bar.
                cleanup((t_out, t_err), q_out)
                sys.exit(130)
            # Finish queue & progress bar.
            cleanup((t_out, t_err), q_out)
    except ffmpeg._run.Error as e:
        print(e.stderr.decode('utf8'))
        exit(1)

    print()
