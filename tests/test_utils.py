import unittest
from pathlib import Path

from squeeze_vid import util
from squeeze_vid.media import MediaObject

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class FileOut(unittest.TestCase):
    def setUp(self):
        self.infile = Path(__file__).parent / 'data' / 'test_1.mp4'
        self.media_in = MediaObject(self.infile)

    def test_get_file_out__convert_file(self):
        media_out = self.media_in
        media_out.vbr = 2000000
        media_out.abr = 128000
        media_out.fps = 25
        media_out.suffix = '.mp4'
        expected = 'test_1_v2000kbps_25fps_a128kbps.mp4'
        actual = util.get_file_out(self.media_in, 'convert_file', media_out).name
        self.assertEqual(expected, actual)

    def tearDown(self):
        pass
