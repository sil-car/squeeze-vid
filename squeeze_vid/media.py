import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python

from pathlib import Path

from . import config

# from .util import get_file_out
from .util import parse_timestamp
from .util import print_command
from .util import run_conversion


class MediaObject():
    def __init__(self, infile=None):
        # Infile properties.
        self.file = infile
        self.suffix = None
        self.stream = None
        self.astreams = None
        self.vstreams = None
        # ffmpeg.Stream.audio and .video attribs are not modifiable. Must set as
        #   variable, update those, then rebuild stream with ffmpeg.output().
        self.audio = None
        self.video = None
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
        self.mode = 'CRF'
        self.acodec_norm = 'aac'
        self.vcodec_norm = 'libx264'
        self.height_norm = 720
        self.format_norm_a = 'mp3'
        self.suffix_norm_a = '.mp3'
        self.acodec_norm_a = 'mp3'
        self.format_norm_v = 'mp4'
        self.suffix_norm_v = '.mp4'
        if self.file:
            self.suffix = self.file.suffix
            self.stream = ffmpeg.input(str(self.file))
            self.props = self.get_properties(str(self.file))
            self.duration = float(self.props.get('format').get('duration'))
            self.astreams = self.get_astreams(self.props.get('streams'))
            if len(self.astreams) > 0:
                self.audio = self.stream.audio
                self.acodec = self.astreams[0].get('codec_name')
                self.abr = int(self.astreams[0].get('bit_rate'))
            self.vstreams = self.get_vstreams(self.props.get('streams'))
            if len(self.vstreams) > 0:
                self.video = self.stream.video
                self.vcodec = self.vstreams[0].get('codec_name')
                self.height = int(self.vstreams[0].get('height'))
                self.width = int(self.vstreams[0].get('width'))
                self.vbr = int(self.vstreams[0].get('bit_rate', 0))
                avg_frame_rate = (self.vstreams[0].get('avg_frame_rate'))
                fpsn, fpsd = avg_frame_rate.split('/')
                # TODO: fails for MP3s with album cover "video"
                # self.fps = int(float(fpsn)/float(fpsd)) if fpsd != '0' else 0
                self.fps = round(float(fpsn)/float(fpsd), 2) if fpsd != '0' else 0
                self.nb_frames = int(self.vstreams[0].get('nb_frames', 0))
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
            print(e.stderr.decode('utf8'))
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


class SqueezeTask():
    def __init__(self, args=None, media_in=None):
        if args is not None:
            self.args = args
        if type(media_in) is MediaObject:
            self.media_in = media_in

        self.media_out = self.media_in
        self.media_out.file = Path(f"{self.media_in.file.parent}/{self.media_in.file.stem}_{self.media_out.suffix}")

        # Set attribs based on input args.
        self.media_out.abr_norm = self.args.rates[0]
        self.media_out.vbr_norm = self.args.rates[1]
        self.media_out.fps_norm = self.args.rates[2]
        if self.args.rate_control_mode:
            if self.args.rate_control_mode in ['CBR', 'CRF']:
                self.media_out.mode = args.rate_control_mode
            else:
                print(f"Warning: rate control mode not recognized: {self.args.rate_control_mode}; falling back to CRF.")
        if self.args.video_encoder:
            self.media_out.vcodec_norm = self.args.video_encoder
        if self.args.av1:
            self.media_out.vcodec_norm = 'libsvtav1'
            self.media_out.vbr_norm = int(self.media_out.vbr_norm * 0.75) # reduce b/c AV1 is more efficient


        self.outfile_name_attribs = [] # strings appended to name stem
        self.action = None
        self.output_args = [self.media_out.file]
        self.output_kwargs = {
            "profile:v": "high",
            "loglevel": "warning",
            "stats": None,
            "progress": '-',
        }

        self.media_out.crf_h264 = 27 # verified with SSIM on corporate-like content using ffmpeg-quality-metrics
        self.media_out.crf_svt_av1 = int((self.media_out.crf_h264 + 1) * 63 / 52) # interpolation
        self.media_out.crf_vpx_vp9 = int(self.media_out.crf_h264 * 63 / 52) # interpolation
        # CRF ranges: h264: 0-51 [23]; svt-av1: 1-63 [30]; vpx-vp9: 0-63
        self.media_out.crf = str(self.media_out.crf_h264)
        if self.media_out.vcodec == 'libvpx-vp9':
            self.media_out.crf = str(self.media_out.crf_vpx_vp9)
        elif self.media_out.vcodec == 'libsvtav1':
            self.media_out.crf = str(self.media_out.crf_svt_av1)
        self.output_kwargs['crf'] = self.media_out.crf

        # if self.media_out.suffix == '.mp3':
        #     self.media_out.acodec = self.media_out.acodec_norm_a
        #     self.media_out.format = 'mp3'
        # elif len(media_in_formats) > 1:
        #     if 'mp3' in media_in_formats:
        #         self.media_out.format = 'mp3'
        #     elif 'mp4' in media_in_formats:
        #         self.media_out.format = 'mp4'
        # self.output_kwargs['format'] = self.media_out.format

    def setup(self):
        # actions: 'change_speed', 'export_audio', 'normalize', 'trim'
        filters = {
            'audio': {},
            'video': {},
        }

        # Set the output format.
        media_in_formats = self.media_in.format.split(',')
        if self.media_out.suffix == '.mp3':
            self.media_out.acodec = self.media_out.acodec_norm_a
            self.media_out.format = 'mp3'
        elif len(media_in_formats) > 1:
            if 'mp3' in media_in_formats:
                self.media_out.format = 'mp3'
            elif 'mp4' in media_in_formats:
                self.media_out.format = 'mp4'
        self.output_kwargs['format'] = self.media_out.format

        # Set properties and ffmpeg args depending on the action.
        if self.action == 'change_speed':
            # Add filters.
            filters['audio']['atempo'] = [f"{str(self.media_out.factor)}"]
            filters['video']['setpts'] = [f"{str(1 / self.media_out.factor)}*PTS"]
            self.media_out.duration = self.media_in.duration / self.media_out.factor
            # Add attrib to final file name.
            self.outfile_name_attribs.append(f"{str(self.media_out.factor)}x")
        elif self.action == 'export_audio':
            self.media_out.video = None
            self.media_out = normalize_stream_props(self.media_in, self.media_out)
            del self.output_kwargs['crf']
            del self.output_kwargs['profile:v']
            abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0
            self.outfile_name_attribs.append(f"a{round(abitrate)}kbps")
        elif self.action == 'normalize':
            # Normalize media_out properties.
            self.media_out = normalize_stream_props(self.media_in, self.media_out)
            # Add video filters: Define video max height.
            filters['video']['scale'] = [
                "trunc(oh*a/2)*2",
                f"min({self.media_out.height}, ih)",
            ]
            # Define video max framerate.
            filters['video']['fps'] = [self.media_out.fps]
            abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0
            self.outfile_name_attribs.extend([
                f"crf{self.media_out.crf}",
                f"{self.media_out.fps}fps",
                f"a{abitrate}kbps"
            ])
        elif self.action == 'trim':
            self.media_out.endpoints = [parse_timestamp(e) for e in self.media_out.endpoints]
            self.media_out.duration = self.media_out.endpoints[1] - self.media_out.endpoints[0]
            self.output_kwargs['ss'] = self.media_out.endpoints[0]
            self.output_kwargs['to'] = self.media_out.endpoints[1]
            if self.media_out.video is not None:
                self.output_kwargs['c:v'] = self.media_out.vcodec
            if self.media_out.audio is not None:
                self.output_kwargs['c:a'] = 'copy'
            self.outfile_name_attribs.append(f"{self.media_out.duration}s")

        # Modify command args according to variables.
        tile_col_exp = "1" # 2**1 = 2 columns
        tile_row_exp = "1" # 2**1 = 2 rows
        if config.VERBOSE:
            self.output_kwargs["loglevel"] = "verbose"
        if config.DEBUG:
            self.output_kwargs["loglevel"] = "debug"
        if config.FFMPEG_EXPERIMENTAL:
            self.output_kwargs["strict"] = "-2"

        if self.media_out.mode == 'CBR':
            # Note: Some codecs require max vbr > target vbr.
            self.output_kwargs['video_bitrate'] = self.media_out.vbr - 1 if self.media_out.vbr > 0 else 0
            self.output_kwargs['maxrate'] = self.media_out.vbr
            self.output_kwargs['bufsize'] = self.media_out.vbr/2
            self.outfile_name_attribs.remove(f"crf{self.media_out.crf}")
            vbitrate = round(self.media_out.vbr/1000) if self.media_out.vbr is not None else 0
            self.outfile_name_attribs.insert(0, f"v{vbitrate}kbps")
        if self.media_out.vcodec == 'libvpx-vp9':
            self.output_kwargs["row-mt"] = "1"
            self.output_kwargs["cpu-used"] = "8"
            self.output_kwargs["tile-columns"] = tile_col_exp
            self.output_kwargs["tile-rows"] = tile_row_exp
        if self.media_out.vcodec == 'libsvtav1':
            self.output_kwargs["svtav1-params"] = f"tile-columns={tile_col_exp}:tile-rows={tile_row_exp}:fast-decode=1"

        # Apply filters & create command stream.
        if self.media_out.video is not None:
            for k, vs in filters.get('video').items():
                self.media_out.video = ffmpeg.filter(self.media_out.video, k, *vs)
            self.output_args.insert(0, self.media_out.video) # index 0 is video, 1 is currently outfile
        if self.media_out.audio is not None:
            for k, vs in filters.get('audio').items():
                self.media_out.audio = ffmpeg.filter(self.media_out.audio, k, *vs)
            self.output_args.insert(-2, self.media_out.audio) # index 0 is video, 1 is audio, 2 is outfile
        specs_str = '_'.join(self.outfile_name_attribs)
        stem = self.media_out.file.stem.rstrip('_') # removes '_' from earlier addition
        self.media_out.file = f"{self.media_out.file.parent}/{stem}_{specs_str}{self.media_out.suffix}"
        self.output_args[-1] = self.media_out.file # replaces fallback outfile
        self.ffmpeg_output_stream = ffmpeg.output(*self.output_args, **self.output_kwargs)

    def run(self):
        if self.args.command:
            # Print command if desired.
            print_command(self.ffmpeg_output_stream)
            return
        run_conversion(self.ffmpeg_output_stream, self.media_out.duration)
        return Path(self.media_out.file)

# def convert_file(show_cmd, media_in, action, media_out):
#     """
#     actions: 'change_speed', 'export_audio', 'normalize', 'trim'
#     """
#     # Set media_out attributes.
#     media_out.stream = media_in.stream
#     media_out.astreams = media_in.astreams
#     media_out.audio = media_in.audio
#     media_out.vstreams = media_in.vstreams
#     media_out.video = media_in.video
#     media_out.duration = media_in.duration
#     media_out.abr = media_in.abr
#     media_out.vbr = media_in.vbr
#     media_out.fps = media_in.fps
#     media_out.nb_frames = media_in.nb_frames
#     media_out.acodec = media_in.acodec
#     media_out.vcodec = media_in.vcodec
#     media_out.height = media_in.height
#     media_out.width = media_in.width
#     media_in_formats = media_in.format.split(',')
#     media_out.crf_h264 = 27 # verified with SSIM on corporate-like content using ffmpeg-quality-metrics
#     media_out.crf_svt_av1 = int((media_out.crf_h264 + 1) * 63 / 52) # interpolation
#     media_out.crf_vpx_vp9 = int(media_out.crf_h264 * 63 / 52) # interpolation
#     # CRF ranges: h264: 0-51 [23]; svt-av1: 1-63 [30]; vpx-vp9: 0-63
#     media_out.crf = str(media_out.crf_h264)
#     if media_out.vcodec == 'libvpx-vp9':
#         media_out.crf = str(media_out.crf_vpx_vp9)
#     elif media_out.vcodec == 'libsvtav1':
#         media_out.crf = str(media_out.crf_svt_av1)
#     if media_out.suffix == '.mp3':
#         media_out.acodec = media_out.acodec_norm_a
#         media_out.format = 'mp3'
#     elif len(media_in_formats) > 1:
#         if 'mp3' in media_in_formats:
#             media_out.format = 'mp3'
#         elif 'mp4' in media_in_formats:
#             media_out.format = 'mp4'
#     else:
#         media_out.format = media_in.format
#     if media_out.suffix is None:
#         media_out.suffix = media_in.suffix

#     # Add filters.
#     output_stream = None
#     if action == 'change_speed':
#         # Add video filters.
#         if media_out.video is not None:
#             media_out.video = ffmpeg.filter(
#                 media_out.video,
#                 'setpts',
#                 f"{str(1 / media_out.factor)}*PTS"
#             )
#         # Add audio filters.
#         if media_out.audio is not None:
#             media_out.audio = ffmpeg.filter(
#                 media_out.audio,
#                 'atempo',
#                 f"{str(media_out.factor)}"
#             )
#         media_out.duration = media_in.duration / media_out.factor
#     elif action == 'export_audio':
#         media_out.video = None
#         media_out = normalize_stream_props(media_in, media_out)
#     elif action == 'normalize':
#         # Normalize media_out properties.
#         media_out = normalize_stream_props(media_in, media_out)
#         # Add video filters.
#         if media_out.video is not None:
#             # Define video max height.
#             media_out.video = ffmpeg.filter(
#                 media_out.video,
#                 'scale',
#                 "trunc(oh*a/2)*2",
#                 f"min({media_out.height}, ih)",
#             )
#             # Define video max framerate.
#             media_out.video = ffmpeg.filter(
#                 media_out.video,
#                 'fps',
#                 media_out.fps,
#             )
#     elif action == 'trim':
#         media_out.endpoints = [parse_timestamp(e) for e in media_out.endpoints]
#         media_out.duration = media_out.endpoints[1] -  media_out.endpoints[0]

#     # Set media_out filename.
#     media_out.file = get_file_out(media_in, action, media_out) # filename depends on action and properties
#     if action == 'trim': # output_stream depends on filename being set
#         if media_out.video is None and media_out.audio is not None:
#             output_stream = ffmpeg.output(
#                 media_out.audio,
#                 str(media_out.file),
#                 **{'ss': media_out.endpoints[0]},
#                 **{'to': media_out.endpoints[1]},
#                 **{'c:a': 'copy'},
#                 **{'c:v': media_out.vcodec},
#             )
#         if media_out.video is not None and media_out.audio is None:
#             output_stream = ffmpeg.output(
#                 media_out.video,
#                 str(media_out.file),
#                 **{'ss': media_out.endpoints[0]},
#                 **{'to': media_out.endpoints[1]},
#                 **{'c:a': 'copy'},
#                 **{'c:v': media_out.vcodec},
#             )
#         else: # surely there won't be a situation where both audio and video are None
#             output_stream = ffmpeg.output(
#                 media_out.video,
#                 media_out.audio,
#                 str(media_out.file),
#                 **{'ss': media_out.endpoints[0]},
#                 **{'to': media_out.endpoints[1]},
#                 **{'c:a': 'copy'},
#                 **{'c:v': media_out.vcodec},
#             )
#     if output_stream is None:
#         # Build output stream.
#         # output_stream = build_output_stream(media_out)
#         out_args = []
#         out_kwargs = {
#             'format': media_out.format,
#         }
#         if media_out.video is not None:
#             out_args.append(media_out.video)
#             out_kwargs['vcodec'] = media_out.vcodec
#             out_kwargs["crf"] = str(media_out.crf)
#             # # Note: Some codecs require max vbr > target vbr.
#             # out_kwargs['video_bitrate'] = media_out.vbr - 1 if media_out.vbr > 0 else 0
#             # out_kwargs['maxrate'] = media_out.vbr
#             # out_kwargs['bufsize'] = media_out.vbr/2
#         if media_out.audio is not None:
#             out_args.append(media_out.audio)
#             out_kwargs['acodec'] = media_out.acodec
#             out_kwargs['audio_bitrate'] = media_out.abr
#         out_args.append(str(media_out.file))
#         output_stream = ffmpeg.output(*out_args, **out_kwargs)

#     # Show debug details.
#     if config.DEBUG:
#         keys = list(media_out.__dict__.keys())
#         keys.sort()
#         print("Media_in vs Media_out:")
#         for k in keys:
#             print(f"  {k}: {media_in.__dict__.get(k)} | {media_out.__dict__.get(k)}")
#         print()

#     # Tweak stdout by updating kwargs of the existing output stream.
#     output_stream.node.kwargs = {
#         **output_stream.node.kwargs,
#         "loglevel": "warning",
#         "stats": None,
#         "progress": '-',
#     }

#     # Modify args according to variables.
#     tile_col_exp = "1" # 2**1 = 2 columns
#     tile_row_exp = "1" # 2**1 = 2 rows
#     if config.VERBOSE:
#         output_stream.node.kwargs["loglevel"] = "verbose"
#     if config.DEBUG:
#         output_stream.node.kwargs["loglevel"] = "debug"
#     if config.FFMPEG_EXPERIMENTAL:
#         output_stream.node.kwargs["strict"] = "-2"
#     if media_out.mode == 'CBR':
#         # Note: Some codecs require max vbr > target vbr.
#         output_stream.node.kwargs['video_bitrate'] = media_out.vbr - 1 if media_out.vbr > 0 else 0
#         output_stream.node.kwargs['maxrate'] = media_out.vbr
#         output_stream.node.kwargs['bufsize'] = media_out.vbr/2
#         del output_stream.node.kwargs['CRF']
#     # if media_out.vcodec == 'libaom-av1':
#     #     output_stream.node.kwargs["row-mt"] = "1"
#     #     output_stream.node.kwargs["cpu-used"] = "8"
#     #     output_stream.node.kwargs["tile-columns"] = tile_col_exp
#     #     output_stream.node.kwargs["tile-rows"] = tile_row_exp
#     if media_out.vcodec == 'libvpx-vp9':
#         output_stream.node.kwargs["row-mt"] = "1"
#         output_stream.node.kwargs["cpu-used"] = "8"
#         output_stream.node.kwargs["tile-columns"] = tile_col_exp
#         output_stream.node.kwargs["tile-rows"] = tile_row_exp
#     if media_out.vcodec == 'libsvtav1':
#         output_stream.node.kwargs["svtav1-params"] = f"tile-columns={tile_col_exp}:tile-rows={tile_row_exp}:fast-decode=1"

#     # Print command if desired.
#     if show_cmd:
#         print_command(output_stream)
#         return
#     # Run conversion.
#     run_conversion(output_stream, media_out.duration)
#     return media_out.file

def normalize_stream_props(media_in, media_out):
    # Determine audio attributes for media_out.
    if media_out.audio is not None:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_a
        media_out.suffix = media_out.suffix_norm_a
        # Determine vcodec for media_out.
        if media_in.acodec is not None:
            media_out.acodec = media_out.acodec_norm_a # set for audio-only first
        # Determine audio bitrate for media_out.
        if media_in.abr is not None:
            media_out.abr = min([media_in.abr, media_out.abr_norm])
    # Determine video attributes for media_out.
    if media_out.video is not None:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_v
        media_out.suffix = media_out.suffix_norm_v
        if media_in.acodec is not None:
            media_out.acodec = media_out.acodec_norm # set for video; overwrite setting for audio-only
        # Determine vcodec for media_out.
        if media_in.vcodec is not None:
            media_out.vcodec = media_out.vcodec_norm
        # Determine video bitrate for media_out.
        if media_in.vbr is not None:
            media_out.vbr = min([media_in.vbr, media_out.vbr_norm])
        # Determine maxiumum frame rate for media_out.
        if media_in.fps is not None:
            media_out.fps = min([media_in.fps, media_out.fps_norm])
        # Determine video height from first video stream in input file.
        if media_in.height is not None and media_in.width is not None:
            height_in = min([media_in.height, media_in.width]) # min in case of portrait orientation
            media_out.height = min([height_in, media_out.height_norm])
    return media_out

# def build_output_stream(media_out):
#     out_args = []
#     out_kwargs = {
#         'format': media_out.format,
#     }
#     if media_out.video is not None:
#         out_args.append(media_out.video)
#         out_kwargs['vcodec'] = media_out.vcodec
#         # Note: Some codecs require max vbr > target vbr.
#         out_kwargs['video_bitrate'] = media_out.vbr - 1 if media_out.vbr > 0 else 0
#         out_kwargs['maxrate'] = media_out.vbr
#         out_kwargs['bufsize'] = media_out.vbr/2
#     if media_out.audio is not None:
#         out_args.append(media_out.audio)
#         out_kwargs['acodec'] = media_out.acodec
#         out_kwargs['audio_bitrate'] = media_out.abr
#     out_args.append(str(media_out.file))
#     return ffmpeg.output(*out_args, **out_kwargs)
