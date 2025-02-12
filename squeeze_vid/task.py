# import ffmpeg
import os
from pathlib import Path

from . import config
from .media import MediaObject
from .util import parse_timestamp
from .util import print_command
from .util import run_conversion


class SqueezeTask():
    def __init__(self, args=None, media_in=None):
        if args is not None:
            self.args = args
        if type(media_in) is MediaObject:
            self.media_in = media_in

        self.infile = self.media_in.file
        self.media_out = self.media_in
        self.media_out.file = Path(f"{self.media_in.file.parent}/{self.media_in.file.stem}_{self.media_out.suffix}")  # noqa: E501

        self.filters = {
            'audio': {},
            'video': {},
        }

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

    def change_speed(self) -> Path|str:
        self.media_out.factor = float(self.args.speed)
        self._setprops_change_speed()
        return self._run_task()

    def export_audio(self) -> Path|str:
        self.media_out.suffix = self.media_out.suffix_norm_a
        self._setprops_export_audio()
        return self._run_task()

    def normalize(self) -> Path|str:
        self._setprops_normalize()
        return self._run_task()

    def trim(self) -> Path|str:
        self.media_out.endpoints = self.args.trim
        self._setprops_trim()
        return self._run_task()

    def _run_task(self) -> Path|str:
        self._set_output_format()
        self._set_codecs()
        self._set_ffmpeg_command_args()
        self._set_ffmpeg_command_stream()
        return self._run_ffmpeg()

    def _run_ffmpeg(self) -> Path|str:
        if self.args.command:
            # Print command if desired.
            return print_command(self.ffmpeg_output_stream)
        run_conversion(self.media_out.ffmpeg, self.media_out.duration)
        return Path(self.media_out.file)

    def _set_codecs(self) -> None:
        if self.media_out.has_audio and not self.output_kwargs.get('c:a'):
            self.output_kwargs['c:a'] = self.media_out.acodec
        if self.media_out.has_video and not self.output_kwargs.get('c:v'):
            self.output_kwargs['c:v'] = self.media_out.vcodec

    def _set_ffmpeg_command_args(self) -> None:
        self.media_out.ffmpeg.input(self.infile)
        self.media_out.ffmpeg.option('y')
        # Modify command args according to variables.
        tile_col_exp = "1"  # 2**1 = 2 columns
        tile_row_exp = "1"  # 2**1 = 2 rows
        if config.VERBOSE:
            self.output_kwargs["loglevel"] = "verbose"
        if config.DEBUG:
            self.output_kwargs["loglevel"] = "debug"
        if config.FFMPEG_EXPERIMENTAL:
            self.output_kwargs["strict"] = "-2"

        if self.media_out.has_video:
            self.output_kwargs['crf'] = self.media_out.crf
            if self.media_out.mode == 'CBR':
                # Note: Some codecs require max vbr > target vbr.
                self.output_kwargs['video_bitrate'] = self.media_out.vbr - 1 if self.media_out.vbr > 0 else 0  # noqa: E501
                self.output_kwargs['maxrate'] = self.media_out.vbr
                self.output_kwargs['bufsize'] = self.media_out.vbr/2
                self.outfile_name_attribs.remove(f"crf{self.media_out.crf}")
                vbitrate = round(self.media_out.vbr/1000) if self.media_out.vbr is not None else 0  # noqa: E501
                self.outfile_name_attribs.insert(0, f"v{vbitrate}kbps")
            if self.media_out.vcodec == 'libx264':
                self.output_kwargs['profile:v'] = "high"
            if self.media_out.vcodec == 'libsvtav1':
                self.output_kwargs["svtav1-params"] = f"tile-columns={tile_col_exp}:tile-rows={tile_row_exp}:fast-decode=1"  # noqa: E501
            if self.media_out.vcodec == 'libvpx-vp9':
                self.output_kwargs['b:v'] = "0"
                self.output_kwargs["row-mt"] = "1"
                self.output_kwargs["cpu-used"] = str(min(int(len(os.sched_getaffinity(0))), 8))  # available proc count, max=8  # noqa: E501
                self.output_kwargs["tile-columns"] = tile_col_exp
                self.output_kwargs["tile-rows"] = tile_row_exp

    def _set_ffmpeg_command_stream(self) -> None:
        # Apply filters & create command stream.
        if self.media_out.has_video:
            filters_str = ''
            for k, vs in self.filters.get('video').items():
                f = f"{k}={':'.join((str(v) for v in vs))}"
                if filters_str:
                    f = f":{f}"
                filters_str += f"{f}"
            if filters_str:
                self.output_kwargs['vf'] = filters_str
        if self.media_out.has_audio:
            filters_str = ''
            for k, vs in self.filters.get('audio').items():
                f = f"{k}={':'.join((str(v) for v in vs))}"
                if filters_str:
                    f = f":{f}"
                filters_str += f"{f}"
            if filters_str:
                self.output_kwargs['af'] = filters_str

        specs_str = '_'.join(self.outfile_name_attribs)
        stem = self.media_out.file.stem.rstrip('_')  # removes extra '_' from above
        self.media_out.file = f"{self.media_out.file.parent}/{stem}_{specs_str}{self.media_out.suffix}"  # noqa: E501
        self.ffmpeg_output_stream = self.media_out.ffmpeg.output(
            self.media_out.file,
            **self.output_kwargs
        )

    def _set_output_format(self) -> None:
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

    def _setprops_change_speed(self) -> None:
        # Add filters.
        self.filters['audio']['atempo'] = [f"{str(self.media_out.factor)}"]
        self.filters['video']['setpts'] = [f"{str(1 / self.media_out.factor)}*PTS"]  # noqa: E501
        self.media_out.duration = self.media_in.duration / self.media_out.factor  # noqa: E501
        # Add attrib to final file name.
        self.outfile_name_attribs.append(f"{str(self.media_out.factor)}x")

    def _setprops_export_audio(self) -> None:
        self.media_out.has_video = False
        self.media_out = normalize_stream_props(
            self.media_in,
            self.media_out
        )
        abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0  # noqa: E501
        self.outfile_name_attribs.append(f"a{round(abitrate)}kbps")

    def _setprops_normalize(self) -> None:
        # Normalize media_out properties.
        self.media_out = normalize_stream_props(
            self.media_in,
            self.media_out
        )
        # Add video filters: Define video max height.
        if self.media_out.has_video:
            self.filters['video']['scale'] = [
                "trunc(oh*a/2)*2",
                rf"min({self.media_out.height}\,ih)",
            ]
            fps = round(self.media_out.fps, 2)
            self.output_kwargs['r'] = fps
            self.outfile_name_attribs.extend([
                f"crf{self.media_out.crf}",
                f"{fps}fps"
            ])
        if self.media_out.has_audio:
            abitrate = round(self.media_out.abr/1000) if self.media_out.abr is not None else 0  # noqa: E501
            self.outfile_name_attribs.append(f"a{abitrate}kbps")

    def _setprops_trim(self) -> None:
        self.media_out.endpoints = [parse_timestamp(e) for e in self.media_out.endpoints]  # noqa: E501
        self.media_out.duration = self.media_out.endpoints[1] - self.media_out.endpoints[0]  # noqa: E501
        self.output_kwargs['ss'] = self.media_out.endpoints[0]
        self.output_kwargs['to'] = self.media_out.endpoints[1]
        if self.media_out.has_audio:
            self.output_kwargs['c:a'] = 'copy'
        self.outfile_name_attribs.append(f"{self.media_out.duration}s")


def normalize_stream_props(media_in, media_out):
    # Determine audio attributes for media_out.
    if media_out.has_audio:
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
    if media_out.has_video:
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