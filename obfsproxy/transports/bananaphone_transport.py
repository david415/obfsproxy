#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self):
        self.output_bytes     = Buffer()
        self.output_words     = Buffer()
        self.encodingSpec     = 'words,sha1,4'
        self.modelName        = 'markov'
        self.corpusFilename   = '/usr/share/dict/words'

        self.encoder = rh_encoder(self.encodingSpec, self.modelName, self.corpusFilename) > self.wordSinkToBuffer
        self.decoder = rh_decoder(self.encodingSpec) > self.byteSinkToBuffer

    def transcribeFrom(self, input):
        for byte in input:
            self.decoder.send(byte)
        return self.output_bytes.read()

    def transcribeTo(self, input):
        for byte in input:
            self.encoder.send(byte)
        return self.output_words.read()

    def wordSinkToBuffer(self, input):
        self.output_words.write(input)

    def byteSinkToBuffer(self, input):
        self.output_bytes.write(input)
 

class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):
        self.bananaBuffer = BananaPhoneBuffer()

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        return

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeTo(data.read()))
        return


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

