import ffmpeg
# ffmpeg API: https://kkroening.github.io/ffmpeg-python
# ffmpeg Ex: https://github.com/kkroening/ffmpeg-python
import os

from pathlib import Path

from . import config

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
        # ffmpeg.Stream.audio and .video attribs are not modifiable. Must set
        # as variable, update those, then rebuild stream with ffmpeg.output().
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
                self.fps = float(fpsn)/float(fpsd) if fpsd != '0' else 0
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
        self.media_out.file = Path(f"{self.media_in.file.parent}/{self.media_in.file.stem}_{self.media_out.suffix}")  # noqa: E501

        # Set attribs based on input args.
        self.media_out.abr_norm = self.args.rates[0]
        self.media_out.vbr_norm = self.args.rates[1]
        self.media_out.fps_norm = self.args.rates[2]
        if self.args.rate_control_mode:
            if self.args.rate_control_mode.upper() in ['CBR', 'CRF']:
                self.media_out.mode = args.rate_control_mode
            else:
                print(f"Warning: rate control mode not recognized: {self.args.rate_control_mode}; falling back to CRF.")  # noqa: E501
        if self.args.video_encoder:
            self.media_out.vcodec_norm = self.args.video_encoder
        if self.args.av1:
            self.media_out.vcodec_norm = 'libsvtav1'
            self.media_out.vbr_norm = int(self.media_out.vbr_norm * 0.75)  # reduce b/c AV1 is more efficient  # noqa: E501

        self.outfile_name_attribs = []  # strings appended to name stem
        self.action = None
        self.output_args = [self.media_out.file]
        self.output_kwargs = {
            "profile:v": "high",
            "loglevel": "warning",
            "stats": None,
            "progress": '-',
        }

        self.media_out.crf_h264 = 27  # verified with SSIM on corporate-like content using ffmpeg-quality-metrics  # noqa: E501
        self.media_out.crf_svt_av1 = 42  # int((self.media_out.crf_h264 + 1) * 63 / 52) # interpolation  # noqa: E501
        self.media_out.crf_vpx_vp9 = 42  # int(self.media_out.crf_h264 * 63 / 52) # interpolation  # noqa: E501
        # CRF ranges: h264: 0-51 [23]; svt-av1: 1-63 [30]; vpx-vp9: 0-63
        self.media_out.crf = str(self.media_out.crf_h264)
        if self.media_out.vcodec_norm == 'libvpx-vp9':
            self.media_out.crf = str(self.media_out.crf_vpx_vp9)
        elif self.media_out.vcodec_norm == 'libsvtav1':
            self.media_out.crf = str(self.media_out.crf_svt_av1)
        self.output_kwargs['crf'] = self.media_out.crf

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
            filters['video']['setpts'] = [f"{str(1 / self.media_out.factor)}*PTS"]  # noqa: E501
            self.media_out.duration = self.media_in.duration / self.media_out.factor  # noqa: E501
            # Add attrib to final file name.
            self.outfile_name_attribs.append(f"{str(self.media_out.factor)}x")
        elif self.action == 'export_audio':
            self.media_out.video = None
            self.media_out = normalize_stream_props(
                self.media_in,
                self.media_out
            )
            del self.output_kwargs['crf']
            del self.output_kwargs['profile:v']
            abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0  # noqa: E501
            self.outfile_name_attribs.append(f"a{round(abitrate)}kbps")
        elif self.action == 'normalize':
            # Normalize media_out properties.
            self.media_out = normalize_stream_props(
                self.media_in,
                self.media_out
            )
            # Add video filters: Define video max height.
            filters['video']['scale'] = [
                "trunc(oh*a/2)*2",
                f"min({self.media_out.height}, ih)",
            ]
            # Define video max framerate.
            filters['video']['fps'] = [self.media_out.fps]
            abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0  # noqa: E501
            self.outfile_name_attribs.extend([
                f"crf{self.media_out.crf}",
                f"{round(self.media_out.fps, 2)}fps",
                f"a{abitrate}kbps"
            ])
        elif self.action == 'trim':
            self.media_out.endpoints = [parse_timestamp(e) for e in self.media_out.endpoints]  # noqa: E501
            self.media_out.duration = self.media_out.endpoints[1] - self.media_out.endpoints[0]  # noqa: E501
            self.output_kwargs['ss'] = self.media_out.endpoints[0]
            self.output_kwargs['to'] = self.media_out.endpoints[1]
            if self.media_out.audio is not None:
                self.output_kwargs['c:a'] = 'copy'
            self.outfile_name_attribs.append(f"{self.media_out.duration}s")

        # Set codecs.
        if self.media_out.audio is not None:
            self.output_kwargs['c:a'] = self.media_out.acodec
        if self.media_out.video is not None:
            self.output_kwargs['c:v'] = self.media_out.vcodec

        # Modify command args according to variables.
        tile_col_exp = "1"  # 2**1 = 2 columns
        tile_row_exp = "1"  # 2**1 = 2 rows
        if config.VERBOSE:
            self.output_kwargs["loglevel"] = "verbose"
        if config.DEBUG:
            self.output_kwargs["loglevel"] = "debug"
        if config.FFMPEG_EXPERIMENTAL:
            self.output_kwargs["strict"] = "-2"

        if self.media_out.mode == 'CBR':
            # Note: Some codecs require max vbr > target vbr.
            self.output_kwargs['video_bitrate'] = self.media_out.vbr - 1 if self.media_out.vbr > 0 else 0  # noqa: E501
            self.output_kwargs['maxrate'] = self.media_out.vbr
            self.output_kwargs['bufsize'] = self.media_out.vbr/2
            self.outfile_name_attribs.remove(f"crf{self.media_out.crf}")
            vbitrate = round(self.media_out.vbr/1000) if self.media_out.vbr is not None else 0  # noqa: E501
            self.outfile_name_attribs.insert(0, f"v{vbitrate}kbps")
        if self.media_out.vcodec != 'libx264':
            del self.output_kwargs['profile:v']  # remove irrelevant option
        if self.media_out.vcodec == 'libsvtav1':
            self.output_kwargs["svtav1-params"] = f"tile-columns={tile_col_exp}:tile-rows={tile_row_exp}:fast-decode=1"  # noqa: E501
        if self.media_out.vcodec == 'libvpx-vp9':
            self.output_kwargs['b:v'] = "0"
            self.output_kwargs["row-mt"] = "1"
            self.output_kwargs["cpu-used"] = str(min(int(len(os.sched_getaffinity(0))), 8))  # available proc count, max=8  # noqa: E501
            self.output_kwargs["tile-columns"] = tile_col_exp
            self.output_kwargs["tile-rows"] = tile_row_exp

        # Apply filters & create command stream.
        if self.media_out.video is not None:
            for k, vs in filters.get('video').items():
                self.media_out.video = ffmpeg.filter(
                    self.media_out.video,
                    k,
                    *vs
                )
            self.output_args.insert(0, self.media_out.video)  # index 0 is video, 1 is currently outfile  # noqa: E501
        if self.media_out.audio is not None:
            for k, vs in filters.get('audio').items():
                self.media_out.audio = ffmpeg.filter(
                    self.media_out.audio,
                    k,
                    *vs
                )
            self.output_args.insert(-2, self.media_out.audio)  # index 0 is video, 1 is audio, 2 is outfile  # noqa: E501
        specs_str = '_'.join(self.outfile_name_attribs)
        stem = self.media_out.file.stem.rstrip('_')  # removes '_' from earlier addition  # noqa: E501
        self.media_out.file = f"{self.media_out.file.parent}/{stem}_{specs_str}{self.media_out.suffix}"  # noqa: E501
        self.output_args[-1] = self.media_out.file  # replaces fallback outfile
        self.ffmpeg_output_stream = ffmpeg.output(
            *self.output_args,
            **self.output_kwargs
        )

    def run(self):
        if self.args.command:
            # Print command if desired.
            print_command(self.ffmpeg_output_stream)
            return
        run_conversion(self.ffmpeg_output_stream, self.media_out.duration)
        return Path(self.media_out.file)


def normalize_stream_props(media_in, media_out):
    # Determine audio attributes for media_out.
    if media_out.audio is not None:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_a
        media_out.suffix = media_out.suffix_norm_a
        # Determine vcodec for media_out.
        if media_in.acodec is not None:
            media_out.acodec = media_out.acodec_norm_a  # set for audio-only first  # noqa: E501
        # Determine audio bitrate for media_out.
        if media_in.abr is not None:
            media_out.abr = min([media_in.abr, media_out.abr_norm])
    # Determine video attributes for media_out.
    if media_out.video is not None:
        # Set file attributes for media_out.
        media_out.format = media_out.format_norm_v
        media_out.suffix = media_out.suffix_norm_v
        if media_in.acodec is not None:
            media_out.acodec = media_out.acodec_norm  # set for video; overwrite setting for audio-only  # noqa: E501
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
            height_in = min([media_in.height, media_in.width])  # min in case of portrait orientation  # noqa: E501
            media_out.height = min([height_in, media_out.height_norm])
    return media_out
