#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging

from cocotools import cmap
from bananaphone import parseEncodingSpec, getMarkovModel, getModelEncoder, toBytes, changeWordSize, buildWeightedRandomModel, truncateHash, readTextFile


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self):
        self.output         = []
        self.encodingSpec   = 'words,sha1,13'
        self.corpusFilename = '/usr/share/dict/words'

        self.tokenize, self.hash, self.bits = parseEncodingSpec(self.encodingSpec)

        self.corpusTokens   = list( self.tokenize < readTextFile( self.corpusFilename ) )
        self.truncatedHash  = truncateHash(self.hash, self.bits)

        self.randomModel    = buildWeightedRandomModel(self.corpusTokens, self.truncatedHash)
        self.model          = getMarkovModel(self.randomModel, self.truncatedHash, self.corpusTokens, self.bits)

    def transcribeFrom(self, input):
        self.drain()
        decoder = self.get_decoder()
        for byte in input:
            decoder.send(byte)
        decoder.close()
        return self.getOutput().rstrip("\0")

    def transcribeTo(self, input):
        self.drain()
        encoder = self.get_encoder()
        for byte in input:
            encoder.send(byte)
        encoder.close()
        return self.getOutput()

    def getOutput(self):
        return "".join(self.output)

    def drain(self):
        self.output = []

    def byteSinkToBuffer(self, input):
        self.output.append(input)

    def get_decoder(self):
        return toBytes | self.tokenize | cmap( truncateHash( self.hash, self.bits ) ) | changeWordSize( self.bits, 8 ) | cmap( chr ) > self.byteSinkToBuffer

    def get_encoder(self):
        model_encoder = getModelEncoder(self.randomModel, self.model)
        return toBytes | cmap(ord) | changeWordSize(8, self.bits) | cmap(model_encoder) > self.byteSinkToBuffer


class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):
        self.bananaBuffer = BananaPhoneBuffer()

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeTo(data.read()))

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeFrom(data.read()))


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

