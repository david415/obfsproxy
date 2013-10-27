#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from cocotools import cmap
from bananaphone import parseEncodingSpec, getMarkovModel, getModelEncoder, toBytes, changeWordSize, buildWeightedRandomModel, truncateHash, readTextFile

from scapy.all import hexdump



log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self):
        self.output_bytes     = Buffer()
        self.output_words     = Buffer()
        self.encodingSpec     = 'words,sha1,13'
        self.corpusFilename   = '/usr/share/dict/words'

        self.tokenize, self.hash, self.bits = parseEncodingSpec(self.encodingSpec)

        self.corpusTokens   = list( self.tokenize < readTextFile( self.corpusFilename ) )
        self.truncatedHash  = truncateHash(self.hash, self.bits)

        self.randomModel    = buildWeightedRandomModel(self.corpusTokens, self.truncatedHash)
        self.model          = getMarkovModel(self.randomModel, self.truncatedHash, self.corpusTokens, self.bits)

    def transcribeFrom(self, input):
        #print "transcribeFrom"
        decoder = self.get_decoder()
        for byte in input:
            #print "hex",
            #hexdump(byte)
            decoder.send(byte)
        decoder.close()
        #print "peek"
        #hexdump(self.output_bytes.peek())
        # BUG: wtf null terminated!?
        return self.output_bytes.read()[:-1]

    def transcribeTo(self, input):
        #print "transcribeTo"
        encoder = self.get_encoder()
        for byte in input:
            #print "hex"
            #hexdump(byte)
            encoder.send(byte)
        encoder.close()
        #print "peek"
        #hexdump(self.output_words.peek())
        return self.output_words.read()

    def wordSinkToList(self, input):
        self.output_words.write(input)

    def byteSinkToStream(self, input):
        assert len(input) == 1
        self.output_bytes.write(input)

    def get_decoder(self):
        return toBytes | self.tokenize | cmap( truncateHash( self.hash, self.bits ) ) | changeWordSize( self.bits, 8 ) | cmap( chr ) > self.byteSinkToStream

    def get_encoder(self):
        model_encoder = getModelEncoder(self.randomModel, self.model)
        return toBytes | cmap(ord) | changeWordSize(8, self.bits) | cmap(model_encoder) > self.wordSinkToList


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

