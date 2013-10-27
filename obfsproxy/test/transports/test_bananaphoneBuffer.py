#!/usr/bin/env python

import unittest
import twisted.trial.unittest
from struct import pack

from obfsproxy.transports.bananaphone_transport import BananaPhoneBuffer

from scapy.all import hexdump

class test_BananaPhoneBuffer(twisted.trial.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        #cls.seed_str = 'the quick brown fox the quick brown fox the quick brown fox the quick brown fox the quick brown fox'
        
        #cls.seed_str = '\xEF'
        cls.seed_str = '\xDE\xAD\x07\xBE\xEF'
        hexdump(cls.seed_str)

        #bytes = []
        #for i in range(255):
        #    bytes.append(chr(i))

        #cls.seed_str = "".join(bytes)
        #cls.seed_str = cls.seed_str.rstrip('\x00')

        cls.bananaBuffer = BananaPhoneBuffer()
        cls.result1 = cls.bananaBuffer.transcribeTo(cls.seed_str)

    def test_1(self):
        flip1 = self.bananaBuffer.transcribeTo(self.seed_str)
        self.assertTrue(flip1.endswith(' '))

    def test_2(self):
        result3 = self.bananaBuffer.transcribeTo(self.seed_str)
        left = self.bananaBuffer.transcribeFrom(self.result1)
        right = self.bananaBuffer.transcribeFrom(result3)
        self.assertEqual(left, right)

    def test_3(self):

        flip = self.bananaBuffer.transcribeTo(self.seed_str)

        flop = self.bananaBuffer.transcribeFrom(flip)

        print "flip"
        hexdump(flip)

        print "flop"
        hexdump(flop)

        print "seed_str"
        hexdump(self.seed_str)

        self.assertEqual(flop, self.seed_str)


if __name__ == '__main__':
    unittest.main()
