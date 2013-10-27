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

    # BUG: but why does the coroutine pipeline return a null terminated string!?
    # get a null terminated string every time... WTF
    def transcribeFrom(self, input):
        self.drain()
        decoder = self.get_decoder()
        for byte in input:
            decoder.send(byte)
        decoder.close()
        return self.getOutput()[:-1]

    def transcribeTo(self, input):
        self.drain()
        encoder = self.get_encoder()
        for byte in input:
            encoder.send(byte)
        encoder.close()
        return self.getOutput()

    # BUG: but why does the coroutine pipeline return a null terminated string!?
    def getOutput(self):
        data = "".join(self.output)
        if data[-1] == '\x00':
            print "got null tail"
            return data[:-1]
        return data

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
        circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        return

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeTo(data.read()))
        return


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

