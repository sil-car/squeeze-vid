import ffmpeg
import sys

from pathlib import Path
# https://docs.python.org/3/library/queue.html?highlight=queue#module-queue
from queue import Queue
from threading import Thread


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
    print(f"ffmpeg {' '.join(command)}\n")

def show_progress(duration, q):
    w = 60
    suffix = ''
    def show(c):
        p = int(w*c/100)
        print(f"[{u'█'*p}{('.'*(w-p))}]{suffix}", end='\r', file=sys.stdout, flush=True)

    show(0)
    while True:
        current = q.get()
        progress = int(round(current * 100 / duration, 0))
        show(progress)
        q.task_done()

def run_conversion(output_stream, duration):
    duration = float(duration)
    filepath = output_stream.node.kwargs.get('filename')
    print(filepath)

    # Start progress queue & thread.
    # NOTE: The surprise to me here is that the progress function is run in a
    #   thread, while the main subprocess runs in the foreground.
    q = Queue()
    t = Thread(target=show_progress, args=(duration, q), daemon=True)
    t.start()

    # Run ffmpeg command.
    try:
        with ffmpeg.run_async(
            output_stream,
            overwrite_output=True,
            pipe_stdout=True,
            pipe_stderr=True,
        ) as p:
            for line in p.stdout:
                k, v = line.decode('utf8').rstrip().split('=')
                if k == 'out_time_ms':
                    current = float(v) / 1000000 # convert to sec
                    q.put(current)
    except ffmpeg._run.Error as e:
        print(f"Error: {e}")
        exit(1)

    # Finish queue & progress bar.
    q.join()
    print()
