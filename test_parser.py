# test_parser.py
import unittest
from pyais import decode

class TestAISParsing(unittest.TestCase):

    def test_valid_ais_sentence(self):
        sentence = "!AIVDM,1,1,,A,15Muq;001oG?tTpE>nD4p?vN0TKH,0*11"
        msg = decode(sentence)
        self.assertIsNotNone(msg)
        self.assertTrue(hasattr(msg, "lat"))
        self.assertTrue(hasattr(msg, "lon"))
        self.assertTrue(-90 <= msg.lat <= 90)
        self.assertTrue(-180 <= msg.lon <= 180)

    def test_invalid_checksum(self):
        sentence = "!AIVDM,1,1,,A,15Muq;001oG?tTpE>nD4p?vN0TKH,0*XX"
        msg = decode(sentence)
        self.assertIsNotNone(msg)  # It will still decode, just possibly incorrectly
        self.assertTrue(hasattr(msg, "mmsi"))

    def test_missing_fields(self):
        sentence = ""
        with self.assertRaises(Exception):
            decode(sentence).decode()

if __name__ == '__main__':
    unittest.main()
