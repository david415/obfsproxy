#!/usr/bin/env python

import unittest
import twisted.trial.unittest
from struct import pack

from obfsproxy.network.buffer import Buffer
from obfsproxy.transports.bananaphone import rh_encoder, rh_decoder

class test_Bananaphone(twisted.trial.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.encodingSpec = 'words,sha1,4'
        cls.modelName    = 'markov'
        cls.order        = 1
        cls.corpus       = '/usr/share/dict/words'
        cls.abridged     = None

    def writeEncodeBuffer(self, buff):
        self.encodeBuffer.write(buff)

    def writeDecodeBuffer(self, buff):
        self.decodeBuffer.write(buff)

    def test_1(self):
        self.encodeBuffer = Buffer()
        self.decodeBuffer = Buffer()

        if self.modelName == 'markov':
            args = [ self.corpus, self.order, self.abridged ]
        elif self.modelName == 'random':
            args = [ self.corpus ]

        self.encoder = rh_encoder(self.encodingSpec, self.modelName, *args) > self.writeEncodeBuffer
        self.decoder = rh_decoder(self.encodingSpec) > self.writeDecodeBuffer

        orig_message = 'War is peace. Freedom is slavery.  Ignorance is strength.'
        self.encoder.send(orig_message)
        encoded_message = self.encodeBuffer.read()
        self.decoder.send(encoded_message)
        self.assertEqual(orig_message, self.decodeBuffer.read())


if __name__ == '__main__':
    unittest.main()
