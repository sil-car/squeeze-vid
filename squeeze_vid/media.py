import json
import sys
from ffmpeg import errors
from ffmpeg import FFmpeg


class MediaObject():
    def __init__(self, infile=None):
        self.ffmpeg = FFmpeg()
        self.ffprobe = FFmpeg(executable='ffprobe')
        # Infile properties.
        self.file = infile
        self.suffix = None
        self.stream = None
        self.astreams = None
        self.vstreams = None
        self.has_audio = None
        self.has_video = None
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
        if self.file.is_file():
            self.suffix = self.file.suffix
            self.format = self.suffix
            self.props = self._get_properties(str(self.file))
            self.astreams = self._get_astreams(self.props.get('streams'))
            if len(self.astreams) > 0:
                self.has_audio = True
                if self.duration is None:
                    self.duration = float(self.astreams[0].get('duration'))
                self.acodec = self.astreams[0].get('codec_name')
                self.abr = int(self.astreams[0].get('bit_rate'))
            self.vstreams = self._get_vstreams(self.props.get('streams'))
            if len(self.vstreams) > 0:
                self.has_video = True
                if self.duration is None:
                    self.duration = float(self.vstreams[0].get('duration'))
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

    def show_properties(self):
        for s in self.props.get('streams'):
            for k, v in s.items():
                skip = ['disposition', 'tags']
                if k in skip:
                    continue
                print(f"{k:<24} {v}")
            print()

    def _get_astreams(self, streams) -> list:
        if streams == 'placeholder':
            return [streams]
        else:
            return [a for a in streams if a.get('codec_type') == 'audio']

    def _get_vstreams(self, streams) -> list:
        if streams == 'placeholder':
            return [streams]
        else:
            return [v for v in streams if v.get('codec_type') == 'video']

    def _get_properties(self, infile):
        if infile == '<infile>':
            # Dummy file for printing command.
            return 'placeholder'
        try:
            output = self.ffprobe.input(
                infile,
                show_streams=None,
                print_format='json'
            ).execute()
            probe = json.loads(output)
        except errors.FFmpegError as e:
            print(f"{e.message}; command: {e.arguments}")
            sys.exit(1)
        return probe

    def __str__(self):
        s = ''
        for k, v in dict(sorted(self.__dict__.items())).items():
            s += f"{k}: {v}\n"
        return s