import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python

from util import get_file_out
from util import parse_timestamp
from util import print_command
from util import run_conversion


class MediaObject():
    def __init__(self, infile=None):
        # Infile properties.
        self.file = infile
        self.suffix = None
        self.stream = None
        self.astreams = None
        self.vstreams = None
        self.props = None
        self.duration = None
        self.acodec = None
        self.abr = None
        self.vcodec = None
        self.height = None
        self.width = None
        self.vbr = None
        self.fps = None
        self.nb_frames = None
        self.format = None
        if self.file:
            self.suffix = self.file.suffix
            self.stream = ffmpeg.input(str(self.file))
            self.props = ffmpeg.probe(str(self.file))
            self.duration = float(self.props.get('format').get('duration'))
            self.astreams = [a for a in self.props.get('streams') if a.get('codec_type') == 'audio']
            self.acodec = self.astreams[0].get('codec_name')
            self.abr = int(self.astreams[0].get('bit_rate'))
            self.vstreams = [v for v in self.props.get('streams') if v.get('codec_type') == 'video']
            self.vcodec = self.vstreams[0].get('codec_name')
            self.height = int(self.vstreams[0].get('height'))
            self.width = int(self.vstreams[0].get('width'))
            self.vbr = int(self.vstreams[0].get('bit_rate'))
            avg_frame_rate = (self.vstreams[0].get('avg_frame_rate'))
            fpsn, fpsd = avg_frame_rate.split('/')
            self.fps = int(float(fpsn)/float(fpsd))
            self.nb_frames = int(self.vstreams[0].get('nb_frames'))
            self.format = self.props.get('format').get('format_name')


    def get_astreams(self, streams):
        if streams == 'placeholder':
            return [streams]
        else:
            return [a for a in streams if a.get('codec_type') == 'audio']

    def get_vstreams(self, streams):
        if streams == 'placeholder':
            return [streams]
        else:
            return [v for v in streams if v.get('codec_type') == 'video']

    def get_properties(self, file):
        if file == '<infile>':
            # Dummy file for printing command.
            return 'placeholder'
        try:
            probe = ffmpeg.probe(file)
        except ffmpeg._run.Error as e:
            print(f"Error: {e}\nNot an audio or video file?")
            exit(1)
        return probe

    def show_properties(self):
        for s in self.props.get('streams'):
            for k, v in s.items():
                skip = ['disposition', 'tags']
                if k in skip:
                    continue
                print(f"{k:<24} {v}")
            print()


def convert_file(show_cmd, media_in, action, media_out):
    """
    actions: 'change_speed', 'export_audio', 'normalize', 'trim'
    """
    # Set media_out attributes.
    media_out.stream = media_in.stream
    media_out.duration = media_in.duration
    media_out.abr = media_in.abr
    media_out.vbr = media_in.vbr
    media_out.fps = media_in.fps
    media_out.acodec = media_in.acodec
    media_out.vcodec = media_in.vcodec
    media_out.height = media_in.height
    media_in_formats = media_in.format.split(',')
    if len(media_in_formats) > 1:
        if 'mp3' in media_in_formats:
            media_out.format = 'mp3'
        elif 'mp4' in media_in_formats:
            media_out.format = 'mp4'
    else:
        media_out.format = media_in.format
    media_out.suffix = media_in.suffix
    if action == 'normalize':
        media_out = normalize_stream(media_in, media_out)
    video = media_out.stream.video
    audio = media_out.stream.audio
    # Add filters.
    if action == 'change_speed':
        # Add video filters.
        if video:
            video = ffmpeg.filter(video, 'setpts', f"{str(1 / media_out.factor)}*PTS")
        # Add audio filters.
        if audio:
            audio = ffmpeg.filter(audio, 'atempo', f"{str(media_out.factor)}")
        # Set media_out filename.
        media_out.file = get_file_out(media_in, action, media_out)
        media_out.duration = media_in.duration / media_out.factor
        # Create output stream.
        output_stream = build_output_stream(media_out, video, audio)
    elif action == 'export_audio':
        # TODO: Need an additional action in order to strip out audio.
        # if media_out.suffix == '.mp3':
        #     media_out.format = 'mp3'
        #     video = None
        pass
    elif action == 'normalize':
        # Add video filters.
        if video:
            # Define video max height.
            video = ffmpeg.filter(video, 'scale', -1, f"min({media_out.height}, ih)")
            # Define video max framerate.
            video = ffmpeg.filter(video, 'fps', media_out.fps)
        # Set media_out filename.
        media_out.file = get_file_out(media_in, action, media_out)
        # Create output stream.
        output_stream = build_output_stream(media_out, video, audio)
    elif action == 'trim':
        media_out.endpoints = [parse_timestamp(e) for e in media_out.endpoints]
        media_out.duration = media_out.endpoints[1] -  media_out.endpoints[0]
        # Set media_out filename.
        media_out.file = get_file_out(media_in, action, media_out)
        output_stream = ffmpeg.output(
            video, audio, str(media_out.file),
            **{'ss': media_out.endpoints[0]}, **{'to': media_out.endpoints[1]},
            **{'c:a': 'copy'}, **{'c:v': media_out.vcodec},
        )

    # Tweak stdout by updating kwargs of the existing output stream.
    output_stream.node.kwargs = {
        **output_stream.node.kwargs,
        "loglevel": "quiet",
        "stats": None,
        "progress": '-',
    }

    # Print command if desired.
    if show_cmd:
        print_command(output_stream)
        return
    # Run conversion.
    run_conversion(output_stream, media_out.duration)
    return media_out.file

def normalize_stream(media_in, media_out):
    # Determine audio attributes for media_out.
    if media_out.stream.audio:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_a
        media_out.suffix = media_out.suffix_norm_a
        # Determine vcodec for media_out.
        if media_in.acodec is not None:
            media_out.acodec = media_out.acodec_norm
        # Determine audio bitrate for media_out.
        if media_in.abr is not None:
            media_out.abr = media_out.abr_norm
            media_out.abr = min([media_in.abr, media_out.abr])
    # Determine video attributes for media_out.
    # if media_out.stream.video and type(media_out.stream.video[0]) is not str:
    if media_out.stream.video:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_v
        media_out.suffix = media_out.suffix_norm_v
        # Determine vcodec for media_out.
        if media_in.vcodec is not None:
            media_out.vcodec = media_out.vcodec_norm
        # Determine video bitrate for media_out.
        if media_in.vbr is not None:
            media_out.vbr = media_out.vbr_norm
            media_out.vbr = min([media_in.vbr, media_out.vbr])
        # Determine maxiumum frame rate for media_out.
        if media_in.fps is not None:
            media_out.fps = media_out.fps_norm
            media_out.fps = min([media_in.fps, media_out.fps])
        # Determine video height from first video stream in input file.
        if media_in.height is not None and media_in.width is not None:
            height_in = min([media_in.height, media_in.width]) # min in case of portrait orientation
            media_out.height = media_out.height_norm
            media_out.height = min([height_in, media_out.height])

    return media_out

def build_output_stream(media_out, video=None, audio=None):
    # Create output stream.
    if video and audio:
        output = ffmpeg.output(
            video, audio,
            str(media_out.file),
            vcodec=media_out.vcodec,
            video_bitrate=media_out.vbr,
            maxrate=media_out.vbr,
            bufsize=media_out.vbr/2,
            acodec=media_out.acodec,
            audio_bitrate=media_out.abr,
            format=media_out.format,
        )
    elif video and not audio:
        output = ffmpeg.output(
            video,
            str(media_out.file),
            vcodec=media_out.vcodec,
            video_bitrate=media_out.vbr,
            maxrate=media_out.vbr,
            bufsize=media_out.vbr/2,
            format=media_out.format,
        )
    elif not video and audio:
        output = ffmpeg.output(
            audio,
            str(media_out.file),
            # acodec=media_out.acodec, # -acodec gives error if using -f 'mp3'
            audio_bitrate=media_out.abr,
            format=media_out.format,
        )
    return output
