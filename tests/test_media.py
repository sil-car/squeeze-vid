# import shutil
import unittest
from pathlib import Path

from squeeze_vid.app import get_parser
from squeeze_vid.media import MediaObject
from squeeze_vid.task import SqueezeTask

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase
VIDEO_FILE = Path(__file__).parent / 'data' / 'test_1.mp4'
AUDIO_FILE = Path(__file__).parent / 'data' / 'test_1.mp3'


class Command(unittest.TestCase):
    def setUp(self):
        self.infile = VIDEO_FILE
        self.media_in = MediaObject(self.infile)
        self.parser = get_parser()

    def test__command(self):
        args = self.parser.parse_args([str(self.infile), '-k', '1', '5', '-c'])
        task = SqueezeTask(args=args, media_in=self.media_in)
        command = task.trim()
        self.assertIsInstance(command, str)


class Conversion(unittest.TestCase):
    def setUp(self):
        self.audiofile = AUDIO_FILE
        self.videofile = VIDEO_FILE
        self.media_in_audio = MediaObject(self.audiofile)
        self.media_in_video = MediaObject(self.videofile)
        self.in_duration_audio = self.media_in_audio.duration
        self.in_duration_video = self.media_in_video.duration
        self.parser = get_parser()

    def test__change_speed_audio(self):
        factor = 15
        sfactor = float(factor)
        args = self.parser.parse_args([str(self.audiofile), '-s', str(factor)])
        task = SqueezeTask(args=args, media_in=self.media_in_audio)
        self.outfile = task.change_speed()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{sfactor}x.mp3'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertAlmostEqual(m_out.duration, self.in_duration_audio/factor, 0)

    def test__change_speed_video(self):
        factor = 10
        sfactor = float(factor)
        args = self.parser.parse_args([str(self.videofile), '-s', str(factor)])
        task = SqueezeTask(args=args, media_in=self.media_in_video)
        self.outfile = task.change_speed()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{sfactor}x.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertAlmostEqual(m_out.duration, self.in_duration_video/factor, 0)

    def test__export_audio(self):
        args = self.parser.parse_args(['-a', str(self.videofile)])
        task = SqueezeTask(args=args, media_in=self.media_in_video)
        self.outfile = task.export_audio()
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_a128kbps.mp3'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 0)

    def test__normalize_audio(self):
        args = self.parser.parse_args([str(self.audiofile)])
        task = SqueezeTask(args=args, media_in=self.media_in_audio)
        self.outfile = task.normalize()
        # shutil.copy(self.outfile, self.outfile.with_stem(f'{self.outfile.stem}b'))
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_a128kbps.mp3'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.acodec, 'mp3')
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 0)

    def test__normalize_video(self):
        args = self.parser.parse_args([str(self.videofile)])
        task = SqueezeTask(args=args, media_in=self.media_in_video)
        self.outfile = task.normalize()
        # shutil.copy(self.outfile, self.outfile.with_stem(f'{self.outfile.stem}b'))
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_crf27_25fps_a128kbps.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.vcodec, 'h264')
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 1)

    def test__normalize_av1(self):
        args = self.parser.parse_args([str(self.videofile), '--av1'])
        task = SqueezeTask(args=args, media_in=self.media_in_video)
        self.outfile = task.normalize()
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_crf42_25fps_a128kbps.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.vcodec, 'av1')
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 1)

    def test__trim_audio(self):
        i = '0:01'
        f = '0:20'
        d = '19'
        args = self.parser.parse_args([str(self.audiofile), '-k', i, f])
        task = SqueezeTask(args=args, media_in=self.media_in_audio)
        self.outfile = task.trim()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{float(d)}s.mp3'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertAlmostEqual(m_out.duration, float(d), 1)

    def test__trim_video(self):
        i = '1'
        f = '5'
        d = '4'
        args = self.parser.parse_args([str(self.videofile), '-k', i, f])
        task = SqueezeTask(args=args, media_in=self.media_in_video)
        self.outfile = task.trim()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{float(d)}s.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertAlmostEqual(m_out.duration, float(d), 1)

    def tearDown(self):
        try:
            self.outfile.unlink()
        except (FileNotFoundError, AttributeError):
            pass


class Media(unittest.TestCase):
    def setUp(self):
        self.infile_good = VIDEO_FILE
        self.infile_bad = VIDEO_FILE.with_stem('test_none')

    def test__file_does_not_exist(self):
        media_in = MediaObject(self.infile_bad)
        self.assertIsNone(media_in.suffix)

    def test__file_exists(self):
        media_in = MediaObject(self.infile_good)
        self.assertTrue(media_in.suffix)

    def tearDown(self):
        pass