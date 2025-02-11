import unittest
import shutil
from pathlib import Path

from squeeze_vid.app import get_parser
from squeeze_vid.media import MediaObject
from squeeze_vid.media import SqueezeTask

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase
INFILE = Path(__file__).parent / 'data' / 'test_1.mp4'


class Command(unittest.TestCase):
    def setUp(self):
        self.infile = INFILE
        self.media_in = MediaObject(self.infile)
        self.parser = get_parser()

    def test__command(self):
        args = self.parser.parse_args([str(self.infile), '-k', '1', '5', '-c'])
        task = SqueezeTask(args=args, media_in=self.media_in)
        command = task.trim()
        self.assertIsInstance(command, str)


class Conversion(unittest.TestCase):
    def setUp(self):
        self.infile = INFILE
        self.media_in = MediaObject(self.infile)
        self.in_duration = self.media_in.duration
        self.parser = get_parser()

    def test__change_speed(self):
        factor = 10
        sfactor = float(factor)
        args = self.parser.parse_args([str(self.infile), '-s', str(factor)])
        task = SqueezeTask(args=args, media_in=self.media_in)
        self.outfile = task.change_speed()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{sfactor}x.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertAlmostEqual(m_out.duration, self.in_duration/factor, 0)

    def test__export_audio(self):
        args = self.parser.parse_args(['-a', str(self.infile)])
        task = SqueezeTask(args=args, media_in=self.media_in)
        self.outfile = task.export_audio()
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_a128kbps.mp3'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 0)

    def test__normalize(self):
        args = self.parser.parse_args([str(self.infile)])
        task = SqueezeTask(args=args, media_in=self.media_in)
        self.outfile = task.normalize()
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_crf27_25fps_a128kbps.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.vcodec, 'h264')
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 1)

    def test__normalize_av1(self):
        args = self.parser.parse_args([str(self.infile), '--av1'])
        task = SqueezeTask(args=args, media_in=self.media_in)
        self.outfile = task.normalize()
        m_out = MediaObject(self.outfile)

        expected_name = 'test_1_crf42_25fps_a128kbps.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.vcodec, 'av1')
        self.assertEqual(len(m_out.astreams), 1)
        self.assertEqual(len(m_out.vstreams), 1)

    def test__trim(self):
        i = '1'
        f = '5'
        d = str(float(f) - float(i))
        args = self.parser.parse_args([str(self.infile), '-k', '1', '5'])
        task = SqueezeTask(args=args, media_in=self.media_in)
        self.outfile = task.trim()
        m_out = MediaObject(self.outfile)

        expected_name = f'test_1_{d}s.mp4'
        actual_name = self.outfile.name

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(m_out.duration, 4.0)

    def tearDown(self):
        self.outfile.unlink()


class Media(unittest.TestCase):
    def setUp(self):
        self.infile_good = INFILE
        self.infile_bad = INFILE.with_stem('test_none')

    def test__file_does_not_exist(self):
        media_in = MediaObject(self.infile_bad)
        self.assertIsNone(media_in.suffix)

    def test__file_exists(self):
        media_in = MediaObject(self.infile_good)
        self.assertTrue(media_in.suffix)

    def tearDown(self):
        pass