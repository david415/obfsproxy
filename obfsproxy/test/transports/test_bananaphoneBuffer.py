#!/usr/bin/env python

import unittest
import twisted.trial.unittest

from obfsproxy.transports.bananaphone_transport import BananaPhoneBuffer

class test_BananaPhoneBuffer(twisted.trial.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.seed_str = 'the quick brown fox'
        cls.bananaBuffer = BananaPhoneBuffer()
        cls.result1 = cls.bananaBuffer.transcribeTo(cls.seed_str)

    def test_1(self):
        self.result2 = self.bananaBuffer.transcribeFrom(self.result1)
        self.assertEqual(self.result2, self.seed_str)

    def test_2(self):
        result3 = self.bananaBuffer.transcribeTo(self.seed_str)
        left = self.bananaBuffer.transcribeFrom(self.result1)
        right = self.bananaBuffer.transcribeFrom(result3)
        self.assertEqual(left, right)
        self.assertEqual(left, self.seed_str)

if __name__ == '__main__':
    unittest.main()

